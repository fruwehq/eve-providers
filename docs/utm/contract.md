# Proposed UTM contract (not yet implemented)

All structures below must become closed JSON Schema objects
(`additionalProperties: false`) with every named field required, except explicit
discriminated alternatives. No arbitrary configuration dictionary or shell/QEMU
argument list is accepted. Field names and bounds are proposals pending interface
proof; no shipped manifest or core schema advertises UTM today.

## Configuration

| Field | Type and constraint |
| --- | --- |
| `architecture` | `arm64` only; host architecture must also be `arm64`. Reject x86/emulation. |
| `backend` | `apple` or `qemu`. |
| `cpu` | Positive integer, within explicit host capability limits. |
| `disk` | Closed object: `template_drive_id` (nonempty stable drive identifier), `size_gib` (positive integer). No unrelated disk attachment. |
| `guest_os` | `linux`, `macos`, or `windows-arm64`. Apple accepts Linux/macOS; QEMU/HVF accepts Linux/Windows ARM. Reject other combinations. |
| `host_control` | Closed SSH object: `address` (validated DNS/IP, no user/option/URI syntax), `port` (1–65535), `username` (validated account), `host_identity`, `credential_reference`, `utmctl_path` (absolute path inside the approved signed UTM.app). |
| `host_control.credential_reference` | Shared closed `{type: ssh-private-key-file, path: absolute controller path}`. Explicit reference only; no inline key or ambient discovery. |
| `host_control.host_identity` | Closed `{algorithm: ssh-ed25519, fingerprint: SHA256:<43 base64 characters>, public_key: validated Ed25519 public key}`; the key's computed fingerprint must match before use. Fingerprint alone cannot populate known_hosts. |
| `hypervisor` | `hvf` for QEMU; `virtualization-framework` for Apple. Must match backend and host/guest architecture. |
| `memory_mib` | Positive integer within explicit host limits. |
| `network` | Closed discriminated selection: `bridged` requires an explicit host interface; `forwarded` requires explicit host/guest addresses and ports and backend support. No unreachable host-only/NAT endpoint guessed for an external controller. Guest NIC identity/MAC must be observed and matched. |
| `ownership_token` | Controller-generated cryptographically random lowercase 64-hex token; durable before effects, never display-name ownership. |
| `template` | Closed object: canonical `vm_uuid`, immutable `sha256` covering prepared configuration and all base disks under an agreed supported hashing/snapshot contract, exact `utm_version` and `utm_build`, matching backend/architecture/OS. UUID alone is insufficient. |
| `guest_ssh` | Closed object: `username`, `port` (1–65535), explicit private-key credential reference, configured pinned Ed25519 public host identity, and selected network endpoint. Template bootstrap must authorize only the configured controller public key and establish per-clone identity safely. |

No meaningful default, host address, account, key path, template name, pool limit,
or guest endpoint is embedded in code or tracked defaults. A future catalog
example uses placeholders and an explicit backend; it must not become an active
catalog entry until the provider is usable. macOS package provisioning and Windows
ARM OS entries require separate existing-core capability review, not unsupported
OS claims by the provider.

## Identity and guest access

The proposed shared provider identity variant is:

```text
{ provider: "utm", identity: {
    backend: "apple" | "qemu",
    host_address: validated DNS/IP,
    host_key_fingerprint: pinned SHA256 Ed25519 fingerprint,
    host_port: integer 1..65535,
    ownership_token: lowercase 64-hex,
    template_sha256: lowercase 64-hex,
    vm_uuid: canonical UUID
} }
```

Every layer is closed. Include host endpoint and pin to distinguish equal VM
UUIDs on different hosts. Store the same ownership/template token in authenticated
UTM metadata atomically with clone identity; the inspected interface does not yet
meet this requirement. A provider operation must compare the full identity,
backend, requested mutable configuration, template provenance, and actual state
before any effect. Names are labels only.

Guest access preserves the shared closed envelope: `address`, `port`,
`protocol: ssh`, `version: 2`, `username`, `credential_reference`,
`host_identity`, `provider_identity`. Initially use `configured-fingerprint`;
do not reuse `incus-authenticated-exec` for UTM. A supported, authenticated
per-clone key-discovery mechanism would need its own precise schema and tests.
Guest exec cannot replace normal SSH package management. No copied ambient
private keys, agent forwarding, TOFU, accept-new, or disabled certificate/pin
verification. Cloning reusable host keys across guests is not an acceptable
substitute for authenticated per-guest identity.

## Observations and operation crash boundaries

| Observation | Required evidence |
| --- | --- |
| `absent` | Successful complete authenticated inventory proves exact UUID absent; an SSH/AppleEvents failure is not absence. |
| `creating` | Supported authenticated operation identity proves an owned create still in flight; do not infer from a name. |
| `failed` | Supported authoritative failure evidence tied to owned identity; not merely stopped, a timeout, or a lost connection. |
| `running` | Exact owned UUID has UTM `started`, matching configuration and authenticated access binding. |
| `stopped` | Exact owned UUID has UTM `stopped`, with ownership/configuration verified. |
| `unknown` | Transient/paused/ambiguous/incomplete data, identity drift, failed refresh, or interrupted mutation pending reconciliation. |

UTM `starting`, `stopping`, `pausing`, `paused`, and `resuming` map to `unknown`
until an operation-specific supported observation proves more. Clear guest access
on every non-running or failed refresh; core must not retain a stale merged binding.

* Before clone: persist desired immutable request and ownership identity without
  provider effects. Check pinned template and conflict identity first.
* During clone and before owner assignment: interruption is `unknown`; no adoption
  or deletion by name/inventory delta. Current UTM atomicity gap blocks this step.
* After clone before start: observe exact UUID and complete requested configuration,
  ownership and template provenance before start or guest access.
* During start/stop: success is observed final power state, not command exit alone.
  Lost response/timeout is `unknown`; retry only after identity/power reconciliation.
* During delete: verify ownership/configuration and stopped state. Lost response
  is `unknown` until complete authenticated inventory proves absence.
* Cleanup: bounded retry/observation, report unresolved qualified host/UUID identity;
  never claim cleanup after SIGKILL, unavailable API, or broken authentication.

Do not create pre-authorization effects or emulate pending Determa restoration.
Tests must distinguish provider observation from core transition authority.

## Windows ARM graphics

No generic `gpu: true` capability is proposed. A future explicitly experimental
Windows 11 ARM, QEMU/HVF profile must pin an exact UTM build and guest-driver
artifact digest and record per-game measurements. UTM
[5.0.5 beta](https://github.com/utmapp/UTM/releases/tag/v5.0.5) introduced
experimental D3DMetal DirectX 12; [5.0.6 beta](https://github.com/utmapp/UTM/releases/tag/v5.0.6)
warns its updated driver is unreleased and recommends the prior release for users
depending on this feature. No known-good pair has been validated by Eve.
This indirectly uses the Apple GPU through Metal, not GPU passthrough. It promises
no CUDA, DLSS, NVENC, NVIDIA compatibility, or ray tracing. Eve does not implement
or maintain QEMU forks, translation layers, or guest graphics drivers.
