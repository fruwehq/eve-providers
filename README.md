# eve-providers

The first-party **eve** providers, **one independent subfolder per provider**.
A provider owns infra stand-up and everything needed to reach an SSH session
(init / cloud-init / bootstrap user) — the pre-provisioning, SSH-readiness tier.

> **Status: scaffold.** Providers are extracted here from the `eve` monorepo in
> v4.0 Phase 3, each scaffolded from `eve-plugin-template`. See the v4.0 roadmap.

## Intended layout
```
aws/  gcp/  vultr/  truenas/  raspberry-pi/  local-qemu/
```
Each subfolder is independently sourced, versioned, and CI'd against the eve contract.

MIT licensed.
