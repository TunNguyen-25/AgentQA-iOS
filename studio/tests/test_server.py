import json
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from threading import Thread

import pytest

from studio.server import make_server


@pytest.fixture
def live_server(tmp_path):
    cfgdir = tmp_path / ".agentqa"
    cfgdir.mkdir()
    (cfgdir / "config.yml").write_text(textwrap.dedent("""\
        platform: ios
        bundle_id: com.acme.app
        test_dir: AutomationTests
        build:
          policy: human
        reset_app_data: always
        appium:
          port: 4723
    """))
    (tmp_path / ".agentqa" / "memory" / "flows").mkdir(parents=True)
    (tmp_path / ".agentqa" / "memory" / "flows" / "login.md").write_text("# login\n")
    srv = make_server(tmp_path, memory_scripts=None, port=0)
    Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    yield "http://127.0.0.1:%d" % port
    srv.shutdown()


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, r.read().decode()


def test_config_endpoint(live_server):
    status, body = _get(live_server, "/api/config")
    assert status == 200
    data = json.loads(body)
    assert data["app_id"] == "com.acme.app"
    assert data["build_policy"] == "human"


def test_memory_endpoint_lists_flow(live_server):
    status, body = _get(live_server, "/api/memory")
    assert status == 200
    assert "login" in json.loads(body)["flows"]


def test_index_served(live_server):
    status, body = _get(live_server, "/")
    assert status == 200
    assert "AgentQA Studio" in body


def test_unknown_route_404(live_server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(live_server, "/api/nope")
    assert exc.value.code == 404


def test_run_rejects_unknown_target(live_server):
    import urllib.request, json as _json
    req = urllib.request.Request(
        live_server + "/api/run", method="POST",
        data=_json.dumps({"target": "../../etc/passwd", "env": {}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "expected HTTP 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_post_malformed_body_returns_400(live_server):
    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        live_server + "/api/run", method="POST",
        data=b"not json", headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "expected HTTP 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_post_missing_config_returns_500(tmp_path):
    import json as _json
    import urllib.request
    import urllib.error
    from threading import Thread
    from studio.server import make_server
    # tmp_path has NO .agentqa/config.yml
    srv = make_server(tmp_path, memory_scripts=None, port=0)
    Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    try:
        req = urllib.request.Request(
            base + "/api/run", method="POST",
            data=_json.dumps({"target": "all"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "expected HTTP 500"
        except urllib.error.HTTPError as e:
            assert e.code == 500
    finally:
        srv.shutdown()
