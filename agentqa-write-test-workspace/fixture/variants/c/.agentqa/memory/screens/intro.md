---
title: intro
type: screen
tags: [login]
summary: IntroductionContentViewController — login / guest entry point
last_verified: 2026-07-23
---

# intro

## Observations
- [native] IntroductionContentViewController, UIKit xib #login
- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; verified-in-hierarchy 2026-07-23 #login
- [quirk] requests notification permission in viewDidLoad, so the alert covers this screen on a wiped launch #login

## Relations
- used-by [[login]]
