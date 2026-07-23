import UIKit

final class AppRouter {
    static let shared = AppRouter()

    func presentLogin(from vc: UIViewController) {
        vc.navigationController?.pushViewController(LoginViewController(), animated: true)
    }

    func presentHome(guest: Bool) {
        UIApplication.shared.keyWindow?.rootViewController =
            MainTabBarController(guest: guest)
    }
}
