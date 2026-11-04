# DanMan lead feeds

Free daily feeds of Utah building activity for DanMan Leads. They run on GitHub Actions, cost nothing and use no AI.

- **Planning agendas, all of Utah**: the Utah Public Notice Website (utah.gov/pmn) carries every city, town and county planning commission, council and design-review agenda. Each day the feed reads new agendas and packets and keeps the subdivisions, site plans, multifamily and commercial items, with the companies named.
- **Permits**: Salt Lake City (Accela portal), city permit map layers (ArcGIS), and the monthly permit PDF reports cities post.

Output: `data/latest.json` (rolling 45 days) and `data/YYYY-MM-DD.json` (each day's new items). DanMan Leads' Lead Finder and Permit Watch routines read `data/latest.json` first, before spending any web searches.

Rules: public pages only, robots.txt respected, about one request per second per site, identifying user agent, no logins or CAPTCHAs.

Add a source: edit `sources.json`. Run now: Actions → lead-feeds → Run workflow (`daily`, or `discover` to find more public bodies).
