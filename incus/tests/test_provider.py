"""Offline official-client boundary tests; no Incus daemon or network."""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from eve_sdk.schema import SchemaValidationError, validate_output

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("incus_provider", ROOT / "provider.py")
assert spec and spec.loader
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
PUBLIC = (
    "ssh-ed25519 "
    + base64.b64encode(
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes(range(32))
    ).decode()
)


def resolved() -> dict:
    return {
        "access": {
            k: "ubuntu" for k in ("bootstrap_user", "human_user", "provision_user")
        },
        "bundle_packages": [],
        "composition": {
            "name": "test-one",
            "machine": "incus-ubuntu-ci",
            "os": "ubuntu-26.04-amd64",
            "init": "incus-cloud-init",
            "location": "incus-pool",
        },
        "engine": "incus",
        "init": {"id": "incus-cloud-init"},
        "instance": {
            "name": "test-one",
            "machine": "incus-ubuntu-ci",
            "os": "ubuntu-26.04-amd64",
            "init": "incus-cloud-init",
            "location": "incus-pool",
        },
        "location": {"name": "incus-pool"},
        "machine": {
            "name": "incus-ubuntu-ci",
            "provider": "incus",
            "kind": "container",
            "defaults": p.DEFAULTS["machine"],
        },
        "os": {
            "id": "ubuntu-26.04-amd64",
            "family": "ubuntu",
            "arch": "amd64",
            "version": "26.04",
        },
        "package_plugins": [],
        "package_sources": {},
        "provider_config": {},
        "provider_plugin": "incus",
        "stack_tags": "incus",
    }


class FakeIncus:
    def __init__(self, provider):
        self.provider = provider
        self.rows = []
        self.calls = []
        self.fail = None
        self.timeout = False
        self.invalid = None

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        assert cmd[:3] == ["incus", "--project", "eve-ci"]
        assert kwargs["env"]["INCUS_CONF"] == self.provider.config["config_dir"]
        assert kwargs["timeout"] == self.provider.config["command_timeout"]
        assert kwargs["capture_output"] and not kwargs.get("shell")
        assert (
            "AWS_ACCESS_KEY_ID" not in kwargs["env"]
            and "SSH_AUTH_SOCK" not in kwargs["env"]
        )
        op = cmd[3]
        if self.timeout:
            raise subprocess.TimeoutExpired(
                cmd, 1, output=PUBLIC, stderr="credential-leak"
            )
        if self.fail == op:
            return subprocess.CompletedProcess(cmd, 17, PUBLIC, "credential-leak")
        out = ""
        if op == "list":
            assert cmd[4:] == [self.provider.remote + ":", "--format=json"]
            out = self.invalid if self.invalid is not None else json.dumps(self.rows)
        elif op == "init":
            assert cmd[4:] == [
                self.provider.config["image"],
                self.provider.target,
                "--no-profiles",
            ]
            document = yaml.safe_load(kwargs["input"])
            self.rows = [
                document
                | {
                    "name": self.provider.name,
                    "project": "eve-ci",
                    "type": "container",
                    "status": "Stopped",
                    "status_code": 102,
                }
            ]
        elif op in {"start", "stop"}:
            assert cmd[4:] == [self.provider.target]
            self.rows[0].update(
                status="Running" if op == "start" else "Stopped",
                status_code=103 if op == "start" else 102,
            )
            self.rows[0]["state"] = {
                "network": {
                    "eth0": {
                        "addresses": [
                            {
                                "family": "inet",
                                "scope": "global",
                                "address": "10.201.153.42",
                            }
                        ]
                    }
                }
            }
        elif op == "delete":
            assert cmd[4:] == [self.provider.target]
            self.rows = []
        elif op == "exec":
            assert cmd[4:] == [
                self.provider.target,
                "--",
                "cat",
                "/etc/ssh/ssh_host_ed25519_key.pub",
            ]
            out = PUBLIC + " guest-comment\n"
        else:
            raise AssertionError(cmd)
        return subprocess.CompletedProcess(cmd, 0, out, "")


@pytest.fixture
def boundary(config, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "negative-isolation-only")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/ambient/agent")
    monkeypatch.setenv("INCUS_CONF", "/ambient/incus")
    provider = p.Provider(config, resolved())
    fake = FakeIncus(provider)
    monkeypatch.setattr(p.subprocess, "run", fake)
    return provider, fake


def test_init_configure_start_order_and_cloud_init(boundary):
    provider, fake = boundary
    assert provider.lifecycle("up")["status"] == "running"
    assert [c[0][3] for c in fake.calls] == ["list", "init", "list", "start", "list"]
    data = yaml.safe_load(fake.calls[1][1]["input"])
    cloud = yaml.safe_load(data["config"]["cloud-init.user-data"])
    assert cloud["packages"] == ["openssh-server"]
    assert cloud["users"] == [
        {
            "name": "ubuntu",
            "lock_passwd": True,
            "shell": "/bin/bash",
            "ssh_authorized_keys": [PUBLIC],
            "sudo": "ALL=(ALL) NOPASSWD:ALL",
        }
    ]
    assert cloud["runcmd"] == [["systemctl", "enable", "--now", "ssh"]]
    assert cloud["disable_root"] and not cloud["ssh_pwauth"]
    assert data["profiles"] == []
    assert data["config"]["limits.cpu"] == "2"
    assert data["config"]["limits.memory"] == "2048MiB"
    assert data["config"]["security.privileged"] == "false"
    assert data["devices"]["eth0"] == {
        "type": "nic",
        "name": "eth0",
        "network": "incusbr0",
    }
    assert data["devices"]["root"]["pool"] == "default"
    assert provider.lifecycle("up")["status"] == "running"
    assert sum(c[0][3] == "init" for c in fake.calls) == 1


def test_init_never_starts_and_can_resume(boundary):
    provider, fake = boundary
    assert provider.lifecycle("init")["status"] == "stopped"
    assert not any(c[0][3] == "start" for c in fake.calls)
    provider.lifecycle("up")
    assert sum(c[0][3] == "init" for c in fake.calls) == 1


def test_stopped_running_absent_idempotency(boundary):
    provider, fake = boundary
    assert provider.lifecycle("down")["status"] == "absent"
    with pytest.raises(p.IncusError):
        provider.lifecycle("start")
    provider.lifecycle("up")
    provider.lifecycle("start")
    assert sum(c[0][3] == "start" for c in fake.calls) == 1
    provider.lifecycle("stop")
    provider.lifecycle("stop")
    assert sum(c[0][3] == "stop" for c in fake.calls) == 1
    provider.lifecycle("down")
    provider.lifecycle("down")
    assert sum(c[0][3] == "delete" for c in fake.calls) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("project", "default"),
        ("type", "virtual-machine"),
        ("config", {"user.eve.owner": "other-run"}),
    ],
)
def test_conflicting_instances_never_mutated(boundary, field, value):
    provider, fake = boundary
    provider.lifecycle("init")
    fake.rows[0][field] = value
    for command in ["up", "start", "stop", "down", "status"]:
        with pytest.raises(p.IncusError):
            provider.lifecycle(command)
    assert not any(c[0][3] in {"start", "stop", "delete"} for c in fake.calls)


@pytest.mark.parametrize("drift", ["config", "devices", "profiles"])
def test_bootstrap_drift_is_not_retrofitted(boundary, drift):
    provider, fake = boundary
    provider.lifecycle("init")
    fake.rows[0][drift] = {} if drift != "profiles" else ["default"]
    with pytest.raises(p.IncusError):
        provider.lifecycle("up")
    assert not any(c[0][3] == "start" for c in fake.calls)


@pytest.mark.parametrize(
    "code,text,expected",
    [
        (102, "Stopped", "stopped"),
        (103, "Running", "running"),
        (106, "Starting", "creating"),
        (112, "Error", "failed"),
        (110, "Frozen", "unknown"),
        (999, "Mystery", "unknown"),
        (103, "Stopped", "unknown"),
    ],
)
def test_observed_state_mapping(boundary, code, text, expected):
    provider, fake = boundary
    provider.lifecycle("init")
    fake.rows[0].update(status_code=code, status=text)
    assert provider.lifecycle("status")["status"] == expected
    if expected in {"creating", "unknown", "failed"}:
        with pytest.raises(p.IncusError):
            provider.lifecycle("start")
    validate_output(provider.lifecycle("status"), "provider_command_output")


@pytest.mark.parametrize(
    "raw", ["broken-json", "null", "{}", '[{"name":null}]', '[{"name":"x"},3]']
)
def test_malformed_list_is_not_absent(boundary, raw):
    provider, fake = boundary
    fake.invalid = raw
    with pytest.raises(p.IncusError, match="Malformed"):
        provider.lifecycle("down")
    assert not any(c[0][3] == "delete" for c in fake.calls)


@pytest.mark.parametrize("field", ["status", "status_code", "project", "type"])
def test_incomplete_instance_is_not_success(boundary, field):
    provider, fake = boundary
    provider.lifecycle("init")
    del fake.rows[0][field]
    with pytest.raises(p.IncusError):
        provider.lifecycle("status")


def test_duplicate_instance_is_ambiguous(boundary):
    provider, fake = boundary
    provider.lifecycle("init")
    fake.rows *= 2
    with pytest.raises(p.IncusError):
        provider.lifecycle("down")


def test_address_and_authenticated_binding(boundary):
    provider, fake = boundary
    provider.lifecycle("up")
    fake.rows[0]["state"]["network"]["unrelated0"] = {
        "addresses": [{"family": "inet", "scope": "global", "address": "192.168.1.200"}]
    }
    binding, key = provider.access()
    assert binding["address"] == "10.201.153.42"
    assert binding["username"] == "ubuntu" and binding["port"] == 22
    assert binding["protocol"] == "ssh" and binding["version"] == 2
    assert binding["credential_reference"] == {
        "path": provider.config["ssh_private_key_file"],
        "type": "ssh-private-key-file",
    }
    assert binding["host_identity"]["mechanism"] == "provider-authenticated-exec"
    assert binding["provider_identity"] == provider.identity
    assert key == PUBLIC
    assert PUBLIC not in json.dumps(binding) and "guest-comment" not in json.dumps(
        binding
    )
    validate_output(
        {"status": "running", "guest_access": binding}, "provider_command_output"
    )


@pytest.mark.parametrize(
    "addresses",
    [
        [],
        [{"family": "inet", "scope": "global", "address": "192.168.1.42"}],
        [{"family": "inet", "scope": "global", "address": "10.201.153.42"}] * 2,
        [{"family": "inet", "scope": "global", "address": "invalid"}],
        [{"address": "10.201.153.42"}],
        [{"family": "inet6", "scope": "global", "address": "fe80::1"}],
        [{"family": "inet", "scope": "global", "address": "10.201.153.255"}],
    ],
)
def test_no_guessing_addresses(boundary, addresses):
    provider, fake = boundary
    provider.lifecycle("up")
    fake.rows[0]["state"]["network"]["eth0"]["addresses"] = addresses
    with pytest.raises(p.IncusError):
        provider.access()


def test_missing_nic_or_state_rejected(boundary):
    provider, fake = boundary
    provider.lifecycle("up")
    for state in [{}, {"network": {"unrelated": {}}}]:
        fake.rows[0]["state"] = state
        with pytest.raises(p.IncusError):
            provider.access()


@pytest.mark.parametrize("command", ["init", "start", "stop", "delete", "list", "exec"])
def test_command_failure_propagates_and_redacts(boundary, command):
    provider, fake = boundary
    fake.fail = command
    with pytest.raises(p.IncusError) as error:
        provider.call(command, provider.target, input_text=PUBLIC)
    assert "exit 17" in str(error.value)
    assert PUBLIC not in str(error.value) and "credential-leak" not in str(error.value)


def test_timeout_is_not_success(boundary):
    provider, fake = boundary
    fake.timeout = True
    with pytest.raises(p.IncusError, match="timed out"):
        provider.lifecycle("status")


def test_partial_create_crash_can_be_reconciled(boundary):
    provider, fake = boundary
    fake.fail = "start"
    with pytest.raises(p.IncusError):
        provider.lifecycle("up")
    assert provider.state(fake.rows[0]) == "stopped"
    fake.fail = None
    assert provider.lifecycle("up")["status"] == "running"
    assert sum(c[0][3] == "init" for c in fake.calls) == 1


@pytest.mark.parametrize(
    "name",
    ["x", "../escape", "remote:name", "Uppercase", "-option", "name\nother", "a" * 64],
)
def test_instance_names_rejected_before_operations(config, name):
    data = resolved()
    data["instance"]["name"] = name
    with pytest.raises(p.IncusError):
        p.Provider(config, data)


def test_run_identity_avoids_collisions(config):
    one = p.Provider(config, resolved())
    two = p.Provider(
        config | {"run_id": "11111111-1e2f-4ec3-b243-ef668bd20b2d"}, resolved()
    )
    assert one.name != two.name and one.owner != two.owner


@pytest.mark.parametrize(
    "field,value",
    [
        ("project", "default"),
        ("endpoint", "http://192.168.1.108:8443"),
        ("remote", "local:"),
        ("run_id", "../escape"),
        ("image", "--vm"),
        ("subnet", "fe80::/64"),
        ("command_timeout", 0),
        ("unexpected", {}),
    ],
)
def test_configuration_is_typed_and_confined(config, monkeypatch, field, value):
    for name in p.CONFIG_SCHEMA["properties"]:
        monkeypatch.delenv("EVE_INCUS_" + name.upper(), raising=False)
    data = resolved()
    data["provider_config"] = config | {field: value}
    with pytest.raises((p.IncusError, ValueError)):
        p.configuration(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("addr", "https://other:8443"),
        ("auth_type", "oidc"),
        ("protocol", "simplestreams"),
        ("project", "default"),
        ("public", True),
    ],
)
def test_tls_remote_selectors_checked(config, field, value):
    path = Path(config["config_dir"]) / "config.yml"
    client = yaml.safe_load(path.read_text())
    client["remotes"]["eve-incus-pool"][field] = value
    path.write_text(yaml.safe_dump(client))
    with pytest.raises(p.IncusError):
        p.Provider(config, resolved())


def test_pin_and_identity_permissions_required(config):
    directory = Path(config["config_dir"])
    directory.chmod(0o755)
    with pytest.raises(p.IncusError):
        p.Provider(config, resolved())
    directory.chmod(0o700)
    (directory / "client.key").chmod(0o644)
    with pytest.raises(p.IncusError):
        p.Provider(config, resolved())
    (directory / "client.key").chmod(0o600)
    (directory / "servercerts/eve-incus-pool.crt").unlink()
    with pytest.raises(p.IncusError):
        p.Provider(config, resolved())


@pytest.mark.parametrize(
    "key", ["", "ssh-rsa invalid", "ssh-ed25519 invalid", "-----BEGIN PRIVATE KEY-----"]
)
def test_invalid_public_key_cannot_start(boundary, key):
    provider, fake = boundary
    Path(provider.config["public_key_file"]).write_text(key)
    with pytest.raises(p.IncusError):
        provider.lifecycle("up")
    assert not any(c[0][3] in {"init", "start"} for c in fake.calls)


def test_ssh_uses_only_selected_credentials_and_strict_host_identity(boundary):
    provider, fake = boundary
    provider.lifecycle("up")
    calls = []

    def run(cmd, **kwargs):
        if cmd[0] == "incus":
            return fake(cmd, **kwargs)
        calls.append(cmd)
        path = Path(
            next(x.split("=", 1)[1] for x in cmd if x.startswith("UserKnownHostsFile="))
        )
        assert path.stat().st_mode & 0o077 == 0
        assert path.read_text() == provider.name + " " + PUBLIC + "\n"
        return subprocess.CompletedProcess(cmd, 0)

    with patch.object(p.subprocess, "run", run):
        assert provider.ssh(["--", "true"]) == 0
        assert provider.ssh(["--scp", "/tmp/payload", "/tmp/upload"]) == 0
    for cmd in calls:
        assert cmd[cmd.index("-i") + 1] == provider.config["ssh_private_key_file"]
        assert "StrictHostKeyChecking=yes" in cmd and "IdentityAgent=none" in cmd
        assert "HostKeyAlias=" + provider.name in cmd
        assert "ubuntu@10.201.153.42" in " ".join(cmd)
        assert not Path(
            next(x.split("=", 1)[1] for x in cmd if x.startswith("UserKnownHostsFile="))
        ).exists()


def test_parent_environment_unmodified(boundary):
    provider, _fake = boundary
    before = dict(os.environ)
    provider.lifecycle("up")
    provider.access()
    assert dict(os.environ) == before


def test_command_process_redacts_untrusted_failures(config):
    environment = os.environ | {
        "EVE_RESOLVED_JSON": "credential-leak",
        "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "eve"),
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "commands/incus-provider"), "up"],
        env=environment,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "credential-leak" not in result.stderr and not result.stdout


@pytest.mark.parametrize(
    "field,value",
    [
        ("port", 0),
        ("version", 1),
        ("protocol", "telnet"),
        ("username", "-root"),
        ("credential_reference", {"type": "raw-key", "value": "secret"}),
        ("host_identity", {"mechanism": "skip-verification"}),
        ("provider_identity", {"project": "eve-ci"}),
        ("opaque", {}),
    ],
)
def test_binding_rejects_untyped_or_unsafe_fields(boundary, field, value):
    provider, _fake = boundary
    provider.lifecycle("up")
    binding, _key = provider.access()
    broken = copy.deepcopy(binding)
    broken[field] = value
    with pytest.raises(SchemaValidationError):
        validate_output(broken, "guest_access")


@pytest.mark.parametrize(
    "override",
    [
        {},
        {"unexpected": "must-not-log"},
        {"project": "default"},
        {"command_timeout": "opaque-string"},
    ],
)
def test_metadata_validation_is_offline_and_validates_overrides(
    monkeypatch, capsys, override
):
    data = resolved()
    data["provider_config"] = override
    monkeypatch.setenv("EVE_RESOLVED_JSON", json.dumps(data))

    def fail(*args):
        raise AssertionError(
            "Metadata validation must not instantiate an authenticated client"
        )

    monkeypatch.setattr(p, "Provider", fail)
    assert p.main(["validate"]) == (1 if override else 0)
    captured = capsys.readouterr()
    assert "must-not-log" not in captured.err


@pytest.mark.parametrize(
    "key", ["", "ssh-rsa invalid", "ssh-ed25519 invalid", PUBLIC + "\n" + PUBLIC]
)
def test_missing_malformed_or_ambiguous_host_identity_rejected(boundary, key):
    provider, _fake = boundary
    provider.lifecycle("up")
    call = provider.call
    with patch.object(
        provider,
        "call",
        lambda *args, **kwargs: key if args[0] == "exec" else call(*args, **kwargs),
    ):
        with pytest.raises(p.IncusError):
            provider.access()
