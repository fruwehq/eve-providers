# Manual Remote Login feasibility proof (not session-neutral)

This is a supervised proof plan, not an installed host artifact or live provider
test. No Mac was contacted. Do not run automatically. The administrator must
approve the exact Mac, account, signed UTM build, explicit controller key and host
pin, including the possibility of app/session effects. Passing this proof does
not authorize VM operations or resolve strict-ID, clone, template or bootstrap
gates.

## Auto-launch and check/use race

Pinned `UTMAPICommand.run()` creates `SBApplication` and sets
`launchFlags = [.defaults, .andHide]`. Calling `version` or `list` can launch UTM
if it is not running. There is no proven no-launch flag in this CLI. Calling it
against an unavailable app is therefore not a read-only negative test.

Before **each** invocation, independently establish that the intended GUI owner
session and exact UTM process are already active. Verification must not itself
send UTM AppleEvents or invoke utmctl/osascript to launch the app. Use an
administrator's trusted local GUI observation and built-in process inspection
(`ps` on the confirmed PID), recording owner UID, GUI login session, PID, process
start time, executable path and approved app build. Process ownership alone does
not prove GUI-session association. Multiple or ambiguous UTM processes fail the
precondition. Do not infer session identity from a VM name or inventory.

Keep independent observation before, during and after invocation. Record whether
it launches/relaunches UTM and whether PID/start time/owner/session change. A new,
restarted or different app session is **proof failure**, even if output looks
valid. Compare returned inventory with the already active intended GUI instance.
There remains a check/use race: the process may exit after inspection and CLI may
auto-launch another. Monitoring detects evidence of that race; it cannot prevent
it or prove atomic process binding. A supported no-launch/session-bound operation
is requested upstream. Do not claim zero session effects from a successful probe.

## Administrator preparation

1. Select and pin a signed UTM build, macOS version and Apple Silicon architecture.
   Use built-in `codesign --verify --deep --strict` for integrity against the
   approved absolute app path; independently verify publisher/build trust.
2. The owner must already be logged in and UTM running in that GUI session.
   Record whether Remote Login uses that owner or a distinct scoped account.
   Dedicated non-admin ownership of a dedicated GUI session is preferable if
   supported; do not assume another account can control a personal owner's UTM.
3. Enable Remote Login only for the approved account. Keep PAM/TCC intact. Do not
   grant sudo, broad Full Disk Access, disable TCC, arrange automatic login or hop
   GUI sessions. Obtain the host's Ed25519 public key and SHA256 pin through an
   independent trusted channel, not a network key scan. Supply an explicit
   controller key; do not generate/discover/copy ambient private keys.
4. Do not install the earlier draft's two-command forced wrapper: it was described
   incorrectly as read-only and did not establish process continuity. A static
   forced-command shell/AppleScript artifact is eligible only after session proof
   and strict-ID source proof, using documented scripting and a fixed allowlist.
   It must never evaluate arbitrary `SSH_ORIGINAL_COMMAND` or caller scripts.
   Initial source-audit proof requires an explicitly approved, administrator-
   supervised session; if it cannot be done within the approved account/key
   boundary, stop. Do not weaken restrictions merely to obtain a passing probe.

## Supervised invocation

After independent verification, invoke only one inspection command at a time
using the selected absolute bundled CLI. For an installation explicitly approved
at `/Applications/UTM.app`, the first command is:

```text
/Applications/UTM.app/Contents/MacOS/utmctl version
```

Re-verify the same existing process/session independently before a separate
`/Applications/UTM.app/Contents/MacOS/utmctl list` invocation. Neither command is
a lifecycle operation, but each may launch/hide the app or trigger authorization.
Record sanitized errors and exit status; a zero status or empty table is not
proof if AppleEvents errors occur. Authorization, if prompted, is administrator-
approved for the exact caller/UTM pair, never an automatic TCC reset or bypass.

The external controller's eventual SSH invocation must use `-F /dev/null`,
`BatchMode=yes`, `IdentitiesOnly=yes`, `IdentityAgent=none`, `AddKeysToAgent=no`,
`ForwardAgent=no`, `ClearAllForwardings=yes`, `RequestTTY=no`,
`PermitLocalCommand=no`, `StrictHostKeyChecking=yes`, `UpdateHostKeys=no`,
`HostKeyAlgorithms=ssh-ed25519`, `GlobalKnownHostsFile=/dev/null`, an explicit
0600 known_hosts file containing the independently pinned public key, and explicit
key/account/address/port. Bound connect and execution time on the controller.
The Mac must not need Python, developer tools, a package manager or source checkout.
Do not log private paths, accounts, inventory or key material in public artifacts.

## Proof and negative-test matrix

* Owner and separate-account results are distinct. Local Terminal success does
  not prove Remote Login or access to another owner's GUI session.
* Reconnect and repeat with independently verified process continuity. An
  administrator may deliberately restart UTM between runs, but each new run must
  establish the intended pre-existing session afresh. Test lock/unlock separately.
* If no intended GUI session/process is active, fail the precondition **without
  invoking utmctl**. Do not run an unavailable-app probe and claim no effects.
* Future offline boundary tests must reject changed/new process identity,
  auto-launch/relaunch evidence, ambiguous owner/session, bad pin/key, arbitrary
  commands, forwarding and PTY requests. They cannot prove macOS feasibility.
* Any future separately authorized auto-launch experiment must record host/session
  effects and is not a passing continuity proof. No such experiment is requested
  or performed here.

Report exact versions, approved session arrangement, sanitized error and smallest
failing inspection command to upstream draft A. No daemon or session-hopping
workaround. The source audit does not establish strict scripting ID semantics;
that is a separate prerequisite before installing any host-control artifact.

## Cleanup and later live-test gate

No VM, image, key or temporary host artifact is created by this revision. A later
manual proof must remove only its explicitly installed authorization/artifacts,
record app launches/relaunches, and leave session restoration to the administrator.
Do not kill an app to hide effects or claim cleanup after unavailable access or
SIGKILL. Preserve unrelated keys, processes, templates and configuration.

A remote live lifecycle test remains deferred until all five feasibility gates
pass. It requires explicit target, immutable prepared template, unique ownership,
strict ID-only effects, authenticated per-clone guest SSH, bounded stop/start/delete
and cleanup with unresolved qualified identity reporting. It remains opt-in.
