# UTM provider: phase-one feasibility

## Decision and implementation gate

One future provider, `utm`, will use UTM's supported automation interface for
both QEMU and Apple Virtualization guests. This document does not register a
plugin, extend core schemas, or implement a lifecycle transport. No Mac was
contacted. Phase two is blocked on the host-session proof below and a supported
clone identity/reconciliation boundary. Fake commands cannot prove either.

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
| Version | `utmctl version` | Read-only host-session probe; pin app build separately. |
| Inventory | `utmctl list` | Human-readable UUID/status/name table; no VM-list JSON flag in inspected CLI. Names are not identity. |
| Status | `utmctl status UUID` | `started`, `stopped`, and transient states; no authoritative persistent failure state. |
| Start/stop | `utmctl start UUID`, `utmctl stop UUID` | Supported via AppleEvents; distinguish graceful stop from force/kill and observe completion. |
| Clone | `utmctl clone UUID --name NAME` | Only name exposed by CLI; no returned clone UUID, ownership token, immutable template digest, or idempotency key. |
| Delete | `utmctl delete UUID` | No confirmation; requires prior authenticated ownership and actual stopped-state verification. |
| Configuration | Scripting `configuration`, `update configuration`, `reload configuration` | Backend-specific CPU/memory/drives/network/notes available; no equivalent inspect/update CLI command. Must use a supported structured scripting boundary if feasible. |
| Guest address | `utmctl ip-address UUID` | Unlabelled list of addresses; cannot choose a configured NIC by position or first IPv4. |
| Guest exec/files | `utmctl exec`, `file pull/push` | QEMU guest-agent-dependent; not generic Apple guest access or normal Eve provisioning. |

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

Neither a UTM UUID nor a snapshot name is a content hash of all template disks
and configuration. A supported immutable template identity needs definition.
Do not read/rewrite private UTM bundle formats or assume a configuration UUID
attests to unchanged template bytes. Address selection likewise needs a
supported NIC/MAC binding or an explicit independently authenticated endpoint.

## Proposed implementation boundary

[contract.md](contract.md) describes required closed types and rejection rules;
they are a design proposal, not installed schemas. Core's existing `kind: vm`
honestly represents these guests. Shared guest SSH remains the management
transport. Core changes should only add a closed `provider: utm` identity variant
and, if justified by a supported bootstrap interface, a specifically documented
host-identity mechanism. Do not expand the Incus variant or loosen its tests.

The host needs the signed UTM.app and built-in macOS facilities only. The eventual
controller orchestration is Python. A minimal forced-command shell artifact may
be considered only after proof; it must invoke an explicitly configured absolute
bundled `utmctl` path, validate an allowlisted versioned protocol, and never
evaluate `SSH_ORIGINAL_COMMAND` as shell source. No Python, compiler, package
manager, developer tools, checkout, or undocumented UTM Server protocol is needed
or proposed on the Mac.

## Phase gates and validation plan

1. Run the authorized read-only [Remote Login proof](remote-login-proof.md) on
   the intended owner session/account/build. Record exact versions, authorization
   behavior, restart behavior, and scoped-account results. No VM mutation yet.
2. Resolve atomic clone ownership/identity and immutable-template inspection with
   a supported upstream interface. An upstream request draft is in
   [upstream-request.md](upstream-request.md); it has not been posted.
3. Implement closed schemas and capability validators, then a fake host boundary
   using actual supported commands. Cover injected arguments, no ambient agent/
   keys/config, host pin rejection, credential redaction, output corruption,
   timeouts, all observation states, configuration/template drift, idempotency,
   and interruption before/after every mutation. Run existing full suites and
   cross-repo catalog/conformance, preserving Incus.
4. Add an explicit opt-in remote live test with unique ownership, approved
   prepared template, authenticated guest SSH, stop/start/delete, bounded cleanup,
   and final unresolved UUID reporting. No automatic CI activation.

No Determa dependency, adapter, replay restoration, seed mechanism, or provisional
API is introduced. A provider may emit raw observations under the released Eve
contract; richer durable in-flight FSM restoration remains Determa-dependent.
Host feasibility and clone atomicity are UTM interface issues, not Determa issues.
