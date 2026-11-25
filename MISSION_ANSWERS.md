# MISSION_ANSWERS.md — Day 14

> Ghi câu trả lời và kết quả tự chạy tại đây. Không điền số liệu chưa đo.

## Part 1 — Localhost vs Production

### Anti-patterns tìm được trong `01-localhost-vs-production/develop/app.py`

1. API key và database URL được hardcode trong source; nếu dùng secret thật rồi push repo public thì có thể bị lộ.
2. Không có config management: `DEBUG = True` và `MAX_TOKENS = 500` được gán cố định, không đọc từ environment.
3. Dùng `print()` thay structured logging; dòng debug còn in cả API key ra log.
4. Không có endpoint `/health` hoặc `/ready` để nền tảng kiểm tra liveness/readiness.
5. Port bị cố định ở `8000`, không đọc biến `PORT` mà nền tảng cloud cung cấp.
6. Bind vào `localhost`, khiến dịch vụ không nhận kết nối từ bên ngoài container/máy.
7. `reload=True` luôn bật, không phù hợp cho cách chạy production.

### Kết quả thử develop

Chạy trong WSL2 bằng `python app.py`, sau đó gửi `curl -i -X POST "http://localhost:8000/ask?question=Hello"`. Server khởi động ở `http://localhost:8000`; request trả `HTTP/1.1 200 OK` cùng câu trả lời mock. Log cho thấy `[DEBUG] Got question: Hello`, `[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this` và câu trả lời. Như vậy app chạy được local, nhưng log đã phơi bày giá trị key giả được hardcode. Khi dừng tiến trình thử nghiệm, Uvicorn ghi nhận shutdown và thoát.

### Bảng so sánh develop/production

| Khía cạnh | Develop | Production | Ý nghĩa khi deploy |
|---|---|---|---|
| Cấu hình/secret | Hardcode trong `app.py`; `DEBUG=True` | Cấu hình tập trung trong `config.py`, lấy từ environment | Thay đổi môi trường mà không sửa source; tránh commit secret thật |
| Logging | `print()`, có dòng in API key | Logger với format có cấu trúc; log request không chứa secret | Dễ tìm kiếm/thu thập log và giảm nguy cơ lộ thông tin |
| Host và port | `localhost:8000` cố định | Host/port lấy theo settings, hỗ trợ bind `0.0.0.0` và `PORT` | Container/cloud có thể nhận traffic qua cổng được nền tảng cấp |
| Kiểm tra trạng thái | Không có health endpoint | Có `GET /health`, `GET /ready` và `/metrics` | Nền tảng/load balancer kiểm tra trạng thái và readiness |
| Debug/reload | `reload=True` luôn bật | Reload chỉ bật khi cấu hình debug bật | Tránh chế độ phát triển chạy ngoài ý muốn trong production |
| Vòng đời/tắt app | Không có cleanup/lifecycle riêng | Có lifespan startup/shutdown và xử lý SIGTERM | Có điểm để khởi tạo/đóng tài nguyên khi app bắt đầu hoặc dừng |

## Part 2 — Docker

TODO: trả lời Exercise 2.1; ghi kết quả container, kích thước image đo được, sơ đồ stack và test Nginx.

## Part 3 — Cloud Deployment

TODO: mô tả pipeline Cloud Run (Exercise 3.3), nền tảng deploy Part 6 và URL sau khi deploy.

## Part 4 — API Security

TODO: ghi kết quả HTTP 401/200/429; che token.

## Part 5 — Scaling & Reliability

TODO: ghi kết quả scale 3 instance và test_stateless.py.

## Part 6 — Final Project

TODO: dán kết quả check_production_ready.py sau khi chạy.

## AI log

- TODO: ghi câu hỏi đã hỏi AI, gợi ý nhận được, phần tự sửa và cách tự kiểm tra.
