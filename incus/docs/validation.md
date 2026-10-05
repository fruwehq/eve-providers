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

## Review fixes — 2026-10-05 (Asia/Tokyo)

The review revision starts from core `4282c0e` and providers `1576c8b`.

* Safe absolute and home-relative SCP paths now accept the actual core
  provisioning uploads (`provision/` and `provision/state/`). An integration
  regression executes `provision_ubuntu` and routes its six real uploads through
  the Incus SSH transport; hostile destinations fail before upload.
* Core wheels explicitly include runtime assets. `python scripts/test-wheel`
  builds a wheel, installs it into a fresh venv outside the checkout, and verifies
  CLI help, positive/negative command validation, all runtime schemas, FSM,
  configuration, scripts, TUI, and shipped OS assets. This passes and runs in
  both core CI matrix jobs; source-only validation no longer masks packaging.
* Running observations carry authenticated access. Failed observations retain
  their raw status and use the existing error presentation; running/provisioned
  history cannot enable actions after an observed failure. Refresh replaces
  bindings and clears binding/address on non-running or failed refreshes.
  Validation consumes the exact status object selected for persistence.
* Identity now uses a closed provider-discriminated envelope. Incus fields live
  under its `identity` variant. SSH host identity supports an explicit configured
  fingerprint or the namespaced Incus authenticated-exec mechanism. OS account
  names are not restricted to lowercase Unix names.
* Deletion checks actual power after scope/type/ownership verification. Error
  alone never means stopped. Confirmed running/frozen power is stopped before
  deletion. Cleanup retries transient observations within a deadline, caps each
  client timeout at the remaining budget, and names the qualified resource if
  absence cannot be established. Incus 7.0 rejects `--project` on `query`; the
  guarded state URL includes `?project=<configured-project>` explicitly and
  accepts no other path. Other calls retain the project flag.
* Creation requires a preloaded immutable fingerprint and verifies Incus's
  `volatile.base_image` on reconciliation. Mutable aliases and fingerprint drift
  are rejected. Pool endpoint/remote/project/subnet values have moved from
  generic defaults to `pool.example.yaml`; generic project configuration accepts
  explicit non-default projects authorized by the restricted client identity.

Final validation: **536 core Python tests passed, 1 intentional skip**, excluding
only the 20-test TUI smoke file; **27 focused core contract tests passed**;
all **16 non-Python suite groups passed**; **122 Incus offline tests passed**;
other provider entrypoints and all 8 environment contracts passed;
**48-plugin cross-repository conformance passed with 0 failures**;
actual Linux and PowerShell provision runners, schema tests, Ruff/type checks,
formatting, and offline CI pipeline checks passed. PowerShell used temporary
XDG cache/config/data directories because the Cloud home directory is read-only.

The complete core Python invocation was attempted: lint/type checks and 523
Python tests passed before it stalled at the unchanged TUI smoke file and was
interrupted. The isolated TUI smoke run also exited 124 at 120 seconds. The
previous untouched-baseline reproducer remains documented above; a completely
green full suite is not claimed and no test configuration disables that file.

Live testing remains explicitly skipped. No private-pool access, TLS enrollment,
live resource operation, Determa dependency/FSM/adapter/restoration change, or
unreleased capability was introduced. New CI must be evaluated on the pushed
review-fix commits independently of earlier results.

### Installed-wheel CI layout follow-up

The first review-fix CI run passed 121 Incus tests and failed one discovery
integration test because the workflow nested the Eve checkout inside the provider
plugin root. Discovery then encountered Eve's intentionally invalid test
manifests. The workflow now checks out providers and core as siblings and runs
provider commands from the providers directory.

This layout was reproduced from tracked Git archives with a newly built,
non-editable Eve wheel installed into a clean venv (no source PYTHONPATH):
**all 122 Incus tests passed**, along with AWS, host-resolver, manifest environment
contracts, and backend/status tests. Both GitHub core matrix jobs have also
successfully executed the new isolated wheel test. Full core Linux CI and fresh
provider checks still require their own final conclusions.
