# SRD-014 — Đăng nhập (Login)

| | |
|---|---|
| Owner | Trang N. (PM) |
| Status | Approved — released in 4.8.0 |
| Last reviewed | 2026-05-12 |

## 1. Scope

Cho phép người dùng đã có tài khoản MyTV đăng nhập trên iOS để truy cập nội dung
thuê bao. Guest (chưa đăng nhập) vẫn xem được nội dung miễn phí.

## 2. Entry points

Người dùng có thể vào màn hình đăng nhập từ hai nơi:

1. **Màn hình giới thiệu (Introduction)** — nút "Đăng nhập ngay".
2. **Tab Cá nhân khi đang ở chế độ guest** — nút "Đăng nhập để tiếp tục".

Cả hai đều mở cùng một `LoginViewController`.

## 3. Preconditions

- Thiết bị đã cài app, người dùng đang ở trạng thái **chưa đăng nhập**.
- Backend staging hoạt động bình thường.
- Tài khoản QA không bật OTP/2FA.

## 4. Main flow (happy path)

1. Mở app. Ở lần mở đầu tiên sau khi cài/xoá dữ liệu, hệ thống hiển thị
   **hộp thoại xin quyền thông báo** của iOS. Người dùng chọn một trong hai.
2. Nhấn "Đăng nhập ngay" → màn hình đăng nhập.
3. Nhập **Tên đăng nhập** và **Mật khẩu**.
4. **Tích vào ô "Tôi đồng ý với điều khoản sử dụng"** — nút "Đăng nhập" bị
   **disabled** cho tới khi ô này được tích. Đây là yêu cầu pháp lý, bắt buộc.
5. Nhấn "Đăng nhập".
6. Thành công → chuyển sang **màn hình chính có thanh tab dưới cùng**
   (Trang chủ / Truyền hình / Cá nhân).

## 5. Alternate & error flows

| # | Điều kiện | Kết quả mong đợi |
|---|---|---|
| 5.1 | Sai tên đăng nhập hoặc mật khẩu | **Ở lại màn hình đăng nhập**, hiển thị dòng chữ đỏ **"Sai tên đăng nhập hoặc mật khẩu"** ngay dưới ô mật khẩu. Không có popup, không quay về màn hình giới thiệu. |
| 5.2 | Chưa tích ô điều khoản | Nút "Đăng nhập" disabled; nếu submit vẫn hiện "Vui lòng đồng ý với điều khoản sử dụng". |
| 5.3 | Nhấn "Điều khoản sử dụng" | Mở sheet điều khoản (trang web nhúng), có nút "Xong" để đóng. |

## 6. Acceptance criteria

- [x] AC-1: Đăng nhập đúng thông tin + đã tích điều khoản → vào được màn hình
      chính và nhìn thấy thanh tab.
- [x] AC-2: Sai mật khẩu → ở lại màn hình đăng nhập kèm thông báo lỗi inline.
- [x] AC-3: Nút đăng nhập disabled khi chưa tích điều khoản.
- [x] AC-4: Không lưu mật khẩu vào log hay file trong repo.
