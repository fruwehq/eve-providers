"""Exercise real Eve dispatch and Incus CLI subprocesses, entirely offline."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

from eve_sdk.plugin_manifest import PluginManifest
from eve_sdk.provider_command import dispatch_instance_command

from test_provider import PUBLIC


def test_eve_dispatch_lifecycle_through_fake_executable(tmp_path, monkeypatch, config):
    providers = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("EVE_HOME", str(tmp_path))
    monkeypatch.setenv("EVE_DISABLE_STATE", "1")  # transport test; no Determa adapters
    monkeypatch.setenv("EVE_PLUGIN_ROOTS", str(providers))
    monkeypatch.setenv("EVE_PLUGIN_ROOTS_EXCLUSIVE", "1")
    monkeypatch.setenv("EVE_CATALOG_LOCAL", str(tmp_path / "empty-catalog.yaml"))
    settings = tmp_path / "config.yaml"
    settings.write_text(yaml.safe_dump({"incus": config}))
    monkeypatch.setenv("EVE_CONFIG_PATH", str(settings))
    registry = tmp_path / "instances.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "instances": [
                    {
                        "name": "dispatch-test",
                        "machine": "incus-ubuntu-ci",
                        "os": "ubuntu-26.04-amd64",
                        "init": "incus-cloud-init",
                        "location": "incus-pool",
                    }
                ]
            }
        )
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state = tmp_path / "fake-incus-state.json"
    executable = bin_dir / "incus"
    executable.write_text(
        f"#!{sys.executable}\n"
        + f"STATE = {str(state)!r}\nPUBLIC = {PUBLIC!r}\n"
        + """
import json,sys
from pathlib import Path
import yaml
assert sys.argv[1:3] == ["--project", "eve-ci"]
op = sys.argv[3]
path = Path(STATE)
rows = json.loads(path.read_text()) if path.exists() else []
if op == "list":
    assert sys.argv[4:] == ["eve-incus-pool:", "--format=json"]
    print(json.dumps(rows))
else:
    target = sys.argv[5] if op == "init" else sys.argv[4]
    assert target.startswith("eve-incus-pool:eve-ci-dispatch-test-")
    if op == "init":
        assert not rows
        document = yaml.safe_load(sys.stdin.read())
        rows = [document | {"name": target.split(":",1)[1], "project": "eve-ci", "type": "container", "status": "Stopped", "status_code": 102}]
    elif op in {"start", "stop"}:
        rows[0].update(status="Running" if op == "start" else "Stopped",status_code=103 if op == "start" else 102)
        rows[0]["state"] = {"network": {"eth0": {"addresses": [{"address": "10.201.153.42", "family": "inet", "scope": "global"}]}}}
    elif op == "exec":
        assert sys.argv[5:] == ["--", "cat", "/etc/ssh/ssh_host_ed25519_key.pub"]
        print(PUBLIC)
    elif op == "delete":
        rows = []
    else:
        raise AssertionError(op)
    path.write_text(json.dumps(rows))
"""
    )
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    plugins = [
        PluginManifest.public(PluginManifest.load(providers / "incus/eve-plugin.yaml"))
    ]
    outputs = []
    for command, expected in [
        ("up", "running"),
        ("status", "running"),
        ("stop", "stopped"),
        ("stop", "stopped"),
        ("start", "running"),
        ("access", "running"),
        ("down", "absent"),
        ("down", "absent"),
    ]:
        outputs.clear()
        code = dispatch_instance_command(
            "dispatch-test",
            command,
            registry_path=str(registry),
            plugins=plugins,
            on_output=outputs.append,
        )
        assert code == 0
        output = json.loads("".join(outputs))
        assert output["status"] == expected
        assert output["provider_identity"]["project"] == "eve-ci"
        assert PUBLIC not in json.dumps(output)
        if command == "access":
            assert output["guest_access"]["username"] == "ubuntu"
            assert output["guest_access"]["address"] == "10.201.153.42"
    assert json.loads(state.read_text()) == []
