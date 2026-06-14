# eve-providers

The first-party **eve** providers, **one independent subfolder per provider**.
A provider owns infra stand-up and everything needed to reach an SSH session
(init / cloud-init / bootstrap user) — the pre-provisioning, SSH-readiness tier.

Each provider lives in its own subfolder alongside shared dispatchers that
several providers reference via relative `../_common/...` exec paths.

## Layout
```
_common/             # provider-agnostic shared command dispatchers (validate-os,
                     #   ssh, helper libs) — referenced by other providers, not a
                     #   standalone plugin (no eve-plugin.yaml)
_terraform-common/   # terraform shared dispatchers (init/plan/up/down) — same idea
local-qemu/          # the Local QEMU provider plugin
  eve-plugin.yaml    # manifest: access, bring-up commands, supports, catalog
  commands/          # exec scripts for every provider command
.github/workflows/   # CI running `eve plugin test` conformance checks
```

`_common` and `_terraform-common` are shared dispatchers, not standalone
plugins — they have no `eve-plugin.yaml` and are not run through the harness
on their own.

## Consuming a provider

Point an eve **source** at the provider subfolder you want and `eve pull` it:

```sh
eve source add local-qemu /path/to/eve-providers/local-qemu
eve pull local-qemu
```

Because each provider is sourced independently, you can pin or vendor only the
ones you need.

## CI

[`.github/workflows/conformance.yml`](.github/workflows/conformance.yml) runs
eve's `plugin-test` conformance harness against `local-qemu` on every push and
pull request. It validates the manifest against the plugin contract schema and
enforces the SSH-readiness boundary (provider owns bring-up + access).

MIT licensed.
