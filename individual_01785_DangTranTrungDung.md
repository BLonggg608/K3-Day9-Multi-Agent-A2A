# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung          |
| --------------- | ----------------- |
| Họ và tên       | Đặng Trần Trung Dũng     |
| MSSV            | 2A202601785   |
| Khóa/Lớp        | K3 / D303|
| Vai trò chính   | Order & Seller Agent |
| Ngày hoàn thành | 2026-08-05        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Order & Seller Agent Logic | `src/order_seller/agent.py` / `analyze` | Dictionary `context` (chứa `claimed_order_id`) | Object `AgentResult` chứa thông tin order, items, sellers và vi phạm | Hoàn thành |
| Data Query cho Order | `src/order_seller/queries.py` / `OrderDataStore` | `order_id` hoặc danh sách `seller_ids` | Pandas `DataFrame` chứa dữ liệu lọc từ CSV | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| [Mô tả nếu có, ví dụ: Hỗ trợ tích hợp] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng truy vấn dữ liệu từ CSV | `src/order_seller/queries.py` | Lớp `OrderDataStore` load và lọc dữ liệu đơn hàng thành công | Chạy unit test hoặc test độc lập hàm `get_order` |
| Thu thập và phân tích dữ liệu order, tính toán phí và kiểm tra trễ hạn | `src/order_seller/agent.py` | Các trường `item_total_brl`, `freight_total_brl`, `seller_handoff_violations` trong kết quả trả về | Log đầu ra của agent khi chạy pipeline với một case cụ thể |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Agent trả về đối tượng `AgentResult` với `ok=True`, trong đó thuộc tính `data` là một dictionary chứa chi tiết trạng thái đơn hàng (order_status), tổng giá trị hàng hoá (`item_total_brl`), tổng phí vận chuyển (`freight_total_brl`), danh sách seller, cũng như cờ `seller_handoff_violations` (bằng True nếu có người bán giao hàng trễ cho đơn vị vận chuyển). Các ID dữ liệu này cũng được đưa vào mảng `evidence_ids`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong một hệ thống giải quyết khiếu nại (dispute resolution) có nhiều tác nhân (Multi-Agent), khi khách hàng khiếu nại về một đơn hàng, hệ thống cần biết chính xác chi tiết của đơn hàng đó. Nhiệm vụ của phần này là trích xuất toàn bộ dữ liệu liên quan đến Order và Seller từ dataset gốc, tính toán các chỉ số tài chính cơ bản (tiền hàng, phí ship), và đặc biệt là phát hiện xem nguyên nhân gây ra sự cố có phải do người bán (Seller) chậm trễ trong việc giao hàng cho đơn vị vận chuyển (Carrier) hay không.

### Cách triển khai

1. **Khởi tạo Data Store:** Sử dụng thư viện Pandas để đọc các file `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, và `olist_sellers_dataset.csv`. Chuyển đổi các cột ngày tháng sang định dạng datetime của pandas để tiện tính toán.
2. **Xử lý Logic Agent:** Trong hàm `analyze`, agent lấy `claimed_order_id` từ `context["case"]["customer_request"]`. 
3. Nếu order_id hợp lệ, agent dùng `OrderDataStore` để lấy dòng thông tin của order và tất cả các items thuộc order đó.
4. Quét qua các items, agent tính tổng tiền và tổng phí vận chuyển. Đồng thời, so sánh `order_delivered_carrier_date` (từ bảng orders) với `shipping_limit_date` (từ bảng order_items). Nếu thời gian giao cho carrier lớn hơn giới hạn, agent đánh dấu `seller_handoff_violations = True` và ghi lại danh sách `violating_seller_ids`.
5. Đảm bảo toàn bộ Timestamp của Pandas được format về dạng chuỗi (string) qua hàm `_serialize_timestamp` và `dt.strftime` để ngăn chặn lỗi serialize khi xuất JSON cho các tác nhân khác (như Coordinator hoặc Verifier).

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | `context: dict[str, Any]` lấy từ Coordinator, chứa dictionary `case` |
| Output                  | `AgentResult` chứa thuộc tính `data` có các trường `order_id`, `item_total_brl`, `seller_handoff_violations`, v.v. |
| Module phụ thuộc        | `src.shared.contracts` (AgentResult), File dữ liệu `.csv` của Olist |
| Module sử dụng output   | Coordinator Agent, Policy Agent, Verifier Agent |
| Điều kiện lỗi cần xử lý | Thiếu `claimed_order_id` trong request, hoặc không tìm thấy `order_id` trong DB (`df.empty`) |

### Cách xác minh

```bash
# Ví dụ: Gọi trực tiếp agent bằng đoạn script test nhỏ (tùy thuộc dự án của bạn)
python -c "from src.order_seller.agent import OrderSellerAgent; agent = OrderSellerAgent(); print(agent.analyze({'case': {'customer_request': {'claimed_order_id': '00010242fe8c5a6d1ba2dd792cb16214'}}}).model_dump())"
```

- **Kết quả mong đợi:** In ra dictionary chứa data với `ok=True`, các trường tiền tệ được làm tròn chính xác 2 chữ số thập phân, `evidence_ids` có chứa định dạng chuẩn.
- **Kết quả thực tế:** [Tự điền kết quả bạn quan sát được]
- **Artifact/log:** `trace.jsonl` sau khi chạy pipeline.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Xử lý và serialize các giá trị ngày tháng từ Pandas ra JSON.
- **Các phương án đã cân nhắc:** (1) Giữ nguyên kiểu Pandas Timestamp và viết một JSON Encoder tuỳ chỉnh (custom default encoder) lúc xuất file JSON cuối cùng ở Coordinator. (2) Chuyển đổi (ép kiểu) thành string ngay tại output của `OrderSellerAgent`.
- **Phương án đã chọn:** Phương án (2) - dùng hàm `_serialize_timestamp` và hàm `dt.strftime('%Y-%m-%d %H:%M:%S')` trên data copy của dataframe.
- **Lý do:** Phương án (1) yêu cầu can thiệp vào tầng Coordinator và các tác nhân khác, phá vỡ tính đóng gói của Agent (mỗi agent nên trả về dữ liệu cơ bản đã xử lý xong, dễ xài). Phương án (2) đảm bảo `AgentResult` luôn chứa dictionary gồm các kiểu dữ liệu nguyên thủy (primitive types), an toàn khi lưu trữ và trao đổi nội bộ.
- **Bằng chứng quyết định phù hợp:** Pipeline chạy không bị crash với lỗi `TypeError: Object of type Timestamp is not JSON serializable` khi đẩy dữ liệu vào LLM.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: Object of type Timestamp is not JSON serializable`
- **Lệnh hoặc bước tái hiện:** Chạy test toàn bộ pipeline khi hệ thống cố gắng lưu lại execution trace ra file JSON.
- **Nguyên nhân gốc:** Pandas sau khi đọc file csv và gọi `pd.to_datetime` sẽ chuyển các trường thời gian (như `shipping_limit_date`) thành Pandas Timestamp, không tương thích mặc định với thư viện `json` của Python.
- **Cách xử lý:** Trong `agent.py`, tạo bản sao của DataFrame `items_df_copy = items_df.copy()` và chuyển cột ngày về string `items_df_copy['shipping_limit_date'].dt.strftime('%Y-%m-%d %H:%M:%S')` trước khi chuyển về dictionary (hàm `to_dict`). Ngoài ra cũng tạo hàm helper `_serialize_timestamp` cho các trường ngày giờ độc lập.
- **Cách xác minh sau khi sửa:** Chạy lại pipeline và theo dõi file output `trace.jsonl` tạo ra bình thường.
- **Điều học được:** Khi dùng Pandas xử lý dữ liệu để đẩy qua API hoặc vào output JSON cho LLM, luôn cần kiểm tra kiểu dữ liệu của các cột ngày tháng, NaN, NaT và ép kiểu cẩn thận tại ranh giới kết quả đầu ra.

## 7. Hiểu biết về luồng end-to-end

Luồng hoạt động End-to-End của hệ thống E-commerce Resolution bằng Multi-Agent:

1. **Tiếp nhận khiếu nại (Coordinator):** Khi khách hàng gửi khiếu nại (VD: hàng giao trễ, hàng bị lỗi), yêu cầu đầu tiên được đưa tới Coordinator Agent. Tác nhân này đóng vai trò điều phối, phân tích ban đầu xem cần gọi những tác nhân chuyên trách nào.
2. **Thu thập dữ liệu (Order & Seller / Payment / Delivery):** 
   - Coordinator gọi **Order & Seller Agent** (phần việc của tôi) để lấy chi tiết đơn hàng, người bán, tổng tiền, và kiểm tra xem người bán có giao hàng trễ hẹn cho đơn vị vận chuyển hay không.
   - Nếu liên quan đến thanh toán, gọi **Payment Agent** để kiểm tra trạng thái giao dịch.
   - Nếu liên quan đến vận chuyển, gọi **Delivery Agent** để tra cứu lịch sử giao hàng.
3. **Đối chiếu chính sách (Policy Agent):** Sau khi có đủ dữ liệu từ các agent con, Coordinator chuyển thông tin cho Policy Agent. Policy Agent dựa vào dữ liệu đó và luật/chính sách của sàn (SLA) để quyết định ai có lỗi (Seller hay Carrier) và mức độ bồi thường/phạt tiền là bao nhiêu.
4. **Xác minh (Verifier):** Trước khi đưa ra phán quyết cuối cùng, Verifier Agent kiểm tra chéo lại toàn bộ báo cáo, logic quyết định, định dạng JSON và bằng chứng (evidence IDs) để đảm bảo tính chính xác tuyệt đối, ngăn chặn hallucination (bịaa thông tin).
5. **Xuất kết quả:** Hệ thống tổng hợp lại thành một phán quyết (financial reconciliation) hoàn chỉnh xuất dưới định dạng JSON đúng chuẩn, kết thúc quy trình xử lý khiếu nại tự động.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đặng Trần Trung Dũng
**Ngày xác nhận:** 2026-08-05
