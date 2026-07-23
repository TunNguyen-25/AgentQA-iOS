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
