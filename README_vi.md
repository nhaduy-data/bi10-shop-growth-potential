# BI10 Round 3 – How big can this shop become?

Bài phân tích trả lời câu hỏi của đề: một shop có thể tăng thực tế đến đâu, cái gì đang kìm shop lại, và ban quản lý bán hàng nên dồn nguồn lực vào shop nào.

Mỗi shop có 4 con số, tính ở 4 bước khác nhau và không dùng lẫn cho nhau:
- **Current Actual** (Bước 1): shop đang bán bao nhiêu contract mỗi tháng (trung bình 07, 08, 09/2026).
- **Business-as-Usual – BAU** (Bước 2): shop sẽ bán bao nhiêu mỗi tháng từ 10/2026 đến 03/2027 nếu công ty không thay đổi gì.
- **Attainable Potential** (Bước 3): shop bán được bao nhiêu nếu làm tốt bằng 1/4 số shop cùng loại đang làm.
- **Addressable Market Ceiling** (Bước 4): mức tối đa về lý thuyết mà thị trường của tỉnh cho phép.

**Opportunity gap** = Attainable Potential − BAU, là phần shop tăng thêm được nhờ can thiệp (Bước 5). Bước 6 xếp ưu tiên shop theo gap, Bước 7 kiểm tra các con số tin được đến đâu.

---

## 1. Các file trong bài

**Notebook phân tích** (chạy theo thứ tự từ trên xuống):
- `BI10_R03_EDA.ipynb`: khám phá dữ liệu, tìm lỗi và chọn cách xử lý.
- `BI10_R03_clean.ipynb`: làm sạch dữ liệu, ghi ra thư mục `clean_data/`.
- `BI10_R03_Buoc0.ipynb`: Bước 0, hiểu tình hình kinh doanh.
- `Bước 1/BI10_R03_Buoc1.ipynb`: Bước 1, Current Actual.
- `Bước 2/BI10_R03_Buoc2_Nhi.ipynb`: Bước 2, BAU.
- `Bước 3/BI10_R03_Buoc3_Duy.ipynb`: Bước 3, Attainable Potential, kèm kiểm chứng chỉ nâng tỷ lệ (mục 3.10).
- `Bước 4/Task4_Addressable_Market_Ceiling_Giang.ipynb`: Bước 4, Addressable Market Ceiling.
- `Bước 5/BI10_R03_Buoc5.ipynb`: Bước 5, opportunity gap và nguyên nhân.
- `Bước 6/BI10_R03_Buoc6.ipynb`: Bước 6, xếp ưu tiên và lộ trình triển khai.
- `Bước 7/BI10_R03_Buoc7.ipynb`: Bước 7, độ tin cậy và cách kiểm chứng.

**File Python dùng chung** (đặt ở thư mục gốc):
- `r3_db.py`: mở dữ liệu sạch bằng DuckDB. Lần chạy đầu tiên, file này nạp các file CSV trong `clean_data/` vào `output/r3_clean.duckdb` (mất vài phút); các lần sau chỉ mở file này.
- `load_clean.py`: đọc một file CSV sạch với đúng kiểu dữ liệu.
- `r3_tiem_nang.py`: các hàm viết lại phép tính của Bước 1, Bước 3, Bước 4 và Bước 5, để Bước 5, 6, 7 tính lại kết quả khi đổi giả định (ví dụ đổi mức benchmark, hoặc đứng ở một tháng trong quá khứ).
- `r3_bau.py`: các hàm BAU của Bước 2 (chép nguyên văn từ notebook Bước 2), cộng thêm hàm `bau_tai` để dựng BAU ở một tháng bất kỳ. Bước 6 và Bước 7 dùng file này.

**Dữ liệu ngoài:** `Bước 4/external_data.xlsx` (mô tả ở mục 5).

**Ảnh biểu đồ cho slide** (chữ tiếng Anh, notebook tự lưu khi chạy): `hinh_buoc0/`, `Bước 1/hinh/`, `Bước 5/hinh/`, `Bước 6/hinh/`, `Bước 7/hinh/`.

---

## 2. Cách chạy lại

1. Cài Python 3 và các thư viện:
   `pip install duckdb pandas numpy scipy matplotlib openpyxl jupyter`
2. Đặt dữ liệu của Ban tổ chức vào thư mục `Round3_BI10_dataset/`.
3. Chạy `BI10_R03_clean.ipynb` để tạo thư mục `clean_data/`. Thư mục này (khoảng 1,9 GB) và file `output/r3_clean.duckdb` (khoảng 600 MB) không có trong file nén vì quá nặng; chạy bước này là tạo lại được.
4. Chạy lần lượt Bước 0 đến Bước 7. Mỗi notebook tự tìm thư mục gốc của bài (thư mục có `Bước 1`), nên mở notebook từ thư mục gốc hay từ thư mục của bước đều chạy được.

Thời gian chạy: Bước 1 khoảng 1 phút, Bước 4 khoảng 1 phút, các bước còn lại dưới 30 giây mỗi bước (chưa tính lần đầu nạp dữ liệu vào DuckDB).

---

## 3. Nội dung từng bước

### Bước 0. Hiểu tình hình kinh doanh – `BI10_R03_Buoc0.ipynb`
Vẽ bức tranh kinh doanh bằng số thật trước khi phân tích từng shop: quy mô mạng lưới, doanh số dồn vào bao nhiêu shop, tăng trưởng đến từ mở thêm shop hay từ mỗi shop bán nhiều hơn, contract của từng sản phẩm ghi tại shop hay ở kênh online, rủi ro, và các giới hạn của dữ liệu.
- Kết quả chính: tăng trưởng đến từ mở thêm shop; mỗi shop có hồ sơ vẫn chỉ khoảng 8–9 hồ sơ mỗi tháng. Trong quý 3/2026, 35% shop Active không ký được contract nào; 10% shop đứng đầu ký 51% tổng số contract.
- Đầu ra: không ghi file.

### Bước 1. Current Actual – `Bước 1/BI10_R03_Buoc1.ipynb`
Tính KPI của từng shop theo từng tháng (01/2025 – 09/2026) và Current Actual. Doanh số của shop được tách thành các phần mà ban quản lý tác động được:

```
contract bán trực tiếp = số SA × số hồ sơ mỗi SA × (1 − tỷ lệ bị từ chối − tỷ lệ hủy)
Current Actual         = contract bán trực tiếp + contract cross-sell
```

- SA là nhân viên làm hồ sơ vay tại shop; số SA được đếm theo người thực sự làm hồ sơ trong tháng.
- Cross-sell: lead do shop tạo ra được nối với contract theo đúng 3 điều kiện của đề (cùng khách, cùng sản phẩm, lead được giao trước hoặc cùng lúc khách nộp hồ sơ). Mỗi contract chỉ ghi công cho lead được giao gần nhất, trong vòng 30 ngày. Contract ký ở nơi khác với shop tạo lead là cross-sell của shop đó.
- Rủi ro: tỷ lệ contract có khách trễ hạn ít nhất một trong 4 kỳ trả đầu, đo trên contract ký từ 03/2025 đến hết 05/2026.
- Kết quả chính: Current Actual của các shop Active có mặt bằng là 39.450 contract mỗi tháng, trong đó cross-sell 1.786.
- Giới hạn: bảng leads có 1,87 triệu dòng với cột `sample_weight` bằng 19,66, nhưng StructureTable không mô tả cột này. Bài đếm mỗi dòng là một lead và không nhân trọng số.
- Đầu ra (thư mục `Bước 1/`): `shop_month.csv` (một shop trong một tháng), `shop_current.csv` (một shop: Current Actual và KPI quý 3/2026), `shop_goods_mix.csv` (nhóm hàng của từng shop), `shop_lead_result.csv` (kết quả lead của từng shop), `lead_contract_match.csv` (contract được ghi công cho lead), và hai bảng đầu vào cho Bước 2 (mục 1.9): `shop_month_kpi.csv` (KPI mỗi shop mỗi tháng, đặt tên cột theo Bước 2) và `cross_sell_attribution.csv` (từng contract cross-sell đã ký).

### Bước 2. BAU – `Bước 2/BI10_R03_Buoc2_Nhi.ipynb`
Dự báo mỗi shop sẽ bán bao nhiêu từ 10/2026 đến 03/2027 nếu để yên. BAU của shop = mức hiện tại của shop × phần xu hướng 6 tháng gần nhất còn kéo dài × đường đi theo tuổi của shop (shop mới bán cao ở những tháng đầu rồi giảm dần) × số ngày và mùa vụ của từng tháng. Xu hướng của shop bán ít được kéo về gần mức chung, vì doanh số của các shop này lên xuống chủ yếu do ngẫu nhiên.
- Kết quả chính: BAU bán tại shop là 37.734 contract mỗi tháng; cộng cross-sell ký ở nơi khác là 39.272, gần bằng Current Actual. Không can thiệp thì mạng lưới hiện có đứng yên.
- Đầu vào: `Bước 1/shop_month_kpi.csv`, `Bước 1/cross_sell_attribution.csv` (do Bước 1 tạo ở mục 1.9), `Round3_BI10_dataset/salesroom.xlsx`.
- Đầu ra (thư mục `Bước 2/`): `shop_bau.csv` (một shop: BAU theo contract và tiền, xu hướng), `shop_bau_monthly.csv` (BAU từng tháng), `shop_bau_dictionary.csv` (giải thích cột), `bau_params.json` (các tham số đã ước lượng).

### Bước 3. Attainable Potential – `Bước 3/BI10_R03_Buoc3_Duy.ipynb`
So mỗi shop với các shop giống nó (peer group: cùng cỡ shop, cùng ngành hàng, cùng kiểu làm hồ sơ, cùng tỉnh). Benchmark là mức mà 1/4 số shop tốt nhất trong nhóm đã đạt được. KPI nào của shop kém hơn benchmark thì nâng lên bằng benchmark, rồi tính lại số contract. Hai giới hạn giữ con số thực tế:
- chỉ giảm tỷ lệ bị từ chối ở shop có đủ 30 contract để đo rủi ro và khách không trễ hạn nhiều hơn mức chung của nhóm;
- kết quả không vượt số contract mà 1/4 shop tốt nhất của nhóm đang ký.
- Kết quả chính: Attainable Potential trước khi áp trần thị trường là 59.861 contract mỗi tháng, cao hơn BAU 52%.
- Đầu vào: `Bước 1/shop_current.csv`, `Bước 2/shop_bau.csv`.
- Đầu ra: `output/shop_attainable.csv`.

**Kiểm chứng: chỉ nâng tỷ lệ, giữ nguyên số hồ sơ (mục 3.10, theo cách làm của Nguyên)**

Attainable Potential ở trên nâng cả số hồ sơ lẫn tỷ lệ. Mục 3.10 đo riêng phần tăng không cần thêm khách: giữ nguyên số hồ sơ và số lead của shop, chỉ nâng tỷ lệ hồ sơ ký được và số contract cross-sell trên mỗi lead.
- Cách làm: chỉ tính shop không phải shop mới, có từ 30 hồ sơ (hoặc 30 lead) trong quý 3/2026; làm mượt tỷ lệ của shop về mức chung của peer (như cộng thêm 30 hồ sơ có tỷ lệ bằng mức chung); so với một shop donor có thật gần mức 75% của peer; giữ phần tăng bằng 0 ở shop có tỷ lệ trễ hạn cao hơn peer group.
- Kết quả: 1.342 shop đủ dữ liệu; phần tăng nhờ tỷ lệ là 1.355,7 contract mỗi tháng, gấp 2,2 lần phần tỷ lệ trong Attainable Potential của cùng các shop (613,8). Lý do: 90% các shop này chạm giới hạn theo nhóm, nên phần tỷ lệ bị cắt nhiều. Vì vậy phần tỷ lệ trong Attainable Potential là con số thận trọng.
- Các shop đủ dữ liệu chỉ giữ 13% phần Attainable Potential cao hơn BAU; 87% còn lại ở shop nhỏ và shop mới, nơi không đủ hồ sơ để đo tỷ lệ của riêng shop. Vì vậy Attainable Potential chính vẫn dùng cách so với peer group cho mọi shop.
- Kiểm tra theo thời gian: dùng tỷ lệ ký quý 2 để đoán quý 3 trên 815 shop, tỷ lệ làm mượt có sai số 0,073, so với 0,080 khi dùng tỷ lệ thật và 0,094 khi chỉ dùng mức chung.
- Đầu ra: `Bước 3/shop_kiem_chung_ty_le.csv`.

### Bước 4. Addressable Market Ceiling – `Bước 4/Task4_Addressable_Market_Ceiling_Giang.ipynb`
Tính trần thị trường của từng tỉnh: số contract mỗi năm trên 1.000 người trong độ tuổi lao động (penetration) của mỗi tỉnh; lấy mức chuẩn là trung vị penetration của nhóm 1/4 số tỉnh cao nhất; trần của tỉnh = mức chuẩn × số người trong độ tuổi lao động của tỉnh (không thấp hơn mức đang bán). Trần được kiểm tra lại bằng một cách thứ hai dựa trên doanh thu bán lẻ.
- Kết quả chính: trần toàn quốc là 586.892 contract mỗi năm, gấp 1,46 lần mức đang bán (đo trên 01–09/2026); đổi cách chọn mức chuẩn thì trần gấp 1,20–1,48 lần.
- Đầu vào: `clean_data/` (salesroom, contract, leads), `Bước 4/external_data.xlsx`.
- Đầu ra (thư mục `Bước 4/task4_output/`): các file `csv/s1` đến `csv/s7` (dữ liệu ngoài đã kiểm tra, bảng shop, contract theo shop × tháng, penetration và trần theo tỉnh, trần của shop) và biểu đồ trong `figures/`.

### Bước 5. Opportunity gap và nguyên nhân – `Bước 5/BI10_R03_Buoc5.ipynb`
Ghép 4 con số của mỗi shop, kiểm tra thứ tự, tính opportunity gap theo contract và tiền cho vay, tìm nguyên nhân và hành động cho từng shop.
- Trần của Bước 4 được tính lại trên cùng quý 3/2026 như Current Actual, và trần tỉnh được chia cho shop theo mức thực tế của từng shop. Lý do: khi tính trên 01–09/2026 và chia đều theo cỡ shop, 1.435 shop có trần thấp hơn mức đang bán. Sau khi tính lại, không shop nào sai thứ tự.
- Kết quả chính: Current Actual 39.450 · BAU 39.272 · Attainable Potential 55.595 · Addressable Market Ceiling 65.959 contract mỗi tháng. Opportunity gap là 16.324 contract và 222,9 tỷ đồng mỗi tháng (41,6% BAU).
- Gap đến từ: số hồ sơ mỗi SA 42,7%, số SA 32,1%, chặn đà giảm của shop 18,8%, cross-sell 4,6%, tỷ lệ hủy 1,4%, tỷ lệ bị từ chối 0,4%.
- Cầu nối từ BAU lên Attainable Potential, xếp theo mức chắc chắn: BAU 39.272 → ký tốt hơn trên khách hiện có +1.045 (sửa quy trình, làm được ngay; trên 1.342 shop đủ dữ liệu, cách kiểm chứng ở Bước 3 cho mức gấp 4,1 lần bậc này, nên đây là con số thận trọng) → giữ mức hiện tại +3.069 → thêm SA +5.247 (chi phí nhân sự; mỗi SA thêm chỉ được tính 1,54 contract mỗi tháng, so với 3,83 mà một SA đang làm) → tăng hồ sơ mỗi SA +6.964 (cần thêm khách; chỉ 14,6% shop dưới benchmark tự đạt được sau hai quý, nên cần thử trước) → Attainable Potential 55.595. Ảnh: `Bước 5/hinh/b5_02_bridge_bau_to_ap.png`.
 Trần thị trường cắt 20,7% phần tăng, ở 8 tỉnh; 26 tỉnh còn lại vẫn dưới trần kể cả khi mọi shop đạt Attainable Potential. TP. Hồ Chí Minh, TP. Hà Nội và Đồng Nai giữ 72,8% phần bị cắt vì có nhiều shop nhất. Ảnh: `Bước 5/hinh/b5_03_ceiling_by_province.png`. 379 shop có rủi ro cao.
- Hai shop thật cùng doanh số nhưng gap khác nhau (mục 5.8): shop 90118566 và 102169356, cùng ở Đắk Lắk, cùng ký 4,33 contract mỗi tháng, gap là 0 và 2,93.
- Đầu ra (thư mục `Bước 5/`): `shop_gap.csv` (một shop: 4 con số, gap, phần gap theo từng KPI, nguyên nhân chính, hành động), `province_ceiling_q3.csv` (trần của 34 tỉnh tính trên quý 3/2026).

### Bước 6. Xếp ưu tiên và lộ trình – `Bước 6/BI10_R03_Buoc6.ipynb`
Chia shop thành 4 nhóm theo gap (ngưỡng 2 contract mỗi tháng), độ tin cậy của con số và rủi ro: Đầu tư ngay, Pilot (làm thử trước), Giữ nguyên, Risk cao. Kiểm tra các nhóm có khác nhau rõ và có ổn định không, xếp hành động theo tác động và chi phí, đưa ra lộ trình 3 giai đoạn và kết quả kỳ vọng.
- Kết quả chính: Đầu tư ngay 184 shop, Pilot 2.915 shop (giữ 72% tổng gap), Giữ nguyên 8.274 shop, Risk cao 379 shop. Nếu các shop Đầu tư ngay và Pilot đạt 50% gap, mạng lưới ký thêm khoảng 6.175 contract mỗi tháng (15,7% BAU).
- Đầu ra: `Bước 6/shop_priority.csv` (một shop: 4 con số, gap, nguyên nhân, hành động, nhãn độ tin cậy, nhóm ưu tiên).

### Bước 7. Độ tin cậy và cách kiểm chứng – `Bước 7/BI10_R03_Buoc7.ipynb`
Backtest cách dự báo BAU, kiểm tra nhãn độ tin cậy, kiểm tra giả định "thêm SA thì bán thêm" bằng các trường hợp đã xảy ra, thử đổi các giả định chính, và đề xuất thử nghiệm có nhóm đối chứng.
- Kết quả chính: BAU sai ít hơn cách "trung bình 3 tháng trước" (WAPE 0,460 so với 0,474–0,475). Shop từ 1 lên khoảng 2 SA ký thêm 2,7–3,4 contract mỗi tháng so với shop giữ 1 SA. Tổng gap dao động từ 11.892 đến 20.626 contract mỗi tháng khi đổi giả định.
- Đầu ra: `Bước 7/xsell_theo_so_ngay.csv` (cross-sell của từng shop theo tháng với giới hạn nối lead 30 và 90 ngày). Notebook tự tạo lại file này nếu có `output/r3_clean.duckdb`.

---

## 4. Công cụ và phương pháp

Bài dùng hai công cụ chính:
- **DuckDB (SQL)** để đọc và nối các file lớn: file leads khoảng 1,3 GB, file contract khoảng 580 MB. DuckDB chạy câu lệnh SQL thẳng trên file mà không cần nạp toàn bộ vào bộ nhớ, và câu lệnh SQL dễ đọc lại để kiểm tra.
- **Python** (pandas, numpy, scipy, matplotlib) để tính KPI, dự báo, kiểm định thống kê và vẽ biểu đồ.

Bài không dùng machine learning. Mọi con số đều là phép tính, so sánh với shop cùng loại, hoặc kiểm định thống kê đơn giản, nên ban quản lý lần lại được từ con số cuối cùng về dữ liệu gốc. Thay cho một mô hình phức tạp, bài kiểm tra từng bước bằng số liệu cũ (backtest) và thử đổi giả định (sensitivity test).

Công cụ và phương pháp của từng bước:

**Bước 0 – Hiểu tình hình kinh doanh**
- Dùng gì: truy vấn SQL trên DuckDB; theo dõi các nhóm shop bắt đầu hoạt động cùng quý (cohort).
- Giúp gì: tách tăng trưởng do mở thêm shop khỏi tăng trưởng của từng shop.
- Vì sao phù hợp: chỉ cần đếm và cộng, nhưng phải đọc file lớn.

**Bước 1 – Current Actual**
- Dùng gì: SQL nối lead với contract theo 3 điều kiện của đề; hàm `ROW_NUMBER` để giữ đúng một lead gần nhất cho mỗi contract; công thức tách doanh số thành số SA, hồ sơ mỗi SA, tỷ lệ bị từ chối, tỷ lệ hủy và cross-sell.
- Giúp gì: mỗi contract chỉ được tính cho một shop; doanh số được tách thành các phần ứng với một việc ban quản lý làm được (thêm SA, đào tạo SA, giảm hủy, chốt lead).
- Vì sao phù hợp: công thức kiểm tra được trên từng shop (tích các phần bằng đúng số contract).

**Bước 2 – BAU**
- Dùng gì: so cùng một shop giữa hai tháng liền nhau để đo mùa vụ mà không lẫn việc mở thêm shop; khớp đường cong (`curve_fit` của scipy) cho đường đi theo tuổi của shop; đường thẳng xu hướng 6 tháng của từng shop; kéo xu hướng của shop ít dữ liệu về gần mức chung (Empirical Bayes); đo trên số liệu cũ xem bao nhiêu phần xu hướng thật sự kéo dài sang 6 tháng sau.
- Giúp gì: dự báo riêng cho từng shop, không gán cho shop mức tăng chung của mạng lưới (vốn đến từ mở thêm shop).
- Vì sao phù hợp: 3/4 số shop bán dưới 4 contract mỗi tháng nên doanh số tháng lên xuống phần lớn do ngẫu nhiên; kéo dài xu hướng thô thì dự báo sai gấp đôi (Bước 7).

**Bước 3 – Attainable Potential**
- Dùng gì: so với peer group; benchmark là mức mà 1/4 số shop tốt nhất cùng nhóm đạt được; hai giới hạn về rủi ro và về số contract của shop tốt nhất nhóm.
- Giúp gì: cho biết shop kém shop cùng loại ở KPI nào và tăng được bao nhiêu.
- Vì sao phù hợp: dễ giải thích với ban quản lý ("nếu shop này làm tốt bằng 1/4 số shop cùng loại, shop sẽ ký N contract mỗi tháng"), và mức này đã có nhiều shop thật làm được.
- Mục 3.10 dùng thêm: làm mượt tỷ lệ về mức chung của peer (credibility weighting, như cộng thêm 30 hồ sơ có tỷ lệ bằng mức chung) và so với một shop donor có thật. Giúp gì: không coi một shop ít hồ sơ là kém chỉ vì ngẫu nhiên. Vì sao phù hợp: kiểm tra theo thời gian cho thấy tỷ lệ làm mượt đoán tỷ lệ quý sau sát hơn tỷ lệ thật (sai số 0,073 so với 0,080).

**Bước 4 – Addressable Market Ceiling**
- Dùng gì: ghép dữ liệu ngoài theo tỉnh với shop; penetration theo tỉnh; mức chuẩn là trung vị của nhóm 1/4 tỉnh cao nhất; kiểm tra chéo bằng doanh thu bán lẻ; hồi quy giữa penetration và thu nhập (theo logarit).
- Giúp gì: cho biết tỉnh nào còn nhiều khách chưa khai thác, tỉnh nào đã gần hết.
- Vì sao phù hợp: dữ liệu của công ty chỉ biết shop nằm ở tỉnh nào, nên tỉnh là cấp chi tiết nhỏ nhất ghép được với dữ liệu ngoài.

**Bước 5 – Opportunity gap và nguyên nhân**
- Dùng gì: chia gap của mỗi shop cho từng KPI theo logarit của mức tăng của KPI đó; binomial test (kiểm định nhị thức) để tìm shop có tỷ lệ trễ hạn cao hơn shop cùng loại một cách chắc chắn; so gap giữa các nhóm shop để xét từng nhóm nguyên nhân.
- Giúp gì: mỗi shop có một nguyên nhân chính và một hành động cụ thể.
- Vì sao phù hợp: các phần của gap cộng lại đúng bằng tổng gap; kiểm định nhị thức tránh gắn nhãn rủi ro cao cho shop chỉ vì ít contract.

**Bước 6 – Xếp ưu tiên**
- Dùng gì: chọn ngưỡng gap bằng cách xem bao nhiêu phần trăm tổng gap nằm ở bao nhiêu phần trăm số shop; chi-square test (kiểm định chi bình phương) để tìm shop có doanh số biến động bất thường; chạy lại toàn bộ Bước 2 đến Bước 6 với dữ liệu đến 06/2026 để đo độ ổn định của các nhóm; power analysis (tính cỡ mẫu) để tính số shop cần cho pilot.
- Giúp gì: quy tắc chia nhóm có ngưỡng bằng số cụ thể và lý do chọn ngưỡng; biết trước danh sách thay đổi bao nhiêu sau một quý.
- Vì sao phù hợp: ban quản lý tự áp được quy tắc cho quý sau.

**Bước 7 – Độ tin cậy và kiểm chứng**
- Dùng gì: backtest (đứng ở 12/2025 và 03/2026, dự báo 6 tháng sau rồi so với số thật), đo sai số bằng WAPE (tổng sai lệch tuyệt đối / tổng thực tế) và so với cách "trung bình 3 tháng trước"; difference-in-differences (so mức tăng của shop có thêm SA với mức tăng của shop giữ 1 SA trong cùng các tháng); sensitivity test với 5 trường hợp giả định.
- Giúp gì: cho biết con số sai lệch khoảng bao nhiêu, kết luận nào vững, kết luận nào phụ thuộc giả định.
- Vì sao phù hợp: chỉ dùng số liệu đã xảy ra, không cần thêm giả định mới.

---

## 5. Dữ liệu ngoài: `Bước 4/external_data.xlsx`

File có 6 bảng: số liệu gốc theo 63 tỉnh, thành cũ (dân số và diện tích, lực lượng lao động, tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng, thu nhập bình quân), bảng đổi 63 tỉnh cũ sang 34 tỉnh mới, và bảng tổng hợp theo 34 tỉnh mới mà notebook Bước 4 đọc.

Mục này tóm tắt 5 điểm theo yêu cầu đề. Mô tả chi tiết từng bộ dữ liệu (nguồn, đường link, cách ghép, insight, giả định và sai lệch) nằm ở file `Bước 4/README_external_data.docx`.

### Điểm 1. Data source and reporting period
- Nguồn: Cục Thống kê (National Statistics Office), cơ sở dữ liệu trực tuyến pxweb.nso.gov.vn:
  - Diện tích, dân số và mật độ dân số phân theo địa phương: https://pxweb.nso.gov.vn/sq/8bde56c8-414f-4c2b-ad5a-1618890f3411
  - Lực lượng lao động từ 15 tuổi trở lên phân theo địa phương: https://pxweb.nso.gov.vn:443/sq/c9e06d35-e351-4a80-8122-e27b68988af4
  - Thu nhập bình quân một lao động đang làm việc phân theo địa phương: https://pxweb.nso.gov.vn:443/sq/f4d50d24-ab0c-4a0f-84ce-239d5cb8a090
  - Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành phân theo địa phương: https://pxweb.nso.gov.vn:443/sq/ee34506c-b545-46f7-b87e-dc2492a9dba7
- Thời kỳ: năm 2025. Dân số và diện tích là số năm 2025 (diện tích tại 31/12/2023); lực lượng lao động, thu nhập và bán lẻ là số sơ bộ năm 2025.
- Danh sách tỉnh cũ gộp vào tỉnh mới: Nghị quyết 202/2025/QH15 ngày 12/6/2025 về sắp xếp đơn vị hành chính cấp tỉnh, có hiệu lực từ ngày thông qua; chính quyền các tỉnh mới hoạt động từ 01/7/2025. Bảng tra lấy từ https://xaydungchinhsach.chinhphu.vn/chi-tiet-34-don-vi-hanh-chinh-cap-tinh-tu-12-6-2025-119250612141845533.htm

### Điểm 2. Geographic coverage and level of granularity
- Phủ toàn bộ 63 tỉnh, thành cũ, gộp thành 34 tỉnh, thành mới.
- Chi tiết đến cấp tỉnh. Không có số liệu cấp xã hay quanh từng shop.

### Điểm 3. Method used to map or integrate the data with internal shop information
- Số liệu của các tỉnh cũ được cộng lại thành tỉnh mới theo bảng "Sát nhập tỉnh" (dân số, diện tích, lao động, bán lẻ). Thu nhập bình quân của tỉnh mới là trung bình của các tỉnh cũ có tính theo dân số.
- Tên tỉnh được chuẩn hóa trước khi ghép: bỏ dấu, bỏ chữ "TP." hoặc "Tỉnh" ở đầu tên. Shop được ghép với tỉnh theo cột `salesroom_province`, vốn đã được đổi sang 34 tỉnh mới khi làm sạch dữ liệu.
- Kết quả ghép: 100% shop có mặt bằng (14.111 shop, trong đó 11.752 shop Active) ghép được với một tỉnh trong dữ liệu ngoài; không có shop nào không ghép được.
- Kiểm tra chất lượng: mật độ dân số tính lại (dân số / diện tích) lệch với mật độ trong file nhiều nhất 0,01%.
- Số contract của tỉnh gồm contract ký tại các shop có mặt bằng trong tỉnh và contract cross-sell ghi công cho các shop đó qua lead. Shop online không gắn với tỉnh nào nên không đưa vào.

### Điểm 4. Business relevance and additional insights
- Lực lượng lao động (người từ 15 tuổi trở lên đang làm việc hoặc tìm việc) là nhóm khách có thu nhập để vay. Số contract trên 1.000 người (penetration) cho biết công ty đã khai thác thị trường mỗi tỉnh đến đâu, so được giữa tỉnh lớn và tỉnh nhỏ.
- Penetration cao nhất (Đồng Nai, Khánh Hòa, TP. Hồ Chí Minh) gấp 8,3 lần thấp nhất (Điện Biên, Sơn La, Ninh Bình).
- Thu nhập cao hơn 1% thì penetration cao hơn khoảng 1,01% (hồi quy theo logarit), nhưng R² chỉ 0,32: thu nhập giải thích khoảng một phần ba khác biệt giữa các tỉnh, phần còn lại đến từ việc công ty có bao nhiêu shop và SA ở mỗi tỉnh. Thu nhập chỉ dùng để kiểm tra chéo, không đi vào công thức trần.
- Trần thị trường cho thấy tỉnh nào còn chỗ để tăng. Khi tính trên quý 3/2026 (Bước 5), 5 tỉnh đã ở mức chuẩn hoặc cao hơn (Đồng Nai, TP. Hồ Chí Minh, Khánh Hòa, TP. Cần Thơ, TP. Huế) nên không còn chỗ trống; trần thị trường cắt 20,7% phần tăng của Attainable Potential ở 8 tỉnh, nhiều nhất ở TP. Hồ Chí Minh; 26 tỉnh còn lại vẫn dưới trần kể cả khi mọi shop đạt Attainable Potential. Ở các tỉnh bị cắt, thêm nguồn lực bán ít hiệu quả.
- Doanh thu bán lẻ được dùng để tính trần theo cách thứ hai và kiểm tra chéo trần tính theo số người trong độ tuổi lao động.

### Điểm 5. Key assumptions, limitations, and potential biases
- Mức chuẩn lấy từ các tỉnh mà chính công ty đang khai thác tốt nhất, không phải nhu cầu vay thật của người dân. Các tỉnh đã ở mức chuẩn trở lên có trần bằng mức đang bán, nên trần ở các tỉnh này có thể thấp hơn nhu cầu thật.
- Đổi cách chọn mức chuẩn thì trần toàn quốc đổi từ 1,20 đến 1,48 lần mức đang bán, nên trần nên được đọc như một khoảng.
- Số liệu ngoài là của năm 2025, doanh số là năm 2026; dân số và thu nhập có thể đã thay đổi trong khoảng thời gian này.
- Cột "Dân số thuộc tuổi lao động" là lực lượng lao động từ 15 tuổi trở lên theo bảng gốc của Cục Thống kê, bằng 40–59% dân số mỗi tỉnh. Mẫu số này không gồm học sinh, sinh viên, người nghỉ hưu và người nội trợ (vẫn có thể vay), nhưng lại gồm nhóm 15–17 tuổi. Tỉnh có tỷ lệ lao động thấp (Hà Tĩnh 40%, Lạng Sơn 41%, Cao Bằng 42%, so với trung vị 52%) có trần thấp hơn tương đối so với quy mô dân số.
- Contract ký online không biết khách ở tỉnh nào; chỉ phần cross-sell nối được qua lead mới được tính về tỉnh của shop tạo lead. Penetration vì vậy thấp hơn thực tế, nhất là với Cash Loan, Credit Card và BNPL.
- 78% hồ sơ xe máy (TW) được ghi ở điểm bán không có trong bảng salesroom, nên không biết tỉnh của các hồ sơ này; penetration của ngành TW thấp hơn thực tế.
- Shop gần ranh giới tỉnh có thể phục vụ khách của tỉnh bên cạnh.
- Cùng một mức chuẩn được áp cho mọi ngành hàng của tỉnh; tỉnh có cơ cấu ngành hàng khác thường có thể bị tính trần lệch.
