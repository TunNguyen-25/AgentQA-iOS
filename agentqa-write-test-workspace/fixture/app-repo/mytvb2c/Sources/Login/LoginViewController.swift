import UIKit

final class LoginViewController: UIViewController {

    private var loginView: LoginView!

    override func loadView() {
        loginView = Bundle.main.loadNibNamed("LoginView", owner: self)?.first as? LoginView
        view = loginView
        loginView.btnLogin.addTarget(self, action: #selector(submit), for: .touchUpInside)
        loginView.termsLink.addTarget(self, action: #selector(showTerms), for: .touchUpInside)
    }

    @objc private func submit() {
        let username = loginView.usernameTextField.text ?? ""
        let password = loginView.passwordTextField.text ?? ""
        guard loginView.termsAccepted else {
            loginView.showError("Vui lòng đồng ý với điều khoản sử dụng")
            return
        }
        Task {
            do {
                let session = try await AuthService.login(username: username, password: password)
                handle(result: .success(session))
            } catch {
                handle(result: .failure(error))
            }
        }
    }

    private func handle(result: Result<Session, Error>) {
        switch result {
        case .success:
            AppRouter.shared.presentHome(guest: false)
        case .failure:
            loginView.showError("Sai tên đăng nhập hoặc mật khẩu")
        }
    }

    @objc private func showTerms() {
        present(TermsWebViewController(), animated: true)
    }
}
