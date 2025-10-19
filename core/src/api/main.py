from fastapi import FastAPI, UploadFile, File, Form
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import shutil
import csv
import time

from src.parser.executor import Executor
from src.schema_manager import SchemaManager
import pathlib
import datetime
import re


# Heuristic helpers for aligning CSV rows to headers
def infer_type_from_name(name: str):
    n = name.lower()
    if re.search(r"(^|_|-)id$|(^|_)observation_id$|(^|_)id($|_)", n) or n == 'id':
        return 'INT'
    if any(k in n for k in ('count', 'population', 'qty', 'number', 'num')):
        return 'INT'
    if any(k in n for k in ('lat', 'lon', 'latitude', 'longitude', 'weight', 'kg', 'length', 'm', 'size', 'depth')):
        return 'FLOAT'
    if 'date' in n or 'fecha' in n:
        return 'DATE'
    return 'VARCHAR[100]'

def token_type(tok: str):
    if tok is None or str(tok).strip() == '':
        return 'empty'
    t = str(tok).strip()
    if re.fullmatch(r"-?\d+", t):
        return 'int'
    if re.fullmatch(r"-?\d+\.\d+", t):
        return 'float'
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t) or re.fullmatch(r"\d{1,2}-\d{1,2}-\d{4}", t):
        return 'date'
    return 'text'

def align_row(headers, row):
    toks = [c for c in row]
    tt = [token_type(x) for x in toks]
    expected = [infer_type_from_name(h).lower() for h in headers]
    assigned = [None] * len(headers)
    used = [False] * len(toks)

    # 1) direct compatible assignment
    for i, (exp, tok, typ) in enumerate(zip(expected, toks, tt)):
        if typ == 'empty':
            assigned[i] = ''
            continue
        if (exp == 'int' and typ == 'int') or (exp == 'float' and typ in ('float', 'int')) or (exp == 'date' and typ == 'date') or exp.startswith('varchar'):
            assigned[i] = str(tok).strip()
            used[i] = True

    # 2) search nearby matching tokens for unassigned
    for i in range(len(headers)):
        if assigned[i] is not None and assigned[i] != '':
            continue
        exp = expected[i]
        for dist in range(1, min(6, len(toks))):
            found = False
            for sign in (-1, 1):
                j = i + sign * dist
                if 0 <= j < len(toks) and not used[j]:
                    typ = tt[j]
                    tok = toks[j]
                    if typ == 'empty':
                        continue
                    if exp == 'int' and typ == 'int':
                        assigned[i] = str(tok).strip(); used[j] = True; found = True; break
                    if exp == 'float' and typ in ('float', 'int'):
                        assigned[i] = str(tok).strip(); used[j] = True; found = True; break
                    if exp == 'date' and typ == 'date':
                        assigned[i] = str(tok).strip(); used[j] = True; found = True; break
                    if exp.startswith('varchar') and typ in ('text', 'int', 'float'):
                        assigned[i] = str(tok).strip(); used[j] = True; found = True; break
            if found:
                break

    # 3) assign remaining tokens in order
    ui = 0
    for i in range(len(headers)):
        if assigned[i] is None or assigned[i] == '':
            while ui < len(toks) and (used[ui] or tt[ui] == 'empty'):
                ui += 1
            if ui < len(toks):
                assigned[i] = str(toks[ui]).strip()
                used[ui] = True
                ui += 1
            else:
                assigned[i] = ''

    return {h: assigned[i] for i, h in enumerate(headers)}


def parse_simple_insert(sql: str):
    """Parse a very small subset of SQL INSERT: INSERT INTO tbl (c1,c2) VALUES (v1,v2)
    Returns (table, [cols], [vals]) or raises ValueError.
    This is intentionally lightweight and accepts single-row inserts only.
    """
    s = sql.strip().rstrip(';')
    m = re.match(r"insert\s+into\s+([A-Za-z0-9_]+)\s*\(([^\)]+)\)\s*values\s*\((.*)\)$", s, re.I)
    if not m:
        raise ValueError("SQL INSERT not recognized. Expected: INSERT INTO table (col,...) VALUES (val,...)")
    table = m.group(1)
    cols = [c.strip() for c in m.group(2).split(',')]
    raw_vals = m.group(3)
    # split values by comma but respecting quoted strings
    vals = []
    cur = ''
    inq = False
    qchar = None
    for ch in raw_vals:
        if ch in ("'", '"'):
            if not inq:
                inq = True; qchar = ch; cur += ch
                continue
            else:
                cur += ch
                if ch == qchar:
                    inq = False; qchar = None
                continue
        if ch == ',' and not inq:
            vals.append(cur.strip().strip("'\""))
            cur = ''
            continue
        cur += ch
    if cur.strip() != '':
        vals.append(cur.strip().strip("'\""))

    return table, cols, vals




# Inicializamos Executor: compute data_dir relative to this file so it works
# when the process cwd is the repository root.
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
CORE_ROOT = CURRENT_DIR.parent.parent  # core/src -> core
DATA_DIR = str(CORE_ROOT.joinpath("data"))
executor = Executor(data_dir=DATA_DIR)

app = FastAPI(
    title="Mini DB Backend",
    description="Proyecto BD2 - Motor de base de datos con índices",
    version="1.0"
)

# Configuración de CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes restringir a ["http://localhost:3000"] si prefieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# MODELOS
# -------------------------------
class QueryRequest(BaseModel):
    query: str
    use_index: bool  # Se añade el parámetro use_index
    index_hint: Optional[str] = None
    dry_run: Optional[bool] = False

class IndexRequest(BaseModel):
    index_type: str
    table_name: str
    column: Optional[str] = None  # prefer single-column name for non-spatial indexes
    columns: Optional[list] = None  # for spatial indexes, allow explicit columns list


class InsertRequest(BaseModel):
    table: Optional[str] = None
    columns: Optional[list] = None
    values: Optional[list] = None
    mapping: Optional[dict] = None
    sql: Optional[str] = None

# Endpoint to insert via mapping or simple SQL
@app.post('/insert')
def api_insert(req: InsertRequest):
    """Insert a single row via JSON mapping or a simple SQL INSERT string.

    Examples:
      { "mapping": {"id": 1, "name": "Foo"}, "table": "cities" }
      { "sql": "INSERT INTO cities (id, name) VALUES (1, 'Foo')" }
    """
    try:
        if req.mapping:
            if not req.table:
                return {"ok": False, "error": "Provide table name when sending mapping"}
            executor.schema_manager.insert(req.table, req.mapping)
            return {"ok": True, "message": "Row inserted (mapping)"}

        if req.sql:
            try:
                table, cols, vals = parse_simple_insert(req.sql)
            except Exception as e:
                return {"ok": False, "error": str(e)}
            # build mapping
            mapping = {c: v for c, v in zip(cols, vals)}
            executor.schema_manager.insert(table, mapping)
            return {"ok": True, "message": "Row inserted (SQL)", "table": table, "cols": cols}

        return {"ok": False, "error": "Provide either mapping or sql in body"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

# -------------------------------
# ENDPOINTS
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "message": "Backend running!"}

@app.post("/query")
async def run_query(request: Request):
    # Read raw body to tolerate different frontend key names
    try:
        body = await request.json()
    except Exception:
        body = {}

    def _get_bool(keys, default=False):
        for k in keys:
            if k in body:
                v = body.get(k)
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    return v.lower() in ('1', 'true', 'yes', 'on')
                try:
                    return bool(int(v))
                except Exception:
                    return default
        return default

    # normalize expected fields from various frontends
    use_index = _get_bool(['use_index', 'useIndex', 'with_index', 'withIndex'])
    dry_run = _get_bool(['dry_run', 'dryRun'])
    index_hint = body.get('index_hint') or body.get('indexHint') or None
    query_text = body.get('query') or body.get('sql') or ''

    print(f"Query recibida (raw): {body} | Normalized: query='{query_text}' use_index={use_index} index_hint={index_hint} dry_run={dry_run}")

    try:
        result = None
        execution_time = None

        start_time = time.time()
        result = executor.execute(query_text, use_index=use_index, index_hint=index_hint, dry_run=dry_run)
        execution_time = time.time() - start_time

        # Special-case: executor returned a dry-run / executed flag
        if isinstance(result, dict) and (('executed' in result) or ('dry_run' in result)):
            resp = {
                "ok": True,
                "result": result.get("result"),
                "execution_time": execution_time,
                "executed": bool(result.get("executed", True)),
                "dry_run": bool(result.get("dry_run", False)),
            }
            if isinstance(result.get('dry_count'), int):
                resp['dry_count'] = result.get('dry_count')
            return resp

        if isinstance(result, dict) and "result" in result and "used_index" in result:
            resp = {
                "ok": True,
                "result": result["result"],
                "used_index": result["used_index"],
                "index_warning": result.get("index_warning"),
                "execution_time": execution_time,
            }
            if isinstance(result.get('dry_count'), int):
                resp['dry_count'] = result.get('dry_count')
            if "used_index_type" in result:
                resp["used_index_type"] = result["used_index_type"]
            if "used_index_columns" in result:
                resp["used_index_columns"] = result["used_index_columns"]
            if isinstance(result.get('executed'), bool):
                resp['executed'] = result.get('executed')
            if isinstance(result.get('dry_run'), bool):
                resp['dry_run'] = result.get('dry_run')
            return resp

        return {"ok": True, "result": result, "execution_time": execution_time}

    except Exception as e:
        print(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), table_name: str = Form("uploaded_table"), force_varchar: bool = Form(False), overwrite: bool = Form(False)):
    """
    Sube un CSV, lo guarda como tabla en el motor y queda persistido en catalog.json
    """
    try:
        os.makedirs("data", exist_ok=True)
        save_path = os.path.join("data", file.filename)

        # Guardar archivo CSV en disco
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        headers = []
        rows = []
        all_data = []
        record_count = 0

        # Leer el CSV: detectar delimitador (comma/tsv/semicolon) y soportar archivos TSV
        with open(save_path, newline='', encoding="utf-8") as csvfile:
            sample = csvfile.read(2048)
            csvfile.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[',', '\t', ';', '|'])
            except Exception:
                dialect = csv.get_dialect('excel')

            reader = csv.reader(csvfile, dialect)
            try:
                headers = next(reader)  # primera fila = cabeceras
            except StopIteration:
                headers = []

            for i, row in enumerate(reader):
                all_data.append(row)
                if i < 10:  # preview
                    rows.append(row)
                record_count = i + 1

            # Normalizar headers: map accents to ASCII, replace spaces/special chars with
            # underscores and lowercase everything.
            import unicodedata

            def normalize_col_name(s: str) -> str:
                # strip, lowercase
                s = (s or '').strip()
                # normalize unicode (decompose accents)
                s = unicodedata.normalize('NFKD', s)
                # drop non-ascii diacritics
                s = s.encode('ascii', 'ignore').decode('ascii')
                # replace any non-alphanumeric by underscore
                s = re.sub(r"[^0-9A-Za-z]+", '_', s)
                # collapse multiple underscores
                s = re.sub(r"_+", '_', s)
                s = s.strip('_').lower()
                if s == '':
                    s = 'col'
                return s

            clean_headers = [normalize_col_name(col) for col in headers]

            # Infer types by simple, deterministic rules applied to a sample of rows:
            # - If any non-empty sample contains a decimal point -> FLOAT
            # - Else if all non-empty samples are integer digits -> INT
            # - Else -> VARCHAR[100]
            SAMPLE_N = min(200, len(all_data))
            samples = all_data[:SAMPLE_N]

            def infer_type_from_samples(col_idx: int):
                non_empty_tokens = []
                for r in samples:
                    try:
                        tok = r[col_idx]
                    except Exception:
                        tok = ''
                    if tok is None:
                        continue
                    tok = str(tok).strip()
                    if tok == '':
                        continue
                    non_empty_tokens.append(tok)

                if len(non_empty_tokens) == 0:
                    # fallback: generic varchar
                    return 'VARCHAR[100]'

                # If any token has a decimal point -> FLOAT
                for t in non_empty_tokens:
                    if '.' in t:
                        # ensure it is numeric-like
                        if re.fullmatch(r"-?\d+\.\d+", t):
                            return 'FLOAT'

                # If all tokens are integer digits -> INT
                all_int = True
                for t in non_empty_tokens:
                    if not re.fullmatch(r"-?\d+", t):
                        all_int = False
                        break
                if all_int:
                    return 'INT'

                return 'VARCHAR[100]'

            columns_def = []
            for i, col in enumerate(clean_headers):
                try:
                    ctype = infer_type_from_samples(i)
                except Exception:
                    ctype = 'VARCHAR[100]'
                # ensure type is one of INT, FLOAT, or VARCHAR[...]
                if isinstance(ctype, str) and ctype.upper() == 'INT':
                    final_type = 'INT'
                elif isinstance(ctype, str) and ctype.upper() == 'FLOAT':
                    final_type = 'FLOAT'
                else:
                    final_type = 'VARCHAR[100]'
                columns_def.append({"name": col, "type": final_type})

            # Helper: infer token type
            def token_type(tok: str):
                if tok is None or tok.strip() == '':
                    return 'empty'
                t = tok.strip()
                # int
                if re.fullmatch(r"-?\d+", t):
                    return 'int'
                # float
                if re.fullmatch(r"-?\d+\.\d+", t):
                    return 'float'
                # date-ish YYYY-MM-DD or DD-MM-YYYY
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t) or re.fullmatch(r"\d{1,2}-\d{1,2}-\d{4}", t):
                    return 'date'
                return 'text'

            # Align a single row to headers using expected types
            def align_row(headers, row):
                # token types
                toks = [c for c in row]
                tt = [token_type(x) for x in toks]
                expected = [infer_type_from_name(h).lower() for h in headers]
                # map: None means unassigned
                assigned = [None] * len(headers)
                used = [False] * len(toks)

                # 1) try direct compatible assignment
                for i, (exp, tok, typ) in enumerate(zip(expected, toks, tt)):
                    if typ == 'empty':
                        assigned[i] = ''
                        used[i] = False
                        continue
                    if (exp == 'int' and typ == 'int') or (exp == 'float' and typ in ('float', 'int')) or (exp == 'date' and typ == 'date') or exp.startswith('varchar') or exp == 'date':
                        assigned[i] = tok.strip()
                        used[i] = True

                # 2) fill missing by searching nearby matching tokens
                for i in range(len(headers)):
                    if assigned[i] is not None and assigned[i] != '':
                        continue
                    exp = expected[i]
                    # search window
                    for dist in range(1, min(6, len(toks))):
                        for sign in (-1, 1):
                            j = i + sign * dist
                            if 0 <= j < len(toks) and not used[j]:
                                typ = tt[j]
                                tok = toks[j]
                                if typ == 'empty':
                                    continue
                                if exp == 'int' and typ == 'int':
                                    assigned[i] = tok.strip(); used[j] = True; break
                                if exp == 'float' and typ in ('float', 'int'):
                                    assigned[i] = tok.strip(); used[j] = True; break
                                if exp == 'date' and typ == 'date':
                                    assigned[i] = tok.strip(); used[j] = True; break
                                if exp.startswith('varchar') and typ in ('text', 'int', 'float'):
                                    assigned[i] = tok.strip(); used[j] = True; break
                        if assigned[i] is not None:
                            break

                # 3) assign remaining unused tokens in order
                ui = 0
                for i in range(len(headers)):
                    if assigned[i] is None or assigned[i] == '':
                        # find next unused token
                        while ui < len(toks) and (used[ui] or tt[ui] == 'empty'):
                            ui += 1
                        if ui < len(toks):
                            assigned[i] = toks[ui].strip()
                            used[ui] = True
                            ui += 1
                        else:
                            assigned[i] = ''

                return {h: assigned[i] for i, h in enumerate(headers)}

        # --- Crear tabla solo si no existe ---
        if table_name in executor.schema_manager.tables:
            if overwrite:
                # drop and recreate
                try:
                    # remove data file and indexes
                    datafile = os.path.join('data', f"{table_name}.dat")
                    if os.path.exists(datafile):
                        os.remove(datafile)
                except Exception:
                    pass
                try:
                    # remove indexes dir (use module-level shutil)
                    idx_base = os.path.join('data')
                    for d in os.listdir(idx_base):
                        if d.startswith('idx_'):
                            p = os.path.join(idx_base, d, table_name)
                            if os.path.exists(p):
                                shutil.rmtree(p)
                except Exception:
                    pass
                # allow recreation
            else:
                return JSONResponse(
                    content={"ok": False, "error": f"La tabla '{table_name}' ya existe."},
                    status_code=400
                )

        # if force_varchar requested, set schema to VARCHAR for all columns
        if force_varchar:
            columns_def = [{"name": col, "type": 'VARCHAR[100]'} for col in clean_headers]
        else:
            executor_schema = columns_def
            columns_def = columns_def

        executor.schema_manager.create_table(table_name, columns_def)

        inserted = 0
        failed = 0
        # reset pack error counter for this upload
        try:
            from src.record import reset_pack_errors, get_pack_errors
            reset_pack_errors()
        except Exception:
            pass

        # Insertar cada fila como diccionario (alineando por heurística)
        for row_data in all_data:
            try:
                # ensure row length equals headers by padding
                row = list(row_data) + [''] * max(0, len(clean_headers) - len(row_data))
                record_dict = align_row(clean_headers, row)
                executor.schema_manager.insert(table_name, record_dict)
                inserted += 1
            except Exception as insert_error:
                print(f"[ERROR] insertando fila {inserted + failed + 1}: {insert_error}")
                failed += 1

        # Verificar que se insertaron los datos
        verify = executor.schema_manager.select(table_name, ["*"], None)
        print(f"[DEBUG] Registros en {table_name}: {len(verify)}")

        # collect pack error summary
        pack_err_count = 0
        pack_err_examples = []
        try:
            pack_err_count, pack_err_examples = get_pack_errors()
        except Exception:
            pass

        return {
            "ok": True,
            "fileName": file.filename,
            "tableName": table_name,
            "fileSize": f"{round(os.path.getsize(save_path)/1024, 2)} KB",
            "recordCount": record_count,
            "inserted": inserted,
            "failed": failed,
            "headers": clean_headers,
            "rows": rows,
            "message": f"Tabla '{table_name}' creada y persistida. Insertados: {inserted}, Fallidos: {failed}",
            "pack_error_count": pack_err_count,
            "pack_error_examples": pack_err_examples
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] upload: {error_detail}")
        return JSONResponse(
            content={"ok": False, "error": str(e), "detail": error_detail},
            status_code=500
        )

@app.post("/create_index")
def create_index(request: IndexRequest):
    """
    Crea un índice en la tabla especificada usando el motor DBMS.
    """
    try:
        idx_type = request.index_type.lower()
        if idx_type not in ("sequential", "isam", "btree", "hash", "rtree"):
            return {"ok": False, "error": f"Index type '{request.index_type}' not implemented yet. Available: sequential, isam, btree, hash, rtree"}

        # If explicit columns array provided and spatial index requested, call SchemaManager helper
        if request.columns and idx_type == "rtree":
            cols = request.columns
            # validate list
            if not isinstance(cols, list) or len(cols) == 0:
                return {"ok": False, "error": "columns must be a non-empty list when provided"}
            # call SchemaManager helper to build multi-column spatial index
            res = executor.schema_manager.create_index_multi(request.table_name, cols, idx_type)
            return {"ok": True, "message": res}

        # Fallback to legacy single-column create via executor (parses CREATE INDEX SQL)
        if not request.column:
            return {"ok": False, "error": "Missing 'column' for index creation"}
        query = f"CREATE INDEX {idx_type} ON {request.table_name} ({request.column})"
        result = executor.execute(query)
        return {"ok": True, "message": f"{idx_type} index created on {request.table_name} column {request.column}", "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.post("/compare_query")
def compare_query(request: dict):
    """Request body: { table: str, columns: ["col"], condition: str, methods?: ["sequential","isam",...] }
    Returns per-technique timings and disk access counts.
    """
    try:
        table = request.get("table")
        cols = request.get("columns")
        cond = request.get("condition")
        methods = request.get("methods")
        res = executor.schema_manager.compare_query_methods(table, cols, cond, methods=methods)
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# -------------------------------
# Esquema/Metadatos
# -------------------------------
@app.get("/get_table_columns")
def get_table_columns(table_name: str):
    try:
        if table_name not in executor.schema_manager.tables:
            return {"ok": False, "error": f"Tabla '{table_name}' no existe"}

        table_info = executor.schema_manager.tables[table_name]
        columns_meta = table_info["schema"].columns  # lista de dicts { name, type }
        column_names = [c.get("name") for c in columns_meta]
        return {"ok": True, "columns": column_names}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/sequential_index_info")
def sequential_index_info(table_name: str, column: str):
    try:
        if table_name not in executor.schema_manager.tables:
            return {"ok": False, "error": f"Tabla '{table_name}' no existe"}
        idx = executor.schema_manager.tables[table_name]["indexes"].get(column)
        if not idx or not hasattr(idx, "info"):
            return {"ok": False, "error": "No sequential index for given table/column"}
        return {"ok": True, "info": idx.info()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/system_stats")
def system_stats():
    try:
        total_records = 0
        total_tables = len(executor.schema_manager.tables)
        total_indexes = 0
        
        for table_name, table_info in executor.schema_manager.tables.items():
            # Count records in each table
            try:
                records = table_info["file"].scan_all()
                total_records += len(records)
            except:
                pass
            # Count indexes
            total_indexes += len(table_info["indexes"])
        
        return {
            "ok": True,
            "stats": {
                "total_records": total_records,
                "total_tables": total_tables,
                "total_indexes": total_indexes,
                "tables": list(executor.schema_manager.tables.keys())
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# -------------------------------
# Endpoint: List tables with indexes
# -------------------------------
@app.get("/tables_with_indexes")
def tables_with_indexes():
    try:
        result = []
        for table_name, table_info in executor.schema_manager.tables.items():
            indexed = []
            for col, idx_obj in table_info.get("indexes", {}).items():
                # determine index type
                itype = None
                try:
                    cname = idx_obj.__class__.__name__.lower()
                    if "sequential" in cname or isinstance(idx_obj, type(None)):
                        itype = "sequential"
                    elif "isam" in cname:
                        itype = "isam"
                    elif "bplustree" in cname or "bplus" in cname or "btree" in cname:
                        itype = "btree"
                    elif "extend" in cname or "hash" in cname:
                        itype = "hash"
                    elif "rtree" in cname:
                        itype = "rtree"
                    else:
                        itype = cname
                except Exception:
                    itype = "unknown"
                meta = {"column": col, "type": itype}
                # expose underlying covered columns for spatial indexes
                try:
                    cols = getattr(idx_obj, "_columns", None)
                    if cols:
                        meta["columns"] = list(cols)
                except Exception:
                    pass
                indexed.append(meta)
            if indexed:
                result.append({"table": table_name, "indexes": indexed})
        return {"ok": True, "tables": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/drop_index")
def drop_index(table_name: str, column: str):
    """Remove the index files for a table.column and update the catalog."""
    try:
        executor.schema_manager.drop_index(table_name, column)
        return {"ok": True, "message": f"Index dropped for {table_name}({column})"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/reload_catalog")
def reload_catalog():
    """Reload catalog.json from disk into memory (reinstantiates indexes)."""
    try:
        executor.schema_manager.reload_catalog()
        return {"ok": True, "message": "Catalog reloaded"}
    except Exception as e:
        return {"ok": False, "error": str(e)}