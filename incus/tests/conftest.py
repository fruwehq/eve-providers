"""Explicit temporary TLS selectors for offline tests; no real credentials."""

from pathlib import Path

import pytest
import yaml

from test_provider import PUBLIC, p


@pytest.fixture
def config(tmp_path: Path) -> dict:
    directory = tmp_path / "client"
    directory.mkdir(mode=0o700)
    (directory / "servercerts").mkdir()
    (directory / "config.yml").write_text(
        yaml.safe_dump(
            {
                "remotes": {
                    "eve-incus-pool": {
                        "addr": "https://192.168.1.108:8443",
                        "auth_type": "tls",
                        "project": "eve-ci",
                        "protocol": "incus",
                    }
                }
            }
        )
    )
    for filename in ["client.crt", "client.key", "servercerts/eve-incus-pool.crt"]:
        (directory / filename).touch(mode=0o600)
    pub = tmp_path / "controller.pub"
    pub.write_text(PUBLIC + " comment-not-exported\n")
    return p.DEFAULTS["config"] | {
        "endpoint": "https://192.168.1.108:8443",
        "instance_prefix": "eve-ci",
        "image": "eve-incus-pool:" + "a" * 64,
        "project": "eve-ci",
        "remote": "eve-incus-pool",
        "subnet": "10.201.153.0/24",
        "config_dir": str(directory),
        "public_key_file": str(pub),
        "run_id": "0bca1721-1e2f-4ec3-b243-ef668bd20b2d",
        "ssh_private_key_file": str(tmp_path / "selected-private-key"),
    }
