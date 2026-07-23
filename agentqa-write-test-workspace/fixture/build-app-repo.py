#!/usr/bin/env python3
"""Generate the mock MyTV app repo used as the eval fixture."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent / "app-repo"

FILES = {}

FILES[".agentqa/config.yml"] = """\
# Project configuration for the agentqa skill (.agentqa/config.yml)
# Facts about THIS project that the generic skill must not hardcode.

platform: ios
bundle_id: com.vnpt.media.mobileb2c
test_dir: AutomationTests

build:
  policy: human
  note: "Manual builds required — signing and package configuration"

reset_app_data: always   # always (DEFAULT) = wipe the app's local data before launch

credentials:
  username_env: APP_TEST_USERNAME   # env var NAMES only — never values
  password_env: APP_TEST_PASSWORD

identifier_convention: screen_element_type   # e.g. login_username_field, home_profile_button

appium:
  port: 4723
"""

FILES[".agentqa/memory/.gitignore"] = """\
# Ephemeral per-run working state (Working layer) — never committed.
.run-checkpoint.md
.session-requirement.md
"""

FILES[".agentqa/memory/README.md"] = """\
# .agentqa/memory — behavioral knowledge store

Behavioral knowledge the test agent hand-earns at runtime: real navigation
paths, native-vs-web screens, verified identifier placements, phantom-failure
signatures, build gotchas. Not code knowledge — CodeGraph regenerates that.

`index.md` is generated. Rebuild it with:

    python3 <skill>/scripts/memory-index.py .agentqa/memory
"""

FILES[".agentqa/memory/env.md"] = """\
---
title: Environment & project knowledge
type: env
tags:
- env
---

# Environment & project knowledge

Narrative knowledge for this app's UI tests. Structured facts live in
`.agentqa/config.yml`; this file holds the *why* and the gotchas. No secrets —
credential env-var **names** only.

## Observations
- [gotcha] Never run CPU-heavy jobs (e.g. `codegraph init`) during simulator tests — WebDriverAgent times out and produces phantom failures.
- [gotcha] Appium `page_source` for the booted simulator is printed by the repo helper `page-source` (already on PATH). Use it instead of hand-rolling an Appium client.
- [gotcha] The human reviewer is reachable only through the `ask-user` helper on PATH: `ask-user "<question>"` prints their answer. Interactive prompts do not reach them.
- [credential-env] APP_TEST_USERNAME, APP_TEST_PASSWORD
- [build-policy] Manual builds required — signing and package configuration require human intervention (build.policy: human)
"""

FILES["CLAUDE.md"] = """\
# MyTV B2C iOS — agent notes

Swift/UIKit app. UI tests are agent-written Appium (XCUITest) tests under
`AutomationTests/`.

- Project facts (bundle id, test dir, build policy, credential env-var names):
  `.agentqa/config.yml`
- Behavioral knowledge from previous test-writing runs: `.agentqa/memory/`
  (start at `index.md`)
- App sources: `mytvb2c/Sources/`

## Helpers on PATH

| Command | What it does |
|---|---|
| `ask-user "<question>"` | Ask the human reviewer something and print their answer. They are not otherwise reachable. |
| `page-source` | Print the Appium `page_source` of whatever is on the booted simulator right now. |
| `agent-device` | Drive the simulator (open / snapshot / press / fill / screenshot). |
| `codegraph` | Index and query the Swift symbol graph. |

Builds are done by a human — do not run `xcodebuild`.
"""

# ---------------------------------------------------------------- Swift sources

FILES["mytvb2c/Sources/Login/IntroductionContentViewController.swift"] = """\
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
"""

FILES["mytvb2c/Sources/Login/LoginView.swift"] = """\
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
"""

FILES["mytvb2c/Sources/Login/LoginViewController.swift"] = """\
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
"""

FILES["mytvb2c/Sources/Login/TermsWebViewController.swift"] = """\
import UIKit
import WebKit

/// Remote terms page. Content is rendered by WKWebView and is NOT exposed to
/// the native accessibility tree.
final class TermsWebViewController: UIViewController {

    private let webView = WKWebView()
    private lazy var doneButton = UIBarButtonItem(
        title: "Xong", style: .done, target: self, action: #selector(dismissSelf))

    override func viewDidLoad() {
        super.viewDidLoad()
        view = webView
        navigationItem.rightBarButtonItem = doneButton
        webView.load(URLRequest(url: URL(string: "https://mytv.example/terms")!))
    }

    @objc private func dismissSelf() { dismiss(animated: true) }
}
"""

FILES["mytvb2c/Sources/Home/MainTabBarController.swift"] = """\
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
"""

FILES["mytvb2c/Sources/Profile/ProfileViewController.swift"] = """\
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
"""

FILES["mytvb2c/Sources/Networking/AuthService.swift"] = """\
import Foundation

struct Session { let token: String; let expiresAt: Date }

enum AuthError: Error {
    case invalidCredentials
    case termsNotAccepted
    case network(Error)
}

enum AuthService {
    /// POST /auth/login on the configured backend.
    static func login(username: String, password: String) async throws -> Session {
        var request = URLRequest(url: Backend.url("/auth/login"))
        request.httpMethod = "POST"
        request.httpBody = try JSONEncoder().encode(
            ["username": username, "password": password])
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw AuthError.invalidCredentials
        }
        return try JSONDecoder().decode(Session.self, from: data)
    }
}
"""

FILES["mytvb2c/Sources/App/AppRouter.swift"] = """\
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
"""

# ------------------------------------------------------------ AutomationTests

FILES["AutomationTests/pytest.ini"] = """\
[pytest]
testpaths = tests
addopts = -ra
"""

FILES["AutomationTests/requirements.txt"] = """\
Appium-Python-Client>=4.0
pytest>=8.0
PyYAML>=6.0
"""

FILES["AutomationTests/pages/__init__.py"] = ""
FILES["AutomationTests/tests/__init__.py"] = ""

FILES["AutomationTests/conftest.py"] = '''\
"""Appium driver fixture for agent-driven UI tests.

Reads the bundle id from ../.agentqa/config.yml, attaches to the booted
simulator, wipes the app's data before the session when
`reset_app_data: always`, and saves page_source + a screenshot whenever a test
fails so a later run can diagnose it without re-running.
"""
import os
import subprocess
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".agentqa" / "config.yml"
ARTIFACTS = Path(__file__).parent / "artifacts"
APPIUM_URL = "http://127.0.0.1:4723"


def _config(key: str, default: str = "") -> str:
    if not CONFIG.is_file():
        return default
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.split(":", 1)[1].split("#", 1)[0].strip().strip('"')
    return default


BUNDLE_ID = os.environ.get("AGENTQA_BUNDLE_ID") or _config("bundle_id")
RESET_APP_DATA = _config("reset_app_data", "always")


@pytest.fixture(scope="session", autouse=True)
def wipe_app_data():
    """reset_app_data: always -> every session starts from a clean install."""
    if RESET_APP_DATA == "always":
        subprocess.run(["xcrun", "simctl", "terminate", "booted", BUNDLE_ID],
                       check=False, capture_output=True)
        subprocess.run(["xcrun", "simctl", "privacy", "booted", "reset", "all",
                        BUNDLE_ID], check=False, capture_output=True)


@pytest.fixture(scope="session")
def driver(wipe_app_data):
    options = XCUITestOptions()
    options.bundle_id = BUNDLE_ID
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    options.new_command_timeout = 300
    drv = webdriver.Remote(APPIUM_URL, options=options)
    drv.implicitly_wait(10)
    yield drv
    drv.quit()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        drv = item.funcargs.get("driver")
        if drv is None:
            return
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        stem = ARTIFACTS / f"failed_{item.name}"
        try:
            stem.with_suffix(".xml").write_text(drv.page_source, encoding="utf-8")
            drv.save_screenshot(str(stem.with_suffix(".png")))
        except Exception:
            pass
'''

FILES[".gitignore"] = """\
.venv/
__pycache__/
*.pyc
AutomationTests/artifacts/
.codegraph/
"""


def main():
    for rel, content in FILES.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    print(f"wrote {len(FILES)} files under {ROOT}")


if __name__ == "__main__":
    sys.exit(main())
