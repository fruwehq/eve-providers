# Manual Remote Login feasibility proof (not a live provider test)

Do not run this automatically. No host was accessed or configured for this change.
The administrator must approve the specific Mac, account, signed UTM build,
explicit controller key and host pin before this procedure. A successful probe
does not authorize lifecycle operations or resolve clone atomicity.

## Preparation on the Mac

1. Install the selected signed UTM.app and record its exact version/build and
   macOS version. Record Apple Silicon architecture using built-in `uname -m`.
   Check its signature with built-in `codesign --verify --deep --strict` against
   the approved absolute app path. This is a signature integrity check, not a
   substitute for independently verifying the trusted publisher/build.
2. Log in to the intended UTM owner's GUI session and launch UTM. Record whether
   the controller account is this owner or a distinct dedicated account. A
   dedicated non-admin account that owns a dedicated UTM GUI session is preferable
   to controlling a personal owner's session, if supported. Do not grant sudo.
3. Enable Remote Login only for the chosen account through macOS Settings.
   Keep password/key policy, PAM, TCC and host-key verification intact. Do not
   enable broad Full Disk Access as an assumed workaround. Obtain the Mac's
   Ed25519 SSH host public key and SHA256 fingerprint through an independent
   trusted administrative channel; never trust a network key scan alone.
4. Install a root-owned, non-account-writable, read-only probe at an explicit
   absolute path such as `/usr/local/libexec/eve-utm-probe`. It may use `/bin/sh`
   and invoke only the configured bundled absolute `utmctl` path. The following
   minimal example assumes UTM.app was explicitly installed at `/Applications`;
   change that literal for the approved installation. It is not a provider or a
   general command dispatcher:

   ```sh
   #!/bin/sh
   set -eu
   case "${SSH_ORIGINAL_COMMAND-}" in
     eve-utm-probe-v1) ;;
     *) exit 64 ;;
   esac
   /Applications/UTM.app/Contents/MacOS/utmctl version
   /Applications/UTM.app/Contents/MacOS/utmctl list
   ```

   Never use `eval`, `sh -c "$SSH_ORIGINAL_COMMAND"`, argument passthrough,
   writable executable parents, or a symlink to an unapproved executable. Ensure
   this protocol has no create/start/delete/file/guest-exec capability.
5. Authorize **only the supplied public controller key** for this probe. The
   key's authorized_keys prefix is:

   ```text
   restrict,command="/usr/local/libexec/eve-utm-probe" ssh-ed25519 <supplied-public-key> <label>
   ```

   Verify the installed macOS OpenSSH supports `restrict` and that it prohibits
   agent/port/X11 forwarding, PTY and user rc execution. If unsupported, stop and
   review a fully equivalent explicit restriction set before proceeding. Protect
   authorized_keys from untrusted edits; a forced command is a key-scoped boundary,
   not a sandbox against a malicious host account owner. No private key is copied
   to the Mac and no new unrelated key is generated or discovered.

## Controller probe

Use only explicitly provided values. `CONTROL_KEY_FILE` is a reference supplied
by the administrator, not a search of controller home files. `KNOWN_HOSTS_FILE`
must contain the independently verified public key for the exact host/port, with
0600 permissions; verify its fingerprint against the approved pin first.

```sh
ssh -F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes \
  -o IdentityAgent=none -o AddKeysToAgent=no -o ForwardAgent=no \
  -o ClearAllForwardings=yes -o RequestTTY=no -o PermitLocalCommand=no \
  -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \
  -o HostKeyAlgorithms=ssh-ed25519 \
  -o GlobalKnownHostsFile=/dev/null \
  -o UserKnownHostsFile="$KNOWN_HOSTS_FILE" \
  -o ConnectTimeout=10 -i "$CONTROL_KEY_FILE" -p "$HOST_PORT" \
  -l "$HOST_ACCOUNT" -- "$HOST_ADDRESS" eve-utm-probe-v1
```

Bound execution externally (for example Python `subprocess.run(..., timeout=30)`
on the controller). macOS itself need not have Python or a `timeout` executable.
Save exit code and sanitized stdout/stderr without account names, VM inventory,
key material or private paths in public artifacts. Inventory can be sensitive.
On AppleEvents denial or a hang, stop; do not treat an empty table as absence or
a zero exit code as proof if errors were emitted. Interactive authorization, if
requested, must be approved by the Mac administrator for the exact caller/UTM
pair. Record the permission scope and retry without relaxing restrictions.

## Required proof matrix

* Verify version and actual known UUIDs match the same logged-in GUI owner session,
  including when the SSH account is distinct. No adoption by display name.
* Reconnect and repeat after UTM restart and after locking/unlocking the owner
  desktop. Record logout/reboot behavior as unavailable if GUI login is required;
  do not silently launch a separate app/session.
* Try an unallowlisted command and ensure rejection occurs before UTM invocation.
  Confirm forwarding, PTY and arbitrary shell access are unavailable to this key.
* Confirm wrong host key, wrong controller key and an unauthorized account fail.
* Test no active owner session and an unavailable app without mutating guests;
  report unavailable/unknown, never absent. Do not require logged-out operation
  unless UTM documents support.

Pass means repeatable read-only access to the intended session under the actual
restricted key/account/build. A local Terminal success, user anecdote, permission
prompt, or fake host test is insufficient. Failure requires reporting exact
versions, session arrangement, sanitized error and smallest failing command to
the upstream request. Do not build a daemon or session-hopping workaround.

## Cleanup and later live-test gate

Remove the temporary probe authorization/artifact when the proof is finished;
delete only the files/key entry installed for this proof. Do not remove unrelated
authorized keys, host keys, templates or UTM configuration. No VM/image/key was
created by the probe. Do not claim cleanup after unavailable access or SIGKILL.

A provider live test is deferred until both host feasibility and authenticated
clone recovery are solved. It will require an explicit target, pinned immutable
prepared template, unique ownership token, bounded cleanup, per-clone guest
identity, guest SSH command execution, stop/start and delete. It must remain
opt-in and leave any unconfirmed cleanup identity visible. This document is not
an implementation or a passing result of that future test.
