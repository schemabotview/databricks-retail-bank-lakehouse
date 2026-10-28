# Thumbnails

`film.png` — the thumbnail for the single full-course video (`scripts/out/film.mp4`).
A copy of `film-dark.png`. Rebuild every variant with:

```sh
npm run thumb:film -- --all
```

Variants kept for comparison: `film-dark.png` (shipped), `film-ember.png`,
`film-light.png`, and the two card sources — `film-medallion.png` (shipped) and
`film-terminal.png`.

## The card: the medallion, drawn from the real counts

Both cards show the **same numbers**, parsed out of one spine session
(`spine/pipeline/09-full-refresh/session.txt`, §7.9) — the row counts the workspace actually
returned. Neither is a retyped or invented figure, and `thumb-film.mjs` throws rather than
render if that session stops containing a bronze, a silver and a gold row.

The **terminal** card lists them as the session printed them. The **medallion** card draws them
as the arc the course builds: three coloured bands, bronze → silver → gold, each carrying its
layer's total. Where a layer has more than one table the band sums them and says so (silver is
`16,666 + 5,084 = 21,750`, labelled "2 tables").

The medallion ships, for one measured reason: **at the ~336px the mobile feed actually renders,
the terminal card communicates only "there is a terminal".** Its monospace rows turn to mush and
only the colour rhythm survives. The medallion's three bands stay legible at that size — you can
still read `bronze 16,797`, `silver 21,750`, `gold 5` and see the arrows between them — so the
cover says *raw → correct → ready* to someone scrolling, which is what the film is about.

`gold.card_spend_daily` really is 5 rows: that slice of the pipeline course aggregates to five
days. It looks small beside 16,797, and it is left alone — the cover shows the lakehouse the
course builds, not a better-looking one.

## The mark: ours, not Databricks'

The cover carries the **layers glyph** (lucide, ISC) — the mark the scenes already use for Delta
throughout, and literally what the card beside it shows.

It deliberately does **not** carry the Databricks logo or wordmark as a brand element.
"Databricks" appears as the headline because that is the accurate, nominative name of the thing
the course teaches, which is the use trademark law leaves open. The logo is a different
question: this is an independent course, a monetised channel is a commercial use, and nothing
here is produced or endorsed by Databricks. The sister repo
(`python-expense-tracker`) reached the same conclusion about the PSF logo and shipped its own
glyph; this repo starts there and never vendors the mark at all.

## Headline grammar

`LEARN` / `<CONCEPT>` / `FULL COURSE`, matching `python-expense-tracker` and
`spark-ecommerce-analytics`. The covers only read as one series if they rhyme, so the section
count and runtime live in the description (`output/film-description.txt`), not on the badge.
Override per build with `--head1`, `--head2`, `--badge`.
