"""Hàm dùng chung cho Bước 5, 6, 7: tính lại Current Actual, Attainable Potential và trần thị trường
với một giả định khác (cửa sổ tháng, mức benchmark, số ngày nối lead).

Mỗi hàm làm lại đúng các phép tính của bước gốc:
- kpi_shop: Bước 1, mục 1.7 (Current Actual và các KPI của shop trên một cửa sổ tháng);
- attainable: Bước 3 (benchmark trong peer group, giới hạn rủi ro, giới hạn theo shop tốt nhất nhóm);
- tran_tinh: Bước 4 (penetration theo tỉnh, chuẩn = trung vị nhóm 1/4 tỉnh cao nhất, trần tỉnh);
- ghep_4_so: Bước 5 (chia trần tỉnh cho shop, xếp 4 con số đúng thứ tự, tách opportunity gap).

Bước 5 và Bước 6 kiểm tra rằng các hàm này cho lại đúng số của bước gốc trước khi dùng.
"""
from pathlib import Path

import numpy as np
import pandas as pd

G = ['salesroom_category', 'salesroom_product', 'salesroom_model', 'salesroom_province']   # peer group
G_QG = G[:3]                                                                              # cùng loại, toàn quốc


def tim_goc():
    """Thư mục gốc của bài (thư mục có 'Bước 1'), để notebook chạy được từ thư mục gốc hoặc từ thư mục 'Bước N'."""
    p = Path.cwd()
    for q in [p, *p.parents]:
        if (q / 'Bước 1').exists():
            return q
    raise FileNotFoundError('Không tìm thấy thư mục gốc có "Bước 1"')


# ---------------------------------------------------------------- Bước 1: KPI trên một cửa sổ tháng
def kpi_shop(shop, sm, thang_tu, thang_den, xsell=None, rr_den=None):
    """KPI của từng shop trên các tháng từ thang_tu đến thang_den (trung bình mỗi tháng), như Bước 1 mục 1.7.

    shop: bảng shop (skp_salesroom, peer group, salesroom_status, shop_online, thang_bat_dau).
    sm: bảng shop × tháng của Bước 1 (shop_month.csv).
    xsell: nếu có, bảng (skp_salesroom, thang, xsell_hd) thay cho cột xsell_hd của Bước 1 (đổi số ngày nối lead).
    rr_den: nếu có, chỉ đo tỷ lệ trễ hạn trên contract của các tháng đến rr_den (dùng khi đứng ở một thời điểm trong
        quá khứ, lúc contract ký gần đó chưa đến đủ 4 kỳ trả). Mặc định dùng mọi contract tính rủi ro của Bước 1.
    """
    sm = sm.copy()
    if xsell is not None:
        sm = sm.drop(columns='xsell_hd').merge(xsell, on=['skp_salesroom', 'thang'], how='left')
        sm['xsell_hd'] = sm.xsell_hd.fillna(0)
    n = len(pd.date_range(thang_tu, thang_den, freq='MS'))
    w = sm[(sm.thang >= thang_tu) & (sm.thang <= thang_den)]
    a = w.groupby('skp_salesroom')[['hd_ky', 'xsell_hd', 'ho_so', 'so_sa', 'hs_tu_choi', 'hs_huy', 'lead', 'so_tien']].sum()
    k = pd.DataFrame(index=a.index)
    k['ca_hd_truc_tiep'] = a.hd_ky / n
    k['ca_xsell'] = a.xsell_hd / n
    k['ca_hd_tong'] = k.ca_hd_truc_tiep + k.ca_xsell
    k['ca_so_tien'] = a.so_tien / n
    k['ca_ho_so'] = a.ho_so / n
    k['ca_so_sa'] = a.so_sa / n
    k['ca_ho_so_moi_sa'] = a.ho_so / a.so_sa.replace(0, np.nan)
    k['ca_ty_le_ky'] = a.hd_ky / a.ho_so.replace(0, np.nan)
    k['ca_ty_le_tu_choi'] = a.hs_tu_choi / a.ho_so.replace(0, np.nan)
    k['ca_ty_le_huy'] = a.hs_huy / a.ho_so.replace(0, np.nan)
    k['ca_lead'] = a.lead / n
    k['ca_xsell_moi_lead'] = a.xsell_hd / a.lead.replace(0, np.nan)
    r = (sm if rr_den is None else sm[sm.thang <= rr_den]).groupby('skp_salesroom')[['hd_tinh_rui_ro', 'hd_tre_han']].sum()
    k = k.join(r.rename(columns={'hd_tinh_rui_ro': 'rr_hd'}), how='left')
    k['rr_ty_le_tre'] = k.hd_tre_han / k.rr_hd.replace(0, np.nan)
    k = k.drop(columns='hd_tre_han')
    out = shop.merge(k.reset_index(), on='skp_salesroom', how='left')
    for c in ['ca_hd_truc_tiep', 'ca_xsell', 'ca_hd_tong', 'ca_so_tien', 'ca_ho_so', 'ca_so_sa', 'ca_lead', 'rr_hd']:
        out[c] = out[c].fillna(0)
    return out


# ---------------------------------------------------------------- Bước 3: Attainable Potential
def attainable(d, muc=0.75, so_shop_toi_thieu=5):
    """Attainable Potential trước khi so với BAU, theo đúng các quy tắc của Bước 3.

    d: bảng shop đã lọc (Active, không online) có các cột KPI ca_* và rr_*.
    muc: mức benchmark cho KPI càng cao càng tốt (0,75 = mức mà 1/4 shop tốt nhất đạt); tỷ lệ bị từ chối
         và tỷ lệ hủy dùng mức 1 − muc.
    Trả về d thêm các cột benchmark (bm_*), KPI sau khi nâng (sau_*), ap_truc_tiep, ap_xsell, ap_truoc_bau.
    """
    x = d.copy()
    x['dang_ban'] = x.ca_ho_so > 0
    db_ = x[x.dang_ban]

    def benchmark(cot, nen, ten, q):
        tinh = nen.groupby(G)[cot].agg(n_tinh='count', bm_tinh=lambda s: s.quantile(q)).reset_index()
        qg = nen.groupby(G_QG)[cot].agg(n_qg='count', bm_qg=lambda s: s.quantile(q)).reset_index()
        o = x[['skp_salesroom'] + G].merge(tinh, on=G, how='left').merge(qg, on=G_QG, how='left')
        dung_tinh = o.n_tinh.fillna(0) >= so_shop_toi_thieu
        o[ten] = np.where(dung_tinh, o.bm_tinh, o.bm_qg)
        o[ten + '_nguon'] = np.where(dung_tinh, 'peer group', 'toàn quốc')
        return o[['skp_salesroom', ten, ten + '_nguon']]

    # Điều kiện tối thiểu của Bước 3: trung bình từ 10 hồ sơ mỗi quý cho hai tỷ lệ, từ 30 lead mỗi quý cho cross-sell mỗi lead.
    du_10_hs = db_[db_.ca_ho_so * 3 >= 10]
    du_30_lead = db_[db_.ca_lead * 3 >= 30]
    cac_kpi = [('ca_so_sa', db_, 'bm_so_sa', muc), ('ca_ho_so_moi_sa', db_, 'bm_ho_so_moi_sa', muc),
               ('ca_ty_le_tu_choi', du_10_hs, 'bm_ty_le_tu_choi', 1 - muc), ('ca_ty_le_huy', du_10_hs, 'bm_ty_le_huy', 1 - muc),
               ('ca_xsell_moi_lead', du_30_lead, 'bm_xsell_moi_lead', muc), ('ca_hd_truc_tiep', db_, 'bm_hd_truc_tiep', muc)]
    for cot, nen, ten, q in cac_kpi:
        x = x.merge(benchmark(cot, nen, ten, q), on='skp_salesroom')
    rr = x.assign(tre=x.rr_hd * x.rr_ty_le_tre.fillna(0)).groupby(G).agg(tre=('tre', 'sum'), hd=('rr_hd', 'sum'))
    rr['rr_peer_group'] = rr.tre / rr.hd.replace(0, np.nan)
    x = x.merge(rr[['rr_peer_group']].reset_index(), on=G, how='left')
    x['duoc_giam_tu_choi'] = (x.rr_hd >= 30) & (x.rr_ty_le_tre <= x.rr_peer_group)
    db = x.dang_ban
    du_hs = x.ca_ho_so * 3 >= 10
    x['sau_so_sa'] = np.where(db, np.maximum(x.ca_so_sa, x.bm_so_sa), np.nan)
    x['sau_ho_so_moi_sa'] = np.where(db, np.maximum(x.ca_ho_so_moi_sa, x.bm_ho_so_moi_sa), np.nan)
    x['sau_ty_le_tu_choi'] = np.where(db, np.where(x.duoc_giam_tu_choi, np.minimum(x.ca_ty_le_tu_choi, x.bm_ty_le_tu_choi.fillna(1)),
                                                   x.ca_ty_le_tu_choi), np.nan)
    x['sau_ty_le_huy'] = np.where(db, np.where(du_hs, np.minimum(x.ca_ty_le_huy, x.bm_ty_le_huy.fillna(1)), x.ca_ty_le_huy), np.nan)
    x['sau_ty_le_ky'] = 1 - x.sau_ty_le_tu_choi - x.sau_ty_le_huy
    x['tt_tinh_lai'] = np.where(db, x.sau_so_sa * x.sau_ho_so_moi_sa * x.sau_ty_le_ky, 0)
    x['tran_nhom'] = np.maximum(x.bm_hd_truc_tiep, x.ca_hd_truc_tiep)
    x['ap_truc_tiep'] = np.where(db, np.minimum(x.tt_tinh_lai, x.tran_nhom), 0)
    x['sau_xsell_moi_lead'] = np.where(db, np.maximum(x.ca_xsell_moi_lead.fillna(0), x.bm_xsell_moi_lead.fillna(0)), np.nan)
    x['ap_xsell'] = np.where(db, np.maximum(x.ca_lead * x.sau_xsell_moi_lead, x.ca_xsell), x.ca_xsell)
    x['ap_truoc_bau'] = x.ap_truc_tiep + x.ap_xsell
    co_nhom = db_.groupby(G).size().rename('so_shop_peer_group').reset_index()
    x = x.merge(co_nhom, on=G, how='left')
    x['so_shop_peer_group'] = x.so_shop_peer_group.fillna(0).astype(int)
    x['dung_bm_toan_quoc'] = (x[[t + '_nguon' for _, _, t, _ in cac_kpi[:4]]] == 'toàn quốc').any(axis=1)
    return x


def tach_phan_tang(x):
    """Chia phần Attainable Potential cao hơn Current Actual (ap_truoc_bau − ca_hd_tong) cho từng KPI, như Bước 3 mục 3.7:
    phần bán trực tiếp chia theo logarit của tỷ số sau/trước của số SA, hồ sơ mỗi SA, tỷ lệ ký; phần tỷ lệ ký chia tiếp
    cho tỷ lệ bị từ chối và tỷ lệ hủy theo mức giảm; phần cross-sell tính riêng."""
    def log_ty_so(sau, truoc):
        sau, truoc = np.asarray(sau, float), np.asarray(truoc, float)
        ok = (truoc > 0) & (sau > 0)
        return np.log(np.where(ok, sau / np.where(ok, truoc, 1), 1))
    l_sa = log_ty_so(x.sau_so_sa, x.ca_so_sa)
    l_ns = log_ty_so(x.sau_ho_so_moi_sa, x.ca_ho_so_moi_sa)
    l_ky = log_ty_so(x.sau_ty_le_ky, x.ca_ty_le_ky)
    tong = l_sa + l_ns + l_ky
    giam_tc = np.nan_to_num(x.ca_ty_le_tu_choi - x.sau_ty_le_tu_choi)
    giam_huy = np.nan_to_num(x.ca_ty_le_huy - x.sau_ty_le_huy)
    phan_tc = np.where(giam_tc + giam_huy > 0, giam_tc / np.where(giam_tc + giam_huy > 0, giam_tc + giam_huy, 1), 0)
    tang_tt = np.where(x.dang_ban, x.ap_truc_tiep - x.ca_hd_truc_tiep, 0)
    chia = lambda l: np.where(tong > 0, tang_tt * l / np.where(tong > 0, tong, 1), 0)
    return pd.DataFrame({'so_sa': chia(l_sa), 'ho_so_moi_sa': chia(l_ns), 'ty_le_tu_choi': chia(l_ky) * phan_tc,
                         'ty_le_huy': chia(l_ky) * (1 - phan_tc),
                         'xsell': np.where(x.dang_ban, x.ap_xsell - x.ca_xsell, 0)}, index=x.index)


# ---------------------------------------------------------------- Bước 4: trần thị trường của tỉnh
def tran_tinh(s3, s2, s1, thang, bench_q=0.75):
    """Trần của tỉnh theo công thức Bước 4: Q_p = số contract ghi công cho shop vật lý của tỉnh (quy ra năm),
    penetration = Q_p / dân số tuổi lao động (nghìn người), chuẩn π* = trung vị penetration của các tỉnh từ mức bench_q
    trở lên, trần C_p = max(π* × dân số tuổi lao động, Q_p). Trả về bảng tỉnh và π*."""
    phys = s2[s2.is_physical == 1][['shop', 'pkey']]
    m = s3[s3.month.isin(thang)].merge(phys, on='shop')
    q = (m.groupby('pkey').contracts.sum() * 12 / len(thang)).rename('q_nam')
    p = s1.set_index('pkey')[['province', 'workpop_k']].join(q).fillna({'q_nam': 0})
    p['penetration'] = p.q_nam / p.workpop_k
    pi_sao = p.penetration[p.penetration >= p.penetration.quantile(bench_q)].median()
    p['tran_nam'] = np.maximum(pi_sao * p.workpop_k, p.q_nam)
    p['tran_thang'] = p.tran_nam / 12
    p['q_thang'] = p.q_nam / 12
    return p.reset_index(), pi_sao


# ---------------------------------------------------------------- Bước 5: ghép 4 con số và tách opportunity gap
NHOM_PHAN = ['giu_muc_hien_tai', 'so_sa', 'ho_so_moi_sa', 'ty_le_tu_choi', 'ty_le_huy', 'xsell']


def ghep_4_so(x, bau, tinh_cua_shop, tran):
    """x: kết quả attainable(); bau: Series BAU (contract/tháng) theo skp_salesroom;
    tinh_cua_shop: Series pkey theo skp_salesroom; tran: bảng tran_tinh().

    - AP thô = max(ap_truoc_bau, BAU).
    - Trần tỉnh được chia cho shop theo tỷ trọng của mức thực tế của shop, w = max(AP thô, Current Actual);
      trần của shop không thấp hơn max(Current Actual, BAU).
    - Attainable Potential = min(AP thô, trần của shop). Opportunity gap = Attainable Potential − BAU.
    - Phần gap được chia cho các KPI theo tỷ lệ; phần bị trần thị trường cắt ghi riêng (tru_do_thi_truong).
    """
    o = x.copy()
    o['bau'] = o.skp_salesroom.map(bau).fillna(0).to_numpy()
    o['pkey'] = o.skp_salesroom.map(tinh_cua_shop).to_numpy()
    o['ap_tho'] = np.maximum(o.ap_truoc_bau, o.bau)
    o['w'] = np.maximum(o.ap_tho, o.ca_hd_tong)
    tw = o.groupby('pkey').w.transform('sum')
    o['tran_tinh_thang'] = o.pkey.map(tran.set_index('pkey').tran_thang).to_numpy()
    o['tran_shop'] = np.maximum(o.tran_tinh_thang * o.w / tw.replace(0, np.nan), np.maximum(o.ca_hd_tong, o.bau)).fillna(
        np.maximum(o.ca_hd_tong, o.bau))
    o['ap'] = np.minimum(o.ap_tho, o.tran_shop)
    o['gap'] = (o.ap - o.bau).clip(lower=0)
    o['gap_truoc_tran'] = o.ap_tho - o.bau
    o['tru_do_thi_truong'] = o.gap_truoc_tran - o.gap
    p = tach_phan_tang(o)
    hold = np.clip(o.ca_hd_tong - o.bau, 0, None)
    tang = p.sum(axis=1)
    # Khi BAU cao hơn Current Actual, phần AP vượt BAU nhỏ hơn tổng phần tăng: thu nhỏ các phần theo cùng tỷ lệ.
    he_truoc = np.where(tang > 0, (o.gap_truoc_tran - hold) / np.where(tang > 0, tang, 1), 0)
    p = p.mul(np.clip(he_truoc, 0, None), axis=0)
    p.insert(0, 'giu_muc_hien_tai', np.minimum(hold, o.gap_truoc_tran.clip(lower=0)))
    he_tran = np.where(o.gap_truoc_tran > 0, o.gap / np.where(o.gap_truoc_tran > 0, o.gap_truoc_tran, 1), 0)
    p = p.mul(he_tran, axis=0)
    for c in NHOM_PHAN:
        o['gap_' + c] = p[c].to_numpy()
    return o


# ---------------------------------------------------------------- Bước 5–6: rủi ro, độ tin cậy, nhóm ưu tiên
def gan_rui_ro_cao(s, so_hd_toi_thieu=10, muc_y_nghia=0.05):
    """Bước 5 mục 5.6.6: shop có tỷ lệ contract trễ hạn trong 4 kỳ đầu cao hơn peer group một cách chắc chắn
    (binomial test một phía, xác suất dưới 5%), chỉ xét shop có từ 10 contract tính rủi ro."""
    from scipy import stats
    tre = (s.rr_hd * s.rr_ty_le_tre.fillna(0)).round()
    p = np.where(s.rr_hd > 0, stats.binom.sf(tre - 1, s.rr_hd.astype(int), s.rr_peer_group.fillna(0)), 1.0)
    return pd.Series((s.rr_hd >= so_hd_toi_thieu) & (s.rr_ty_le_tre > s.rr_peer_group) & (p < muc_y_nghia), index=s.index), p


def bien_dong_bat_thuong(sm, shops, thang_tu, thang_den, phi_theo_quy_mo, muc_y_nghia=0.05):
    """Bước 6 mục 6.1: doanh số theo tháng (bán trực tiếp + cross-sell) của shop lên xuống mạnh hơn hẳn các shop cùng quy mô.
    Với 6 tháng có đủ số liệu, đại lượng (số tháng − 1) × phương sai / (φ × trung bình) theo phân phối chi-square
    nếu shop chỉ dao động như mức thường gặp φ của shop cùng quy mô (φ lấy từ Bước 2); vượt mức 5% thì coi là bất thường."""
    from scipy import stats
    w = sm[(sm.thang >= thang_tu) & (sm.thang <= thang_den)]
    v = w.groupby('skp_salesroom').hd_tong.agg(n='size', mu='mean', var='var')
    band = pd.cut(v.mu, [0, 1, 3, 10, 30, np.inf], labels=['≤1', '1–3', '3–10', '10–30', '>30'], include_lowest=True)
    phi = band.astype(object).map(phi_theo_quy_mo).astype(float)
    n_can = len(pd.date_range(thang_tu, thang_den, freq='MS'))
    stat = (v.n - 1) * v['var'] / (phi * v.mu)
    bd = (v.n == n_can) & (v.mu > 0) & (stats.chi2.sf(stat, v.n - 1) < muc_y_nghia)
    return shops.map(bd).eq(True)   # shop không có trong bd (không đủ dữ liệu) nhận False


NGUONG_GAP = 2.0   # Bước 6 mục 6.2


def chia_nhom(s, nguong_gap=NGUONG_GAP):
    """Bước 6 mục 6.3: Risk cao trước; rồi gap lớn (≥ ngưỡng) và độ tin cậy cao → Đầu tư ngay; gap lớn, độ tin cậy thấp
    → Pilot; còn lại → Giữ nguyên."""
    return np.select([s.rui_ro_cao, (s.gap >= nguong_gap) & (s.do_tin_cay == 'cao'), s.gap >= nguong_gap],
                     ['Risk cao', 'Đầu tư ngay', 'Pilot'], 'Giữ nguyên')


def gan_do_tin_cay(s, bien_dong):
    """Bước 6 mục 6.1: thấp nếu shop mới, bán dưới 3 contract mỗi tháng, peer group dưới 20 shop, có benchmark phải lấy từ
    toàn quốc, hoặc doanh số biến động bất thường; không tính được nếu shop không có hồ sơ trong quý; còn lại là cao."""
    thap = (s.shop_moi == 1) | (s.ca_hd_tong < 3) | (s.so_shop_peer_group < 20) | s.dung_bm_toan_quoc | bien_dong
    return np.select([~s.dang_ban, thap], ['không tính được', 'thấp'], 'cao')


def chay_lai(shop, sm, s1, s2, s3, bau, thang_tu, thang_den, phi, muc=0.75, xsell=None, rr_den=None,
             thang_bien_dong=None):
    """Chạy lại Bước 3 → Bước 6 với một giả định khác. shop: bảng shop (đã lọc Active, không online, có shop_moi đúng
    với thời điểm đứng). bau: Series BAU theo skp_salesroom. Trả về bảng shop có gap, nhóm và các cột trung gian."""
    k = kpi_shop(shop, sm, thang_tu, thang_den, xsell=xsell, rr_den=rr_den)
    x = attainable(k, muc=muc)
    tran, _ = tran_tinh(s3, s2, s1, pd.date_range(thang_tu, thang_den, freq='MS').strftime('%Y-%m').tolist())   # trần đo cùng cửa sổ
    s = ghep_4_so(x, bau, s2.set_index('shop').pkey, tran)
    s['rui_ro_cao'], _ = gan_rui_ro_cao(s)
    tu, den = thang_bien_dong if thang_bien_dong else ((pd.Timestamp(thang_den) - pd.DateOffset(months=5)).strftime('%Y-%m-%d'), thang_den)
    s['bien_dong'] = bien_dong_bat_thuong(sm, s.skp_salesroom, tu, den, phi).to_numpy()
    s['do_tin_cay'] = gan_do_tin_cay(s, s.bien_dong)
    s['nhom'] = chia_nhom(s)
    return s
