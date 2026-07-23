import UIKit

/// Profile tab. Guests see a sign-in prompt here — the second way into the
/// login flow, alongside the intro screen.
final class ProfileViewController: UIViewController {

    @IBOutlet private weak var emptyStateLabel: UILabel!
    @IBOutlet private weak var btnSignIn: UIButton!

    private var isGuest: Bool { SessionStore.shared.current == nil }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        emptyStateLabel.text = "Bạn chưa đăng nhập"
        btnSignIn.setTitle("Đăng nhập để tiếp tục", for: .normal)
        emptyStateLabel.isHidden = !isGuest
        btnSignIn.isHidden = !isGuest
    }

    @IBAction private func didTapSignIn(_ sender: UIButton) {
        AppRouter.shared.presentLogin(from: self)
    }
}
