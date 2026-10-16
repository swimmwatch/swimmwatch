# Profile header automation

The `Update profile header` workflow runs daily at 03:17 UTC (06:17 Moscow)
and can also be started manually from GitHub Actions.

It refreshes `profile/top-langs.svg`, fetches public GitHub profile metrics,
regenerates all six `profile/banner-*.svg` variants, and commits the SVG files
to the default branch when their contents change. Animation and layout are
preserved. The README selects layout by width; its dark-default SVGs inherit
the page color scheme internally, so GitHub cannot discard width conditions
while applying its selected theme. Static light versions are also regenerated.
Repeat runs on the same day may produce no changes.

Public repository count and followers come from the user profile. Stars and
forks are summed across public repositories owned by the user, excluding forks.
The language chart describes repository code, not professional experience.

The renderer uses only the Python standard library. GitHub Actions supplies
the repository's `GITHUB_TOKEN`; no personal access token or extra secret is
required. API and commit failures fail the workflow instead of being hidden.

Run the local checks with:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
```

To refresh the banners locally, run
`python3 scripts/update-profile-stats.py swimmwatch`. The optional
`GITHUB_TOKEN` environment variable enables authenticated API requests.
