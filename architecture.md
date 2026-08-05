# Kiến trúc hệ thống Multi-Agent E-commerce Dispute Resolution

## 1. Mục tiêu

Hệ thống nhận một case khiếu nại trong `input/`, truy vấn dữ liệu Olist, phân tích độc lập theo từng domain, handoff bằng kết quả có cấu trúc, sau đó tạo một JSON hợp lệ trong `output/`.

## 2. Luồng xử lý

```text
Input case
   |
   v
Coordinator
   |-- Order & Seller Agent ----> order/item/seller facts
   |-- Payment Agent ------------> payment reconciliation
   |-- Delivery Agent -----------> delivery facts and delay owner
   |-- Policy Agent -------------> primary issue, refund, action
   |-- Verifier Agent ------------> IDs, amounts, schema checks
   v
Output JSON + trace
```

Coordinator chỉ điều phối và ghép kết quả. Agent domain là nơi duy nhất được phép áp dụng logic truy vấn hoặc quy tắc nghiệp vụ của domain đó.

## 3. Ownership và quyền truy cập

| Agent | Ownership | Dữ liệu được đọc | Kết quả bàn giao |
| --- | --- | --- | --- |
| Coordinator | `src/coordinator/` | Input và kết quả agent | Case context/output |
| Order & Seller | `src/order_seller/` | orders, order_items, sellers | Order, item, seller facts |
| Payment | `src/payment/` | order_payments | Payment facts và reconciliation |
| Delivery & Policy | `src/delivery_policy/` | Order facts, item facts, policy | Root cause, party, refund, action |
| Verifier | `src/verifier/` | Output và source facts | Validation errors/pass |

`src/shared/contracts.py` là contract chung. Sau khi nhóm thống nhất, file này được khóa; thay đổi contract phải được cả nhóm review.

## 4. Handoff contract

Mỗi agent nhận một context có dạng:

```json
{
  "case": {"case_id": "EC_001", "...": "..."},
  "results": {
    "agent_name": {
      "agent": "agent_name",
      "ok": true,
      "data": {},
      "errors": [],
      "evidence_ids": []
    }
  }
}
```

Mỗi agent trả về `AgentResult`. Agent sau chỉ sử dụng facts trong `results`; không tự tạo evidence khi không có dòng dữ liệu chứng minh.

## 5. Quy tắc tích hợp

1. Domain agents không sửa output của agent khác.
2. Coordinator không chứa logic tính refund hoặc phân loại nguyên nhân.
3. Verifier không sửa kết quả; chỉ báo lỗi.
4. Output cuối phải có đúng schema trong README.
5. `trace.jsonl` được ghi lại sau mỗi lần chạy mới, không append giữa các lần chạy.
6. Secret chỉ nằm trong `.env`, không commit vào repository hoặc ZIP.

## 6. Cấu trúc source đề xuất

```text
src/
  shared/contracts.py
  coordinator/agent.py
  order_seller/agent.py
  payment/agent.py
  delivery_policy/delivery_agent.py
  delivery_policy/policy_agent.py
  verifier/agent.py
```

Các agent domain và verifier do thành viên tương ứng triển khai trên branch riêng. Coordinator đã được viết theo dependency injection để có thể nhận các implementation đó mà không cần sửa lại orchestration.
