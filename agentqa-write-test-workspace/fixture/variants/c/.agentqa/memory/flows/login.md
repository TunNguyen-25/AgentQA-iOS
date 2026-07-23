---
title: login
type: flow
tags: [login, authentication]
summary: Intro → login form → home tab bar, gated on a terms checkbox
last_verified: 2026-07-23
---

# login

## Observations
- [flow-step] launch → notifications permission alert (SpringBoard) → dismissed with "Don't Allow" per reviewer #login
- [flow-step] IntroductionContentViewController → press "Đăng nhập ngay" → LoginViewController #login
- [flow-step] fill username + password, tick "Tôi đồng ý với điều khoản sử dụng", press "Đăng nhập" #login
- [flow-step] success → MainTabBarController with tab bar Trang chủ / Truyền hình / Cá nhân #login
- [assertion] valid credentials + terms ticked lands on the home tab bar #login
- [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" under the password field, stays on login #login
- [edge-case] terms unticked → "Vui lòng đồng ý với điều khoản sử dụng", submit is disabled #login
- [native] intro, login and home are native UIKit #login
- [web] the terms sheet is a WKWebView with no native nodes — screenshot only #login
- [quirk] the permission alert is owned by SpringBoard and appears on every wiped launch #login

## Relations
- covers [[intro]]
- covers [[login_form]]
- covers [[home]]
