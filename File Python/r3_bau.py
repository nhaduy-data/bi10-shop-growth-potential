"""Phương pháp BAU (Business-as-Usual) của Bước 2, đóng gói lại để Bước 6 và Bước 7 dùng ở các thời điểm khác.

Các hàm từ month_diff đến score được chép nguyên văn từ notebook Bước 2 (BI10_R03_Buoc2_Nhi.ipynb), cùng các tham số CFG.
Phần thêm vào cuối file:
- panel_tu_shop_month: dựng bảng shop × tháng theo đúng các cột mà Bước 2 dùng, từ shop_month.csv của Bước 1;
- bau_tai: đứng ở một tháng bất kỳ, dựng BAU contract bán tại shop cho 6 tháng sau theo đúng các quy tắc của Bước 2
  (mức nền × trend đã lọc nhiễu × đường vòng đời × mùa vụ; shop mới mở dùng mức của shop mới cùng cỡ × ngành;
  shop có mức nền 0 dùng tỷ lệ nền thực nghiệm; shop chưa từng bán = 0).
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

CFG = {
    "FIRST_MONTH": pd.Timestamp("2025-01-01"),
    "LAST_ACTUAL": pd.Timestamp("2026-09-01"),
    "HORIZON": 6,
    "CA_START": pd.Timestamp("2026-07-01"),
    "WINDOW": 6,
    "NAIVE_WINDOW": 3,
    "MIN_VALID_FOR_TREND": 4,
    "TREND_CAP": 0.15,
    "SEASON_MIN_PANEL": 100,
    "KAPPA_ORIGINS": pd.date_range("2025-06-01", "2026-03-01", freq="MS"),
    "KAPPA_MIN_SHOPS": 150,
    "HOLDOUT_ORIGIN": pd.Timestamp("2026-03-01"),
    "SMOOTH_C": 0.5,
    "XSELL_FIRST_FULL_MONTH": pd.Timestamp("2026-02-01"),
}
MEAN_DAYS = 365.25 / 12
size_bins = [0, 1, 3, 10, 30, np.inf]
size_labels = ["≤1", "1–3", "3–10", "10–30", ">30"]


def month_diff(a, b):
    """Số tháng giữa hai Series datetime (a − b), vector hóa."""
    return (a.dt.year - b.dt.year) * 12 + (a.dt.month - b.dt.month)


def same_store_links(df, metric, min_age=1, min_panel=1):
    """Tỷ số tháng này/tháng trước THEO NGÀY, chỉ trên shop có đủ cả hai tháng đầy đủ (age ≥ min_age)."""
    g = df.groupby("shop_id", sort=False)
    d = df.assign(prev_y=g[metric].shift(1), prev_age=g["age"].shift(1), prev_dim=g["dim"].shift(1))
    d = d.loc[d["prev_age"].ge(min_age) & d["age"].ge(min_age)]
    link = (d.groupby("month")
              .agg(n_shops=("shop_id", "size"), y=(metric, "sum"), y_prev=("prev_y", "sum"),
                   dim=("dim", "first"), dim_prev=("prev_dim", "first"))
              .reset_index())
    link = link.loc[link["n_shops"].ge(min_panel) & link["y"].gt(0) & link["y_prev"].gt(0)].copy()
    link["l"] = np.log((link["y"] / link["dim"]) / (link["y_prev"] / link["dim_prev"]))   # log MoM theo ngày
    link["moy"] = link["month"].dt.month
    link["year"] = link["month"].dt.year
    return link


def estimate_lifecycle(df, origin, max_age=12, min_shops=150):
    """Đường vòng đời f(a) = 1 + amp·exp(−(a−1)/τ), f(∞) = 1. Chỉ dùng dữ liệu ≤ origin."""
    d = df.loc[df["month"].le(origin) & df["age"].between(1, max_age)]
    for K in range(max_age, 3, -1):           # K lớn nhất có đủ shop quan sát trọn K tháng
        dk = d.loc[d["age"].le(K)]
        dk = dk.loc[dk.groupby("shop_id")["age"].transform("size").eq(K)]
        if dk["shop_id"].nunique() >= min_shops:
            break
    rel = dk["signed_contracts"] / dk.groupby("shop_id")["signed_contracts"].transform("mean")
    prof = rel[np.isfinite(rel)].groupby(dk["age"]).agg(["mean", "size"])

    def fn(a, p, amp, tau):
        return p * (1 + amp * np.exp(-(a - 1) / tau))

    (p, amp, tau), _ = curve_fit(fn, prof.index.to_numpy(float), prof["mean"].to_numpy(),
                                 p0=[0.9, 0.5, 2.0], sigma=1 / np.sqrt(prof["size"].to_numpy()),
                                 bounds=([0.1, -0.9, 0.2], [3, 5, 24]))
    return {"origin": origin, "K": K, "n_shops": int(dk["shop_id"].nunique()), "plateau": p, "amp": amp,
            "tau": tau, "f": lambda a: 1 + amp * np.exp(-(np.asarray(a, dtype=float) - 1) / tau)}


def estimate_season(df, origin, metric="signed_contracts", shrink=None, min_age=1,
                    min_panel=CFG["SEASON_MIN_PANEL"]):
    """Mùa vụ same-store theo ngày, chỉ dùng dữ liệu ≤ origin. shrink=None → B ước lượng từ dữ liệu (EB)."""
    link = same_store_links(df.loc[df["month"].le(origin)], metric, min_age, min_panel)
    lr = link.groupby("moy")["l"].mean().reindex(range(1, 13))
    n_obs = link.groupby("moy")["l"].size().reindex(range(1, 13)).fillna(0)
    mu = lr.mean()
    s_raw = (lr - mu).fillna(0).cumsum()
    s_raw = s_raw - s_raw.mean()
    rep = link.pivot_table(index="moy", columns="year", values="l").dropna()     # tháng có ≥ 2 năm
    sigma2, corr = np.nan, np.nan
    if rep.shape[0] >= 3 and rep.shape[1] >= 2:
        diff = rep.iloc[:, -1] - rep.iloc[:, -2]
        sigma2 = float((diff ** 2).mean() / 2)                                   # Var(nhiễu) 1 quan sát
        corr = float(np.corrcoef(rep.iloc[:, -2], rep.iloc[:, -1])[0, 1])
    obs = n_obs[n_obs > 0]
    if np.isfinite(sigma2):
        tau2 = max(float(lr.dropna().var(ddof=1)) - float((sigma2 / obs).mean()), 0.0)
        B_eb = tau2 / (tau2 + sigma2 / float(obs.mean()))
    else:
        tau2, B_eb = np.nan, 0.0                     # chưa có bằng chứng lặp lại → không dùng mùa vụ
    B = B_eb if shrink is None else float(shrink)
    s_used = B * s_raw
    return {"origin": origin, "link": link, "lr": lr, "n_obs": n_obs, "mu": mu, "s_raw": s_raw,
            "sigma2": sigma2, "tau2": tau2, "corr_years": corr, "B": B, "s_used": s_used - s_used.mean()}


def season_factor(months, season):
    """S_m = (số ngày / 30,44) × exp(B·s_m)."""
    months = pd.DatetimeIndex(months)
    days = np.ones(len(months)) if season.get("no_days") else months.days_in_month / MEAN_DAYS
    return np.asarray(days) * np.exp(season["s_used"].reindex(months.month).to_numpy())


def level_trend(df, origin, season, metric="signed_contracts", window=CFG["WINDOW"],
                min_valid=CFG["MIN_VALID_FOR_TREND"], cap=CFG["TREND_CAP"], min_month=None, life=None):
    """Mức nền, độ dốc, kiểm định và trend sau lọc nhiễu của từng shop tại `origin` (dữ liệu ≤ origin)."""
    start = origin - pd.DateOffset(months=window - 1)
    w = df.loc[df["month"].between(start, origin) & df["valid"]]
    if min_month is not None:
        w = w.loc[w["month"].ge(min_month)]
    w = w.assign(S=season_factor(w["month"], season),
                 t=month_diff(w["month"], pd.Series(origin, index=w.index)).astype(float),
                 LF=life["f"](w["age"]) if life else 1.0)
    w = w.assign(ys=w[metric] / (w["S"] * w["LF"]))                       # (1) chuỗi chuẩn hóa
    a = w.groupby("shop_id").agg(n_valid=("t", "size"), t_bar=("t", "mean"), level=("ys", "mean"),
                                 raw_mean=(metric, "mean"))
    a["age_origin"] = (w["age"] - w["t"]).groupby(w["shop_id"]).max()
    w = w.join(a[["t_bar", "level"]], on="shop_id")
    dt, dy = w["t"] - w["t_bar"], w["ys"] - w["level"]
    sums = (pd.DataFrame({"shop_id": w["shop_id"], "sxy": dt * dy, "sxx": dt ** 2, "syy": dy ** 2})
              .groupby("shop_id")[["sxy", "sxx", "syy"]].sum())
    a = a.join(sums)
    a["beta"] = a["sxy"] / a["sxx"].replace(0, np.nan)                    # (2) OLS
    a["g_raw"] = a["beta"] / a["level"].replace(0, np.nan)
    a["rss"] = (a["syy"] - a["sxy"] ** 2 / a["sxx"].replace(0, np.nan)).clip(lower=0)
    a["size_band"] = pd.cut(a["raw_mean"], size_bins, labels=size_labels, include_lowest=True)
    est = a.loc[a["n_valid"].ge(min_valid) & a["level"].gt(0)]
    num = est.groupby("size_band", observed=True)["rss"].sum()           # (3) φ theo quy mô
    den = ((est["n_valid"] - 2) * est["level"]).groupby(est["size_band"], observed=True).sum()
    phi = (num / den.replace(0, np.nan)).astype(float)
    a["phi"] = a["size_band"].astype(object).map(phi.to_dict()).astype(float).fillna(1.0).clip(lower=1.0)
    a["se2"] = a["phi"] / (a["sxx"] * a["level"]).replace(0, np.nan)
    ok = a["n_valid"].ge(min_valid) & a["level"].gt(0) & np.isfinite(a["g_raw"]) & np.isfinite(a["se2"])
    wts = 1 / a.loc[ok, "se2"]                                            # (5) DerSimonian–Laird
    mu = float((wts * a.loc[ok, "g_raw"]).sum() / wts.sum())
    Q = float((wts * (a.loc[ok, "g_raw"] - mu) ** 2).sum())
    k = int(ok.sum())
    tau2 = max(0.0, (Q - (k - 1)) / (wts.sum() - (wts ** 2).sum() / wts.sum())) if k > 1 else 0.0
    a["B_shrink"] = np.where(ok, tau2 / (tau2 + a["se2"]), 0.0)
    a["g_shrunk"] = np.clip(np.where(ok, mu + a["B_shrink"] * (a["g_raw"] - mu), 0.0), -cap, cap)
    a["z"] = np.where(ok, a["g_raw"] / np.sqrt(a["se2"]), np.nan)          # (4) kiểm định & nhãn
    a["trend_label"] = np.select(
        [a["level"].le(0) & a["n_valid"].ge(3), ~ok, a["z"].gt(1.96), a["z"].lt(-1.96)],
        ["Ngủ đông (0 contract)", "Chưa đủ dữ liệu", "Đi lên", "Đi xuống"], default="Đứng yên")
    a.attrs.update({"mu": mu, "tau2": tau2, "Q_over_df": Q / max(k - 1, 1), "k": k, "phi": phi.to_dict()})
    return a


def calibrate_kappa(df, origins, metric="signed_contracts", horizon=CFG["HORIZON"], c=CFG["SMOOTH_C"],
                    min_shops=CFG["KAPPA_MIN_SHOPS"], last_actual=CFG["LAST_ACTUAL"]):
    """κ = phần trend sau lọc nhiễu còn kéo dài sang `horizon` tháng sau, ước lượng tại nhiều gốc (dữ liệu ≤ gốc)."""
    rows, pooled = [], []
    for T in origins:
        if T + pd.DateOffset(months=horizon) > last_actual:
            continue
        se = estimate_season(df, T, metric)
        life = estimate_lifecycle(df, T)
        lt = level_trend(df, T, se, metric, life=life)
        lt = lt.loc[lt["n_valid"].ge(CFG["MIN_VALID_FOR_TREND"]) & lt["level"].gt(0)]
        fut = df.loc[df["month"].between(T + pd.DateOffset(months=1), T + pd.DateOffset(months=horizon))]
        fut = fut.assign(ys=fut[metric] / (season_factor(fut["month"], se) * life["f"](fut["age"])))
        d = lt.join(fut.groupby("shop_id")["ys"].mean().rename("fbar"), how="inner")
        if len(d) < min_shops:
            continue
        d["growth"] = np.log((d["fbar"] + c) / (d["level"] + c))
        d["x"] = d["g_shrunk"] * ((horizon + 1) / 2 - d["t_bar"])
        d["x_raw"] = d["g_raw"].clip(-1, 1) * ((horizon + 1) / 2 - d["t_bar"])
        W = np.sqrt(d["level"].to_numpy())
        fit = lambda x: np.linalg.lstsq(np.column_stack([np.ones(len(d)), x]) * W[:, None],
                                        d["growth"].to_numpy() * W, rcond=None)[0][1]
        rows.append({"origin": T.strftime("%Y-%m"), "shops": len(d),
                     "kappa (trend sau lọc)": fit(d["x"].to_numpy()), "kappa (trend thô)": fit(d["x_raw"].to_numpy())})
        pooled.append(d.assign(origin=T))
    tab = pd.DataFrame(rows)
    kappa = float(np.clip(tab["kappa (trend sau lọc)"].median(), 0, 1)) if len(tab) else 0.0
    return kappa, tab, (pd.concat(pooled) if pooled else pd.DataFrame())


def forecast_path(lt, season, kappa, origin, horizon=CFG["HORIZON"], life=None):
    """Ma trận dự báo shop × h. life → nhân hệ số vòng đời theo tuổi tương lai."""
    fmonths = pd.date_range(origin + pd.DateOffset(months=1), periods=horizon, freq="MS")
    h = np.arange(1, horizon + 1)
    growth = np.exp(kappa * lt["g_shrunk"].to_numpy()[:, None] * (h[None, :] - lt["t_bar"].to_numpy()[:, None]))
    lf = life["f"](lt["age_origin"].to_numpy()[:, None] + h[None, :]) if life else 1.0
    F = lt["level"].to_numpy()[:, None] * growth * lf * season_factor(fmonths, season)[None, :]
    return pd.DataFrame(F, index=lt.index, columns=fmonths)


def zero_base_rates(df, origins, horizon=CFG["HORIZON"], window=CFG["WINDOW"]):
    """Shop có n tháng đầy đủ toàn 0 trong cửa sổ tại gốc T → TB contract/tháng của 6 tháng sau (gộp các gốc)."""
    rows = []
    for T in origins:
        if T + pd.DateOffset(months=horizon) > CFG["LAST_ACTUAL"]:
            continue
        w = df.loc[df["month"].between(T - pd.DateOffset(months=window - 1), T) & df["valid"]]
        g = w.groupby("shop_id")["signed_contracts"].agg(["size", "sum"])
        z = g.loc[g["sum"].eq(0), "size"].rename("n_zero")
        fut = df.loc[df["month"].between(T + pd.DateOffset(months=1), T + pd.DateOffset(months=horizon))]
        rows.append(z.to_frame().join(fut.groupby("shop_id")["signed_contracts"].mean().rename("future_mean")))
    r = pd.concat(rows)
    return r.groupby("n_zero")["future_mean"].agg(["mean", "size"]).rename(columns={"mean": "rate", "size": "obs"})


def run_backtest(df, origin, metric="signed_contracts", kappa=None, shrink=None, window=CFG["WINDOW"],
                 day_adjust=True, use_life=True, horizon=CFG["HORIZON"]):
    """Đứng ở `origin`, dựng BAU bằng đúng phương pháp Bước 2 (mọi tham số chỉ dùng dữ liệu ≤ origin).
    Trả về bảng shop × {actual, BAU, FULL_TREND, NAIVE3, RAW_TREND} cho tổng `horizon` tháng sau.
    → Bước 7 dùng lại hàm này cho backtest chính thức."""
    if kappa is None:
        kappa, _, _ = calibrate_kappa(df, [o for o in CFG["KAPPA_ORIGINS"]
                                           if o + pd.DateOffset(months=horizon) <= origin], metric,
                                      last_actual=origin)
    se = estimate_season(df, origin, metric, shrink=shrink)
    if not day_adjust:
        se = {**se, "s_used": se["s_used"] * 0, "no_days": True}
    life = estimate_lifecycle(df, origin) if use_life else None
    lt = level_trend(df, origin, se, metric, window=window, life=life)
    fm = pd.date_range(origin + pd.DateOffset(months=1), periods=horizon, freq="MS")
    out = pd.DataFrame(index=lt.index)
    out["actual"] = df.loc[df["month"].isin(fm)].groupby("shop_id")[metric].sum().reindex(lt.index).fillna(0)
    out["BAU"] = forecast_path(lt, se, kappa, origin, horizon, life).sum(axis=1)
    out["FULL_TREND"] = forecast_path(lt, se, 1.0, origin, horizon, life).sum(axis=1)
    hist = df.loc[df["month"].between(origin - pd.DateOffset(months=window - 1), origin) & df["in_scope"]]
    out["NAIVE3"] = (hist.loc[hist["month"].gt(origin - pd.DateOffset(months=CFG["NAIVE_WINDOW"]))]
                         .groupby("shop_id")[metric].mean().reindex(lt.index).fillna(0) * horizon)
    hh = hist.assign(t=month_diff(hist["month"], pd.Series(origin, index=hist.index)).astype(float))
    g = hh.groupby("shop_id")
    tb, yb = g["t"].transform("mean"), g[metric].transform("mean")
    b = (((hh["t"] - tb) * (hh[metric] - yb)).groupby(hh["shop_id"]).sum()
         / ((hh["t"] - tb) ** 2).groupby(hh["shop_id"]).sum().replace(0, np.nan)).fillna(0)
    a0 = yb.groupby(hh["shop_id"]).first() - b * tb.groupby(hh["shop_id"]).first()
    H = np.arange(1, horizon + 1)
    raw = np.clip(a0.to_numpy()[:, None] + b.to_numpy()[:, None] * H[None, :], 0, None).sum(axis=1)
    out["RAW_TREND"] = pd.Series(raw, index=a0.index).reindex(lt.index).fillna(0)
    out["age_origin"] = lt["age_origin"]
    out.attrs.update({"kappa": kappa, "B": se["B"], "origin": origin})
    return out


def score(bt, col):
    A = bt["actual"]
    return {"WAPE": float((bt[col] - A).abs().sum() / A.sum()), "Bias": float((bt[col].sum() - A.sum()) / A.sum())}

# ---------------------------------------------------------------- phần thêm cho Bước 6 và Bước 7
def panel_tu_shop_month(sm, shop, thang_cuoi="2026-09-01"):
    """Bảng shop × tháng (01/2025 đến thang_cuoi) cho mọi shop trong `shop`, với các cột Bước 2 dùng:
    signed_contracts = số contract ký tại shop (cột hd_ky của Bước 1), funded_volume, first_seen_month (tháng đầu tiên
    shop có hồ sơ hoặc contract), age, dim, in_scope, valid, is_physical, SALESROOM_PRODUCT, shop_category."""
    months = pd.date_range(CFG["FIRST_MONTH"], thang_cuoi, freq="MS")
    grid = pd.MultiIndex.from_product([shop.skp_salesroom.astype(str), months], names=["shop_id", "month"]).to_frame(index=False)
    s = sm.assign(shop_id=sm.skp_salesroom.astype(str), month=pd.to_datetime(sm.thang))
    s = s.loc[s.month.le(thang_cuoi), ["shop_id", "month", "hd_ky", "ho_so", "so_tien"]]
    p = grid.merge(s, on=["shop_id", "month"], how="left").fillna({"hd_ky": 0, "ho_so": 0, "so_tien": 0})
    p = p.rename(columns={"hd_ky": "signed_contracts", "so_tien": "funded_volume"})
    first = p.loc[p.ho_so.gt(0) | p.signed_contracts.gt(0)].groupby("shop_id").month.min().rename("first_seen_month")
    p = p.join(first, on="shop_id")
    p["age"] = month_diff(p["month"], p["first_seen_month"])
    p["dim"] = p["month"].dt.days_in_month
    p["moy"] = p["month"].dt.month
    p["in_scope"] = p["age"].ge(0)
    p["valid"] = p["age"].ge(1)
    p["is_physical"] = True
    info = shop.assign(shop_id=shop.skp_salesroom.astype(str))[["shop_id", "salesroom_product", "salesroom_category"]]
    p = p.merge(info.rename(columns={"salesroom_product": "SALESROOM_PRODUCT", "salesroom_category": "shop_category"}),
                on="shop_id", how="left")
    return p.sort_values(["shop_id", "month"], ignore_index=True)


def bau_tai(phys, origin, kappa=None):
    """BAU contract bán tại shop (trung bình 6 tháng sau `origin`) của mọi shop trong phys, chỉ dùng dữ liệu đến origin.
    Trả về (bảng shop có cột bau, level, trend_label, bau_method; các tham số đã ước lượng)."""
    origin = pd.Timestamp(origin)
    old_last = CFG["LAST_ACTUAL"]
    CFG["LAST_ACTUAL"] = origin
    try:
        d = phys.loc[phys["month"].le(origin)]
        kap_origins = [o for o in CFG["KAPPA_ORIGINS"] if o + pd.DateOffset(months=CFG["HORIZON"]) <= origin]
        if kappa is None:
            kappa, _, _ = calibrate_kappa(d, kap_origins, last_actual=origin)
        se = estimate_season(d, origin)
        life = estimate_lifecycle(d, origin)
        lt = level_trend(d, origin, se, life=life)
        fm = pd.date_range(origin + pd.DateOffset(months=1), periods=CFG["HORIZON"], freq="MS")
        F = forecast_path(lt, se, kappa, origin, life=life)
        last = d.loc[d["month"].eq(origin)].set_index("shop_id")
        never = last.index[last["first_seen_month"].isna() | last["first_seen_month"].gt(origin)]
        launch = last.index[last["age"].eq(0)]
        moi = last.index[last["age"].between(0, 5)]
        # shop có mức nền bằng 0: tỷ lệ nền thực nghiệm
        zr = zero_base_rates(d, kap_origins)
        zero = lt.index[lt["level"].le(0)]
        rate = lt.loc[zero, "n_valid"].map(zr["rate"]).fillna(zr["rate"].iloc[-1])
        F_zero = pd.DataFrame(rate.to_numpy()[:, None] * season_factor(fm, se)[None, :], index=zero, columns=fm)
        # shop mới mở trong tháng origin: trung vị mức nền của shop mới cùng cỡ × ngành
        info = last[["shop_category", "SALESROOM_PRODUCT"]]
        new_lv = (lt.join(info).loc[lambda x: x.index.isin(moi) & x["level"].gt(0)]
                  .groupby(["shop_category", "SALESROOM_PRODUCT"])["level"].median())
        lv = pd.Series([new_lv.get((info.at[s, "shop_category"], info.at[s, "SALESROOM_PRODUCT"]), new_lv.median())
                        for s in launch], index=launch, dtype=float)
        F_launch = pd.DataFrame(lv.to_numpy()[:, None] * life["f"](np.arange(1, CFG["HORIZON"] + 1))[None, :]
                                * season_factor(fm, se)[None, :], index=launch, columns=fm)
        F_never = pd.DataFrame(0.0, index=never, columns=fm)
        F_all = pd.concat([F.drop(index=zero), F_zero, F_launch, F_never])
        F_all = F_all.loc[~F_all.index.duplicated()]
        out = pd.DataFrame(index=last.index)
        out["bau"] = F_all.reindex(out.index).mean(axis=1).fillna(0.0)
        out = out.join(lt[["level", "trend_label", "n_valid"]])
        out["bau_method"] = np.select([out.index.isin(launch), out.index.isin(never), out["level"].le(0)],
                                      ["peer_new_shop_median", "zero_never_sold", "zero_level_base_rate"],
                                      default="level×trend×season")
        return out, {"kappa": kappa, "B": se["B"], "amp": life["amp"], "tau": life["tau"]}
    finally:
        CFG["LAST_ACTUAL"] = old_last
