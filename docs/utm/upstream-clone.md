# Draft B: atomic clone identity, immutable provenance and guest bootstrap

Not submitted; ready for user approval. Host-session and strict-ID operations are
separate [draft A](upstream-automation.md). Related existing macOS provisioning
discussions: [UTM #7757](https://github.com/utmapp/UTM/issues/7757) and
[#6092](https://github.com/utmapp/UTM/issues/6092). This request does not assume
those APIs already solve disposable-clone bootstrap.

## Atomic idempotent clone returning owned identity

At official commit `968fef31ee3299224feaf4de1e40e1e5f46369c1`,
[UTMData.clone](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Platform/UTMData.swift)
copies data, creates/saves a new UUID and adds/selects the new VM before
[scripting clone](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptingVirtualMachineImpl.swift)
applies caller configuration. CLI clone exposes only name and returns no UUID.
Interruption can leave an untagged clone. This is source analysis, not a live
failure claim.

Please accept a caller ownership/idempotency token and immutable template revision
atomically with clone creation, return its UUID and operation result, and expose
recovery by token after lost responses. Define behavior under interrupted copies,
registration-before-response, retries and concurrent GUI/other-client operations.
A sidecar ledger or serialized wrapper cannot authenticate an untagged clone and
must not adopt/delete by name or inventory difference. Manual reconciliation is
safe failure, not the recoverable disposable lifecycle we need.

## Template provenance

Supported scripting export checks stopped/not-installing, then asynchronously
copies the bundle tree; it does not emit a canonical manifest/digest or bind the
later clone to an immutable revision. External drives and concurrent mutations
cannot be assumed covered/frozen. See the [pinned export audit](source-audit.md).

Please define immutable prepared-template identity covering configuration, all
disks/layers/external resources, and clone provenance with quiescence and race
prevention. An export-based workflow is acceptable if exact UUID/config revision,
resource closure, deterministic bytes or a supported manifest, and atomic later
clone association are guaranteed. We do not want to parse private bundle formats
or treat UUID/snapshot names as content hashes.

## Bootstrap capability needs

The [four-profile matrix](bootstrap-matrix.md) identifies unresolved per-clone
controller authorized-key injection, unique SSH host-key regeneration and
authenticated discovery, NIC/MAC-to-routable-address association, before-first-
boot timing and reboot persistence. These must be supported or explicitly marked
unavailable for Linux ARM/QEMU-HVF, Windows 11 ARM/QEMU-HVF, Linux ARM/Apple and
macOS/Apple. Reusable cloned guest host keys are forbidden.

macOS 27 account/password/Remote Login provisioning in the pinned beta exposes no
public-key input and applies to first boot after installation, not necessarily a
prepared clone. QEMU guest-agent exec/files require an already running prepared
guest; Apple does not share that interface. Guest operations may only bootstrap/
attest identity through a precise authenticated contract, never replace standard
guest SSH management. No automatic-login assumption, provisional restoration API,
guest graphics stack, QEMU fork or custom host daemon is requested.
