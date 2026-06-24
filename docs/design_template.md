# Design Template

## Problem

Xây dựng một **research assistant** nhận một câu hỏi nghiên cứu dạng dài (ví dụ:
"Research GraphRAG state-of-the-art and write a 300-word summary"), tự đi tìm nguồn,
phân tích, kiểm chứng và viết ra câu trả lời cuối cùng có trích dẫn nguồn. Hệ thống
phải so sánh được hai cách tiếp cận: single-agent baseline và multi-agent workflow.

## Why multi-agent?

Single-agent gói toàn bộ việc (tìm nguồn + phân tích + viết + tự kiểm) vào một prompt
duy nhất, dẫn đến:

- **Trộn lẫn trách nhiệm**: model dễ bỏ qua bước phân tích phản biện hoặc bịa nguồn vì
  không có ranh giới rõ giữa "tìm" và "viết".
- **Khó trace/debug**: chỉ có một output, không biết lỗi nằm ở khâu tìm nguồn hay khâu viết.
- **Không có khâu kiểm chứng độc lập**: không ai soát citation coverage hay hallucination.

Multi-agent tách mỗi trách nhiệm thành một agent riêng, mỗi bước ghi trace + cost riêng,
và thêm được một **critic độc lập** để soát chất lượng. Đánh đổi là chậm và đắt hơn
(xem Benchmark plan), nên chỉ dùng khi chất lượng/độ tin cậy quan trọng hơn tốc độ/chi phí.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Quyết định bước kế tiếp & khi nào dừng (routing) | `ResearchState` (các field notes/answer/critique đã có chưa) | `route_history` được cập nhật route kế tiếp | Loop vô hạn → chặn bằng `max_iterations`; có lỗi → route `done` |
| Researcher | Tìm nguồn + tóm tắt thành research notes có citation | `request.query`, `max_sources` | `state.sources`, `state.research_notes` | Search trả rỗng / nguồn rác → fallback mock; lỗi → ghi `state.errors` |
| Analyst | Trích key claims, so sánh quan điểm, flag bằng chứng yếu | `state.research_notes` | `state.analysis_notes` | Notes nghèo → phân tích hời hợt; được critic bắt lại |
| Writer | Tổng hợp câu trả lời cuối cho đúng audience, giữ citation | `research_notes` + `analysis_notes` | `state.final_answer` | Bỏ citation / lệch audience → critic verdict REVISE |
| Critic (bonus) | Fact-check, citation coverage, hallucination check | `final_answer` + `sources` + `research_notes` | `state.critique` + verdict PASS/REVISE | LLM tự tin sai → verdict chỉ là tín hiệu, không tự sửa |

## Shared state

`ResearchState` (xem `core/state.py`) là single source of truth truyền qua mọi agent:

| Field | Lý do cần |
|---|---|
| `request` | Query gốc + `max_sources` + `audience` để mọi agent bám đúng yêu cầu |
| `iteration`, `route_history` | Đếm vòng lặp (guardrail) và biết luồng đã đi qua những đâu để trace |
| `sources` | Nguồn thô để writer/critic kiểm chứng citation |
| `research_notes`, `analysis_notes`, `final_answer`, `critique` | Output từng khâu; cũng là tín hiệu để supervisor route (field nào `None` thì chạy khâu đó) |
| `agent_results` | Lưu cost/token từng agent để benchmark |
| `trace` | Chuỗi event (name + payload) để dump JSON deliverable |
| `errors` | Gom lỗi để fallback thay vì crash |

## Routing policy

State-machine field-driven (không cần LangGraph cho lab 2 giờ vì tuần tự, dễ debug):

```text
        ┌─────────────┐
        │ Supervisor  │◀────────────┐
        └──────┬──────┘             │
   research_notes is None? ──yes──▶ Researcher ─┐
        │ no                                    │
   analysis_notes is None? ──yes──▶ Analyst ────┤ (mỗi worker
        │ no                                    │  cập nhật state
   final_answer is None?   ──yes──▶ Writer ─────┤  rồi quay lại
        │ no                                    │  Supervisor)
   critique is None?       ──yes──▶ Critic ─────┘
        │ no
        ▼
       done
```

Stop khi: có `final_answer` + `critique`, HOẶC `iteration >= max_iterations`, HOẶC có lỗi.

## Guardrails

- **Max iterations**: `MAX_ITERATIONS=6` (config), enforced trong `SupervisorAgent` → không loop vô hạn.
- **Timeout**: `TIMEOUT_SECONDS=60` truyền vào OpenAI client (`LLMClient`).
- **Retry**: `tenacity` retry 3 lần với exponential backoff trong `LLMClient.complete`.
- **Fallback**: agent fail → `MultiAgentWorkflow` bắt exception, ghi `state.errors`, dừng gọn thay vì crash; search không có key → fallback mock.
- **Validation**: input/output qua Pydantic schema (`ResearchQuery` với `min_length`, `SourceDocument`, `BenchmarkMetrics` với `quality_score` 0-10).

## Benchmark plan

| Query | Metric | Expected outcome |
|---|---|---|
| "Research GraphRAG state-of-the-art and write a 300-word summary" | Latency (s) | Multi-agent chậm hơn baseline ~2-3x (nhiều LLM call tuần tự) |
| ↑ | Cost (USD) | Multi-agent đắt hơn ~5x (4-5 call vs 1 call) |
| ↑ | Citation coverage | Multi-agent cao hơn rõ (~100%) nhờ researcher giữ nguồn + critic soát |
| ↑ | Failure rate | Cả hai ~0 với query chuẩn; multi-agent có fallback nên không crash |
| ↑ | Quality (peer review 0-10) | Multi-agent ≥ baseline về độ có cấu trúc & trích dẫn |

Đo bằng `malab benchmark -q "..."` → ghi `reports/benchmark_report.md`. Kết quả thực tế:
baseline 10.3s / $0.000217, multi-agent 34.5s / $0.001202 / citation 100%.
