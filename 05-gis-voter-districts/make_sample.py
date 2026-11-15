"""Create synthetic test data (no real people): precincts, districts, voters, construction sites."""
import random
import geopandas as gpd
import pandas as pd
from shapely.geometry import box

random.seed(1)
x0, y0, w, h = -122.80, 45.42, 0.06, 0.04          # precinct grid near Portland, OR
precincts = gpd.GeoDataFrame(
    {"precinct": [f"P{r}{c}" for r in range(4) for c in range(6)]},
    geometry=[box(x0 + c * w, y0 + r * h, x0 + (c + 1) * w, y0 + (r + 1) * h) for r in range(4) for c in range(6)],
    crs="EPSG:4326")
xm, ym, xe = x0 + 2 * w, y0 + 2 * h, x0 + 4 * w      # 4 districts west of xe, Gresham/Unincorporated east
districts = gpd.GeoDataFrame(
    {"district": ["District 1", "District 2", "District 3", "District 4", "Gresham/Unincorporated"]},
    geometry=[box(x0, ym, xm, y0 + 4 * h), box(xm, ym, xe, y0 + 4 * h), box(x0, y0, xm, ym), box(xm, y0, xe, ym),
              box(xe, y0, x0 + 6 * w, y0 + 4 * h)], crs="EPSG:4326")
rows = []
for i in range(2000):
    p = precincts.sample(1, random_state=i).iloc[0]
    minx, miny, maxx, maxy = p.geometry.bounds
    rows.append({"voter_id": f"V{i:05d}", "name": f"Test Voter {i}", "precinct": p.precinct,
                 "lat": round(random.uniform(miny, maxy), 6), "lon": round(random.uniform(minx, maxx), 6)})
for j, (la, lo) in enumerate([(45.48, -122.70), (45.45, -122.55)] * 40):   # cluster near sites
    rows.append({"voter_id": f"N{j:04d}", "name": f"Near Voter {j}", "precinct": "P23" if lo > -122.6 else "P21",
                 "lat": round(la + random.uniform(-0.004, 0.004), 6), "lon": round(lo + random.uniform(-0.005, 0.005), 6)})
rows.append({"voter_id": "V99999", "name": "Bad Precinct", "precinct": "PXX", "lat": None, "lon": None})
pd.DataFrame(rows).to_csv("voters.csv", index=False)
precincts.to_file("precincts.shp"); districts.to_file("districts.shp")
pd.DataFrame([{"project": "Bridge Repair", "lat": 45.48, "lon": -122.70},
              {"project": "School Build", "lat": 45.45, "lon": -122.55}]).to_csv("construction_sites.csv", index=False)
print("sample data written")
