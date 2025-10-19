#!/usr/bin/env python3
"""
Script to build an RTree index in an isolated process.
Usage: build_rtree_index.py <data_dir> <table_name> <joined_key> <cols_csv>

This script imports the project's src modules by adding the core directory to sys.path.
It iterates records using SchemaManager._iter_with_offsets and inserts them into an RTree index.
"""
import sys
import os
import traceback

def main():
    if len(sys.argv) < 5:
        print("usage: build_rtree_index.py <data_dir> <table_name> <joined_key> <cols_csv> [start] [limit]")
        return 2

    data_dir = sys.argv[1]
    table = sys.argv[2]
    joined = sys.argv[3]
    cols_csv = sys.argv[4]
    cols = cols_csv.split(",") if cols_csv else [joined]
    start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    limit = int(sys.argv[6]) if len(sys.argv) > 6 else None

    # Ensure we can import 'src' by adding the core folder to sys.path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.dirname(script_dir)
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)

    try:
        from src.schema_manager import SchemaManager
        from src.dbms.rtree import RTree
    except Exception as e:
        print("Failed to import project modules:", e)
        traceback.print_exc()
        return 3

    try:
        mgr = SchemaManager(data_dir=data_dir)
        # Final index dir and a temporary working dir to build into
        index_dir = os.path.join(data_dir, f"idx_rtree", table, joined)
        tmp_dir = index_dir + f".tmp.{os.getpid()}"
        # ensure tmp dir is clean
        if os.path.exists(tmp_dir):
            try:
                import shutil
                shutil.rmtree(tmp_dir)
            except Exception:
                pass
        os.makedirs(tmp_dir, exist_ok=True)
        # Dimension guess
        dimension = 3 if len(cols) >= 3 else 2
        idx = RTree(table, joined, data_dir=tmp_dir, dimension=dimension)
        try:
            idx._columns = cols
        except Exception:
            pass

        # Use SchemaManager._iter_with_offsets to get offsets and records
        count = 0
        i = 0
        for off, rec in mgr._iter_with_offsets(table):
            if i < start:
                i += 1
                continue
            if limit is not None and (i - start) >= limit:
                break
            try:
                # Build key same as SchemaManager expects
                if hasattr(idx, "_columns") and len(idx._columns) > 1:
                    parts = [rec.get(c) for c in idx._columns]
                    if any(p is None for p in parts):
                        i += 1
                        continue
                    key = tuple(float(p) for p in parts)
                else:
                    colname = cols[0]
                    raw = rec.get(colname)
                    if raw is None:
                        i += 1
                        continue
                    if isinstance(raw, (list, tuple)):
                        key = tuple(float(x) for x in raw)
                    elif isinstance(raw, str):
                        s = raw.strip()
                        if s.startswith("[") and s.endswith("]"):
                            s = s[1:-1]
                        parts = [p.strip() for p in s.split(",") if p.strip()]
                        if len(parts) >= 2:
                            key = (float(parts[0]), float(parts[1]))
                        else:
                            i += 1
                            continue
                    else:
                        i += 1
                        continue

                idx.add(key, off)
                count += 1
                i += 1
                # occasionally flush/close and reopen to avoid large in-memory structures in libspatialindex
                if count % 2000 == 0:
                    try:
                        idx.close()
                    except Exception:
                        pass
                    idx = RTree(table, joined, data_dir=index_dir, dimension=dimension)
                    try:
                        idx._columns = cols
                    except Exception:
                        pass
            except Exception as e:
                # keep going; log
                print(f"[WARN] builder: failed to add record off={off}: {e}")
                i += 1
                continue

        try:
            idx.close()
        except Exception:
            pass

        # Move tmp_dir to final index_dir atomically (remove old index if present)
        try:
            import shutil
            if os.path.exists(index_dir):
                try:
                    shutil.rmtree(index_dir)
                except Exception:
                    pass
            shutil.move(tmp_dir, index_dir)
        except Exception as e:
            print(f"[WARN] could not move built index into place: {e}")
            # leave tmp_dir for manual inspection

        print(f"Built rtree index for {table}({joined}) inserted={count}")
        return 0

    except Exception as e:
        print("Builder failed:", e)
        traceback.print_exc()
        return 4

if __name__ == '__main__':
    sys.exit(main())
