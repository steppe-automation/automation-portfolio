# GIS voter district slicer (demo, synthetic data)

```bash
python make_sample.py
python district_slice.py voters.csv precincts.shp districts.shp out
python buffer_extract.py voters.csv construction_sites.csv out
```

- Script 1 joins voters to precincts and precincts to council districts (spatial join on the precinct interior point), adds a Gresham/Unincorporated flag, writes one CSV per district and an UNMATCHED file for rows to check.
- Script 2 projects to Oregon North (EPSG:2913, US feet) so 500 ft / 1,000 ft buffers are exact, and writes one CSV per site and radius.
- Tested: 2,081 synthetic voters, 1 bad-precinct row caught, buffer distances verified (max 411 ft in the 500 ft file).
