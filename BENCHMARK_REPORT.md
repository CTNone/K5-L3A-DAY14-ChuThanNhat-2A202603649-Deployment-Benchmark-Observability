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

P99 phản ứng trước tiên với tỉ lệ slow 0.03: p95 vẫn 235.3 ms nhưng p99 lên 1682.7 ms. Ở rate 0.1, slow response đủ nhiều để cả p95 tăng lên 1705.8 ms. Average che khuất nhóm request chậm nên không đại diện trải nghiệm đuôi. Mỗi cấu hình có 300 request, concurrency 10; error rate mặc định của mock khoảng 1%. File: `reports/load_v2_slow_0.json`, `reports/load_v2_slow_0.03.json` và `reports/load_v2_slow_0.1.json`.

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

- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals) — `screenshots/grafana-dashboard.png`
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian) — `screenshots/jaeger-slow-trace.png`
- [x] Một trace lỗi trong Jaeger (có event `exception`) — `screenshots/jaeger-error-trace.png`
- [x] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing** — `screenshots/prometheus-alert-firing.png` (2 alerts firing cùng lúc)

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` (~1m09s sau khi bắt đầu tải) | ~1m09s | Error rate; khoảng 20–21% |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` (~2m09s sau khi bắt đầu tải) | ~2m09s | Latency p95/p99; p95 ~1.9 s |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` (~2m15s sau khi bắt đầu tải) | ~2m15s | Cost USD/hour; burn rate quan sát được khoảng $11–$15/hour |
| D | `docker pause k5-day14-observability-agent-2` | `AgentInstanceDown` | ~37s sau khi pause | Instances up / Prometheus target; Locust thấy 29 lỗi 504 và 9 lỗi 503 |
| E | `AGENT_VERSION=v1` | Không có alert chất lượng mới | Không phát hiện bằng alert hạ tầng | Agent version và retrieval hit ratio; v1 hiện trên `agent_info`, retrieval series không xuất hiện |

A và B được kích hoạt đồng thời trong một lượt tải: ảnh Prometheus ghi nhận `AgentHighErrorRate` và `AgentHighLatencyP95` cùng **FIRING**. Thời gian trong bảng là thời gian quan sát từ lúc bắt đầu lượt tải đến khi mỗi alert chuyển trạng thái; lần lượt khoảng 1m09s và 2m09s. Ảnh Grafana/Prometheus, CSV từng thí nghiệm và trace JSON/JSONL đã được lưu trong repo.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Sự cố chất lượng không tự làm các Golden Signals hạ tầng báo đỏ. Cần chạy golden dataset eval trước deploy và định kỳ, theo dõi accuracy/regression theo version, retrieval hit/miss và phản hồi người dùng; đặt quality gate làm điều kiện release.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: `011c45688cd30f0dcd9f1029966c835d`
- Tổng thời gian: 1676.3 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` (1651.4 ms, 98.5%)
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts":"2026-11-25T15:21:36.646052+00:00","level":"INFO","service":"observable-agent","instance":"b39d3c80b2f3","event":"llm_call","trace_id":"011c45688cd30f0dcd9f1029966c835d","span_id":"85674ff2bdddd5df","request_id":"a0aef5f5f3f2","model":"mock-llm-small","agent_version":"v2","input_tokens":68,"output_tokens":35,"cost_usd":3.1e-05,"llm_ms":1649.5}
{"ts":"2026-11-25T15:21:36.646977+00:00","level":"INFO","service":"observable-agent","instance":"b39d3c80b2f3","event":"http_request","trace_id":"011c45688cd30f0dcd9f1029966c835d","span_id":"85674ff2bdddd5df","request_id":"a0aef5f5f3f2","method":"POST","route":"/ask","status":200,"ms":1675.1}
```

Trace lỗi: `10bca863cd92dd256f3c51d61746353b` (862.3 ms); span `chat mock-llm-small` có event `exception` với `utils.mock_llm.LLMError`. Log JSON tương ứng:

```json
{"ts":"2026-11-25T15:21:37.782896+00:00","level":"INFO","service":"observable-agent","instance":"b39d3c80b2f3","event":"llm_error","trace_id":"10bca863cd92dd256f3c51d61746353b","span_id":"e1119f8ec347190a","request_id":"f2469985924a","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
{"ts":"2026-11-25T15:21:37.783307+00:00","level":"INFO","service":"observable-agent","instance":"b39d3c80b2f3","event":"http_request","trace_id":"10bca863cd92dd256f3c51d61746353b","span_id":"e1119f8ec347190a","request_id":"f2469985924a","method":"POST","route":"/ask","status":503,"ms":861.6}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 64.62 | 200 | 530 | 1700 | 65 / 7673 |
| 3 | 65.61 | 190 | 250 | 1700 | 64 / 7796 |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Ba replica giảm p95 từ 530 xuống 250 ms (~53%) và p50 từ 200 xuống 190 ms, nhưng RPS chỉ tăng khoảng 1.5%. p99 vẫn 1.7 s ở cả hai cấu hình; điều này khớp với 3% slow mock call cộng thêm khoảng 1.5 s, nên các request đuôi chậm vẫn chi phối dù đã scale. CSV đầy đủ ở `benchmark-results/scale_1_stats.csv` và `benchmark-results/scale_3_stats.csv`; Locust có một số 503 ngẫu nhiên theo cấu hình mock.

Cost/quality trade-off của thí nghiệm C: model `mock-llm-large` làm `LLMCostBurnRateHigh` firing khi cost rate vượt ngưỡng, trong khi thí nghiệm E cho thấy đổi sang v1 không tạo cảnh báo hạ tầng dù chất lượng retrieval suy giảm. Vì vậy cần ghép cost alert với eval theo version; quality gate cuối dùng accuracy 1.0 và baseline `reports/eval_v2.json`, và đã PASS sau khi sửa knowledge base.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. p95/p99 và tail latency cho thấy request chậm mà average hoặc p50 bỏ qua.
  2. Thêm replica giảm p95 dưới workload này, nhưng không loại bỏ p99 do slow call; throughput không tăng tuyến tính.
  3. Metrics/traces phát hiện lỗi hạ tầng, còn chất lượng câu trả lời cần golden eval riêng và quality gate.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Trong production thật, bổ sung metric theo category/intent và tỷ lệ retrieval miss có cardinality thấp; alert theo burn rate của SLO, chất lượng eval và ngân sách cost, đồng thời theo dõi freshness của KB. Kết quả này là lab local trên Docker Desktop, không phải bằng chứng deployment production.
