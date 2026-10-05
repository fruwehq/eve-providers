# Incus offline validation — 2026-10-05 (Asia/Tokyo)

Validation began from Eve `13341e8fcdb4acfa3530055f144e003b8f5fb3c2` and providers
`e8a05465e0d993bec31b17ea7f4a48a075c83cdb`, both on `v4.5`. The user subsequently
authorized preserving the Incus implementation in commits on these branches
and updating main-facing PRs #55 and #10, which remain drafts. Earlier CI results
cover the starting heads; new commit checks must be assessed independently.
No provider activation, TLS enrollment, or live resource creation occurred.

## Commands and results

* Providers: all offline `tests/test-*` entrypoints, excluding the separate
  opt-in live runner, passed. This includes 97 Incus tests, 6 AWS connectivity
  tests, 8 provider status/backend checks, 3 host-resolver checks, and environment
  contracts for all 8 providers. Use an environment with Eve installed for
  subprocess tests; `PYTHONPATH` alone does not survive deliberately isolated
  child environments in the AWS tests.
* `PYTHONPATH=/absolute/eve python tests/test-incus`: passed. Tests cover init
  request contents/order, unique identity/project scope, resource conflicts,
  crash retries, observed state/address parsing, malformed/incomplete API data,
  failures/timeouts, SSH trust/credential selection, environment/log isolation,
  real catalog resolution, real Eve dispatch with a fake executable, live-test
  target guards, and cleanup after both success and post-create failure.
* Eve `PATH=<project .venv>:<Poetry>:<tools> ./scripts/test`: attempted. All 16
  non-Python suite groups passed. The Python suite reached TUI smoke tests and
  stalled in asynchronous shutdown; it was terminated instead of claiming a
  successful full-suite result.
* Eve `PATH=<project .venv>:<Poetry>:<tools> python -m pytest -q tests
  --ignore=tests/python/test_tui_smoke.py`: **525 passed, 1 intentional skip**.
  The 20-test TUI smoke file is the stated exclusion. The separate TUI lint/type
  suite passed. No TUI smoke tests were disabled in repository configuration.
* Focused core `test_container_access_contract.py`: **16 passed**, validating
  container engine selection, all typed observation states, every required
  binding field, nested references, and cache rejection of opaque credentials.
* `scripts/test-cross-repo` with all four companion roots: **48 plugins,
  0 failures** — 8 providers, 25 packages, 11 bundles, 4 OS plugins. Catalog
  composition and Linux/Windows configuration-schema parity passed.
* `scripts/test-provision-runner --plugin-roots <providers>/oses`: real Linux
  and PowerShell runner checks passed.
* `scripts/test-ci-pipeline --offline`, core/provider Ruff, schema meta/negative
  fixtures, Terraform recursive formatting, and diff whitespace checks passed.
  All 28 tracked Terramate files matched formatting of isolated temporary
  copies. Running Terramate project parsing directly in the extracted provider
  repository encounters its existing `/plugins/providers/...` import paths;
  the format check deliberately does not reinterpret those imports.

## Reproduced baseline limitation

The untouched Eve head was checked out in a temporary detached worktree, using
only tracked Git data. Both edited and untouched checkouts reproduced a timeout
in `test_app_mounts_and_renders` at `asyncio.Runner.close` / `run_until_complete`.
The isolated baseline command was:

```sh
PYTHONPATH=<untouched-worktree> timeout 90 <project-python> -m pytest -vv \
  <untouched-worktree>/tests/python/test_tui_smoke.py::test_app_mounts_and_renders \
  -o faulthandler_timeout=30
```

It exited 124 and recorded the asynchronous shutdown stack. The temporary
worktree was removed. This unrelated TUI code remains unchanged, consistent
with the requirement to keep core changes limited to Incus contract support.
A completely green full Eve suite is therefore **not claimed**.

## Live checks and Determa

The live test was **not run**. Its default entrypoint prints SKIP and contacts
nothing. The pool still requires restricted client TLS enrollment and verified
server-certificate pinning; this Cloud session also has no configured VPN/TCP
access to the private pool. Perform the explicit manual steps in
[tls-setup.md](tls-setup.md), including denial of the default project, and run
from a controller with the documented LAN route. The test accepts only a
preloaded project image fingerprint, so it imports/deletes no shared image,
generates no key, writes no client configuration, and cleans its unique instance.

No Determa dependency, FSM bundle, adapter, seed-by-replay restoration, or
emulation changed. Current stable terminal observations retain the existing
core behavior. Richer in-flight restoration and creating/failed/unknown FSM
reconciliation remain dependent on the agreed released Determa contract.

## Changed files by repository

### eve

* `AGENTS.md`
* `core/schema/command-io.schema.json`
* `core/schema/observed-state.schema.json`
* `core/schema/plugin-manifest.schema.json`
* `core/schema/resolved-instance.schema.json`
* `eve_sdk/resolve.py`
* `eve_sdk/schema.py`
* `scripts/instance-observe`
* `tests/python/sdk/test_container_access_contract.py`

### eve-providers

* `.github/workflows/conformance.yml`
* `.gitignore`
* `README.md`
* `incus/README.md`
* `incus/commands/incus-provider`
* `incus/config.schema.json`
* `incus/defaults.yaml`
* `incus/docs/tls-setup.md`
* `incus/docs/validation.md`
* `incus/eve-plugin.yaml`
* `incus/provider.py`
* `incus/tests/conftest.py`
* `incus/tests/test_composition.py`
* `incus/tests/test_eve_dispatch.py`
* `incus/tests/test_provider.py`
* `tests/test-incus`
* `tests/test-incus-live`
