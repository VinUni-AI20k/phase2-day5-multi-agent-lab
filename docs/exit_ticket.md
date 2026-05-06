# Exit Ticket — Lab 20

**Author:** Trịnh Kế Tiến — 2A202600500
**Date:** 2026-05-06

## Q1. Case nào nên dùng multi-agent? Vì sao?

Multi-agent xứng đáng khi **chất lượng và khả năng audit quan trọng hơn latency / cost**, và task có **các sub-role tách bạch rõ ràng**:

- **Research / due-diligence**: cần search nhiều nguồn → tổng hợp → viết báo cáo có citation. Tách Researcher / Analyst / Writer giúp mỗi prompt ngắn, dễ kiểm soát hallucination, và có intermediate state để debug nếu output sai.
- **Customer support có escalation**: một agent triage, một agent giải task chuyên môn, một agent rephrase phản hồi. Hand-off rõ ràng giảm rủi ro 1 prompt khổng lồ "biết tuốt" nhưng dễ lệch.
- **Compliance-sensitive workflows**: cần auditable trace chứng minh model đã xem nguồn nào, đã suy luận gì trước khi ra answer cuối — multi-agent ghi log từng bước vào shared state.

Lý do cốt lõi: **separation of concerns**. Mỗi agent có 1 prompt ngắn, 1 trách nhiệm, 1 failure mode dễ test. Đổi 1 phần (vd: thay search backend) không phải viết lại toàn bộ prompt.

## Q2. Case nào không nên dùng multi-agent? Vì sao?

Tránh multi-agent khi **chi phí điều phối lớn hơn lợi ích về chất lượng**:

- **Câu hỏi đơn giản, câu trả lời ngắn**: "Tóm tắt 1 đoạn", "Dịch câu này" — single-agent đã đủ. Multi-agent chỉ đốt token và tăng latency.
- **Latency-critical UX**: chat real-time, autocomplete, voice assistant. Multi-agent (đo được trong [benchmark_report.md](../reports/benchmark_report.md)) chậm gấp ~3.4× — không chấp nhận được trong UI < 2s.
- **Task không có sub-role rõ ràng**: nếu bạn không biết mỗi agent sẽ làm gì khác nhau, thêm agent chỉ tạo overhead. Quy tắc: nếu prompt của 2 agent trông giống nhau 80%, gộp lại.
- **Budget cực hẹp**: mỗi agent là 1 LLM call → cost ~tỉ lệ tuyến tính với số agent. Với volume lớn, single-agent có thể hợp lý hơn cho 90% case và escalate sang multi-agent chỉ khi cần.

**Heuristic cá nhân**: bắt đầu bằng single-agent. Chỉ thêm agent thứ 2 khi single-agent fail có hệ thống ở 1 sub-task cụ thể (vd: hay hallucinate citation → tách Writer + Critic). Đừng thiết kế multi-agent vì "trông xịn".
