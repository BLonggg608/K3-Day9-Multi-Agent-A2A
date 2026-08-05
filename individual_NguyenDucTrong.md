# Member Role Report — Day 9: Multi Agent A2A

> Báo cáo cá nhân về phần Payment Agent trong hệ thống giải quyết khiếu nại thương mại điện tử trên dữ liệu Olist.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Đức Trọng |
| Khóa/Lớp | K3 |
| Vai trò chính | Payment Agent (Thành viên 3) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `src/payment/agent.py`: `PaymentAgent.analyze`, `analyze_payment`, `reconcile_payments` | `order_id`, `item_total_brl`, `freight_total_brl` từ Order & Seller Agent; các payment row từ repository | Tổng payment, trạng thái paid/split/reconciled, payment IDs và evidence IDs | Hoàn thành |
| Truy vấn payment | `src/payment/queries.py`: `PaymentRepository` | `data/olist_order_payments_dataset.csv` và `order_id` | Các payment row của order, được chuẩn hóa và sắp theo `payment_sequential` | Hoàn thành |
| API module | `src/payment/__init__.py` | Các lớp và hàm thuộc payment domain | Public API để Coordinator và test import ổn định | Hoàn thành |
| Unit test Payment | `tests/payment/test_agent.py`, `tests/payment/test_queries.py` | Dữ liệu test trong bộ nhớ và CSV tạm | 13 test về tính tiền, split payment, tolerance, evidence, repository và lỗi đầu vào | Hoàn thành |

Payment Agent chỉ sở hữu dữ kiện thanh toán và đối soát. Tôi không đặt `primary_issue`, không tính refund cuối cùng và không quyết định responsible party hoặc resolution action; các quyết định đó thuộc Policy Agent.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Căn chỉnh handoff với contract chung | Coordinator và Order & Seller Agent | `PaymentAgent` triển khai `name` và `analyze(context) -> AgentResult`, đồng thời tìm prior result có đủ `order_id`, `item_total_brl`, `freight_total_brl` |
| Cung cấp payment facts có cấu trúc | Delivery & Policy Agent | Bàn giao `payment_total_brl`, `is_paid`, `is_split_payment`, `is_payment_reconciled`, `is_valid_split_payment` để policy áp dụng đúng thứ tự ưu tiên |
| Cung cấp affected entities và evidence | Coordinator và Verifier Agent | Tạo payment ID và evidence ID đúng hai định dạng khác nhau, giới hạn tối đa 5 ID |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Đọc và lập index payment CSV | `PaymentRepository._load`, `get_by_order_id` | CSV chỉ được nạp một lần; payment rows được truy vấn theo `order_id` | Test repository đọc và sắp payment sequence |
| Tính tổng payment chính xác | `reconcile_payments`, `_money`, `_rounded` | `payment_total_brl` làm tròn hai chữ số, không nhân với installment | Test payment có 8 installments vẫn có tổng 115.0 BRL |
| Nhận diện split payment | `reconcile_payments` | `is_split_payment = true` khi có từ 2 payment row | Test một row nhiều installment và test hai payment row |
| Đối soát payment | `reconcile_payments` | So sánh tổng payment với item + freight trong tolerance 0.10 BRL | Test sai lệch 0.10 hợp lệ và 0.11 không hợp lệ |
| Tạo entity/evidence ID | `reconcile_payments` | `<order_id>:<sequence>` và `payment:<order_id>:<sequence>` | Test định dạng, thứ tự và giới hạn 5 ID |
| Tích hợp với Coordinator | `PaymentAgent.analyze` | `AgentResult` thành công hoặc lỗi có cấu trúc | Test agent nhận prior order facts và test thiếu prior facts |

Một output cụ thể của phần việc là payment facts cho order có hai payment row tổng cộng 115.0 BRL, trong khi item + freight cũng bằng 115.0 BRL. Payment Agent trả `is_split_payment = true`, `is_payment_reconciled = true`, `is_valid_split_payment = true` cùng hai payment evidence có thể truy ngược về CSV.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một order Olist có thể có một hoặc nhiều payment row. `payment_value` là giá trị của từng row, không phải số tiền của từng installment. Payment Agent phải tính đúng tổng tiền, nhận diện split payment bằng số row, đối soát tổng payment với tổng item và freight, đồng thời tạo evidence từ dữ liệu thật. Kết quả sai ở domain này có thể dẫn tới hoàn sai toàn bộ payment cho đơn canceled/unavailable hoặc phân loại sai `valid_split_payment`.

### Cách triển khai

`PaymentRepository` đọc `olist_order_payments_dataset.csv`, kiểm tra đủ năm cột bắt buộc, chuẩn hóa sequence/installment sang số nguyên và lập index theo `order_id`. Việc index một lần giúp batch 50 case không phải quét lại toàn bộ CSV cho từng case. Các row trả về được sắp theo `payment_sequential` để ID và trace có thứ tự ổn định.

`reconcile_payments` kiểm tra order ID, sequence duy nhất và dương, installment không âm, payment value hợp lệ và không âm. Hàm dùng `Decimal` cho toàn bộ phép tính tiền. Tổng kỳ vọng là `item_total_brl + freight_total_brl`; payment được coi là reconciled khi độ lệch tuyệt đối không vượt quá 0.10 BRL. Split payment chỉ được xác định khi có ít nhất hai payment row, không dựa vào `payment_installments`.

Tất cả payment row đều tham gia tính tổng. Riêng `payment_ids` và payment evidence chỉ lấy tối đa năm sequence đầu tiên để tuân thủ giới hạn output. Adapter `PaymentAgent` nhận context từ Coordinator, tìm kết quả agent trước có đủ ba order facts cần thiết, gọi logic đối soát rồi trả `AgentResult`. Nếu thiếu dữ kiện, thiếu CSV hoặc dữ liệu không hợp lệ, agent trả `ok = false` với lỗi có cấu trúc thay vì làm pipeline dừng không rõ nguyên nhân.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Context có prior result chứa `order_id`, `item_total_brl`, `freight_total_brl`; repository đọc payment CSV |
| Output | Payment totals, payment rows, paid/split/reconciled flags, payment IDs; evidence nằm trong `AgentResult.evidence_ids` |
| Module phụ thuộc | `src/shared/contracts.py`, kết quả từ Order & Seller Agent |
| Module sử dụng output | Coordinator Agent, Delivery & Policy Agent và Verifier Agent |
| Điều kiện lỗi cần xử lý | Thiếu prior order facts, CSV không tồn tại hoặc thiếu cột, số tiền sai định dạng/âm, sequence trùng hoặc order ID không khớp |

### Cách xác minh

```bash
python -m unittest discover -s tests/payment -v
```

- **Kết quả mong đợi:** Toàn bộ test Payment Agent và Payment Repository pass.
- **Kết quả thực tế:** `Ran 13 tests in 0.011s` và `OK` vào ngày 2026-08-05.
- **Artifact/log:** `tests/payment/test_agent.py`, `tests/payment/test_queries.py`; không chứa secret.

Smoke test từng được chạy trên payment CSV thật với order `b81ef226f3fe1789b1e8b2acac839d17`; kết quả `payment_total_brl = 99.33`, `is_paid = true`, một payment ID và một evidence ID đúng định dạng.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Policy cho phép sai lệch tối đa đúng 0.10 BRL. Phép toán bằng `float` có thể biểu diễn số thập phân tiền tệ không chính xác tại biên này.
- **Các phương án đã cân nhắc:** (1) Dùng `float` và `round`; (2) dùng `Decimal` từ chuỗi nguồn cho mọi phép cộng, trừ, so sánh và chỉ chuyển sang float ở output JSON.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** `Decimal` giữ chính xác giá trị tiền trong CSV và làm cho điều kiện `difference <= 0.10` có tính xác định. Việc dùng `ROUND_HALF_UP` cũng thể hiện rõ quy tắc làm tròn hai chữ số.
- **Bằng chứng quyết định phù hợp:** Hai test biên xác nhận sai lệch `0.10` được chấp nhận và `0.11` bị từ chối; toàn bộ 13 test pass.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** File phân công yêu cầu API `analyze_payment(order_id, item_total, freight_total)`, trong khi Coordinator hiện tại chỉ gọi agent qua interface `analyze(context) -> AgentResult`.
- **Lệnh hoặc bước tái hiện:** Đọc `src/shared/contracts.py`, `src/coordinator/agent.py` và đối chiếu với `chiaviec.md`; nếu chỉ tạo hàm theo phân công thì Coordinator không thể inject và gọi Payment Agent.
- **Nguyên nhân gốc:** Mô tả phân công đưa ra functional API của payment domain, còn contract tích hợp sử dụng agent adapter và handoff envelope chung.
- **Cách xử lý:** Giữ cả hai tầng: `analyze_payment`/`reconcile_payments` cho logic có thể test độc lập, và `PaymentAgent.analyze` làm adapter tương thích Coordinator. Adapter lấy facts từ context và trả `AgentResult`.
- **Cách xác minh sau khi sửa:** Test `test_agent_consumes_prior_order_facts` xác nhận handoff thành công; test thiếu facts xác nhận trả lỗi có cấu trúc; 13/13 test pass.
- **Điều học được:** Logic domain nên tách khỏi adapter orchestration. Cách này giữ thuật toán dễ test nhưng vẫn tuân thủ contract chung giữa các agent.

## 7. Hiểu biết về luồng end-to-end

1. Coordinator đọc từng file `EC_001.json` đến `EC_050.json`. `claimed_order_id` trong `customer_request` là khóa để truy vấn dữ liệu Olist.
2. Order & Seller Agent tra orders/items/sellers, tính tổng item và freight, lấy trạng thái, seller, timestamp và evidence nguồn.
3. Payment Agent nhận order ID cùng tổng item/freight, lấy toàn bộ payment rows, tính tổng payment, nhận diện split payment và đối soát trong tolerance 0.10 BRL.
4. Delivery Agent so sánh thời điểm giao thực tế với ngày dự kiến, đồng thời xác định seller có bàn giao cho carrier sau `shipping_limit_date` hay không.
5. Policy Agent kết hợp order, payment và delivery facts; áp dụng lần lượt canceled paid, unavailable paid, late seller, late logistics, valid split payment và unsupported late claim. Rule được chọn quyết định root cause, responsible party, refund, confidence và action.
6. Coordinator ghép output và evidence. Verifier kiểm tra schema, ID, giới hạn số phần tử, số tiền, refund và action trước khi ghi JSON.
7. Pipeline tạo đúng 50 output tương ứng 50 input, đồng thời ghi trace và metadata. File ZIP nộp bài chỉ chứa 50 JSON trong `output/`, không chứa source, `.env` hoặc audit file.

Payment facts có ảnh hưởng trực tiếp tới ba nhóm kết luận: canceled/unavailable chỉ được hoàn toàn bộ khi tổng payment lớn hơn 0; `valid_split_payment` yêu cầu ít nhất hai payment row và tổng tiền khớp; `unsupported_late_claim` cũng yêu cầu payment được đối soát. Vì vậy Payment Agent phải cung cấp facts chính xác, nhưng không tự chọn policy để giữ ranh giới trách nhiệm giữa các agent.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Trọng  
**Ngày xác nhận:** 05/08/2026
