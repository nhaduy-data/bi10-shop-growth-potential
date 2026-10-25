"""Mở dữ liệu sạch bằng DuckDB cho các notebook Bước 0 đến Bước 4.

Cách dùng trong notebook:
    from r3_db import connect
    con = connect()
    con.execute("select count(*) from contract").df()

Lần chạy đầu tiên, hàm connect() đọc các file CSV trong clean_data/ và lưu vào
file output/r3_clean.duckdb (mất vài phút). Các lần sau chỉ mở file này nên rất nhanh.
Nếu chạy lại notebook làm sạch (BI10_R03_clean.ipynb), hãy xóa file
output/r3_clean.duckdb để dữ liệu được nạp lại.
"""
import os
import tempfile

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN_DIR = os.path.join(HERE, 'clean_data')
OUT_DIR = os.path.join(HERE, 'output')
DB_PATH = os.path.join(OUT_DIR, 'r3_clean.duckdb')
TMP_DIR = os.path.join(tempfile.gettempdir(), 'duck_r3_steps')

TABLES = ['salesroom', 'seller', 'emp_2_salesroom', 'contract', 'contract_product', 'leads', 'cl_lead_fin_reason']

# Các cột mã phải đọc dạng chữ để không mất số 0 ở đầu (ví dụ code_pos "040100").
_TEXT = {
    'leads': ['id_uuid', 'id_lead_source', 'text_accepted_by', 'code_pos', 'code_lead_status',
              'text_contract_number', 'text_tenor', 'code_sa', 'result_code',
              'code_product_type_original', 'code_product_type'],
    'salesroom': ['salesroom_town', 'salesroom_town_norm', 'salesroom_district'],
}

SETTINGS = [f"SET memory_limit='2GB'", f"SET temp_directory='{TMP_DIR}'",
            "SET preserve_insertion_order=false", "SET enable_progress_bar=false"]


def _apply_settings(c):
    for s in SETTINGS:
        try:
            c.execute(s)
        except duckdb.Error:
            pass  # ví dụ: Jupyter thiếu ipywidgets thì không tắt được thanh tiến độ, bỏ qua


def _missing_tables():
    if not os.path.exists(DB_PATH):
        return list(TABLES)
    c = duckdb.connect(DB_PATH, read_only=True)
    have = {r[0] for r in c.execute("select table_name from information_schema.tables").fetchall()}
    c.close()
    return [t for t in TABLES if t not in have]


def _build(missing):
    c = duckdb.connect(DB_PATH)
    _apply_settings(c)
    for t in missing:
        path = os.path.join(CLEAN_DIR, f'{t}.csv').replace('\\', '/')
        types = {k: 'VARCHAR' for k in _TEXT.get(t, [])}
        opt = f", types={types}" if types else ''
        print(f'Đang nạp {t}.csv vào file DuckDB ...', flush=True)
        c.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv('{path}'{opt})")
    c.execute("CHECKPOINT")
    c.close()


def connect():
    """Trả về một kết nối DuckDB có sẵn các bảng sạch (contract, leads, salesroom, ...).

    Các bảng chỉ được đọc, không sửa được. Bảng tạm do notebook tạo ra nằm trong bộ nhớ.
    """
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    missing = _missing_tables()
    if missing:
        _build(missing)
    con = duckdb.connect()
    _apply_settings(con)
    con.execute(f"ATTACH '{DB_PATH.replace(chr(92), '/')}' AS r3 (READ_ONLY)")
    for t in TABLES:
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM r3.{t}")
    return con


def save_csv(df, name):
    """Ghi DataFrame ra output/<name>.csv, mã UTF-8 có BOM để Excel đọc đúng tiếng Việt."""
    path = os.path.join(OUT_DIR, f'{name}.csv')
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'Đã ghi output/{name}.csv: {len(df):,} dòng')
