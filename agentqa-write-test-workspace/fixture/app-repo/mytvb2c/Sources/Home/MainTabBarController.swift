import UIKit

final class MainTabBarController: UITabBarController {

    private let homeTab = UITabBarItem(title: "Trang chủ", image: nil, tag: 0)
    private let liveTab = UITabBarItem(title: "Truyền hình", image: nil, tag: 1)
    private let profileTab = UITabBarItem(title: "Cá nhân", image: nil, tag: 2)

    override func viewDidLoad() {
        super.viewDidLoad()
        let home = HomeViewController()
        home.tabBarItem = homeTab
        let live = LiveViewController()
        live.tabBarItem = liveTab
        let profile = ProfileViewController()
        profile.tabBarItem = profileTab
        viewControllers = [home, live, profile]
    }
}
