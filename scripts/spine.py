#!/usr/bin/env python3
"""Replay every spine step and compare its terminal transcript with what the code really prints.

The spine is the course's one project, `globalbank`, kept as real files: one snapshot per step in
spine/<course>/<step>/project/. Each step's session.txt is the terminal pane a scene shows — `$ `
lines are commands, everything else is their output. Scenes import these files with Vite's `?raw`,
so a frame can only show what this script has verified.

  python3.12 scripts/spine.py            check every step (exit 1 on any difference)
  python3.12 scripts/spine.py --write    re-run every step and rewrite its session.txt / captures
  python3.12 scripts/spine.py start/03   only the steps whose path starts with an argument

Ported from spark-ecommerce-analytics' spine.py (itself python-expense-tracker's); what differs is
the platform's:

- There is no local Spark: no JVM, no jars, no compose services. A step's Python is CPython 3.12.15
  (databricks-connect 18.3 needs 3.12): the replay puts `python` → python3.12 first on PATH.
- Each step is replayed in a FIXED directory, $SPINE_ROOT/home/globalbank (default
  /tmp/globalbank-spine), shown as /home/ana/globalbank. {"venv": true} reuses one venv per
  requirements.txt, parked between steps, as in the Spark course.
- DATA IS GENERATED, NOT COMMITTED. {"generated": {...}} (or a list of them) names
  `python -m globalbank_sim` arguments; the step and every step after it on its chain replay with
  that data in landing/. A scene that shows a data file captures it (`capture`).
- THE WORKSPACE. {"workspace": true} replays against the owner's Databricks Free Edition workspace:
  DATABRICKS_HOST and DATABRICKS_TOKEN must be set (environment secrets, never committed), and the
  step fails rather than replaying without them. Every other step runs with them REMOVED, so a lab
  can never reach the workspace by accident. In a workspace step's transcript the real host is
  shown as https://globalbank.cloud.databricks.com and the real user as ana@globalbank.example,
  and the workspace and account ids as 1234567890123456 and 00000000-0000-4000-8000-000000000000 —
  normalised here, never in a scene.
- `volatile` also masks UUIDs and ISO timestamps (["ts"]): run ids, update ids and times change on
  every run against a live workspace. A scene READS such a value from the session.

Each step is replayed by ONE bash process, so `cd` and `source .venv/bin/activate` carry from command
to command as they do in a real terminal. A command followed by `>>> ` lines is an interactive session:
it is run in a pseudo-terminal and fed those lines.

THE SPINE IS CUMULATIVE. Every step is the step before it plus the changes it declares, and this
script fails a step whose project differs from its parent's anywhere it did not declare — so nothing
written for the platform is thrown away or edited silently. Each step.json says where it sits:

  {"first": true}               starts the chain
  {"from": "start/02-first",    continues that step; `changes` lists every path it adds, edits or
   "changes": ["job.py"]}       removes (a directory covers everything under it). A declared path
                                that did not change fails too: the list is the section's diff.
  {"lab": true}                 a standalone lab outside the chain: the real output a concept scene
                                shows (Course 1, and every full-scene detour)

step.json (other keys, all optional):
  {"venv": true}                start with the shared venv (requirements.txt) activated
  {"workspace": true}           needs the workspace (see above)
  {"capture": ["path", ...]}    files the session creates that a scene shows; saved to captured/
  {"project": "name"}           the folder's name (default globalbank): a lab is not the spine
  {"volatile": true}            output carries ids or timings that change every run: compared with
                                digits, hex, UUIDs and timestamps masked; or a list of only the
                                kinds to mask, e.g. ["uuid"], ["ts"] or ["digits"]
  {"setup": ["cmd", ...]}       run silently before the transcript (after the venv)
  {"mask": ["RUNNING|STOPPED"]} regexes of what legitimately changes between runs: masked when
                                comparing (a warehouse's state, a duration)
  {"generated": {"sf": 1, "from": "2026-10-01", "to": "2026-10-01", "only": ["card_auths"]}}
                                data this step adds to its chain's (see above)
"""
import hashlib
import json
import os
import pty
import re
import select
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / 'spine'
# Every output in the course is produced on this interpreter (COURSE-PLAN.md, "Versions, pinned").
PINNED = 'Python 3.12.15'
INTERPRETERS = ('python3.12',)
PREFIX = '/usr/local'
# Run outputs, the venv, and what materialize() puts in: never part of a step's snapshot.
IGNORED = {'__pycache__', '.venv', 'out', 'landing', '.databricks'}
SHOWN_HOME = '/home/ana'
PROJECT = 'globalbank'
SPINE_ROOT = Path(os.environ.get('SPINE_ROOT', '/tmp/globalbank-spine'))
SHOWN_HOST = 'https://globalbank.cloud.databricks.com'
SHOWN_USER = 'ana@globalbank.example'
SHOWN_WORKSPACE_ID = '1234567890123456'
SHOWN_ACCOUNT_ID = '00000000-0000-4000-8000-000000000000'
SHOWN_METASTORE_ID = '11111111-1111-4111-8111-111111111111'
SHOWN_NAME = 'Ana'
WORKSPACE_VARS = ('DATABRICKS_HOST', 'DATABRICKS_TOKEN')
TS = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?')
ANSI = re.compile(r'\x1b\[[0-9;?]*[@-~]|\x1b[=>]|\r')
MARK = '__SPINE_MARK__'
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def commands(session: str) -> list[tuple[str, list[str]]]:
    """Split a transcript into (command, REPL input lines) pairs."""
    out: list[tuple[str, list[str]]] = []
    for line in session.splitlines():
        if line.startswith('$ '):
            out.append((line[2:], []))
        elif out and (line.startswith('>>> ') or line == '>>>'):
            out[-1][1].append(line[4:])
        elif out and (line.startswith('... ') or line == '...'):
            # Python 3.13+'s REPL indents a block for you: typed WITHOUT the transcript's indentation.
            out[-1][1].append(line[4:].lstrip())
    return out


def repl(cwd: Path, env: dict, inputs: list[str], argv: list[str]) -> str:
    """Run an interactive command in a pty, type each input line, return the screen."""
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvpe(argv[0], argv, {**env, 'TERM': 'xterm-256color'})
    screen = b''

    def drain(timeout: float) -> None:
        nonlocal screen
        end = time.time() + timeout
        while time.time() < end:
            ready, _, _ = select.select([fd], [], [], 0.05)
            if ready:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    return
                if not chunk:
                    return
                screen += chunk
                end = time.time() + 1.0

    drain(30)
    for line in inputs:
        os.write(fd, line.encode() + b'\r')
        drain(30)
    for _ in range(300):
        if os.waitpid(pid, os.WNOHANG)[0]:
            break
        time.sleep(0.1)
    else:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
        screen += b'\n[the session did not exit: check the >>> lines in session.txt]'
    text = ANSI.sub('', screen.decode(errors='replace'))
    return '\n'.join(l.rstrip() for l in text.split('\n')).strip('\n')


def environment(home: Path, workspace: bool = False) -> dict:
    drop = ('VIRTUAL_ENV',) + (() if workspace else tuple(k for k in os.environ if k.startswith('DATABRICKS_')))
    # The authoring agent's own variables: the Databricks CLI notices CLAUDECODE / AI_AGENT and
    # prints an AI-tools hint that a learner's terminal never shows.
    agent = lambda k: k.startswith('CLAUDE') or k in ('AI_AGENT',)
    env = {k: v for k, v in os.environ.items() if k not in drop and not agent(k)}
    shim = SPINE_ROOT / 'bin'  # `python` is python3.12 inside a replay, as on the learner's machine
    shim.mkdir(parents=True, exist_ok=True)
    if not (shim / 'python').exists():
        (shim / 'python').symlink_to(shutil.which('python3.12') or '/usr/local/bin/python3.12')
    return {**env, 'HOME': str(home), 'NO_COLOR': '1', 'PYTHON_COLORS': '0', 'TERM': 'dumb', 'PS1': '',
            'PATH': f"{shim}:{env['PATH']}", 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            # A setup can call the repo's own plumbing (scripts/ws_reset.py) by absolute path.
            'SPINE_REPO': str(REPO),
            # The step's HOME would give pip an empty cache every step: keep the real one.
            'PIP_CACHE_DIR': os.environ.get('PIP_CACHE_DIR', str(Path.home() / '.cache' / 'pip'))}


@__import__('functools').cache
def workspace_identity() -> list[tuple[str, str]]:
    """(real, shown) pairs for a workspace step: the host, its workspace id, and the user."""
    import urllib.request
    host = os.environ['DATABRICKS_HOST'].rstrip('/')
    req = urllib.request.Request(f'{host}/api/2.0/preview/scim/v2/Me', headers={'Authorization': f"Bearer {os.environ['DATABRICKS_TOKEN']}"})
    me = json.load(urllib.request.urlopen(req, timeout=30))
    pairs = [(host, SHOWN_HOST), (host.removeprefix('https://'), SHOWN_HOST.removeprefix('https://')), (me['userName'], SHOWN_USER)]
    # A bundle in development mode prefixes names with the user's SHORT name: the email's local part
    # with every non-word character as `_` ("[dev jane_doe] globalbank_nightly").
    pairs.append((re.sub(r'\W', '_', me['userName'].split('@')[0]), SHOWN_USER.split('@')[0]))
    if me.get('displayName') and me['displayName'] != me['userName']:
        pairs.append((me['displayName'], SHOWN_NAME))
    # The workspace and account ids are not in the host: ask the CLI, which resolves them.
    described = subprocess.run(['databricks', 'auth', 'describe', '-o', 'json'], capture_output=True, text=True)
    config = json.loads(described.stdout)['details']['configuration'] if described.returncode == 0 else {}
    for key, shown in (('workspace_id', SHOWN_WORKSPACE_ID), ('account_id', SHOWN_ACCOUNT_ID)):
        if config.get(key, {}).get('value'):
            pairs.append((str(config[key]['value']), shown))
    # The metastore id appears in Unity Catalog errors (a quota refusal printed it).
    metastore = subprocess.run(['databricks', 'metastores', 'current', '-o', 'json'], capture_output=True, text=True)
    if metastore.returncode == 0:
        pairs.append((json.loads(metastore.stdout)['metastore_id'], SHOWN_METASTORE_ID))
    return pairs


def venv_key(project: Path) -> str:
    req = project / 'requirements.txt'
    if not req.exists():
        sys.exit(f'✗ {project}: "venv": true needs a requirements.txt')
    return hashlib.sha256(req.read_bytes()).hexdigest()[:16]


def replay(step: Path) -> tuple[str, dict[str, str]]:
    config = config_of(step)
    session = (step / 'session.txt').read_text()
    home = SPINE_ROOT / 'home'
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    project = home / config.get('project', PROJECT)
    if (step / 'project').exists():
        shutil.copytree(step / 'project', project)
    else:
        project.mkdir()
    workspace = bool(config.get('workspace'))
    if workspace and not all(os.environ.get(k) for k in WORKSPACE_VARS):
        sys.exit(f'✗ {step.relative_to(ROOT)} needs the workspace: set {" and ".join(WORKSPACE_VARS)} (CLAUDE.md, "The spine")')
    env = environment(home, workspace)
    materialize(step, project)
    parked = None
    if config.get('venv'):
        parked = SPINE_ROOT / 'venvs' / venv_key(project)
        if parked.exists():
            parked.rename(project / '.venv')
        else:
            subprocess.run(['python', '-m', 'venv', '.venv'], cwd=project, env=env, check=True)
            subprocess.run([str(project / '.venv/bin/pip'), 'install', '-q', '-r', 'requirements.txt'], cwd=project, env=env, check=True)
        env['PATH'] = f"{project / '.venv' / 'bin'}:{env['PATH']}"
        env['VIRTUAL_ENV'] = str(project / '.venv')
    try:
        for cmd in config.get('setup', []):
            r = subprocess.run(['bash', '-c', cmd], cwd=project, env=env, capture_output=True, text=True)
            if r.returncode:  # once more: an upload to the workspace can fail on a network blip
                time.sleep(10)
                r = subprocess.run(['bash', '-c', cmd], cwd=project, env=env, capture_output=True, text=True)
            if r.returncode:
                sys.exit(f'✗ {step.relative_to(ROOT)}: setup `{cmd}` failed:\n{r.stdout}{r.stderr}')
        cwd = project
        blocks: list[str] = []
        state = SPINE_ROOT / '.spine-state'
        state.unlink(missing_ok=True)
        for cmd, inputs in commands(session):
            if inputs:
                output = repl(cwd, env, inputs, shlex.split(cmd))
            else:
                script = f'cd {cwd!s}\n{{ {cmd}\n}} 2>&1\necho "{MARK}$PWD"\n'
                if state.exists():
                    script = state.read_text() + script
                r = subprocess.run(['bash', '-c', script + f'declare -p VIRTUAL_ENV PATH 2>/dev/null > {state}'],
                                   env=env, capture_output=True, text=True)
                output, _, after = r.stdout.partition(MARK)
                if after:
                    cwd = Path(after.split('\n')[0])
                output = output.rstrip('\n')
                if state.exists():
                    saved = state.read_text()
                    state.write_text(saved.replace('declare -x', 'export').replace('declare --', 'export') + '\n')
            blocks.append(f'$ {cmd}' + (f'\n{output}' if output else ''))
        transcript = '\n'.join(blocks)
        captured = {name: (project / name).read_text() for name in config.get('capture', [])}
    finally:
        if parked is not None and (project / '.venv').exists():
            parked.parent.mkdir(parents=True, exist_ok=True)
            if not parked.exists():
                (project / '.venv').rename(parked)
    pairs = [(str(home), SHOWN_HOME)] + (workspace_identity() if workspace else [])

    def fix(s: str) -> str:
        for real, shown in pairs:
            s = s.replace(real, shown)
        # A FRAGMENT of a real identifier survives replacement (a storage path cut to 40 columns
        # kept the account id's first 11 characters): refuse to write any transcript holding one.
        for real, _ in pairs[1:]:
            if len(real) >= 8 and not real.startswith('https://') and real[:8] in s:
                sys.exit(f'✗ {step.relative_to(ROOT)}: the transcript holds part of a real identifier (the one shown as {_!r}) — change the command, never commit it')
        return s
    return fix(transcript).rstrip('\n') + '\n', {k: fix(v) for k, v in captured.items()}


def masked(text: str, step: Path) -> str:
    """For a volatile step, hide what legitimately changes from run to run."""
    for pattern in config_of(step).get('mask', []):
        text = re.sub(pattern, '<masked>', text)
    kinds = config_of(step).get('volatile')
    if not kinds:
        return text
    kinds = {'uuid', 'ts', 'hex', 'digits'} if kinds is True else set(kinds)
    if 'ts' in kinds:
        text = TS.sub('<ts>', text)
    if 'uuid' in kinds:
        text = UUID.sub('<uuid>', text)
    if 'hex' in kinds:
        text = re.sub(r'0x[0-9a-f]+', '0x#', text)
    return re.sub(r'\d+(?:[.,]\d+)*', '#', text) if 'digits' in kinds else text


def config_of(step: Path) -> dict:
    return json.loads((step / 'step.json').read_text()) if (step / 'step.json').exists() else {}


def files(step: Path) -> dict[str, bytes]:
    """A step's project as {relative path: bytes}, without caches, the venv and run outputs."""
    root = step / 'project'
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob('*'))
        if p.is_file() and not IGNORED & set(p.relative_to(root).parts) and p.suffix != '.pyc'
    }


def lineage(step: Path) -> list[str]:
    """Why this step is not its parent plus its declared changes (empty when it is)."""
    name = step.relative_to(ROOT)
    config = config_of(step)
    kinds = [k for k in ('first', 'from', 'lab') if config.get(k)]
    if len(kinds) != 1:
        return [f'{name}: step.json needs exactly one of "first", "from", "lab" (has {kinds or "none"})']
    if 'from' not in kinds:
        return [f'{name}: "changes" only means something with "from"'] if config.get('changes') else []
    parent = ROOT / config['from']
    if not (parent / 'session.txt').exists():
        return [f'{name}: "from" names {config["from"]}, which is not a step']
    if config_of(parent).get('lab'):
        return [f'{name}: "from" names a lab, which is outside the chain']
    changes = config.get('changes') or []
    if not changes:
        return [f'{name}: "from" without "changes" — a step that changes nothing is not a section']
    under = lambda path, c: path == c or path.startswith(c.rstrip('/') + '/')
    covered = lambda path: any(under(path, c) for c in changes)
    before, after = files(parent), files(step)
    differs = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
    out = [f'{name}: {path} differs from {config["from"]} but is not in "changes"' for path in sorted(differs) if not covered(path)]
    out += [f'{name}: "changes" lists {c}, which did not change' for c in changes if not any(under(p, c) for p in differs)]
    return out


def same_generator(step: Path) -> list[str]:
    """A project's copy of globalbank_sim must be the repo's, byte for byte: the course shows the
    data `verify` checks, never a drifted copy."""
    copy = step / 'project' / 'globalbank_sim'
    if not copy.exists():
        return []
    ours = {p.relative_to(copy).as_posix(): p.read_bytes() for p in copy.rglob('*.py')}
    repo = {p.relative_to(REPO / 'globalbank_sim').as_posix(): p.read_bytes() for p in (REPO / 'globalbank_sim').rglob('*.py')}
    return [] if ours == repo else [f'{step.relative_to(ROOT)}: project/globalbank_sim differs from the repo\'s globalbank_sim — copy it again']


def lineage_of(step: Path) -> list[Path]:
    """The step and every ancestor through `from`, oldest first."""
    chain = [step]
    while config_of(chain[0]).get('from'):
        chain.insert(0, ROOT / config_of(chain[0])['from'])
    return chain


def data_specs(step: Path) -> list[dict]:
    """Every `generated` spec on the step's chain: data is inherited like code."""
    out = []
    for s in lineage_of(step):
        spec = config_of(s).get('generated')
        out += spec if isinstance(spec, list) else [spec] if spec else []
    return out


def run_logged(args: list[str], **kw) -> None:
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f'✗ `{" ".join(args)}` failed:\n{r.stdout}{r.stderr}')


def materialize(step: Path, project: Path) -> None:
    """Put the step's data into the replay project. It is never committed: landing/ is exactly what
    globalbank_sim writes for the chain's specs (generated once, cached by spec)."""
    for spec in data_specs(step):
        key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]
        cache = SPINE_ROOT / 'data' / key
        if not cache.exists():
            tmp = cache.with_suffix('.tmp')
            shutil.rmtree(tmp, ignore_errors=True)
            args = ['--sf', str(spec.get('sf', 1)), '--out', str(tmp)]
            args += [a for k in ('from', 'to') if k in spec for a in (f'--{k}', spec[k])]
            args += [a for t in spec.get('only', []) for a in ('--only', t)]
            run_logged([shutil.which('python3.12') or sys.executable, '-m', 'globalbank_sim', *args], cwd=REPO)
            tmp.rename(cache)
        shutil.copytree(cache, project / 'landing', dirs_exist_ok=True)


def preflight() -> str | None:
    for name in INTERPRETERS:
        probe = 'import sys, platform; print("Python " + platform.python_version(), sys.base_prefix)'
        try:
            version, _, prefix = subprocess.run([name, '-c', probe], capture_output=True, text=True).stdout.strip().partition(' /')
        except FileNotFoundError:
            version, prefix = '', ''
        prefix = '/' + prefix if prefix else ''
        if version != PINNED or prefix != PREFIX:
            return f'`{name}` is {version or "missing"} from {prefix or "?"}, not {PINNED} from {PREFIX}: run scripts/install-toolchain.sh'
    return None


def main() -> int:
    write = '--write' in sys.argv
    problem = preflight()
    if problem:
        print(f'✗ {problem}')
        return 1
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    every = sorted(p.parent for p in ROOT.glob('*/*/session.txt'))
    steps = [s for s in every if not only or any(str(s.relative_to(ROOT)).startswith(o) for o in only)]
    problems = 0
    # The chain is checked over EVERY step, whatever was asked for: a filtered run must not hide a
    # parent edited out from under its children.
    for problem in (p for s in every for p in lineage(s) + same_generator(s)):
        problems += 1
        print(f'✗ {problem}')
    if problems and write:
        print('✗ the chain or its data is broken: fix step.json or the snapshots before rewriting transcripts')
        return 1
    for step in steps:
        transcript, captured = replay(step)
        name = step.relative_to(ROOT)
        if write:
            (step / 'session.txt').write_text(transcript)
            for file, text in captured.items():
                target = step / 'captured' / file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            print(f'wrote {name}')
            continue
        expected = (step / 'session.txt').read_text()
        if masked(transcript, step) != masked(expected, step):
            problems += 1
            print(f'✗ {name}: the terminal pane differs from a real run')
            import difflib
            sys.stdout.writelines(difflib.unified_diff(expected.splitlines(True), transcript.splitlines(True), 'session.txt', 'real run'))
        for file, text in captured.items():
            if (step / 'captured' / file).read_text() != text:
                problems += 1
                print(f'✗ {name}: captured/{file} differs from a real run')
        print(f'{"✗" if problems else "✓"} {name}')
    if not write:
        print(f"{'✗' if problems else '✓'} {len(steps)} spine step(s) replayed, {problems} problem(s)")
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
