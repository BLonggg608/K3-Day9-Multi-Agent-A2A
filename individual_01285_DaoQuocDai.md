# Member Role Report — Day 9: Multi Agent A2A

> Báo cáo cá nhân về phần Delivery & Policy Agent trong hệ thống giải quyết khiếu nại thương mại điện tử trên dữ liệu Olist.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đào Quốc Đại |
| MSSV | 2A202601285 |
| Khóa/Lớp | K3 |
| Vai trò chính | Delivery & Policy Agent (Role 4) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Delivery Agent | `src/delivery_policy/delivery_agent.py`: `analyze_delivery`, `DeliveryAgent.analyze` | Order, item, seller và các timestamp do Order & Seller Agent bàn giao | Phân loại giao trễ, seller bàn giao trễ và root-cause facts | Hoàn thành |
| Policy Agent | `src/delivery_policy/policy_agent.py`: `apply_policy`, `calculate_confidence`, `PolicyAgent.analyze` | Kết quả có cấu trúc từ Order & Seller, Payment và Delivery Agent | Primary issue, trạng thái case, bên chịu trách nhiệm, refund, action và policy evidence | Hoàn thành |
| Bộ quy tắc policy | `src/delivery_policy/rules.py` | `EC_POLICY_V1`, số tiền và payment facts | Thứ tự ưu tiên, bảng ánh xạ issue/action/cause, làm tròn và đối soát payment | Hoàn thành |
| Unit test role 4 | `tests/delivery_policy/test_delivery_policy.py` | Dữ liệu test cho delivery/payment/order | 13 test cho phân loại, ưu tiên policy, refund, evidence và lỗi đầu vào | Hoàn thành |

Delivery Agent chỉ tạo delivery facts. Policy Agent là nơi duy nhất trong phần việc của tôi chọn kết luận policy cuối cùng; Coordinator chỉ điều phối và ghép kết quả.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Căn chỉnh handoff | Order & Seller Agent và Coordinator | Chấp nhận tên result `order_seller`, `order`, `order_agent` và đọc dữ liệu qua `AgentResult`/dictionary để tích hợp ổn định |
| Cung cấp policy output có cấu trúc | Verifier Agent | Bàn giao đúng các section `assessment`, `root_cause_analysis`, `financial_resolution`, `resolution_actions` và evidence để verifier kiểm tra |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| So sánh ngày giao thực tế với ngày dự kiến | `analyze_delivery` | `is_late_delivery`, `is_within_estimate`, `delivery_classification` | Unit test delivery đúng hạn và giao trễ |
| So sánh carrier handoff với từng `shipping_limit_date` | `analyze_delivery` | `late_handoff_seller_ids`, phân biệt seller/logistics | Test seller bàn giao muộn và logistics giao muộn |
| Áp dụng đúng 6 mức ưu tiên `EC_POLICY_V1` | `_select_issue`, `POLICY_PRIORITY`, `ISSUE_RULES` | Một `primary_issue` duy nhất theo đúng precedence | Test canceled ưu tiên hơn late; seller late ưu tiên hơn split payment |
| Tính trách nhiệm và hoàn tiền | `apply_policy`, `money` | Full refund, freight refund hoặc 0 BRL; làm tròn 2 chữ số | Assertion refund 115.0 và 15.0 trong unit test |
| Tạo confidence có thể giải thích | `calculate_confidence` | Điểm `[0, 1]`, giảm khi thiếu facts quan trọng | Test confidence giảm từ 1.0 xuống 0.8 |
| Xử lý lỗi đầu vào | `_timestamp`, `_select_issue`, adapter `analyze` | Báo lỗi timestamp sai, policy version sai hoặc không có rule phù hợp | Test invalid timestamp và no matching rule |

Output cụ thể của phần việc là một kết quả policy có cấu trúc, ví dụ case giao trễ do logistics nhận `primary_issue = late_delivery_logistics`, `cause_code = CARRIER_DELIVERED_AFTER_ESTIMATE`, responsible party là `LOGISTICS_PROVIDER`, refund bằng tổng freight và action `refund_freight`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một khiếu nại “giao hàng trễ” chưa đủ để kết luận trách nhiệm. Hệ thống phải kiểm tra timestamp thực tế, xác định seller có bàn giao sau hạn hay không, sau đó kết hợp trạng thái order và payment để áp dụng đúng thứ tự ưu tiên policy. Ví dụ, đơn vừa canceled và vừa giao trễ phải được xử lý theo `canceled_order_paid`, không theo lỗi delivery.

### Cách triển khai

`analyze_delivery` chuyển các timestamp ISO/Olist sang `datetime`, so sánh `order_delivered_customer_date` với `order_estimated_delivery_date`, rồi so sánh `order_delivered_carrier_date` với `shipping_limit_date` của từng item. Nếu giao trễ và có seller bàn giao sau hạn, nguyên nhân thuộc seller; nếu giao trễ nhưng seller bàn giao đúng hạn, nguyên nhân thuộc logistics; nếu giao trong hạn, claim giao trễ chưa được dữ liệu hỗ trợ.

`apply_policy` đánh giá lần lượt các rule theo thứ tự: canceled paid, unavailable paid, late seller, late logistics, valid split payment, unsupported late claim. Rule được chọn quyết định cause code, responsible parties, refund và resolution action. Full refund dùng tổng payment; refund do giao trễ dùng tổng freight; các case giải thích/bác claim có refund bằng 0. Tiền được tính bằng `Decimal` và làm tròn `ROUND_HALF_UP` đến hai chữ số.

Delivery Agent không phát `policy:*` evidence tạm thời vì kết luận delivery có thể bị một rule ưu tiên cao hơn ghi đè. Policy Agent chỉ phát evidence sau khi chọn issue cuối cùng, tránh evidence mâu thuẫn với output.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Ba dictionary: `order_data`, `payment_data`, `delivery_data`; adapter nhận chúng trong `CaseContext.results` |
| Output | `assessment`, `root_cause_analysis`, `financial_resolution`, `resolution_actions`, cùng `evidence_ids` |
| Module phụ thuộc | `src/shared/contracts.py`, Order & Seller Agent, Payment Agent |
| Module sử dụng output | Coordinator Agent và Verifier Agent |
| Điều kiện lỗi cần xử lý | Input không phải dictionary, timestamp sai định dạng, thiếu result handoff, policy version không hỗ trợ, hoặc không có rule nào khớp |

### Cách xác minh

```bash
python -m unittest discover -s tests/delivery_policy -v
```

- **Kết quả mong đợi:** Toàn bộ test phân loại delivery, policy precedence, refund, evidence, confidence và lỗi đầu vào đều pass.
- **Kết quả thực tế:** `Ran 13 tests in 0.001s` và `OK` vào ngày 2026-08-05.
- **Artifact/log:** `tests/delivery_policy/test_delivery_policy.py`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Delivery Agent có thể phân loại một case là giao trễ, nhưng Policy Agent còn phải xét các rule ưu tiên cao hơn như canceled/unavailable đã thanh toán.
- **Các phương án đã cân nhắc:** (1) Delivery Agent phát ngay `policy:<cause_code>`; (2) Delivery Agent chỉ bàn giao facts, Policy Agent phát policy evidence sau khi chọn issue cuối cùng.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Tách phân tích domain khỏi quyết định policy, tránh evidence của delivery mâu thuẫn với `primary_issue`, đồng thời giữ Coordinator không chứa business logic.
- **Bằng chứng quyết định phù hợp:** Test `test_delivery_agent_does_not_emit_preliminary_policy_evidence` xác nhận Delivery Agent không phát policy evidence; các test precedence xác nhận Policy Agent chọn đúng kết luận cuối cùng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Delivery và Order Agent có thể dùng tên trường/ngữ cảnh handoff khác nhau, khiến Delivery Agent không tìm thấy result hoặc bỏ sót seller đã được xác định bàn giao muộn.
- **Lệnh hoặc bước tái hiện:** Truyền context có result tên `order_seller`, hoặc truyền `seller_handoff_violations`/`violating_seller_ids` từ Order Agent rồi gọi `DeliveryAgent.analyze`.
- **Nguyên nhân gốc:** Contract tích hợp có nhiều alias trong quá trình các module được phát triển độc lập; hình dạng seller violation cũng có thể là boolean, string, list ID hoặc list dictionary.
- **Cách xử lý:** Dùng `_result_data` để hỗ trợ các tên result đã thống nhất và `_precomputed_violations` để chuẩn hóa seller ID, loại trùng trước khi kết hợp với phép so sánh timestamp tại Delivery Agent.
- **Cách xác minh sau khi sửa:** Chạy `python -m unittest discover -s tests/delivery_policy -v`; 13/13 test pass.
- **Điều học được:** Handoff giữa agent cần chuẩn hóa ở biên module và giữ output có cấu trúc; không nên để khác biệt nhỏ về representation làm thay đổi kết luận policy.

## 7. Hiểu biết về luồng end-to-end

1. Coordinator đọc từng case trong `input/`, lấy `claimed_order_id` và chuyển context cho các agent.
2. Order & Seller Agent tra orders, items và sellers để bàn giao trạng thái order, tổng item/freight, seller IDs, timestamp và evidence nguồn.
3. Payment Agent lấy toàn bộ payment rows, tính tổng payment, nhận diện split payment và đối soát với item + freight.
4. Delivery Agent dùng order/item facts để xác định đơn có giao trễ không và seller có bàn giao sau `shipping_limit_date` không. Agent này chỉ bàn giao facts, chưa quyết định policy cuối cùng.
5. Policy Agent kết hợp cả ba nhóm facts, áp dụng sáu rule `EC_POLICY_V1` đúng thứ tự ưu tiên, rồi tạo primary issue, root cause, responsible parties, refund, confidence và action.
6. Coordinator ghép affected entities và evidence nguồn với kết quả policy. Verifier kiểm tra schema, ID có thật, số tiền, refund và action trước khi ghi 50 file JSON; trace và metadata ghi lại lượt chạy.
7. Kết quả được xem là hợp lệ khi mỗi input có đúng một output tương ứng, toàn bộ output qua validator, evidence truy được về dữ liệu thật và các khoản refund tuân thủ policy. Dùng cùng 50 input cho mọi lần chạy giúp so sánh thay đổi một cách tái lập.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đào Quốc Đại  
**Ngày xác nhận:** 05/08/2026
