import UIKit

/// The login form. `btnLogin` stays disabled until the terms box is ticked.
final class LoginView: UIView {

    @IBOutlet private weak var headingLabel: UILabel!
    @IBOutlet weak var usernameTextField: UITextField!
    @IBOutlet weak var passwordTextField: UITextField!
    @IBOutlet weak var checkBoxTermImgView: UIImageView!
    @IBOutlet weak var termsLink: UIButton!
    @IBOutlet weak var btnLogin: UIButton!
    @IBOutlet private weak var errorLabel: UILabel!

    private(set) var termsAccepted = false {
        didSet { btnLogin.isEnabled = termsAccepted }
    }

    override func awakeFromNib() {
        super.awakeFromNib()
        headingLabel.text = "Đăng nhập"
        usernameTextField.placeholder = "Tên đăng nhập"
        passwordTextField.placeholder = "Mật khẩu"
        passwordTextField.isSecureTextEntry = true
        termsLink.setTitle("Điều khoản sử dụng", for: .normal)
        btnLogin.setTitle("Đăng nhập", for: .normal)
        btnLogin.isEnabled = false
        errorLabel.isHidden = true

        let tap = UITapGestureRecognizer(target: self, action: #selector(toggleTerms))
        checkBoxTermImgView.isUserInteractionEnabled = true
        checkBoxTermImgView.addGestureRecognizer(tap)
    }

    @objc private func toggleTerms() {
        termsAccepted.toggle()
        checkBoxTermImgView.image = UIImage(named: termsAccepted ? "cb_on" : "cb_off")
    }

    func showError(_ message: String) {
        errorLabel.text = message
        errorLabel.isHidden = false
    }
}
