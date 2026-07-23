---
title: login_form
type: screen
tags: [login]
summary: LoginView — username, password, terms checkbox, submit
last_verified: 2026-07-23
---

# login_form

## Observations
- [native] LoginView loaded from a nib by LoginViewController #login
- [identifier] login_username_field → LoginView.usernameTextField; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_password_field → LoginView.passwordTextField; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_terms_link → LoginView.termsLink; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_submit_button → LoginView.btnLogin; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_error_label → LoginView.errorLabel; verified-in-hierarchy 2026-07-23 #login
- [quirk] btnLogin.isEnabled is driven by termsAccepted — the checkbox must be tapped before submit #login
- [quirk] errorLabel is hidden until showError(_:) runs #login

## Relations
- used-by [[login]]
