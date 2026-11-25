# DEPLOYMENT.md — Day 14

## Part 6 — Render

- Nền tảng: Render Web Service (Docker), deploy từ `06-lab-complete/`; Redis dùng Render Key Value.
- Public URL: https://k5-l3a-day14-chuthannhat-2a202603649.onrender.com
- Redis: đã kết nối; `/ready` trả `{"status":"ready","redis":true}`.
- Biến môi trường cấu hình trên Render: `ENVIRONMENT`, `REDIS_URL`, `AGENT_API_KEY`. Không lưu giá trị secret trong repo.

## Lệnh kiểm tra và kết quả thực tế

PowerShell, kiểm tra health/readiness và request thiếu key:

```powershell
$base = "https://k5-l3a-day14-chuthannhat-2a202603649.onrender.com"
Invoke-WebRequest "$base/health" -SkipHttpErrorCheck | Select-Object StatusCode, Content
Invoke-WebRequest "$base/ready" -SkipHttpErrorCheck | Select-Object StatusCode, Content
Invoke-WebRequest "$base/ask" -Method Post -ContentType "application/json" -Body '{"question":"deployment check"}' -SkipHttpErrorCheck | Select-Object StatusCode, Content
```

| Request | HTTP | Kết quả |
|---|---:|---|
| `GET /health` | 200 | `{"status":"ok"}` |
| `GET /ready` | 200 | `{"status":"ready","redis":true}` |
| `POST /ask` không có `X-API-Key` | 401 | API key bị từ chối như mong đợi |
| `POST /ask` có `X-API-Key` hợp lệ, body `{"question":"deployment check"}` | 200 | Trả câu hỏi và câu trả lời mock |

Request có key được gửi bằng PowerShell `Invoke-RestMethod`; key được nhập ẩn qua `Read-Host -AsSecureString` và không lưu trong báo cáo. PowerShell hiển thị tiếng Việt bị lỗi mã hóa ở terminal, nhưng request thành công.

Để tự kiểm tra request có key, lấy giá trị từ secret manager/Render rồi nhập vào biến chỉ tồn tại trong phiên PowerShell; không ghi key vào file hoặc lệnh lưu trong history:

```powershell
$base = "https://k5-l3a-day14-chuthannhat-2a202603649.onrender.com"
$secureKey = Read-Host "AGENT_API_KEY" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    Invoke-RestMethod "$base/ask" -Method Post -Headers @{ "X-API-Key" = $apiKey } -ContentType "application/json" -Body '{"question":"deployment check"}'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    Remove-Variable apiKey, secureKey, ptr -ErrorAction SilentlyContinue
}
```
