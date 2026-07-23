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
