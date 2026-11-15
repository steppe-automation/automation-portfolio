"""Script 1: assign every voter to a council district by precinct and export one CSV per district.
Usage: python district_slice.py voters.csv precincts.shp districts.shp out/"""
import sys, pathlib
import geopandas as gpd, pandas as pd

voters_csv, precinct_shp, district_shp, out = sys.argv[1:5]
out = pathlib.Path(out); out.mkdir(exist_ok=True)
voters = pd.read_csv(voters_csv, dtype={"precinct": str})
prec = gpd.read_file(precinct_shp).to_crs(2913)          # Oregon North (ft)
dist = gpd.read_file(district_shp).to_crs(2913)
# precinct -> district by the precinct's interior point (robust for precincts touching a border)
pts = prec.copy(); pts["geometry"] = prec.representative_point()
lookup = gpd.sjoin(pts, dist[["district", "geometry"]], how="left", predicate="within")[["precinct", "district"]]
voters = voters.merge(lookup, on="precinct", how="left")
voters["gresham_or_unincorporated"] = voters["district"].eq("Gresham/Unincorporated")
unmatched = voters[voters["district"].isna()]
for name, grp in voters.dropna(subset=["district"]).groupby("district"):
    grp.to_csv(out / f"{name.replace('/', '_').replace(' ', '_')}.csv", index=False)
unmatched.to_csv(out / "UNMATCHED_check_these.csv", index=False)
print(voters["district"].value_counts(dropna=False).to_string())
print(f"unmatched: {len(unmatched)} (see UNMATCHED_check_these.csv)")
