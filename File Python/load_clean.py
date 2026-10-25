"""Đọc các file CSV sạch trong thư mục clean_data với đúng kiểu dữ liệu.

Cách dùng:
    from load_clean import load
    contract = load('contract')
"""
import os
import pandas as pd

CLEAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clean_data')

_TEXT_COLUMNS = {
    'leads': ['id_uuid', 'id_lead_source', 'text_accepted_by', 'code_pos', 'code_lead_status',
              'text_contract_number', 'text_tenor', 'code_sa', 'result_code',
              'code_product_type_original', 'code_product_type'],
    'salesroom': ['salesroom_town', 'salesroom_town_norm', 'salesroom_district'],
}
_DATE_COLUMNS = {
    'contract': ['date_sign', 'date_apply', 'apply_month', 'sign_month'],
    'leads': ['dtime_created', 'date_assigned', 'created_month'],
    'emp_2_salesroom': ['dtime_valid_from', 'dtime_valid_to', 'dtime_valid_to_filled'],
    'salesroom': ['salesroom_start', 'salesroom_end'],
    'seller': ['seller_active_date'],
}
_INT_COLUMNS = {
    'contract': ['skp_emp_pre_process', 'skp_product', 'payment_num', 'dpd_1pd', 'dpd_2pd', 'dpd_3pd', 'dpd_4pd'],
    'leads': ['result', 'amt_loan_limit', 'amt_loan_limit_clean'],
}


def load(name, **kwargs):
    """Đọc bảng `name` (contract, leads, salesroom, seller, emp_2_salesroom,
    contract_product, cl_lead_fin_reason) từ clean_data/ thành DataFrame."""
    path = os.path.join(CLEAN_DIR, f'{name}.csv')
    dtype = {c: 'string' for c in _TEXT_COLUMNS.get(name, [])}
    dtype.update({c: 'Int64' for c in _INT_COLUMNS.get(name, [])})
    dtype.update(kwargs.pop('dtype', {}))
    kwargs.setdefault('encoding', 'utf-8-sig')
    return pd.read_csv(path, dtype=dtype, parse_dates=_DATE_COLUMNS.get(name, []), **kwargs)
