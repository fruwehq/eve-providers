# Pinned source audit: strict identity, stop and export

Official source only, commit `968fef31ee3299224feaf4de1e40e1e5f46369c1`
(5.0.6 beta). No Mac experiment or private bundle parsing was performed.

## Strict identity is not established

[UTMCtl.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/utmctl/UTMCtl.swift)
`virtualMachine(forIdentifier:in:)` checks an ID, then falls back to display name.
Example: owned ID U disappears, unrelated ID V is named U; `delete U` can select
V. A preceding inventory/ID check or wrapper lock does not prevent disappearance
between lookup and effect or concurrent GUI/other-client changes.

[UTM.sdef](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTM.sdef)
documents VM objects with a read-only ID and lifecycle commands taking those
objects. [AppDelegate.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Platform/macOS/AppDelegate.swift)
exposes `scriptingVirtualMachines`; the VM implementation returns an
`NSUniqueIDSpecifier` for its ID. These do not by themselves prove an atomic,
strict-ID-only scripted lookup/effect or identity verification after disappearance.
[UTMScriptable.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptable.swift)
suspends commands and schedules asynchronous work on a later event loop; a static
AppleScript block must not be assumed to be a transaction. No eligible host
artifact is implemented. Require supported atomic strict-ID operations or a
source-proven exact-object scripting operation with returned-ID verification.

## Stop policy

CLI `Stop.Style.validate()` selects `force` if no flag is supplied; `--request`
explicitly requests guest OS shutdown. Scripting `stop` likewise defaults to
force. Normal stop must use request semantics, observe actual stopped state within
a bound, and report `unknown` on timeout. Force/kill is separately authorized,
never fallback. `UTMScriptingVirtualMachineImpl.stop` can force cancellation of
an active Apple installation even with a request method; exclude that path from
normal lifecycle policy. Bare CLI stop and ID/name lookup are both unacceptable
as Eve's future normal-stop boundary.

## Supported export investigation

The scripting dictionary documents `export <virtual machine> to <file>`; there
is no export CLI subcommand in the inspected command list.
[UTMScriptingExportCommand.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptingExportCommand.swift)
dispatches the resolved VM to `export` in
[UTMScriptingVirtualMachineImpl.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptingVirtualMachineImpl.swift),
which requires not-installing and stopped at entry. It then awaits
[UTMData.export(vm:to:)](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Platform/UTMData.swift):
remove an existing destination and copy `vm.pathUrl` recursively using
`CopyManager` with `.all`, `.recursive`, `.clone`, `.dataSparse`. This is a
filesystem bundle copy, not a canonical archive, snapshot digest or signed
manifest. Do not execute export on an existing destination during feasibility.

| Required provenance property | Source finding / unresolved condition |
| --- | --- |
| Quiescence | Stopped-at-entry guard exists. No inspected transaction/lease freezes configuration, registry, external files and concurrent GUI/other clients throughout asynchronous copying. |
| Exact UUID/config association | Export receives a VM object; no returned UUID/config digest/manifest ties exported bytes to a strict-ID live template revision. Static scripting atomicity remains unproven. |
| All-disk coverage | Recursive copy covers the bundle tree. External/removable files are not shown being gathered by `export`. Supported scripting config and `UTMAppleConfigurationDrive` permit external image URLs; thus all attached disks cannot be assumed contained. Layer/dependency closure also needs a supported manifest. |
| Deterministic bytes or manifest | No canonical ordering/metadata normalization, hash or supported all-resource manifest is emitted. A user-defined directory hash would define a new private-layout protocol, not prove supported template provenance. |
| Race prevention and later clone association | No audited immutable revision/lease prevents changes during export or between digest and clone. A wrapper lock cannot exclude GUI/other clients; repeated matching hashes alone do not close the race. |

External-drive evidence:
[UTMAppleConfigurationDrive.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Configuration/UTMAppleConfigurationDrive.swift)
and [UTMScriptingConfigImpl.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptingConfigImpl.swift).
These are source evidence, not a plan to parse their persisted private formats.

Conclusion: export alone does **not** establish a safe immutable-template digest
workflow under the required properties. Hashing a sealed independently supplied
artifact could identify that artifact's bytes, but the audited API does not bind
the registered live template and subsequent clone to those bytes. Retain upstream
request B for immutable provenance, resource closure and atomic clone association.
