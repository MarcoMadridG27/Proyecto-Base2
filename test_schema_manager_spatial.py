import os
import shutil
import sys
sys.path.append(os.path.join(os.getcwd(), "core"))
from src.schema_manager import SchemaManager

def test_spatial_fallback():
    db_dir = "test_db_spatial"
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)
    os.makedirs(db_dir)

    sm = SchemaManager(db_dir)
    
    # Create table
    sm.create_table("places", [
        {"name": "id", "type": "int"},
        {"name": "name", "type": "VARCHAR[20]"},
        {"name": "lat", "type": "float"},
        {"name": "lon", "type": "float"}
    ])

    # Insert data
    # Center: 0,0
    # Point A: 1,1 (approx 1.41 dist)
    # Point B: 10,10 (far)
    sm.insert("places", {"id": 1, "name": "Center", "lat": 0.0, "lon": 0.0})
    sm.insert("places", {"id": 2, "name": "Near", "lat": 1.0, "lon": 1.0})
    sm.insert("places", {"id": 3, "name": "Far", "lat": 10.0, "lon": 10.0})

    print("Data inserted.")

    # Query: places within radius 2 of (0,0)
    # condition: "lat IN ([0,0], 2)" - wait, the regex expects "col IN ([x,y], r)"
    # The col name is just a placeholder for the spatial predicate if we use the regex in select_without_index
    # But wait, select_without_index parses: m = re.match(r"\s*([A-Za-z0-9_]+)\s+in\s*\(\s*\[?([^\]]+)\]?\s*,\s*([0-9\.]+)\s*\)\s*$", condition, re.I)
    # It extracts col, point, radius.
    # Then it uses _get_coordinates to find lat/lon columns in the record.
    # So 'col' in the predicate might be ignored for the actual coordinate lookup if _get_coordinates finds 'lat'/'lon'.
    
    condition = "location IN ([0, 0], 2.0)" 
    # 'location' is not a real column, but the spatial logic should handle it if _get_coordinates works.
    
    results = sm.select("places", ["name", "lat", "lon"], condition)
    print(f"Results for radius 2: {results}")

    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    names = sorted([r["name"] for r in results])
    assert names == ["Center", "Near"]

    # Query: radius 0.5
    condition = "location IN ([0, 0], 0.5)"
    results = sm.select("places", ["name"], condition)
    print(f"Results for radius 0.5: {results}")
    assert len(results) == 1
    assert results[0]["name"] == "Center"

    print("Spatial fallback test passed!")

if __name__ == "__main__":
    test_spatial_fallback()
