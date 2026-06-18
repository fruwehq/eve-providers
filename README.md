# eve-providers

The first-party **eve** providers, **one independent subfolder per provider**:
`aws`, `gcp`, `vultr`, `truenas`, `raspberry-pi`, `local-qemu`, and `docker`.

A provider owns infra stand-up and everything needed to make an instance
**manageable** (init / cloud-init / bootstrap user; SSH, or `docker exec` for the
docker provider) — the pre-provisioning tier. Each lives in its own subfolder
alongside shared dispatchers that several providers reference via relative
`../_common/...` exec paths. This repo also ships `_catalog-base/` (shared OS
identity rows + inits) discovered alongside the plugins.

## Layout
```
_common/             # provider-agnostic shared dispatchers (validate-os, ssh, libs)
                     #   — referenced by providers, not a standalone plugin
_terraform-common/   # terraform shared dispatchers (init/plan/up/down) — same idea
_catalog-base/       # shared OS identity rows + inits (catalog-base contribution)
<provider>/          # e.g. aws, gcp, vultr, truenas, raspberry-pi, local-qemu, docker
  eve-plugin.yaml    # manifest: access, bring-up commands, supports, catalog
  commands/          # exec scripts for every provider command
.github/workflows/   # CI running `eve plugin test` conformance checks
```

`_common` / `_terraform-common` are shared dispatchers, not standalone plugins
(no `eve-plugin.yaml`); they are not run through the harness on their own.

## Use it

This is an external plugin source — nothing is bundled in eve core:

```sh
eve plugin source add --recommended eve-providers
eve pull
```

(or add it from the eve TUI's plugin screen — press `g`). It's in eve's
recommended-source catalog; `eve pull` materializes the providers so eve
discovers them — you don't clone or vendor anything by hand. Pair with
[eve-packages-linux](https://github.com/fruwehq/eve-packages-linux) /
[eve-plugins-ai](https://github.com/fruwehq/eve-plugins-ai) for packages.

## CI

[`.github/workflows/conformance.yml`](.github/workflows/conformance.yml) runs
eve's `plugin-test` conformance harness against **every** provider on push and
pull request — validating each manifest against the plugin contract and enforcing
the manageable boundary (provider owns bring-up + access). It also runs the
`tests/test-host-resolver` OS-portability test.

MIT licensed.
