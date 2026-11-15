"""Script 2: voters within 500 ft and 1,000 ft of each construction site, one CSV per site and radius.
Usage: python buffer_extract.py voters.csv construction_sites.csv out/"""
import sys, pathlib
import geopandas as gpd, pandas as pd

voters_csv, sites_csv, out = sys.argv[1:4]
out = pathlib.Path(out); out.mkdir(exist_ok=True)
v = pd.read_csv(voters_csv).dropna(subset=["lat", "lon"])
voters = gpd.GeoDataFrame(v, geometry=gpd.points_from_xy(v.lon, v.lat), crs=4326).to_crs(2913)
s = pd.read_csv(sites_csv)
sites = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326).to_crs(2913)
for feet in (500, 1000):
    zones = sites.copy(); zones["geometry"] = sites.buffer(feet)   # CRS units are US feet -> exact radius
    hits = gpd.sjoin(voters, zones[["project", "geometry"]], predicate="within")
    for project, grp in hits.groupby("project"):
        f = out / f"{project.replace(' ', '_')}_{feet}ft.csv"
        grp.drop(columns=["geometry", "index_right"]).to_csv(f, index=False)
        print(f"{project:15} {feet:>5} ft: {len(grp):4} voters -> {f.name}")
