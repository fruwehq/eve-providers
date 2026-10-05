"""Project-confined Incus lifecycle and authenticated SSH access.

No Determa APIs or guest package orchestration belong at this boundary.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from eve_sdk.dispatch import process_environment
from eve_sdk.schema import validate_input, validate_output

ROOT = Path(__file__).resolve().parent
DEFAULTS = yaml.safe_load((ROOT / "defaults.yaml").read_text())
CONFIG_SCHEMA = json.loads((ROOT / "config.schema.json").read_text())


class IncusError(RuntimeError):
    """Safe diagnostic: never contains a subprocess transcript or key payload."""


def configuration(resolved: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(DEFAULTS["config"])
    for name in CONFIG_SCHEMA["properties"]:
        value = os.environ.get("EVE_INCUS_" + name.upper())
        if value:
            result[name] = int(value) if name == "command_timeout" else value
    if resolved is not None:
        result.update(resolved["provider_config"])
    errors = list(Draft202012Validator(CONFIG_SCHEMA).iter_errors(result))
    if errors:
        raise IncusError(
            "Invalid or incomplete Incus configuration (see config.schema.json)"
        )
    subnet = ipaddress.ip_network(result["subnet"], strict=True)
    if subnet.version != 4:
        raise IncusError("Incus guest subnet must be IPv4")
    if result["image"] != DEFAULTS["config"]["image"] and not re.fullmatch(
        re.escape(result["remote"]) + r":[0-9a-f]{64}", result["image"]
    ):
        raise IncusError(
            "Image must be the configured cloud alias or a preloaded remote fingerprint"
        )
    return result


def public_key(path: str) -> str:
    """Read only the explicitly selected public key, discarding comments."""
    text = Path(path).read_text().strip()
    if len(text.splitlines()) != 1:
        raise IncusError("A single explicit controller public key is required")
    parts = text.split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise IncusError("An explicit Ed25519 controller public key is required")
    try:
        blob = base64.b64decode(parts[1], validate=True)
        if len(blob) != 51 or blob[:19] != struct.pack(
            ">I", 11
        ) + b"ssh-ed25519" + struct.pack(">I", 32):
            raise ValueError
    except ValueError as error:
        raise IncusError("Invalid Ed25519 public key") from error
    return " ".join(parts[:2])


def validate_composition(resolved: dict[str, Any]) -> str:
    validate_input(resolved)
    # Instance overrides are a typed subset of the same configuration contract;
    # resolution never requires globally configured credentials or API access.
    partial_schema = CONFIG_SCHEMA | {"required": []}
    if list(
        Draft202012Validator(partial_schema).iter_errors(resolved["provider_config"])
    ):
        raise IncusError("Invalid Incus instance configuration overrides")
    if (
        resolved["machine"]["provider"] != "incus"
        or resolved["machine"]["kind"] != "container"
        or resolved["engine"] != "incus"
    ):
        raise IncusError("Incus requires an honestly resolved system container")
    if (
        resolved["os"]["id"] != "ubuntu-26.04-amd64"
        or resolved["init"]["id"] != "incus-cloud-init"
    ):
        raise IncusError("Incus requires the supported Ubuntu cloud-init composition")
    if set(resolved["access"].values()) != {DEFAULTS["bootstrap"]["username"]}:
        raise IncusError("Incus SSH access must use the declared bootstrap user")
    name = resolved["instance"]["name"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,29}[a-z0-9]", name):
        raise IncusError("Invalid instance name (2-31 lowercase DNS characters)")
    return name


class Provider:
    def __init__(
        self, config: dict[str, Any], resolved: dict[str, Any] | None = None
    ) -> None:
        self.config = config
        self.resolved = resolved
        self.remote = config["remote"]
        self.project = config["project"]
        self.environment = process_environment() | {"INCUS_CONF": config["config_dir"]}
        self.environment.pop("SSH_AUTH_SOCK", None)
        self._check_client()
        if resolved is None:
            return
        name = validate_composition(resolved)
        self.name = (
            config["instance_prefix"]
            + "-"
            + name
            + "-"
            + config["run_id"].replace("-", "")
        )
        if len(self.name) > 63:
            raise IncusError("Qualified instance name exceeds Incus DNS limit")
        self.target = self.remote + ":" + self.name
        self.owner = hashlib.sha256(
            (config["run_id"] + ":" + name).encode()
        ).hexdigest()
        self.identity = {
            "endpoint": config["endpoint"],
            "instance_name": self.name,
            "owner_id": self.owner,
            "project": self.project,
            "provider": "incus",
            "remote": self.remote,
        }

    def _check_client(self) -> None:
        directory = Path(self.config["config_dir"])
        if directory.stat().st_mode & 0o077:
            raise IncusError("Incus client directory must be private (0700)")
        # Inspect non-secret remote selectors only. The official client reads its
        # credential files; Eve never reads, copies, or generates the client key.
        client = yaml.safe_load((directory / "config.yml").read_text())
        remote = (
            client.get("remotes", {}).get(self.remote, {})
            if isinstance(client, dict)
            else {}
        )
        if (
            remote.get("addr") != self.config["endpoint"]
            or remote.get("auth_type") != "tls"
            or remote.get("protocol", "incus") != "incus"
            or remote.get("public", False)
        ):
            raise IncusError(
                "Explicit private TLS remote does not match the configured endpoint"
            )
        if remote.get("project") != self.project:
            raise IncusError("Incus remote must explicitly select the confined project")
        for path in [
            directory / "client.crt",
            directory / "client.key",
            directory / "servercerts" / (self.remote + ".crt"),
        ]:
            if not path.is_file():
                raise IncusError(
                    "Restricted TLS identity and pinned server certificate must be configured manually"
                )
        if (directory / "client.key").stat().st_mode & 0o077:
            raise IncusError("Incus client key must have private permissions (0600)")

    def call(self, *args: str, input_text: str | None = None) -> str:
        try:
            result = subprocess.run(
                ["incus", "--project", self.project, *args],
                env=self.environment,
                input=input_text if input_text is not None else "",
                text=True,
                capture_output=True,
                timeout=self.config["command_timeout"],
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise IncusError(
                "Incus operation timed out; observe before retrying"
            ) from error
        except OSError as error:
            raise IncusError("Incus client could not be executed") from error
        if result.returncode:
            raise IncusError(
                f"Incus {args[0]} failed (exit {result.returncode}); observe before retrying"
            )
        return result.stdout

    def observe(self) -> dict[str, Any] | None:
        output = self.call("list", self.remote + ":", "--format=json")
        try:
            rows = json.loads(output)
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not isinstance(row.get("name"), str)
                for row in rows
            ):
                raise ValueError
            matches = [row for row in rows if row["name"] == self.name]
            if len(matches) > 1:
                raise ValueError
            if not matches:
                return None
            row = matches[0]
            if row.get("project") != self.project or row.get("type") != "container":
                raise IncusError("Conflicting instance project or resource type")
            if row.get("config", {}).get("user.eve.owner") != self.owner:
                raise IncusError("Conflicting instance ownership; refusing to operate")
            if not isinstance(row.get("status_code"), int) or not isinstance(
                row.get("status"), str
            ):
                raise ValueError
            return row
        except (ValueError, TypeError, AttributeError) as error:
            raise IncusError("Malformed or incomplete Incus instance output") from error

    @staticmethod
    def state(row: dict[str, Any] | None) -> str:
        if row is None:
            return "absent"
        # Code AND text must agree. Frozen/stopping/unknown codes are ambiguous.
        states = {
            (102, "Stopped"): "stopped",
            (103, "Running"): "running",
            (106, "Starting"): "creating",
            (112, "Error"): "failed",
        }
        return states.get((row["status_code"], row["status"]), "unknown")

    def blueprint(self) -> dict[str, Any]:
        assert self.resolved is not None
        machine = DEFAULTS["machine"] | self.resolved["machine"].get("defaults", {})
        if (
            set(machine) != set(DEFAULTS["machine"])
            or type(machine["cpu_cores"]) is not int
            or type(machine["memory_mb"]) is not int
        ):
            raise IncusError("Invalid container resource defaults")
        if (
            not 1 <= machine["cpu_cores"] <= 6
            or not 256 <= machine["memory_mb"] <= 6144
        ):
            raise IncusError("Container limits exceed the pool contract")
        for key in ("network", "pool"):
            if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", machine[key]):
                raise IncusError("Invalid container network/storage selector")
        bootstrap = DEFAULTS["bootstrap"]
        cloud = {
            "disable_root": True,
            "package_update": bootstrap["package_update"],
            "packages": bootstrap["packages"],
            "ssh_pwauth": False,
            "users": [
                {
                    "name": bootstrap["username"],
                    "lock_passwd": True,
                    "shell": "/bin/bash",
                    "ssh_authorized_keys": [public_key(self.config["public_key_file"])],
                    "sudo": "ALL=(ALL) NOPASSWD:ALL",
                }
            ],
            "runcmd": [["systemctl", "enable", "--now", bootstrap["service"]]],
        }
        document = {
            "profiles": [],
            "config": {
                "cloud-init.user-data": "#cloud-config\n" + yaml.safe_dump(cloud),
                "limits.cpu": str(machine["cpu_cores"]),
                "limits.memory": str(machine["memory_mb"]) + "MiB",
                "security.privileged": "false",
                "user.eve.owner": self.owner,
            },
            "devices": {
                "root": {"type": "disk", "path": "/", "pool": machine["pool"]},
                self.config["nic"]: {
                    "type": "nic",
                    "name": self.config["nic"],
                    "network": machine["network"],
                },
            },
        }
        digest = hashlib.sha256(
            (self.config["image"] + json.dumps(document, sort_keys=True)).encode()
        ).hexdigest()
        document["config"]["user.eve.blueprint"] = digest
        return document

    def create(self) -> dict[str, Any]:
        document = self.blueprint()
        row = self.observe()
        if row is None:
            # The init API request contains every first-boot setting atomically.
            # No launch, no post-start cloud-init retrofit, no automatic deletion.
            self.call(
                "init",
                self.config["image"],
                self.target,
                "--no-profiles",
                input_text=yaml.safe_dump(document),
            )
            row = self.observe()
        if (
            row is None
            or any(
                row.get("config", {}).get(k) != v for k, v in document["config"].items()
            )
            or row.get("devices") != document["devices"]
            or row.get("profiles") != []
        ):
            raise IncusError(
                "Existing instance conflicts with the complete bootstrap blueprint"
            )
        return row

    def lifecycle(self, command: str) -> dict[str, Any]:
        if command in {"init", "up"}:
            row = self.create()
        else:
            row = self.observe()
        state = self.state(row)
        if command in {"up", "start"}:
            if state == "stopped":
                self.call("start", self.target)
            elif state != "running":
                raise IncusError(
                    "Cannot start an absent, failed, or ambiguous instance"
                )
            expected = "running"
        elif command == "stop":
            if state == "running":
                self.call("stop", self.target)
            elif state != "stopped":
                raise IncusError("Cannot stop an absent, failed, or ambiguous instance")
            expected = "stopped"
        elif command == "down":
            if state == "running":
                self.call("stop", self.target)
                if self.state(self.observe()) != "stopped":
                    raise IncusError("Stop did not establish a stopped instance")
            elif state not in {"stopped", "absent", "failed"}:
                raise IncusError("Cannot delete an ambiguous instance")
            if row is not None:
                self.call("delete", self.target)
            expected = "absent"
        else:
            expected = state
        observed = self.state(self.observe())
        if command != "status" and observed != expected:
            raise IncusError(
                "Incus operation did not establish the requested observed state"
            )
        return {"status": observed, "provider_identity": self.identity}

    def address(self, row: dict[str, Any] | None) -> str:
        if self.state(row) != "running":
            raise IncusError("Guest address requires a running container")
        try:
            addresses = row["state"]["network"][self.config["nic"]]["addresses"]  # type: ignore[index]
            if not isinstance(addresses, list):
                raise ValueError
            subnet = ipaddress.ip_network(self.config["subnet"])
            candidates = []
            for item in addresses:
                address = ipaddress.ip_address(item["address"])
                if (
                    item["family"] == "inet"
                    and item["scope"] == "global"
                    and address.version == 4
                    and address in subnet
                    and address
                    not in {subnet.network_address, subnet.broadcast_address}
                ):
                    candidates.append(str(address))
            if len(candidates) != 1:
                raise IncusError("Configured NIC has no unique routed IPv4 address")
            return candidates[0]
        except (KeyError, ValueError, TypeError) as error:
            raise IncusError("Malformed or incomplete Incus network state") from error

    def access(self) -> tuple[dict[str, Any], str]:
        address = self.address(self.observe())
        key = self.call(
            "exec", self.target, "--", "cat", "/etc/ssh/ssh_host_ed25519_key.pub"
        ).strip()
        if len(key.splitlines()) != 1:
            raise IncusError("Guest SSH host identity is missing or ambiguous")
        # Parse a public host key without logging its material.
        parts = key.split()
        if len(parts) != 2 or parts[0] != "ssh-ed25519":
            # ssh-keygen typically appends a host comment; allow and discard it.
            if len(parts) < 2 or parts[0] != "ssh-ed25519":
                raise IncusError("Guest SSH host identity is unavailable")
        try:
            blob = base64.b64decode(parts[1], validate=True)
            if len(blob) != 51 or blob[:19] != struct.pack(
                ">I", 11
            ) + b"ssh-ed25519" + struct.pack(">I", 32):
                raise ValueError
        except ValueError as error:
            raise IncusError("Invalid guest SSH host identity") from error
        fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(blob).digest()
        ).decode().rstrip("=")
        bootstrap = DEFAULTS["bootstrap"]
        binding = {
            "address": address,
            "credential_reference": {
                "path": self.config["ssh_private_key_file"],
                "type": "ssh-private-key-file",
            },
            "host_identity": {
                "fingerprint": fingerprint,
                "mechanism": "provider-authenticated-exec",
            },
            "port": bootstrap["port"],
            "protocol": bootstrap["protocol"],
            "provider_identity": self.identity,
            "username": bootstrap["username"],
            "version": bootstrap["version"],
        }
        validate_output(binding, "guest_access")
        return binding, " ".join(parts[:2])

    def ssh(self, args: list[str]) -> int:
        binding, host_key = self.access()
        # Private keys are references only, passed to OpenSSH; never inferred,
        # read by Eve, copied, or generated. No agent/default identities allowed.
        with tempfile.TemporaryDirectory(prefix="eve-incus-ssh-") as directory:
            known_hosts = Path(directory) / "known_hosts"
            known_hosts.touch(mode=0o600)
            known_hosts.write_text(f"{self.name} {host_key}\n")
            options = [
                "-F",
                "/dev/null",
                "-i",
                binding["credential_reference"]["path"],
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "IdentityAgent=none",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "GlobalKnownHostsFile=/dev/null",
                "-o",
                "UserKnownHostsFile=" + str(known_hosts),
                "-o",
                "HostKeyAlias=" + self.name,
                "-o",
                "HostKeyAlgorithms=ssh-ed25519",
                "-o",
                "BatchMode=yes",
                "-o",
                "PasswordAuthentication=no",
                "-o",
                "KbdInteractiveAuthentication=no",
            ]
            destination = binding["username"] + "@" + binding["address"]
            if args and args[0] == "--scp":
                if (
                    len(args) != 3
                    or args[1].startswith("-")
                    or ":" in args[1]
                    or not re.fullmatch(r"/[a-zA-Z0-9_./-]+", args[2])
                ):
                    raise IncusError(
                        "scp requires an explicit local path and remote path"
                    )
                command = [
                    "scp",
                    *options,
                    "-P",
                    str(binding["port"]),
                    "-r",
                    "--",
                    str(Path(args[1]).resolve()),
                    destination + ":" + args[2],
                ]
            else:
                if args and args[0] == "--":
                    args = args[1:]
                command = [
                    "ssh",
                    *options,
                    "-p",
                    str(binding["port"]),
                    destination,
                    *args,
                ]
            try:
                return subprocess.run(
                    command,
                    env=self.environment,
                    timeout=self.config["command_timeout"],
                    check=False,
                ).returncode
            except subprocess.TimeoutExpired as error:
                raise IncusError("Guest SSH operation timed out") from error


def main(args: list[str]) -> int:
    import sys

    try:
        if not args:
            raise IncusError("An explicit Incus command is required")
        command, *extra = args
        if command == "connectivity":
            provider = Provider(configuration())
            rows = json.loads(
                provider.call("list", provider.remote + ":", "--format=json")
            )
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not isinstance(row.get("name"), str)
                for row in rows
            ):
                raise IncusError("Malformed Incus connectivity output")
            print(
                json.dumps(
                    {
                        "configured": "yes",
                        "reachable": "yes",
                        "notes": "restricted project API reachable",
                    }
                )
            )
            return 0
        raw = os.environ.get("EVE_RESOLVED_JSON") or sys.stdin.read()
        resolved = json.loads(raw)
        validate_input(resolved)
        if command == "resolve" or os.environ.get("EVE_PLUGIN_DRY_RUN") == "1":
            print(
                json.dumps(
                    {
                        "command": command,
                        "dry_run": True,
                        "engine": resolved["engine"],
                        "instance": resolved["instance"]["name"],
                        "kind": "provider",
                        "provider": "incus",
                    }
                )
            )
            return 0
        if command == "validate":
            validate_composition(resolved)
            if extra:
                raise IncusError("Unexpected validation arguments")
            # Metadata validation is called during resolve, before credentials
            # or provider environment exist. It must be entirely offline.
            print(
                json.dumps(
                    {
                        "command": "validate",
                        "engine": "incus",
                        "kind": "provider",
                        "provider": "incus",
                    }
                )
            )
            return 0
        provider = Provider(configuration(resolved), resolved)
        if command == "ssh":
            return provider.ssh(extra)
        if extra:
            raise IncusError("Unexpected Incus command arguments")
        if command == "ip":
            print(provider.address(provider.observe()))
            return 0
        if command == "access":
            binding, _key = provider.access()
            output = {
                "status": "running",
                "provider_identity": provider.identity,
                "guest_access": binding,
            }
        elif command == "plan":
            provider.blueprint()
            output = {
                "status": provider.state(provider.observe()),
                "provider_identity": provider.identity,
            }
        elif command in {"down", "init", "start", "status", "stop", "up"}:
            output = provider.lifecycle(command)
        else:
            raise IncusError("Unsupported Incus command")
        validate_output(output, "provider_command_output")
        print(json.dumps(output, sort_keys=True))
        return 0
    except IncusError as error:
        # IncusError is constructed only from fixed messages and numeric exits.
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        # Even validation/OS errors may quote a key or credential path. Do not
        # echo arbitrary exception data, Incus stdout/stderr, or stdin contents.
        print(
            "Incus operation failed; check explicit configuration, project access, and observed state",
            file=sys.stderr,
        )
        return 1
