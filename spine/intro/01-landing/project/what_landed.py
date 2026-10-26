"""What landed: for each source, its files, its records and the days it covers."""
from pathlib import Path

LANDING = Path('landing')

print(f'{"source":<12}{"files":>7}{"records":>10}  days')
for source in sorted(p for p in LANDING.iterdir() if p.is_dir()):
    files = [p for p in source.rglob('*') if p.is_file()]
    rows = sum(sum(1 for _ in f.open()) - (f.suffix == '.csv') for f in files)
    days = {s for f in files for s in (f.parent.name, f.stem[-10:])
            if s[:2] == '20'}
    span = f'{min(days)} → {max(days)}' if days else '—'
    print(f'{source.name:<12}{len(files):>7}{rows:>10,}  {span}')
