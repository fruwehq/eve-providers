"""Real manifest, catalog, configuration, and opt-in boundary integration."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from eve_sdk.catalog import aggregate
from eve_sdk.config import ConfigEnv
from eve_sdk.plugin_manifest import PluginManifest
from eve_sdk.provider_command import resolved_provider_environment
from eve_sdk.resolve import resolve_init, resolve_instance
from eve_sdk.schema import validate_input

PROVIDERS = Path(__file__).resolve().parents[2]


def test_real_catalog_resolves_container_and_infers_init(tmp_path, monkeypatch):
    manifest = PluginManifest.load(PROVIDERS / "incus/eve-plugin.yaml")
    PluginManifest.validate(manifest)
    catalog = aggregate(
        [yaml.safe_load((PROVIDERS / "_catalog-base/oses.yaml").read_text())],
        [manifest],
    )
    assert (
        resolve_init(catalog, {}, catalog["machines"][0], catalog["oses"][0])["id"]
        == "incus-cloud-init"
    )
    registry = tmp_path / "instances.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "instances": [
                    {
                        "name": "test-one",
                        "init": "incus-cloud-init",
                        "machine": "incus-ubuntu-ci",
                        "os": "ubuntu-26.04-amd64",
                        "location": "incus-pool",
                    }
                ]
            }
        )
    )
    result = resolve_instance(
        "test-one", registry, catalog=catalog, plugins=[PluginManifest.public(manifest)]
    )
    validate_input(result)
    assert result["machine"]["kind"] == "container"
    assert result["engine"] == "incus"
    assert result["init"]["id"] == "incus-cloud-init"
    assert set(result["access"].values()) == {"ubuntu"}


def test_manifest_config_mapping_does_not_read_secrets_or_ambient_identity(
    tmp_path, monkeypatch
):
    manifest = PluginManifest.load(PROVIDERS / "incus/eve-plugin.yaml")
    monkeypatch.setattr(
        PluginManifest,
        "load_all",
        lambda kind=None: [manifest] if kind in (None, "provider") else [],
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "incus": {
                    "config_dir": "/explicit/client",
                    "endpoint": "https://pool:8443",
                    "project": "eve-ci",
                    "public_key_file": "/explicit/key.pub",
                    "remote": "pool",
                    "run_id": "01234567-89ab-4cde-8fab-0123456789ab",
                    "ssh_private_key_file": "/explicit/key",
                }
            }
        )
    )
    monkeypatch.setenv("EVE_CONFIG_PATH", str(config))
    monkeypatch.setenv("INCUS_CONF", "/ambient/client")
    monkeypatch.setenv("EVE_INCUS_CONFIG_DIR", "/ambient/provider-client")

    def fail(*args):
        raise AssertionError("Incus must not read Eve secret files")

    monkeypatch.setattr("eve_sdk.provider_command.Secrets.read", fail)
    env = resolved_provider_environment("incus", manifest)
    assert env["EVE_INCUS_CONFIG_DIR"] == "/explicit/client"
    assert env["EVE_INCUS_SSH_PRIVATE_KEY_FILE"] == "/explicit/key"
    assert "INCUS_CONF" not in env
    assert ConfigEnv.environment()["EVE_INCUS_PUBLIC_KEY_FILE"] == "/explicit/key.pub"


def test_live_runner_default_skips_without_contacting_anything():
    result = subprocess.run(
        [sys.executable, str(PROVIDERS / "tests/test-incus-live")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and "[SKIP]" in result.stdout


@pytest.mark.parametrize(
    "data",
    [
        {"endpoint": "http://wrong", "project": "default"},
        {
            "endpoint": "https://192.168.1.108:8443",
            "remote": "eve-incus-pool",
            "project": "eve-ci",
            "image": "images:ubuntu/26.04/cloud",
        },
    ],
)
def test_live_runner_rejects_wrong_target_and_importing_image_before_contact(
    tmp_path, monkeypatch, data
):
    path = PROVIDERS / "tests/test-incus-live"
    loader = importlib.machinery.SourceFileLoader("incus_live_guard", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    config = tmp_path / "live.yaml"
    config.write_text(yaml.safe_dump(data))

    def fail(*args):
        raise AssertionError("Invalid live configuration must not contact a pool")

    monkeypatch.setattr(module.provider_module, "Provider", fail)
    with pytest.raises(SystemExit) as error:
        module.main(
            [
                "--live",
                "--config",
                str(config),
                "--prefix",
                "eve-it-a1",
                "--target",
                "https://192.168.1.108:8443",
            ]
        )
    assert error.value.code == 2


def test_command_dry_run_uses_real_resolved_contract(tmp_path):
    manifest = PluginManifest.load(PROVIDERS / "incus/eve-plugin.yaml")
    catalog = aggregate(
        [yaml.safe_load((PROVIDERS / "_catalog-base/oses.yaml").read_text())],
        [manifest],
    )
    registry = tmp_path / "instances.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "instances": [
                    {
                        "name": "test-one",
                        "init": "incus-cloud-init",
                        "machine": "incus-ubuntu-ci",
                        "os": "ubuntu-26.04-amd64",
                        "location": "incus-pool",
                    }
                ]
            }
        )
    )
    result = resolve_instance(
        "test-one", registry, catalog=catalog, plugins=[PluginManifest.public(manifest)]
    )
    from eve_sdk.dispatch import command_env, process_environment

    env = command_env(process_environment()) | {
        "EVE_PLUGIN_DRY_RUN": "1",
        "EVE_RESOLVED_JSON": json.dumps(result),
    }
    command = subprocess.run(
        [sys.executable, str(PROVIDERS / "incus/commands/incus-provider"), "up"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert command.returncode == 0
    assert json.loads(command.stdout)["engine"] == "incus"


@pytest.mark.parametrize("fail_after_create", [False, True])
def test_live_runner_cleans_owned_resource_on_success_and_creation_failure(
    tmp_path, monkeypatch, fail_after_create
):
    path = PROVIDERS / "tests/test-incus-live"
    loader = importlib.machinery.SourceFileLoader("incus_live_cleanup", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    image = "a" * 64
    config_path = tmp_path / "live.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "endpoint": "https://192.168.1.108:8443",
                "remote": "eve-incus-pool",
                "project": "eve-ci",
                "image": "eve-incus-pool:" + image,
            }
        )
    )
    created = []

    class FakePool:
        def __init__(self, cfg, resolved):
            self.remote = cfg["remote"]
            self.target = self.remote + ":owned-unique-test"
            self.present = False
            self.commands = []
            created.append(self)

        def call(self, *args):
            assert args == ("image", "list", self.remote + ":", "--format=json")
            return json.dumps([{"fingerprint": image}])

        def observe(self):
            return {"owned": True} if self.present else None

        def lifecycle(self, command):
            self.commands.append(command)
            if command == "up":
                self.present = True
                if fail_after_create:
                    raise module.provider_module.IncusError(
                        "simulated post-create failure"
                    )
            if command == "down":
                self.present = False
            return {
                "status": {"down": "absent", "stop": "stopped"}.get(command, "running")
            }

        def cleanup(self):
            self.lifecycle("down")

        def ssh(self, args):
            return 0

    monkeypatch.setattr(
        module.provider_module,
        "configuration",
        lambda resolved: resolved["provider_config"],
    )
    monkeypatch.setattr(module.provider_module, "Provider", FakePool)
    args = [
        "--live",
        "--config",
        str(config_path),
        "--prefix",
        "eve-it-a1",
        "--target",
        "https://192.168.1.108:8443",
    ]
    if fail_after_create:
        with pytest.raises(module.provider_module.IncusError):
            module.main(args)
    else:
        assert module.main(args) == 0
        assert "stop" in created[0].commands and "start" in created[0].commands
    assert not created[0].present
    assert created[0].commands[-1] == "down"
