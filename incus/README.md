# Incus system-container provider

This provider controls infrastructure through the official Incus client and its
verified TLS API. Guest packages remain owned by Eve's normal Linux provisioning
and package plugins. It neither needs nor uses SSH to the Incus host.

Supported composition: `incus-ubuntu-ci`, `kind: container`, engine `incus`,
`ubuntu-26.04-amd64`, init `incus-cloud-init`, location `incus-pool`. Ubuntu's
bootstrap, provisioning, and human user is `ubuntu`. The default cloud image is
`images:ubuntu/26.04/cloud`; it must contain working cloud-init. ARM, VMs,
privileged containers, nested virtualization, and root SSH are not supported.
The server's `dir` storage pool does not provide a disk quota in this contract.

## Configuration

`config.schema.json` validates the complete provider configuration with unknown
fields prohibited. `eve-plugin.yaml` exposes the same fields as
`EVE_INCUS_<UPPERCASE_FIELD>` to Eve's isolated provider environment. Non-secret
preferences belong under `incus:` in the explicitly selected Eve config YAML;
per-instance `provider_config.incus` overrides use exactly the same schema.
No credential contents belong in this YAML. Defaults are in `defaults.yaml`
and the catalog; authentication paths have no defaults.

| Field | Type / constraint | Meaning |
| --- | --- | --- |
| `command_timeout` | integer, 1–600 seconds | Timeout for every client/SSH operation; default 120. |
| `config_dir` | absolute directory path; mode 0700 | Dedicated client config, restricted TLS identity, pinned server certificate. |
| `endpoint` | HTTPS URL with explicit port | Must exactly match the TLS remote; pool default `https://192.168.1.108:8443`. |
| `image` | exact cloud alias, or configured-remote 64-hex fingerprint | Alias may populate the project's image cache. Live tests require a preloaded fingerprint. |
| `instance_prefix` | lowercase DNS label, 1–10 characters | Resource namespace; default `eve-ci`. |
| `nic` | explicit guest interface name | Only this NIC supplies guest IPv4; default `eth0`. |
| `project` | constant `eve-ci` | Every client call supplies `--project eve-ci`. |
| `public_key_file` | absolute file path | Explicit controller Ed25519 public key, read only for creation/reconciliation. |
| `remote` | lowercase remote name | Explicit TLS remote; default `eve-incus-pool`, never `local`. |
| `run_id` | lowercase UUID | Unique run identity; preserve for retries and cleanup. |
| `ssh_private_key_file` | absolute file path | Selected SSH credential reference; passed to OpenSSH, never read/copied by Eve. |
| `subnet` | strict IPv4 CIDR | Intended routed guest subnet; default `10.201.153.0/24`. |

Example controller preferences (replace paths and the UUID explicitly):

```yaml
incus:
  config_dir: /absolute/controller/eve-incus-client
  endpoint: https://192.168.1.108:8443
  image: images:ubuntu/26.04/cloud
  instance_prefix: eve-ci
  project: eve-ci
  public_key_file: /absolute/controller/eve-ci.pub
  remote: eve-incus-pool
  run_id: 01234567-89ab-4cde-8fab-0123456789ab
  ssh_private_key_file: /absolute/controller/eve-ci
```

Catalog resource defaults are 2 CPUs, 2048 MiB, network `incusbr0`, pool `default`.
Only `cpu_cores`, `memory_mb`, `network`, and `pool` machine overrides are accepted.
Project quotas are enforced by the server, not guessed by the client.

Instance registry names must use 2–31 lowercase DNS characters. The final Incus
name is `<prefix>-<registry-name>-<full-run-UUID-without-hyphens>` and must be at
most 63 characters (thus a 6-character prefix allows a 23-character registry
name). Nothing truncates the run identity. Incus `user.eve.owner` stores the
SHA-256 of run UUID and registry name; `user.eve.blueprint` hashes the complete
bootstrap and resource request. The typed identity includes endpoint, remote,
project, full resource name, and owner digest. Preserve the run UUID after a
controller crash. Eve will not adopt someone else's resource with the same name.

## Lifecycle and access outputs

Core `command-io.schema.json` defines and validates the following outputs, both
at the provider boundary and when core consumes them:

* `init`: create an owned **stopped** container with all first-boot configuration.
* `up`: initialize/reconcile the same blueprint, start, verify observed `running`.
* `start` / `stop`: idempotent for running/stopped respectively; absent start and
  absent stop fail. A request that does not reach its requested state fails.
* `down`: stop before deleting; absent deletion succeeds. Ambiguous states fail.
* `status`: JSON `{status, provider_identity}`. Status is one of `absent`,
  `creating`, `failed`, `running`, `stopped`, `unknown`. Code and status text must
  agree; Starting maps to creating, Error to failed, Frozen/other codes to
  unknown. Invalid/missing data or API failure is an error, never absence.
* `ip`: a single IPv4 text address for compatibility with existing Eve scripts.
  Only one global IPv4 in the configured NIC/subnet is accepted. Missing,
  malformed, or multiple matching addresses fail.
* `access`: JSON `{status: running, provider_identity, guest_access}`. It fails
  until both the intended address and guest SSH host identity are available.
* `plan`: validate the full request and observe without mutating it.
* `validate`: validate composition metadata offline during resolution; no credentials, public-key read, or API call.
* `connectivity`: probe the explicit project's API using the restricted identity.
* `ssh`: SSH or the standard Eve `--scp <local> <remote>` transport; supports
  recursive uploads to explicit absolute Linux paths. No Incus exec substitute
  is used for normal guest management.

The strict `guest_access` object permits **only**:

| Field | Allowed value |
| --- | --- |
| `address` | intended IPv4 address, validated against NIC/subnet by provider |
| `credential_reference` | `{type: ssh-private-key-file, path: <absolute configured path>}` |
| `host_identity` | `{mechanism: provider-authenticated-exec, fingerprint: SHA256:<43-char base64 digest>}` |
| `port` | integer 1–65535; bootstrap uses 22 |
| `protocol` | `ssh` |
| `provider_identity` | strict `{endpoint, instance_name, owner_id, project, provider, remote}` |
| `username` | valid Linux username; bootstrap uses `ubuntu` |
| `version` | integer `2` (SSH protocol) |

`provider_identity` fields are nonempty strings; endpoint is HTTPS, instance
name and remote are validated DNS labels, owner is a 64-hex digest. Here provider
is `incus`, project is `eve-ci`. Core validates these nested objects rather than
accepting an opaque JSON bag. The observation cache validates the same binding.

Creation sends cloud-init user-data, `openssh-server`, the configured public key,
locked password, disabled root/password SSH, sudo for `ubuntu`, service enablement,
limits, and explicit root/NIC devices **in the `incus init` API request**.
`--no-profiles` prevents inherited profile settings from changing that request.
Only after successful reconciliation does `up` call `incus start`. An existing
instance with a different blueprint is rejected; first-boot configuration is
never retrofitted. Infrastructure running does not claim guest bootstrap has
finished: SSH readiness/cloud-init completion are separate checks.

SSH host identity is read from `/etc/ssh/ssh_host_ed25519_key.pub` using the
authenticated, project-qualified Incus exec API. Only its fingerprint enters
the binding. A mode-0600 temporary known_hosts file binds that verified key to
the unique provider resource alias; it is removed after every SSH/SCP call.
OpenSSH uses strict checking, that host-key algorithm, the explicit private-key
reference, no ambient agent, no user SSH configuration, and no password login.
No private key is discovered by removing `.pub`, and no unrelated key is copied.
Incus subprocess transcripts are never forwarded; errors contain safe operation
names/exits only. Public-key/cloud-init payloads stay on subprocess stdin.

## Manual TLS authorization and pool preparation

Complete [the restricted TLS setup](docs/tls-setup.md) before any live run.
The runtime checks private client-directory/key permissions, an explicit private
TLS remote matching endpoint/project, client cert/key presence, and a pinned
server certificate. The official client validates TLS. Administrative verification
of the certificate's restricted authorization remains required; a remote's
project selector alone is **not** authorization confinement.

## Routed guest networking

The dedicated host is `eve-incus-pool`, LAN `192.168.1.108`, MAC
`00:A0:98:28:CC:F0`. Its `incusbr0` bridge is `10.201.153.1/24`; guests use DHCP
within `10.201.153.0/24`. OpenWrt routes that subnet via `192.168.1.108`.
IPv4 NAT is disabled, so guest addresses are reached directly through that route.
Verify IPv6 is disabled. Permit controller-to-guest TCP 22 and the necessary
DHCP/DNS/guest apt egress without opening the host API to the Internet.
A refused guest TCP 22 means routing succeeded but SSH has not started; it is
not a reason to switch to host SSH. No DHCP lease address is permanent.

## Offline and opt-in live checks

```sh
PYTHONPATH=/absolute/eve /absolute/eve/.venv/bin/python tests/test-incus
```

Normal CI runs offline tests only. `tests/test-incus-live` without `--live` prints
SKIP and contacts nothing. It requires an explicit config file, target, and test
prefix, is pinned to this pool/project, and generates a fresh full run UUID.

An administrator must preload the cloud image into `eve-ci` once:

```sh
incus image copy images:ubuntu/26.04/cloud local: --project eve-ci --alias eve-ci-ubuntu-26.04-cloud
incus image list local: --project eve-ci --format=json
```

Select its full fingerprint. The live config YAML has the **flat** configuration
shape above (no `incus:` wrapper), and sets
`image: eve-incus-pool:<full-fingerprint>`. The test refuses downloading aliases,
so it creates no image and never deletes a shared image. Use your explicit
controller SSH pair; the test generates/copies no key or client configuration.

```sh
PYTHONPATH=/absolute/eve /absolute/eve/.venv/bin/python tests/test-incus-live \
  --live --config /absolute/controller/incus-live.yaml \
  --prefix eve-it-a1 --target https://192.168.1.108:8443
```

The test creates a cloud guest, waits for authenticated SSH, verifies `ubuntu`,
cloud-init and sshd, stops/starts, waits again, and deletes. A `finally` block
verifies absence on success, failure, Ctrl-C, and SIGTERM. Temporary host-key
files are removed; no Eve registry is modified. Cleanup failure is an error,
never a claimed clean run. After lost connectivity or SIGKILL, an operator must
reconcile the printed qualified identity; no process can guarantee remote cleanup
while the remote API is unavailable.

## Operation crash boundaries and Determa

| Boundary | Observation/retry behavior |
| --- | --- |
| Before init | No resource mutation. |
| Init request in flight or response lost | List exact scoped identity; adopt only matching owner and complete blueprint. Never replace automatically. |
| Init complete, before start | Owned stopped container, complete cloud-init; `up` verifies and resumes. |
| Start/stop in flight or response lost | Observe; retry only stable running/stopped states. Starting, frozen, or inconsistent outputs cannot fake success. |
| Running, cloud-init incomplete | Infrastructure running; access/SSH fails until bootstrap produces a verified identity. No package provisioning claim. |
| Stop complete, before delete | Owned stopped container; `down` resumes deletion. |
| Delete response lost | An authoritative empty project listing establishes absence; API failures do not. |
| SSH/SCP interrupted | Temporary controller known_hosts is removed on normal unwinding; the configured credential files remain untouched. |

No Determa code, dependency, adapter, restoration, or replay path is introduced
or changed. Core's current stable running/stopped/absent observations use its
existing reconciliation events. Creating/failed/unknown are retained as typed
observations; this provider does not invent new FSM restoration/transition
semantics for them. Durable in-flight restoration and richer observation-driven
transitions remain dependent on the agreed released Determa contract. No claim
is made that unreleased Determa 0.3.0 capabilities are implemented.
