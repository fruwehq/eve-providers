# UTM provider: phase-one feasibility

## Decision and implementation gate

One future provider, `utm`, will use UTM's supported automation interface for
both QEMU and Apple Virtualization guests. This document does not register a
plugin, extend core schemas, or implement a lifecycle transport. No Mac was
contacted. Phase two is blocked on host-session proof, strict ID-only operations,
atomic clone recovery, immutable template provenance, and guest bootstrap.
Fake commands cannot prove these capabilities.

The inspected released source is UTM **5.0.6 beta**, tag commit
`968fef31ee3299224feaf4de1e40e1e5f46369c1`. GitHub marks it prerelease;
the latest non-prerelease is **4.7.5**. Neither is selected as an Eve runtime
dependency by this change. Before implementation, select and pin an exact UTM
build and check its interface; this review of the newest beta is not a claim
that every command exists in 4.7.5.

The [4.7.5 CLI](https://github.com/utmapp/UTM/blob/v4.7.5/utmctl/UTMCtl.swift)
was also checked specifically for this gate: it contains the same SSH-session
warning and the same name-only clone wrapper without a returned UUID. These
limitations are not confined to the newest beta.

In [UTMCtl.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/utmctl/UTMCtl.swift),
`UTMAPICommand.run()` creates `SBApplication(url: utmAppUrl)`, and the AppleEvents
error handler explicitly prints:

> NOTE: utmctl does not work from SSH sessions or before logging in.

It also sets `app.launchFlags = [.defaults, .andHide]`. Even `version`/`list`
can launch UTM; they are not session-neutral or strictly read-only. Independently
verify the intended logged-in GUI owner and exact existing app process before
each invocation, record PID/start time/session before and after, and fail proof
if a new/different app session appears. The check/use race remains: the app may
exit after verification and be auto-launched. An unavailable-app test must not
invoke utmctl and claim no effects. See [remote-login-proof.md](remote-login-proof.md).

[Upstream #5557](https://github.com/utmapp/UTM/issues/5557#issuecomment-1685087102)
attributes SSH failure to the macOS AppleEvents boundary.
[Upstream #5053](https://github.com/utmapp/UTM/issues/5053#issuecomment-1442810841)
explains the logged-in app and per-user sandbox dependency.
[Upstream #5377](https://github.com/utmapp/UTM/issues/5377) also has user reports
of success after interactive authorization. Those reports justify a controlled
proof, not a guarantee or an assertion that SSH is universally impossible.
An owner-account success does not prove that a separate scoped account can
control that owner's GUI session. Do not use `sudo`, `launchctl asuser`, a
LaunchAgent broker, broad Full Disk Access, disabled TCC, or a custom daemon to
bridge this gap in Eve.

## Supported interface coverage

Coverage below is from the pinned Swift CLI and
[scripting dictionary](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTM.sdef).
Scripting capabilities are not automatically CLI flags.

| Need | Existing interface | Consequence |
| --- | --- | --- |
| Version | `utmctl version` | Can auto-launch UTM; not session-neutral. Pin app build and verify existing owner/process independently. |
| Inventory | `utmctl list` | Can auto-launch; human-readable UUID/status/name table, no VM-list JSON flag. Names are not identity. |
| Status | `utmctl status IDENTIFIER` | ID lookup falls back to name, even for UUID-shaped input. Transient states; no authoritative persistent failure state. |
| Start/stop | `utmctl start IDENTIFIER`, `utmctl stop --request IDENTIFIER` | Both use ID/name fallback. Bare stop defaults to force/power-off. Normal stop must explicitly request graceful shutdown and observe bounded completion; no implicit force fallback. |
| Clone | `utmctl clone IDENTIFIER --name NAME` | Source lookup also falls back to name. Only name exposed; no returned UUID, owner/idempotency token or immutable provenance. |
| Delete | `utmctl delete IDENTIFIER` | ID/name fallback makes raw CLI deletion unacceptable even after preflight; stopped check does not close identity race. |
| Configuration | Scripting `configuration`, `update configuration`, `reload configuration` | Backend-specific CPU/memory/drives/network/notes available; no equivalent inspect/update CLI command. Must use a supported structured scripting boundary if feasible. |
| Guest address | `utmctl ip-address UUID` | Unlabelled list of addresses; cannot choose a configured NIC by position or first IPv4. |
| Guest exec/files | `utmctl exec`, `file pull/push` | QEMU guest-agent-dependent; not generic Apple guest access or normal Eve provisioning. |

`virtualMachine(forIdentifier:in:)` first checks `object(withID:)`, then
`object(withName:)`. If owned VM UUID U disappears and an unrelated VM's display
name is U, a later status/start/stop/delete can address that unrelated VM.
Preflight inventory cannot close this lookup/effect race. Require a supported
strict-ID-only operation with atomic lookup/effect, or a narrowly scoped static
documented scripting operation proven to resolve/effect the exact ID object and
verify its returned ID. The pinned dictionary's ID property and VM object
specifier are promising, but do not prove end-to-end atomicity under disappearance
and concurrent GUI activity; no AppleScript implementation is approved here.

The [clone implementation](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptingVirtualMachineImpl.swift)
calls `data.clone(vm: box)` **before** applying supplied configuration and saving.
The clone command returns no new VM identity. Interruption between cloning and
ownership/configuration assignment can therefore leave an untagged VM whose
ownership cannot safely be inferred from its display name or an inventory diff.
The scripting dictionary allows configuration changes during duplicate, but the
implementation does not establish an atomic owner assignment. This is a separate
product gap even if Remote Login succeeds. Do not delete/adopt such a VM by name.
An external sidecar ledger alone cannot authenticate which untagged VM belongs
to an interrupted request.

Serialization covers only cooperating wrapper calls, not GUI/other clients or
UTM/host/controller failure. Failing closed with manual reconciliation is honest
but is not the required recoverable disposable lifecycle. No ledger, daemon,
inventory-diff or name-based adoption/deletion workaround is permitted.

Neither a UTM UUID nor a snapshot name is a content hash of all template disks
and configuration. A supported immutable template identity needs definition.
Do not read/rewrite private UTM bundle formats or assume a configuration UUID
attests to unchanged template bytes. Address selection likewise needs a
supported NIC/MAC binding or an explicit independently authenticated endpoint.

[source-audit.md](source-audit.md) records the supported export investigation:
stopped-at-entry plus bundle copying does not prove quiescence, deterministic
bytes, complete external-disk coverage or race-free association with the live
template. Export is not accepted as an immutable provenance workflow.

Guest bootstrap is an independent blocker for every proposed profile. The closed
four-row [capability matrix](bootstrap-matrix.md) distinguishes supported APIs
from unresolved controller-key injection, unique per-clone SSH host identity,
NIC binding, first-boot timing and reboot persistence. No row is enabled.

## Proposed implementation boundary

[contract.md](contract.md) describes required closed types and rejection rules;
they are a design proposal, not installed schemas. Core's existing `kind: vm`
honestly represents these guests. Shared guest SSH remains the management
transport. Core changes should only add a closed `provider: utm` identity variant
and, if justified by a supported bootstrap interface, a specifically documented
host-identity mechanism. Do not expand the Incus variant or loosen its tests.

The host needs the signed UTM.app and built-in macOS facilities only. The eventual
controller orchestration is Python. A minimal forced-command shell artifact may
be considered only after session proof and strict-ID source proof; it must use
documented UTM scripting with strict ID semantics, validate an allowlisted
versioned protocol, and never
evaluate `SSH_ORIGINAL_COMMAND` as shell source. No Python, compiler, package
manager, developer tools, checkout, or undocumented UTM Server protocol is needed
or proposed on the Mac.

## Phase gates and validation plan

1. Run the administrator-supervised [Remote Login proof](remote-login-proof.md) on
   the intended owner session/account/build. Record exact versions, authorization
   behavior, existing-process continuity, auto-launch/relaunch and scoped-account
   results. No VM mutation; app/session effects remain possible.
2. Resolve strict-ID lookup/effect, atomic clone ownership, immutable-template
   provenance and all guest-bootstrap matrix columns with supported interfaces.
   Two focused upstream drafts are indexed in [upstream-request.md](upstream-request.md);
   neither has been posted. [decision-record.md](decision-record.md) keeps rejected
   alternatives explicit.
3. Implement closed schemas and capability validators, then a fake host boundary
   using actual supported commands. Cover injected arguments, no ambient agent/
   keys/config, host pin rejection, credential redaction, output corruption,
   timeouts, all observation states, configuration/template drift, idempotency,
   and interruption before/after every mutation. Include disappearance followed
   by UUID-as-name collision, preflight races, auto-launch/new-session detection,
   graceful-stop timeout without force, and per-clone key uniqueness. Run existing
   full suites and cross-repo catalog/conformance, preserving Incus.
4. Add an explicit opt-in remote live test with unique ownership, approved
   prepared template, authenticated guest SSH, stop/start/delete, bounded cleanup,
   and final unresolved UUID reporting. No automatic CI activation.

No Determa dependency, adapter, replay restoration, seed mechanism, or provisional
API is introduced. A provider may emit raw observations under the released Eve
contract; richer durable in-flight FSM restoration remains Determa-dependent.
Host feasibility, strict identity, clone atomicity, template provenance and guest
bootstrap are UTM interface/design gates, not a reason to emulate Determa APIs.
