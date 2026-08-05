Dưới đây là cách phân việc cụ thể nhất cho nhóm 5 người. Mỗi thành viên có vùng file riêng, hạn chế sửa chung.

## Thành viên 1 — Kiến trúc và Coordinator

Nhiệm vụ:

1. Tạo cấu trúc source code.
2. Định nghĩa contract chung giữa các agent.
3. Xây dựng `Coordinator Agent`.
4. Nhận input case và chuyển việc cho các agent.
5. Tổng hợp kết quả thành output cuối.
6. Viết sơ đồ hệ thống.

Ownership:

```text
src/shared/contracts.py
src/shared/constants.py
src/coordinator/agent.py
architecture.md
```

API cần bàn giao:

```python
def process_case(case: dict) -> dict:
    ...
```

Kết quả cần có:

- Contract input/output.
- Handoff giữa các agent.
- Coordinator gọi được các agent.
- `architecture.md` mô tả đầy đủ 6 agent.
- Không tự xử lý sâu logic order/payment/delivery.

Thời hạn nội bộ: hoàn thành contract đầu tiên để 4 người còn lại dựa vào đó.

---

## Thành viên 2 — Order và Seller Agent

Nhiệm vụ:

1. Đọc các file:

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_sellers_dataset.csv
```

2. Tìm order từ `claimed_order_id`.
3. Kiểm tra `order_status`.
4. Lấy danh sách item và seller.
5. Tính:

```text
item_total_brl
freight_total_brl
```

6. Xác định seller có giao hàng cho carrier trễ hay không.
7. Tạo evidence order/item/seller.

Ownership:

```text
src/order_seller/agent.py
src/order_seller/queries.py
tests/order_seller/
```

API cần bàn giao:

```python
def analyze_order(case: dict) -> dict:
    ...
```

Kết quả trả về cần gồm:

```text
order_id
order_status
items
seller_ids
item_total_brl
freight_total_brl
seller_handoff_violations
evidence_ids
```

Phải test:

- Order bình thường.
- Order canceled.
- Order unavailable.
- Order có nhiều item.
- Order không có item.
- Nhiều seller.

Không sửa:

```text
src/coordinator/
src/payment/
src/delivery_policy/
output/
```

---

## Thành viên 3 — Payment Agent

Nhiệm vụ:

1. Đọc:

```text
olist_order_payments_dataset.csv
```

2. Lấy tất cả payment row của order.
3. Tính tổng `payment_value`.
4. Kiểm tra order đã thanh toán hay chưa.
5. Kiểm tra split payment.
6. So sánh payment total với item total + freight.
7. Tạo payment evidence.

Ownership:

```text
src/payment/agent.py
src/payment/queries.py
tests/payment/
```

API cần bàn giao:

```python
def analyze_payment(order_id: str, item_total: float, freight_total: float) -> dict:
    ...
```

Kết quả trả về cần gồm:

```text
payment_total_brl
payment_rows
is_paid
is_split_payment
is_valid_split_payment
payment_ids
evidence_ids
```

Phải test:

- Không có payment.
- Một payment.
- Nhiều payment hợp lệ.
- Nhiều payment sai tổng.
- Order canceled nhưng đã thanh toán.
- Order unavailable nhưng đã thanh toán.

Không sửa logic refund hoặc primary issue. Thành viên 4 sẽ dùng kết quả của thành viên này để áp dụng policy.

---

## Thành viên 4 — Delivery và Policy Agent

Đây là một ownership chung nhưng tách thành hai file, chỉ một người phụ trách.

### Phần A: Delivery Agent

Nhiệm vụ:

1. Đọc timestamp từ order và item.
2. So sánh:

```text
delivered_customer_date
estimated_delivery_date
order_delivered_carrier_date
shipping_limit_date
```

3. Phân biệt:

```text
late_delivery_seller
late_delivery_logistics
unsupported_late_claim
```

4. Xác định logistics chịu trách nhiệm hay seller chịu trách nhiệm.
5. Tạo root-cause evidence.

### Phần B: Policy Agent

Nhiệm vụ:

1. Áp dụng `EC_POLICY_V1`.
2. Chọn `primary_issue`.
3. Chọn `case_status`.
4. Xác định `responsible_parties`.
5. Tính `recommended_refund_brl`.
6. Chọn `resolution_actions`.
7. Làm tròn tiền đến 2 chữ số.

Ownership:

```text
src/delivery_policy/delivery_agent.py
src/delivery_policy/policy_agent.py
src/delivery_policy/rules.py
tests/delivery_policy/
```

API cần bàn giao:

```python
def analyze_delivery(order_data: dict) -> dict:
    ...

def apply_policy(
    order_data: dict,
    payment_data: dict,
    delivery_data: dict
) -> dict:
    ...
```

Phải test đúng thứ tự ưu tiên:

1. `canceled_order_paid`
2. `unavailable_order_paid`
3. `late_delivery_seller`
4. `late_delivery_logistics`
5. `valid_split_payment`
6. `unsupported_late_claim`

Không sửa Coordinator và Verifier.

---

## Thành viên 5 — Verifier, chạy 50 case và đóng gói

Nhiệm vụ:

1. Viết kiểm tra output schema.
2. Kiểm tra đủ 50 output.
3. Kiểm tra output không chứa ID giả.
4. Kiểm tra evidence tồn tại trong dữ liệu.
5. Kiểm tra số tiền và refund.
6. Chạy pipeline toàn bộ 50 case.
7. Sinh trace.
8. Điền metadata.
9. Tạo file ZIP cuối cùng.

Ownership:

```text
src/verifier/agent.py
src/verifier/schema_validator.py
tests/verifier/
scripts/run_pipeline.py
scripts/validate_outputs.py
scripts/package_submission.py
logging/metadata.json
logging/trace.jsonl
output/
```

API cần bàn giao:

```python
def validate_output(output: dict, source_data: dict) -> list[str]:
    ...

def validate_all_outputs() -> bool:
    ...
```

Phải kiểm tra:

```text
Có đúng 50 file JSON.
Tên file từ EC_001.json đến EC_050.json.
case_id khớp tên file.
confidence nằm trong [0, 1].
case_status là action_required hoặc no_action.
Các ID có thật.
Evidence có thật.
Refund khớp với resolution action.
Không có file thừa trong ZIP.
```

Thành viên này chỉ tích hợp các module, không tự sửa logic domain. Nếu phát hiện lỗi thì báo cho đúng thành viên phụ trách.

## Thứ tự làm việc

1. Thành viên 1 tạo `contracts.py`.
2. Thành viên 2, 3, 4 làm agent độc lập.
3. Thành viên 5 viết validator độc lập bằng dữ liệu mẫu.
4. Thành viên 1 tích hợp các agent.
5. Thành viên 5 chạy pipeline 50 case.
6. Cả nhóm kiểm tra kết quả và sửa lỗi theo ownership.
7. Thành viên 5 tạo ZIP cuối.

## Quy tắc commit

Mỗi người chỉ commit các thư mục của mình:

```text
Member 1: src/shared, src/coordinator, architecture.md
Member 2: src/order_seller, tests/order_seller
Member 3: src/payment, tests/payment
Member 4: src/delivery_policy, tests/delivery_policy
Member 5: src/verifier, scripts, tests/verifier, logging, output
```

Chỉ có một file cần cả nhóm thống nhất trước rồi khóa lại:

```text
src/shared/contracts.py
```

Mỗi thành viên nên tạo báo cáo riêng:

```text
individual_member01_HoTen.md
individual_member02_HoTen.md
individual_member03_HoTen.md
individual_member04_HoTen.md
individual_member05_HoTen.md
```

Không cùng sửa file template báo cáo hiện tại.