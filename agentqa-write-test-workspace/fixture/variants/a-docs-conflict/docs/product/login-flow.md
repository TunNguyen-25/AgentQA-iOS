# SRD-014 — Đăng nhập (Login)

| | |
|---|---|
| Owner | Trang N. (PM) |
| Status | Draft — viết trước khi bàn giao cho team iOS |
| Last reviewed | 2025-11-03 |

## 1. Scope

Cho phép người dùng đã có tài khoản MyTV đăng nhập trên iOS để truy cập nội dung
thuê bao.

## 2. Entry point

Từ **màn hình giới thiệu (Introduction)** — nút "Đăng nhập ngay".

## 3. Preconditions

- Người dùng đang ở trạng thái chưa đăng nhập.
- Backend staging hoạt động bình thường.

## 4. Main flow (happy path)

1. Mở app → màn hình giới thiệu.
2. Nhấn "Đăng nhập ngay" → màn hình đăng nhập.
3. Nhập **Tên đăng nhập** và **Mật khẩu**.
4. Bật tuỳ chọn **"Ghi nhớ đăng nhập"** nếu muốn giữ phiên đăng nhập cho lần sau.
5. Nhấn "Đăng nhập".
6. Thành công → chuyển sang **Dashboard**, hiển thị popup chào mừng
   "Chào mừng quý khách trở lại".

## 5. Alternate & error flows

| # | Điều kiện | Kết quả mong đợi |
|---|---|---|
| 5.1 | Sai tên đăng nhập hoặc mật khẩu | Hiển thị **hộp thoại (modal)** với tiêu đề "Tài khoản không hợp lệ" và nút "Đóng". Sau khi đóng, **quay về màn hình giới thiệu**. |
| 5.2 | Mất kết nối mạng | Toast "Không có kết nối mạng". |

## 6. Acceptance criteria

- [ ] AC-1: Đăng nhập đúng thông tin → vào Dashboard và thấy popup chào mừng.
- [ ] AC-2: Sai mật khẩu → hiện modal "Tài khoản không hợp lệ", quay về màn
      hình giới thiệu.
- [ ] AC-3: Tuỳ chọn "Ghi nhớ đăng nhập" giữ được phiên sau khi tắt app.
