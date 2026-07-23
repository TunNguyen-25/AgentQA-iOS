# Repo changes

## git diff --numstat

```
1	0	.agentqa/memory/index.md
```

## New files

```
.agentqa/memory/failures/device-register-404-blocks-login.md
```

## Full diff

```diff
diff --git a/.agentqa/memory/index.md b/.agentqa/memory/index.md
index 4fc1f6e..9d4f7e8 100644
--- a/.agentqa/memory/index.md
+++ b/.agentqa/memory/index.md
@@ -11,6 +11,7 @@
 
 ## Failures
 - **wda-timeout-under-load** — WebDriverAgent session timeout when the host is CPU-saturated
+- **device-register-404-blocks-login** — POST /device/register 404s, a "THÔNG BÁO ... (58)" modal covers intro, login form unreachable
 
 ## Env
 - env.md — build policy, credential env-var names, simulator gotchas
```