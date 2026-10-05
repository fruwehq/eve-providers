# Phase-one validation — 2026-10-05 (Asia/Tokyo)

Fresh feature branches `codex/utm-provider` were created from the fetched main
merge commits: Eve `ec580016e5f7c9a3fc8069dd0ef0652987a0027b`, providers
`a77d3995aeac8bcfafd07f5aabb907aad110379b`. The repositories use a narrow fetch
configuration without `origin/main`; the verified fetched `FETCH_HEAD` was used.
Core has no feature changes. Providers changes are documentation only; no plugin,
runtime schema, host artifact, catalog entry, or lifecycle success path was added.

## Results

Commands below run from Eve unless prefixed with the providers working directory.
PATH used the existing Eve virtualenv, temporary Poetry tooling, Terraform,
Terramate, shellcheck and PowerShell installations. XDG cache/config/data were
temporary writable directories. No ignored personal configuration was read.

* `python -m pytest -q tests --ignore=tests/python/test_tui_smoke.py`:
  **536 passed, 1 intentional skip**, 204.19 seconds. The 20-test TUI smoke file
  is explicitly excluded; this is not a full Python-suite pass.
* `timeout 360 ./scripts/test`: **exit 124** at `test_tui_smoke.py`, after Ruff,
  strict mypy and earlier suites passed. This matches the pre-existing asynchronous
  TUI shutdown timeout recorded in the Incus validation; no TUI code changed here.
* Providers `python tests/test-incus`: **122 passed**, 50.56 seconds. These include
  fake-client lifecycle, secure guest SSH, provisioning uploads, observation,
  ownership, template drift and cleanup regressions. Live Incus was not activated.
* Providers `python tests/test-aws-connectivity`: **6 passed**;
  `python tests/test-host-resolver`: **3 checks passed**;
  `python tests/test-manifest-env-contract`: **8 provider manifests passed**;
  `python tests/test-provider-status-errors`: **8 passed**.
* `scripts/test-cross-repo --plugin-root <providers> --plugin-root <linux-packages>
  --plugin-root <windows-packages> --plugin-root <ai-plugins>`: **48 plugins,
  zero failures** (8 providers, 25 packages, 11 bundles, 4 OS plugins); combined
  catalog, manifest/schema/conformance and dual-OS schema parity passed.
* Providers `../eve/scripts/test-provision-runner --plugin-roots <providers>/oses`:
  **all Linux and PowerShell checks passed**. Initial invocation without PowerShell
  on PATH skipped Windows; it was rerun with PowerShell available.
* `/tmp/eve-review-tooling/bin/python scripts/test-wheel`: **passed** clean wheel
  build, isolated install outside source checkout, `eve --help`, schemas,
  positive/negative command output validation and runtime assets. Initial use of
  the project virtualenv failed because that environment has no pip; the tooling
  interpreter resolved this environment prerequisite without source changes.
* Providers `python -m ruff check incus tests` and `git diff --check`: **passed**.

* `./scripts/test catalog config-save core-boundary doctor instances lifecycle
  plugins plugins-sync provision-runner schemas secrets shellcheck
  state-concurrency tf-isolation tui lint`: **all 16 suite groups passed**,
  including PowerShell provisioning checks. This independent run covers the
  later groups that the full-test timeout prevented from running.

## Unperformed checks and blocking evidence

No UTM offline provider suite exists yet: a fake transport would not establish
the missing supported host-session or atomic-clone boundary. The supervised
Remote Login proof and future live lifecycle test were **not run**. Neither the
Mac nor the Incus pool was contacted. No credentials, key material or personal
infrastructure settings were added.

The feasibility report cites the pinned UTM source and existing upstream reports;
it is not a claim of locally reproduced macOS failure. No upstream issue was
submitted. No Determa provisional API, adapter, restoration or emulation was added.

## Review revision validation — 2026-10-05 (Asia/Tokyo)

Started at draft Providers #12 head
`94efd227527d45bdf7cf5438918db3299450176a`, verified against fetched branch head.
This revision changes documentation only. Earlier references to a read-only
Remote Login proof are corrected: utmctl can auto-launch/hide UTM, and independent
before/after process inspection detects but does not prevent the check/use race.
Unavailable-app tests must fail preconditions without invoking utmctl. No static
host-control artifact, AppleScript, schema, plugin or catalog entry is installed.

Pinned official source audit covers CLI launch flags and ID-to-name fallback,
stop's force default/request option, scripting's asynchronous dispatch, clone
registration ordering, export bundle-copy/resource limitations, and the closed
four-profile bootstrap matrix. Export cannot establish the required immutable
provenance guarantees. Static strict-ID scripting remains unproven and gated.
Two upstream drafts are prepared, neither posted. No private bundle was parsed.

Fresh checks for this documentation revision:

* Providers `python tests/test-incus`: **122 passed**, 37.80 seconds.
* Providers AWS connectivity: **6 passed**; host resolver: **3 checks passed**;
  manifest environment contract: **8 manifests passed**; status errors:
  **8 passed**. Provider Ruff passed.
* `../eve/scripts/test-cross-repo` with the same four companion roots:
  **48 plugins, zero failures**; manifest/schema/conformance, dual-OS parity and
  combined catalog composition passed.
* `../eve/scripts/test-provision-runner --plugin-roots <providers>/oses`:
  **all Linux and PowerShell runner checks passed**.
* All local UTM documentation links resolve; `git diff --check` passed.

No Mac, Incus pool or other live provider was accessed. The earlier full core
suite/wheel results above are historical validation of unchanged core; they were
not rerun for a documentation-only revision. The pre-existing TUI shutdown
timeout is not resolved or hidden. Prior head's GitHub Conformance run
`37324847339` succeeded; revised-head CI must be checked independently after push.
