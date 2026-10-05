# Draft A: supported scoped automation and strict ID-only operations

Not submitted; ready for user approval after consolidation with
[UTM #5377](https://github.com/utmapp/UTM/issues/5377),
[#5557](https://github.com/utmapp/UTM/issues/5557) and
[#5053](https://github.com/utmapp/UTM/issues/5053). Independent clone/provenance
requirements are in [draft B](upstream-clone.md).

## Scope and source evidence

An external controller needs supported least-privilege noninteractive access to
the intended logged-in UTM owner session, with only signed UTM.app and built-in
macOS facilities on the host. We do not want an undocumented UTM Server protocol,
TCC bypass, GUI-session broker or custom daemon.

Pinned official source: UTM 5.0.6 beta commit
`968fef31ee3299224feaf4de1e40e1e5f46369c1`,
[UTMCtl.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/utmctl/UTMCtl.swift).
This is source analysis; no Mac reproduction is claimed.

* `UTMAPICommand.run()` constructs `SBApplication` and sets
  `[.defaults, .andHide]`. Even version/list can launch an app. Independent
  preflight cannot close process-exit/auto-launch races or bind an exact session.
  Please support no-launch/session-bound inspection with an explicit owner/session
  identity and clear unavailable/permission errors. Clarify same-owner versus
  separate scoped-account authorization without broad security exceptions.
* `virtualMachine(forIdentifier:in:)` tries ID then display name. A UUID-shaped
  argument is not ID-only. Request supported atomic strict-ID lookup/effect and
  structured inspection returning actual identity, backend, configuration and
  state; no fallback to names. Alternatively, document and prove a safe static
  scripting operation against an exact ID object, with ID verification and
  disappearance behavior, without treating separate AppleEvents as a transaction.
* `stop` defaults to force/power-off; `--request` is graceful request. Document
  request completion and bounded observation semantics, separate force policy,
  and the installation-cancellation exception. Timeout must not imply stopped.

## Smallest verification cases (not run here)

1. Independently confirm exact intended GUI owner/process already active; record
   PID/start time/session. From approved Remote Login invoke bundled absolute
   `utmctl version`, then independently re-verify before `list`. Detect any new/
   different process/session as failure. No unavailable-app invocation is claimed
   effect-free: current CLI may launch UTM.
2. In a separately authorized disposable test fixture, remove VM ID U and give an
   unrelated VM ID V display name U. Current `status U` selects V by name. Do not
   run destructive reproduction against real VMs; source shows start/stop/delete
   share the resolver. A future safe interface must reject U, including when U
   disappears after inventory preflight. Observe returned ID mismatch explicitly.

Success requires a documented, repeatable scoped boundary and exact identity
semantics under concurrent GUI/other-client activity, not an anecdotal permission
prompt fix or wrapper serialization. This request can be discussed independently
of clone and guest bootstrap work in draft B.
