# Decision record: UTM remains the sole backend abstraction

Status: phase-one gated design; no provider/host artifact registered or installed.

| Alternative | Decision and reason |
| --- | --- |
| Auto-login assumptions | Rejected. An existing verified owner GUI session is a proof precondition, not an instruction to weaken login security or assume availability after reboot. |
| Custom daemon / session broker | Rejected. Do not create a large remote service or disguise an unsupported AppleEvents boundary. Request upstream support. |
| Direct Apple Virtualization | Rejected. UTM owns its Apple backend; Eve is not a second virtualization implementation. |
| Direct QEMU | Rejected. UTM owns its QEMU backend; no alternative CLI/backend, fork or graphics stack is added. |
| TCC bypass / session hopping | Rejected. No disabled TCC, broad Full Disk Access workaround, sudo, `launchctl asuser` or GUI-session LaunchAgent bridge. |
| Undocumented UTM Server protocol | Rejected. Interactive/VDI functionality is not an authenticated supported lifecycle API for both backends. |

A static forced-command shell/AppleScript artifact is only **eligible for later
review** after session proof and source-proven strict ID behavior. It must invoke
documented UTM scripting with fixed versioned operations, explicit credentials
and pinned host identity; exact object-ID checks and effects must not fall back to
names. It cannot become a general command/script evaluator, read arbitrary files,
accept arbitrary QEMU arguments or bypass session permissions. It does not solve
atomic clone recovery, immutable provenance or guest bootstrap by itself.

No ledger, wrapper serialization, inventory-diff/name adoption/deletion, ambient
keys, copied template host keys, fake success or provisional Determa API is
accepted. A fail-closed manual-reconciliation result is honest but cannot satisfy
the required recoverable disposable lifecycle.
