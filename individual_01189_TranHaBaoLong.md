# Báo cáo cá nhân — Thành viên 1: Kiến trúc và Coordinator

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Hà Bảo Long |
| MSSV | 2A202601189 |
| Khóa/Lớp | K3 / D303 |
| Vai trò chính | Kiến trúc hệ thống và Coordinator Agent |
| Ngày hoàn thành | 05-08-2026 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Contract dùng chung | `src/shared/contracts.py`: `AgentResult`, `Agent`, `CaseContext`, `REQUIRED_OUTPUT_KEYS` | Case và kết quả agent trước | Envelope handoff thống nhất giữa các agent | Hoàn thành |
| Coordinator | `src/coordinator/agent.py`: `Coordinator.process_case()`, `_assemble_output()` | `case: dict`, danh sách domain agents | Output deterministic, evidence và trạng thái audit/verification | Hoàn thành |
| Sơ đồ kiến trúc | `architecture.md` | Cấu trúc source và luồng thực thi thực tế | Sơ đồ Coordinator, vai trò, quyền đọc và handoff | Hoàn thành |
| Tích hợp audit LLM | `src/shared/llm_client.py` và điểm gọi trong Coordinator | Case và output deterministic | Rationale tiếng Việt; không sửa quyết định nghiệp vụ | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp các agent domain vào pipeline | Order/Seller, Payment, Delivery/Policy | `scripts/run_pipeline.py` có thể khởi tạo và chạy bốn domain agent theo contract chung |
| Kiểm tra handoff và output sau khi các thành viên push code | Tất cả domain agents và Verifier | Xác nhận output ghép có đúng 7 trường, evidence được gom và không trùng |
| Làm rõ ranh giới LLM audit | `src/shared/llm_client.py`, `logging/trace.jsonl` | LLM chỉ tạo rationale; output quyết định vẫn do rule-based code tạo |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Định nghĩa envelope handoff | `src/shared/contracts.py` | Mỗi agent trả `AgentResult(agent, ok, data, errors, evidence_ids)` | Đọc contract và chạy unit test toàn repo |
| Xây dựng luồng điều phối | `src/coordinator/agent.py` | Coordinator nhận case, gọi agent, lưu `CaseContext`, fail-fast khi agent lỗi | `Coordinator.process_case()` và smoke test pipeline |
| Ghép output cuối | `Coordinator._assemble_output()` | Giữ `case_id`, assessment, affected entities, root cause, evidence, financial resolution và actions | Kiểm tra output JSON của 50 case |
| Thiết kế evidence merge | `Coordinator._assemble_output()`, các `AgentResult.evidence_ids` | Gom evidence theo thứ tự agent và loại duplicate; không tự tạo evidence | Verifier và kết quả leaderboard của nhóm |
| Tích hợp LLM audit | `src/shared/llm_client.py`, `Coordinator.process_case()` | Gọi OpenAI sau khi ghép output; rationale được lưu trong trace | Kiểm tra `llm_error`, `rationale` và `logging/trace.jsonl` |
| Viết tài liệu kiến trúc | `architecture.md` | Sơ đồ hub-and-spoke với Coordinator ở trung tâm, quyền truy cập và luồng handoff | `git diff --check` và kiểm tra Markdown |

Kết quả tích hợp được nhóm ghi nhận:

- Unit test: `29 passed` khi chạy với `-p no:cacheprovider` do môi trường Windows không có quyền ghi `.pytest_cache`.
- Smoke test 50 case: `passed=50`, `failed=0`.
- Phiên bản code sau khi pull đã đạt `100 điểm` theo kết quả leaderboard nhóm cung cấp.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các agent thuộc các domain khác nhau cần trao đổi dữ liệu nhưng không nên phụ thuộc trực tiếp vào implementation của nhau. Hệ thống cần một contract chung để:

- Agent phía sau biết cách đọc kết quả agent phía trước.
- Coordinator có thể thay agent bằng dependency injection.
- Output cuối chỉ chứa schema submission, không lộ toàn bộ facts trung gian.
- LLM không được phép thay đổi quyết định, tiền hoàn hoặc evidence.

### Cách triển khai

`CaseContext` chứa hai phần:

```text
case       : input case hiện tại
results    : các AgentResult đã hoàn thành, được index theo agent.name
```

Coordinator chạy qua danh sách agents được inject. Với mỗi agent, Coordinator gọi:

```python
result = agent.analyze(context.as_dict())
```

Sau đó lưu kết quả vào `context.results`. Nếu `result.ok` là `False`, Coordinator dừng pipeline và trả error output gồm agent lỗi, thông báo lỗi và danh sách agent đã hoàn thành.

Sau khi các domain agents hoàn thành, `_assemble_output()`:

1. Giữ `case_id` từ input.
2. Merge các section do Policy Agent tạo.
3. Gom `evidence_ids` từ envelope của từng agent và loại duplicate.
4. Tạo `affected_entities` từ order facts và payment facts.
5. Lọc output về bảy trường được phép nộp.

Trong implementation hiện tại, Order/Seller và Payment có truy vấn CSV; Delivery và Policy xử lý facts đã handoff; Verifier đọc các CSV để kiểm tra ID. Chỉ `OpenAIAuditClient` sử dụng LLM. LLM nhận output deterministic đã ghép và trả rationale, không trả một output mới.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `case` gồm `case_id`, `customer_request.claimed_order_id`, `message` và `policy_version` |
| Handoff input | `context = {"case": ..., "results": ...}` |
| Output của agent | `AgentResult` gồm `agent`, `ok`, `data`, `errors`, `evidence_ids` |
| Output của Coordinator | Bảy trường: `case_id`, `assessment`, `affected_entities`, `root_cause_analysis`, `evidence_ids`, `financial_resolution`, `resolution_actions` |
| Module phụ thuộc | `src/shared/contracts.py`, các domain agents, Verifier và tùy chọn LLM client |
| Module sử dụng output | `scripts/run_pipeline.py`, `src/verifier/agent.py`, bộ đóng gói output |
| Điều kiện lỗi | Case thiếu `case_id`, domain agent trả `ok=False`, LLM lỗi/rationale rỗng hoặc dữ liệu không khớp contract |

### Cách xác minh

Trên Windows CMD, chạy:

```cmd
python -m pytest -q -p no:cacheprovider
python scripts\run_pipeline.py
python scripts\validate_outputs.py
python scripts\package_submission.py
```

- **Kết quả mong đợi:** Unit test pass; pipeline tạo đủ 50 output; validator không báo lỗi; package chỉ chứa các JSON cần nộp.
- **Kết quả thực tế đã ghi nhận:** `29 passed`; smoke test 50 case `passed=50`, `failed=0`; leaderboard đạt 100 điểm.
- **Artifact/log:** `output/`, `logging/trace.jsonl`, `architecture.md`. Không ghi API key hoặc nội dung `.env` vào báo cáo.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Có thể để một LLM duy nhất đọc toàn bộ case và tự quyết định, hoặc tách quyết định thành domain agents deterministic rồi dùng LLM để diễn giải.
- **Các phương án đã cân nhắc:**
  1. Một prompt LLM duy nhất để truy vấn, suy luận và tạo toàn bộ output.
  2. Các agent rule-based xử lý dữ liệu/ policy, Coordinator ghép output, LLM chỉ audit rationale.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Các phép tính tiền, điều kiện giao trễ, evidence và policy cần tái lập và kiểm chứng được. Tách LLM khỏi quyết định giúp tránh LLM tự tạo ID, thay đổi refund hoặc suy diễn dữ liệu không có trong CSV.
- **Bằng chứng quyết định phù hợp:** Verifier kiểm tra schema, ID, evidence, tiền và policy; smoke test 50 case đạt `passed=50`, `failed=0`; phiên bản tích hợp được nhóm ghi nhận đạt 100 điểm.

Một quyết định liên quan là dùng Coordinator tập trung. Agent không gọi trực tiếp agent khác; Coordinator giữ `CaseContext`, lần lượt gọi component và nhận kết quả. Về dependency dữ liệu, Payment và Delivery đều dựa trên Order/Seller facts; Policy cần đủ Order, Payment và Delivery facts.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**

  ```text
  PermissionError: [WinError 5] Access is denied: ...\.pytest_cache\v
  ```

- **Lệnh hoặc bước tái hiện:**

  ```cmd
  python -m pytest -q --disable-warnings --cache-clear
  ```

- **Nguyên nhân gốc:** Pytest cache provider cố xóa/ghi `.pytest_cache`, nhưng tài khoản chạy trên Windows không có quyền truy cập thư mục cache hiện tại. Đây là lỗi môi trường, không phải lỗi logic của agent.
- **Cách xử lý:** Tắt riêng cache provider khi chạy test:

  ```cmd
  python -m pytest -q -p no:cacheprovider
  ```

- **Cách xác minh sau khi sửa:** Bộ test chạy được với kết quả `29 passed`.
- **Điều học được:** Cần phân biệt lỗi quyền ghi của tooling với lỗi nghiệp vụ; không nên sửa business logic chỉ vì pytest cache thất bại.

## 7. Hiểu biết về luồng end-to-end

1. Input `EC_*.json` được `run_pipeline.py` đọc và truyền vào Coordinator. Coordinator gọi các thành phần theo thứ tự implementation: Order/Seller, Payment, Delivery, Policy, LLM Audit và Verifier.
2. Order/Seller truy vấn orders/items/sellers; Payment truy vấn payments. Các agent tạo facts và evidence trong `AgentResult`, sau đó Coordinator lưu vào `CaseContext` để cấp cho agent cần dùng.
3. Policy Agent dùng `EC_POLICY_V1` để tạo issue, root cause, responsible party, refund và action. Coordinator ghép output deterministic; output này không phải là kết quả do LLM tổng hợp.
4. LLM Audit chỉ đọc case và output deterministic để viết rationale ngắn bằng tiếng Việt. Rationale được lưu trong `logging/trace.jsonl`, không được thêm vào submission JSON và không được sửa các quyết định.
5. Verifier kiểm tra schema, enum, giới hạn, ID tồn tại, quan hệ order/item/payment, evidence, tiền refund và sự nhất quán policy. Sau đó pipeline ghi JSON vào `output/` và tạo package theo yêu cầu README.
6. Bộ 50 case phải dùng cùng input chính thức và cùng rule/data hiện tại; artifact cần kiểm tra là 50 file JSON, trace mới nhất và ZIP chỉ chứa output hợp lệ.

## 8. Cam kết của thành viên

- [ ] Tôi đã điền đúng Họ tên và MSSV của mình trước khi nộp.
- [x] Nội dung báo cáo phản ánh phần việc kiến trúc và Coordinator tôi phụ trách.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** `[Tự điền họ và tên]`  
**Ngày xác nhận:** `2026-08-05`
