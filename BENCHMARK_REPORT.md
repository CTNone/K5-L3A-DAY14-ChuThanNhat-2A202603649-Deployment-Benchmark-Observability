# Benchmark & Observability Report — Day 14

> Copy file này thành `BENCHMARK_REPORT.md` trong repo của bạn và điền đầy đủ.
> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Chu Thân Nhất 
**Ngày chạy:** 2026-11-25
**Môi trường:** Windows 10 Pro, Python 3.11.9, 8 logical processors; mock agent chạy local, không dùng Docker/API key.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Ngưỡng SLO mẫu trong README; bảo vệ phần lớn request khỏi chờ lâu. |
| Error rate `/ask` | < 2% | Ngưỡng SLO mẫu trong README; giới hạn lỗi cho phép trong load test. |
| Accuracy trên golden dataset | ≥ 100% sau khi sửa KB | Quality gate cuối chạy với `--min-accuracy 1.0`; bộ golden dataset nhỏ nên đây là gate hồi quy cho các câu đã biết. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 3.89 | 205.5 | 251.0 | 1693.3 | 0% | PASS |
| 10 | 44.14 | 198.8 | 238.5 | 1686.3 | 0.5% | PASS |
| 50 | 45.90 | 337.8 | 2349.2 | 2691.9 | 0.5% | FAIL (p95) |
| 100 | 32.77 | 942.6 | 4266.9 | 5125.8 | 0% | FAIL (p95) |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

Mỗi lần chạy 200 request, SLO p95=500 ms và error rate=2%. RPS tăng rõ từ concurrency 1 đến 10, gần như bão hòa ở 50 rồi giảm ở 100; request queueing làm p95/p99 tăng mạnh. Đây là kết quả của một máy Windows local và mock, không phải giới hạn capacity production. File: `reports/load_v2_c{1,10,50,100}.json`.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 193.4 | 231.9 | 244.8 |
| 0.03 (mặc định) | 219.9 | 235.3 | 1682.7 |
| 0.1 | 360.5 | 1705.8 | 1726.3 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

P99 phản ứng trước tiên với tỉ lệ slow 0.03: p95 vẫn 235.3 ms nhưng p99 lên 1682.7 ms. Ở rate 0.1, slow response đủ nhiều để cả p95 tăng lên 1705.8 ms. Average che khuất nhóm request chậm nên không đại diện trải nghiệm đuôi. Mỗi cấu hình có 300 request, concurrency 10; error rate mặc định của mock khoảng 1%. File: `reports/load_v2_slow_*.json`.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 56.8 | 109.0 | 113.6 |
| Tổng cost (USD) | 0.000400 | 0.000760 | 0.000790 |
| Cost / câu đúng (USD) | 0.00040035 | 0.00003619 | 0.00003436 |
| Quality gate | FAIL (min 80%) | PASS (min 80%, không regression so v1) | PASS (min 100%, không regression so eval_v2) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | `token`, `hết hạn`, `chữ ký` | Thêm entry giải thích JWT là token có chữ ký/thời hạn, khác API key tĩnh. |
| scaling-03 | `cpu`, `memory`, `custom metrics` | Thêm entry HPA Kubernetes scale theo CPU, memory và custom metrics. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

So với v1, v2 tăng accuracy từ 4.3% lên 91.3%, p95 tăng 23.0 ms (205.6→228.6), token trung bình tăng 52.2 và tổng cost tăng khoảng 90% (0.000400→0.000760 USD). Do v2 trả lời đúng nhiều hơn, cost/câu đúng giảm khoảng 91% (0.00040035→0.00003619 USD). Sau khi bổ sung KB, accuracy đạt 100%, không có regression, và cost/câu đúng còn 0.00003436 USD. P95 của lần eval cuối là 1713.1 ms do 3/23 request trúng mock slow mặc định; eval ít mẫu nên percentile này nhiễu, không dùng thay load test.

### Quality gate trong CI

Đã thêm workflow `.github/workflows/quality-gate.yml`. Nó khởi động agent v2 trong runner và chạy golden eval với ngưỡng 100% cùng baseline đã lưu. Khi chạy v1 thay vì v2 để kiểm tra gate, accuracy 4.3%, có 20 regression so baseline v2 và process trả exit code 1; GitHub Actions sẽ đánh dấu check fail và chặn merge theo branch protection nếu yêu cầu check này.

Lệnh gate: `python eval/run_eval.py --url http://127.0.0.1:8000 --min-accuracy 1.0 --baseline ../../../reports/eval_v2.json`

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. p95/p99 và tail latency cho thấy request chậm mà average hoặc p50 bỏ qua.
  2. Concurrency lớn hơn không bảo đảm throughput cao hơn; queueing làm SLO p95 thất bại ở mức 50 và 100.
  3. Golden eval phát hiện hai khoảng trống KB; thêm nội dung đúng giúp v2 lên 100% và CI gate bắt được regression.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Trong production thật, bổ sung metric theo category/intent và tỷ lệ retrieval miss có cardinality thấp; alert theo burn rate của SLO, chất lượng eval và ngân sách cost, đồng thời theo dõi freshness của KB. Phần observability stack và scaling chưa chạy trong lượt này.
