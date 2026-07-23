import UIKit

/// First screen after launch. Offers login or a limited guest experience.
final class IntroductionContentViewController: UIViewController {

    @IBOutlet private weak var titleLabel: UILabel!
    @IBOutlet private weak var subtitleLabel: UILabel!
    @IBOutlet private weak var btnLogin: UIButton!
    @IBOutlet private weak var btnFree: UIButton!

    override func viewDidLoad() {
        super.viewDidLoad()
        titleLabel.text = "Đăng nhập MyTV"
        subtitleLabel.text = "Xem phim, truyền hình mọi lúc mọi nơi"
        btnLogin.setTitle("Đăng nhập ngay", for: .normal)
        btnFree.setTitle("Xem miễn phí", for: .normal)
        NotificationPermission.requestIfNeeded()
    }

    @IBAction private func didTapLogin(_ sender: UIButton) {
        AppRouter.shared.presentLogin(from: self)
    }

    @IBAction private func didTapFree(_ sender: UIButton) {
        AppRouter.shared.presentHome(guest: true)
    }
}
