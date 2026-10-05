# Draft upstream request: supported scoped remote UTM automation

Not submitted. Review and consolidate with
[UTM #5377](https://github.com/utmapp/UTM/issues/5377) before posting.

## Problem and smallest read-only reproducer

An external orchestration controller needs to operate disposable UTM guests on
an Apple Silicon Mac. The host should need only signed UTM.app and built-in macOS
facilities, without developer tools or a custom daemon.

With UTM running in its logged-in owner's desktop session, invoke the bundled
absolute CLI from Remote Login as the intended authorized account:

```sh
/Applications/UTM.app/Contents/MacOS/utmctl version
/Applications/UTM.app/Contents/MacOS/utmctl list
```

UTM v5.0.6's AppleEvents error handler says it does not work from SSH sessions.
Earlier #5557 attributes this to macOS AppleEvents; #5377 contains conflicting
user reports after interactive permission approval. This source review has not
run the reproducer on a Mac. Please clarify a supported least-privilege
authorization/session procedure, including separate scoped accounts, or provide
a supported authenticated remote automation boundary. We do not want to use the
undocumented UTM Server protocol, broad TCC bypasses, or a GUI-session broker.

## Additional lifecycle requirements

* Atomic clone with caller-supplied ownership/idempotency token and immutable
  template identity; return the new UUID and permit recovery by that token.
  Current `duplicate` creates the VM before applying configuration; CLI `clone`
  exposes only name and returns no UUID. An interruption can leave an unowned VM.
* Structured backend-neutral inspection of UUID, power/operation state, ownership,
  architecture/hypervisor, CPU, memory, disks, NICs and template provenance.
  Configuration scripting exists; CLI inspection currently lacks this coverage.
* Supported immutable prepared-template identity covering configuration and disks,
  with drift detection and clone provenance. UUID/snapshot labels alone do not
  attest to content.
* Address reporting tied to NIC/MAC rather than an unlabelled address list, plus
  a supported authenticated bootstrap identity path for both backends.
* Documented interruption/deletion semantics and scoped authorization limiting
  clients to their owned templates/guests.

These are product-interface requirements, not a request for Eve to own a QEMU
fork, graphics translation stack, alternate backend, or headless daemon.
