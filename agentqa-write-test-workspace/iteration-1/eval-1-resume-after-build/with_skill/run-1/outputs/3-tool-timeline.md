# Tool timeline

Every shimmed command and every question, in order. `+Ns` is seconds from the run's first logged action.

| +s | kind | call |
|---:|---|---|
| 0 | tool | `xcrun simctl list devices booted`
| 0 | tool | `xcrun simctl listapps booted`
| 0 | tool | `agent-device --help`
| 38 | tool | `xcrun simctl list devices booted`
| 38 | tool | `xcrun simctl terminate booted com.vnpt.media.mobileb2c`
| 38 | tool | `xcrun simctl get_app_container booted com.vnpt.media.mobileb2c data`
| 38 | tool | `xcrun simctl privacy booted reset all com.vnpt.media.mobileb2c`
| 38 | tool | `agent-device open com.vnpt.media.mobileb2c`
| 44 | tool | `agent-device press e3 --settle`
| 51 | tool | `page-source `
| 55 | tool | `agent-device press e7 --settle`
| 55 | tool | `page-source `
| 75 | tool | `agent-device fill e10 mytv_qa`
| 75 | tool | `agent-device fill e11 wrong_password`
| 75 | tool | `agent-device press e14 --settle`
| 80 | tool | `page-source `
| 88 | tool | `agent-device press e12 --settle`
| 88 | tool | `agent-device press e14 --settle`
| 92 | tool | `agent-device fill e11 Qa!2026pass`
| 92 | tool | `agent-device press e14 --settle`
| 92 | tool | `page-source `
| 235 | tool | `xcrun simctl terminate booted com.vnpt.media.mobileb2c`
| 236 | tool | `agent-device open com.vnpt.media.mobileb2c`
| 340 | tool | `pytest tests -v`
| 361 | ask | Review checkpoint for the login flow. APP CODE: no changes in this session — the 11 accessibility identifiers were already in the build you installed, and al...
| 361 | ask | One divergence from memory found during verification: the memory note said the submit button is DISABLED until the terms box is ticked, but the live hierarch...
| 361 | tool | `ask-user Review checkpoint for the login flow. APP CODE: no changes in this session — the 11 accessibility identifiers were already in the build you installe...`
| 434 | tool | `codegraph init`
| 441 | tool | `pytest tests -v`
| 532 | tool | `pytest tests`
| 559 | tool | `pytest tests`
| 1997 | tool | `pytest tests`
| 2502 | tool | `pytest tests`
