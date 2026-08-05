# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung          |
| --------------- | ----------------- |
| Họ và tên       | Nguyễn Quang Minh |
| MSSV            | 2A202601955       |
| Khóa/Lớp        | K3                |
| Vai trò chính   | Verifier          |
| Ngày hoàn thành | 2026-08-05         |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                        | File/hàm phụ trách                                                         | Input nhận vào                                    | Output bàn giao                                   | Trạng thái   |
| ------------------------------------------ | --------------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------------------- | ------------ |
| Schema/consistency validator (pure function) | `src/verifier/schema_validator.py::validate_output`                       | 1 output case (dict) + set ID hợp lệ từ CSV        | `list[str]` lỗi (rỗng nếu hợp lệ)                   | Hoàn thành   |
| Verifier Agent (adapter cho Coordinator)   | `src/verifier/agent.py::VerifierAgent`, `load_source_data`                 | `context` từ Coordinator (`case`, `results`, `output`) | `AgentResult(ok, errors)`                           | Hoàn thành   |
| Kiểm tra toàn bộ output/ trước khi đóng gói | `scripts/validate_outputs.py::validate_all_outputs`                       | Thư mục `output/`, thư mục `data/`                 | Báo cáo lỗi theo case, trả `bool` pass/fail          | Hoàn thành   |
| Chạy pipeline 50 case + sinh trace         | `scripts/run_pipeline.py::run_pipeline`                                    | 50 file `input/EC_*.json`                          | `output/EC_*.json`, `logging/trace.jsonl`           | Hoàn thành   |
| Đóng gói ZIP nộp bài                       | `scripts/package_submission.py::package_submission`                       | `output/` đã validate                              | `output.zip` (50 file `output/EC_001..050.json`)    | Hoàn thành   |
| Test cho validator                         | `tests/verifier/test_schema_validator.py`, `tests/verifier/test_agent.py`  | Case mẫu, dữ liệu ID giả lập                        | 23 test case, tất cả pass                           | Hoàn thành   |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                                                                                    | Thành viên/module được hỗ trợ | Kết quả                                                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Phát hiện output cuối chứa field nội bộ (raw data) ngoài 7 key chuẩn README, báo lại cho Thành viên 1           | `src/coordinator/agent.py` (Thành viên 1) | Bug được fix bằng cách lọc output theo `output_keys` cố định trước khi trả về; xác nhận lại bằng script so key set với 7 key README trên toàn bộ 50 case            |
| Phân tích breakdown điểm chấm (case 96, entities 94.63, root cause 96.69, **evidence 83.55**, financial 96.63, actions 96.07) để khoanh vùng thành phần yếu nhất | Toàn nhóm                      | Xác định `evidence_ids` là thành phần thấp nhất; điều tra ra 34/50 case có evidence `seller:<id>` dù seller không phải bên chịu trách nhiệm của `primary_issue` đó |
| Đề xuất và prototype fix cho evidence không liên quan (chỉ thêm `seller:` khi `primary_issue == late_delivery_seller`) | `src/coordinator/agent.py` (Thành viên 1) | Đã verify: giảm seller evidence sai từ 34/50 case xuống 0/50; quyết định merge cuối cùng thuộc Thành viên 1 vì đây là file khóa/ownership chung                     |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                                        | File/hàm/artifact liên quan                                          | Kết quả bàn giao                                                        | Cách xác minh                                            |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Viết validator kiểm tra required key, enum, limit, evidence format, financial consistency | `src/verifier/schema_validator.py`                                    | Hàm `validate_output` trả về danh sách lỗi cụ thể theo path (`assessment.confidence`, ...) | `pytest tests/verifier -q` → 23 passed                        |
| Nạp ID hợp lệ trực tiếp từ 4 CSV (order/item/seller/payment) để chống evidence giả | `src/verifier/agent.py::load_source_data`                             | `dict[str, set[str]]` dùng chung cho mọi case, không đọc lại CSV mỗi lần validate | Đọc code + test `test_agent.py` mock `data_dir` bằng CSV nhỏ |
| Validate toàn bộ 50 output trước khi đóng gói                                | `scripts/validate_outputs.py`                                         | `All 50 outputs passed validation.`                                          | `python scripts/validate_outputs.py`                          |
| Chạy lại pipeline sau mỗi lần domain agent sửa lỗi, tái sinh `trace.jsonl`   | `scripts/run_pipeline.py`                                             | 50 file output mới + trace ghi đè (không append)                            | `python scripts/run_pipeline.py`                               |
| Đóng gói `output.zip` đúng cấu trúc `output/EC_001.json..EC_050.json`, refuse nếu validate fail | `scripts/package_submission.py`                                       | `output.zip` (50 entry, không file lạ)                                      | `python scripts/package_submission.py` + kiểm tra `zipfile.namelist()` |

Output cụ thể: `output.zip` ở root repo — 50 file JSON đúng schema, đã qua `validate_all_outputs()` (return `True`), không có case nào bị hard-gate lỗi định dạng/ID giả/refund sai action.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trước khi ghi ra `output/`, hệ thống cần một lớp kiểm tra độc lập với 4 domain agent để đảm bảo: (1) output đúng 7-key schema README, không thiếu không thừa; (2) mọi ID trong `affected_entities`/`evidence_ids` thực sự tồn tại trong CSV (chống "tự tạo ra sự kiện không tồn tại" như README §1 yêu cầu); (3) số tiền và `resolution_actions` nhất quán với nhau (`issue_full_refund` phải bằng `payment_total_brl`, `refund_freight` phải bằng `freight_total_brl`, `no_action` phải có refund = 0); (4) đủ đúng 50 file khi đóng gói ZIP, không lẫn file thừa.

### Cách triển khai

`schema_validator.py` được thiết kế thuần hàm (pure function), không đọc file hay gọi pandas — nhận `output: dict` và `source_data: dict[str, set[str]]` (tập ID hợp lệ) làm tham số, trả về `list[str]` lỗi. Việc tách I/O ra khỏi logic kiểm tra giúp test được bằng dict/set dựng tay, không cần fixture CSV thật cho mỗi test case. Validator gồm 5 bước độc lập chạy tuần tự và cộng lỗi: `_check_required_keys` (đệ quy qua schema lồng nhau `_SCHEMA`), `_check_enums_and_ranges` (enum `primary_issue`/`case_status`/`cause_code`/`party_type`/`resolution_actions`, khoảng `confidence`, rounding 2 chữ số), `_check_limits` (giới hạn 5 entity/10 evidence/3 cause/3 party/5 action theo README §6), `_check_evidence_ids` + `_check_affected_entities_exist` (regex theo 5 prefix `order/item/payment/seller/policy`, đối chiếu set ID thật), `_check_financial_consistency` (khớp refund với action và `case_status`). `VerifierAgent` (adapter) chỉ nạp `source_data` một lần lúc khởi tạo (đọc 4 CSV) rồi gọi `validate_output` — tách biệt "đọc dữ liệu" và "kiểm tra logic" đúng theo `architecture.md` §3 (Verifier chỉ đọc output + source facts, không sửa kết quả agent khác).

### Input, output và contract

| Thành phần              | Mô tả                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| Input                    | `output: dict` (1 case JSON) + `source_data: dict[str, set[str]]` (order/item/seller/payment ID) |
| Output                    | `list[str]` mô tả lỗi theo path (rỗng = hợp lệ)                                            |
| Module phụ thuộc          | `src/shared/contracts.py::AgentResult` (điền `errors`, `ok=not errors`)                     |
| Module sử dụng output     | `src/coordinator/agent.py` (gắn `_verification_errors` nếu có lỗi), `scripts/validate_outputs.py` |
| Điều kiện lỗi cần xử lý   | Thiếu key, sai type, evidence sai format/không tồn tại trong CSV, vượt limit, refund không khớp action, `case_id` không khớp tên file |

### Cách xác minh

```bash
python -m pytest tests/verifier -q
python scripts/validate_outputs.py
python scripts/package_submission.py
```

- **Kết quả mong đợi:** 23 test pass; `All 50 outputs passed validation.`; ZIP được ghi ra `output.zip` với đúng 50 entry.
- **Kết quả thực tế:** Đúng như mong đợi ở lần chạy gần nhất — 23 passed, validate pass toàn bộ 50 case, `output.zip` chứa `output/EC_001.json` … `output/EC_050.json`.
- **Artifact/log:** `output.zip` (root repo), `logging/trace.jsonl`, `logging/metadata.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** README yêu cầu "Nén folder `output/` thành file zip. Zip phải chứa đúng 50 JSON từ `EC_001.json` đến `EC_050.json`" — câu chữ này đọc được theo 2 cách: (a) file phẳng `EC_001.json` ngay gốc ZIP, hoặc (b) giữ nguyên cấu trúc thư mục `output/EC_001.json`.
- **Các phương án đã cân nhắc:**
  1. `arcname=f"{case_id}.json"` — file phẳng ở gốc ZIP, khớp sát nghĩa đen câu chữ README.
  2. `arcname=f"output/{case_id}.json"` — giữ tiền tố thư mục `output/`, khớp cách hiểu "nén folder output/ thành ZIP".
- **Phương án đã chọn:** Phương án 2 (`output/{case_id}.json`).
- **Lý do:** Sau khi thử phương án 1 và xác nhận lại yêu cầu thực tế của kỳ chấm, cấu trúc `output/EC_xxx.json` là cấu trúc được kỳ chấm chấp nhận trên thực tế (đã nộp và không bị hard-gate vì lý do cấu trúc ZIP). Ưu tiên hành vi đã được xác nhận qua nộp bài thật hơn là suy diễn thuần từ câu chữ README, vì README có thể đọc theo nhiều cách còn kết quả chấm thực tế là bằng chứng trực tiếp.
- **Bằng chứng quyết định phù hợp:** Sau khi build ZIP với `output/{case_id}.json` và nộp, điểm case (96), entities, root cause, financial, actions đều ở mức 94–97 — không có case nào bị hard-gate 0 điểm do cấu trúc ZIP.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Nộp `output.zip` theo README nhưng bị chấm 0 điểm toàn bộ, dù pipeline chạy không lỗi và `validate_outputs.py` báo pass 50/50.
- **Lệnh hoặc bước tái hiện:** `python scripts/run_pipeline.py` → `python scripts/validate_outputs.py` (pass) → mở `output/EC_001.json` và đếm số key.
- **Nguyên nhân gốc:** `Coordinator._assemble_output` (`src/coordinator/agent.py`) làm `merged.update(result.data)` cho toàn bộ `data` mà mỗi domain agent trả về, trong đó `OrderSellerAgent`/`PaymentAgent` trả kèm rất nhiều field nội bộ (`order_status`, `items`, `payment_rows`, `is_paid`, `expected_total_brl`, `late_handoff_seller_ids`, ...) để agent sau dùng làm input. Các field này lọt thẳng vào output cuối, khiến mỗi file có ~25 key thay vì đúng 7 key README quy định. `schema_validator.py` không bắt được lỗi này vì nó chỉ kiểm tra **thiếu** key required, không kiểm tra **thừa** key — nên "pass" nội bộ nhưng sai với yêu cầu "đúng schema" của `architecture.md` §5.4.
- **Cách xử lý:** Sửa `_assemble_output` để chỉ giữ lại đúng 7 key (`case_id, assessment, affected_entities, root_cause_analysis, evidence_ids, financial_resolution, resolution_actions`) khi trả về, loại bỏ toàn bộ field nội bộ dùng cho handoff giữa agent.
- **Cách xác minh sau khi sửa:** Chạy lại `run_pipeline.py` rồi so `set(output.keys())` với 7 key chuẩn cho cả 50 file — không còn case nào lệch; `pytest` vẫn pass toàn bộ.
- **Điều học được:** Một validator chỉ kiểm tra "đủ key" (required-keys check) không đồng nghĩa với "đúng schema" (exact-shape check). Với hệ thống nhiều agent handoff dữ liệu thô cho nhau, luôn cần một bước lọc rõ ràng ở biên xuất ra ngoài (Coordinator), tách bạch dữ liệu nội bộ và dữ liệu công khai — nếu không, lỗi này vô hình với chính validator nội bộ vì nó không phải lỗi "thiếu", mà là lỗi "thừa".

Việc đang xử lý (chưa chốt, thuộc ownership Thành viên 1):

- **Phạm vi bị ảnh hưởng:** Thành phần "Evidence IDs" trong điểm chấm — điểm 83.55, thấp hơn rõ rệt so với 5 thành phần còn lại (94–97). Ảnh hưởng `_assemble_output` trong `src/coordinator/agent.py`.
- **Những gì đã loại trừ:** Đã audit độc lập (tính lại từ CSV thô, không dùng code pipeline) cho toàn bộ 50 case — loại trừ khả năng sai `primary_issue`, sai financial totals, sai `affected_entities`; không có case nào lệch. Đã loại trừ nguyên nhân do format/tồn tại của evidence ID (validator pass 100%).
- **Bước tiếp theo:** Đã xác định 34/50 case có evidence `seller:<seller_id>` dù seller không phải bên chịu trách nhiệm của `primary_issue` đó (ví dụ: case `canceled_order_paid` lỗi thuộc platform nhưng vẫn dẫn evidence seller; case `late_delivery_logistics` lỗi thuộc carrier nhưng vẫn dẫn evidence seller đã giao đúng hạn). Đã prototype fix (chỉ thêm evidence `seller:` khi `primary_issue == "late_delivery_seller"`) và verify giảm được 34 → 0 case có evidence seller sai; đang chờ Thành viên 1 (owner `src/coordinator/agent.py`) merge chính thức vì đây là file có ownership riêng, Verifier không tự sửa logic domain của module khác.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Input case (`input/EC_xxx.json`, chứa `claimed_order_id`) đi qua các agent domain như thế nào trước khi thành output cuối?
2. Coordinator dùng gì để xác định thứ tự chạy agent và cách hợp nhất kết quả, thay vì mỗi agent tự ghi file riêng?
3. Verifier kiểm tra những gì mà các domain agent không tự kiểm tra được ở góc nhìn của chính agent đó?
4. Vì sao `schema_validator.py` không đọc file CSV trực tiếp mà nhận `source_data` từ ngoài truyền vào?
5. Một pipeline chạy được xem là "sẵn sàng nộp" dựa trên artifact và lệnh kiểm tra nào?

**Câu trả lời:**

1. `Coordinator.process_case` nhận case, tạo `CaseContext`, rồi gọi lần lượt `OrderSellerAgent → PaymentAgent → DeliveryAgent → PolicyAgent` theo đúng thứ tự cố định trong `architecture.md`. Mỗi agent đọc `context["results"]` của các agent chạy trước (ví dụ `PaymentAgent` cần `item_total_brl`/`freight_total_brl` mà `OrderSellerAgent` đã tính), tự truy CSV theo domain của mình (orders/items/sellers cho Order&Seller, payments cho Payment), rồi trả về `AgentResult(data, evidence_ids, ok)`. Nếu một agent `ok=False` (ví dụ không tìm thấy order), Coordinator dừng ngay và trả `_error_output` — không có agent nào chạy quá phạm vi domain của nó.
2. Coordinator không tính refund hay phân loại nguyên nhân (đúng nguyên tắc `architecture.md` §5.2) — nó chỉ gộp `result.data` của từng agent lại, tính `affected_entities` từ dữ liệu order/payment đã có, rồi lọc ra đúng 7 key theo schema README trước khi trả về. Việc "ai quyết định gì" hoàn toàn nằm ở domain agent tương ứng (Policy Agent quyết `primary_issue`/`resolution_actions`/refund); Coordinator chỉ đóng vai trò lắp ráp và đảm bảo hình dạng output đúng chuẩn, không lặp lại logic nghiệp vụ.
3. Domain agent chỉ nhìn thấy dữ liệu của chính domain mình (Order&Seller không biết payment, Payment không biết delivery...), nên không agent nào có đủ ngữ cảnh để kiểm tra tính nhất quán *chéo* domain trong output cuối — ví dụ refund có khớp với action đã chọn không, evidence có đúng định dạng 5 prefix chuẩn không, hay tổng thể output có đúng 7 key schema không. Verifier là nơi duy nhất nhận toàn bộ `output` đã lắp ráp xong cộng với `source_data` (ID thật từ CSV) để làm việc kiểm tra toàn cục này, đúng vai "gate cuối" trước khi ghi file.
4. Để giữ `schema_validator.py` là pure function, không phụ thuộc I/O hay pandas — giúp test viết được với dict/set dựng tay (không cần CSV thật), chạy nhanh, và tách rõ "đọc dữ liệu" (thuộc `agent.py::load_source_data`, chạy 1 lần) khỏi "kiểm tra logic" (chạy lại cho từng case mà không phải đọc lại CSV mỗi lần).
5. Dựa trên 3 lệnh: `pytest` (toàn bộ agent + verifier pass), `python scripts/validate_outputs.py` (in ra `All 50 outputs passed validation.`), và `python scripts/package_submission.py` (từ chối đóng gói nếu validate fail, sinh `output.zip` chỉ khi cả 50 case sạch). Ngoài ra còn cần `logging/trace.jsonl` được ghi lại từ lượt `run_pipeline.py` mới nhất (không append) để có bằng chứng đã chạy thật 50 case, không phải tạo tay.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quang Minh
**Ngày xác nhận:** 2026-08-05
