# Closed guest-bootstrap capability matrix

These are the only four proposed profiles; none is enabled. `arm64` host and guest
are required, with HVF for QEMU. This is a source-audit matrix, not a runtime
capability promise or a successful guest test. All unresolved cells are blockers.
Guest exec/file operations must never become normal Eve package provisioning.

| Profile | Unique controller-key injection | Per-clone host-key generation and authenticated discovery | NIC/MAC to address | First-boot timing | Reboot persistence |
| --- | --- | --- | --- | --- | --- |
| Linux ARM / QEMU-HVF | Unresolved: CLI exposes no Linux first-boot authorized-key input. Guest-agent file/exec works only after a running guest/agent; it is not a proven pre-start bootstrap. | Unresolved: cloning copies disks, including existing keys. No audited regenerate-and-attest API. Prepared-template cleanup alone does not prove unique post-clone generation. | Guest-agent interface data is flattened by `queryIp` to addresses without NIC/MAC labels. Config exposes MAC; authenticated selected-NIC association remains unresolved. | No audited atomic seed attachment/key bootstrap before first start. A future guest-supported prepared first-boot mechanism needs its own supported contract and timing proof. | Unresolved: persistent authorization and per-clone identity across reboot have not been specified or tested. |
| Windows 11 ARM / QEMU-HVF | Unresolved: no audited Windows OpenSSH first-boot key injection API. Guest agent after boot cannot be assumed installed/running or safely bootstrap arbitrary guests. | Unresolved: no audited per-clone OpenSSH host-key regeneration/discovery. Reusing template host keys is forbidden. | Same QEMU flattening; selected NIC/MAC and routable endpoint unresolved. | Windows first-boot specialization, SSH service/key timing and agent availability unresolved; no prepared Windows profile is advertised. | Unresolved: authorized-key ACLs, SSH service persistence and identity across reboot need explicit tests. |
| Linux ARM / Apple Virtualization | Unresolved: macOS-specific provisioning options do not apply to Linux. No Apple guest-agent exec/file path in the audited scripting implementation. | Unresolved: no supported audited per-clone Linux key regeneration/authenticated discovery. | `queryIp` uses **first configured NIC's MAC** and host ARP, returning zero/one IPv4 address. This is supported source behavior, not authenticated guest identity, arbitrary NIC selection or external reachability. MAC uniqueness on clone remains unresolved. | Unresolved: no audited Linux seed/key mechanism or guaranteed pre-start first-boot ordering. | Unresolved: prepared Linux bootstrap and reboots not validated. |
| macOS / Apple Virtualization | UTM 5.0.6 beta exposes account/password and Remote Login provisioning only for host+guest macOS 27 and first boot after installation; **no public-key input**. Unique key injection unresolved. Auto-login is not accepted. | Unresolved: enabling Remote Login is not host-key regeneration or authenticated discovery, and a cloned already-set-up guest is not a fresh installation. | Same first-NIC MAC/ARP behavior; per-clone MAC and authenticated/routable SSH endpoint unresolved. | Supported macOS 27 provisioning is first-start-after-install only, options never saved. Applicability to disposable prepared clones is unproven; no password bootstrap is selected. | Unresolved: no audit/test proves injected key persistence or identity after clone/reboot. |

## Pinned evidence and acceptance criteria

All implementation evidence is from commit
`968fef31ee3299224feaf4de1e40e1e5f46369c1`:

* [UTM.sdef](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTM.sdef): guest provisioning fields and OS/version/first-boot restrictions.
* [UTMScriptingVirtualMachineImpl.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Scripting/UTMScriptingVirtualMachineImpl.swift): `withGuestAgent`, `start`, `queryIp`; Apple ARP lookup and QEMU address flattening.
* [UTMData.swift](https://github.com/utmapp/UTM/blob/968fef31ee3299224feaf4de1e40e1e5f46369c1/Platform/UTMData.swift): clone copies template disks/config; MAC regeneration depends on `IsRegenerateMACOnClone` and is implemented for QEMU only in this clone path. No host preference may be assumed by Eve.

To enable a row, specify supported mechanisms for **every** column, including
explicit controller public-key reference, OS username, SSH service availability,
unique regenerated per-clone host keys, authenticated public-key discovery,
selected NIC/MAC mapping, reachability, before-first-boot ordering and durable
reboot behavior. Test interruption at each boundary and rejection of duplicated
keys/MACs. A proposed prepared guest bootstrap may be assessed later; it is not
provided or verified by these UTM APIs. Guest management thereafter is shared
authenticated SSH only. Cloned reusable host keys are forbidden for all rows.
