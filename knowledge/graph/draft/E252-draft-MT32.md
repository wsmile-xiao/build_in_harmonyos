# E252: Test asset-gated libraries before loading external assets

> Contributor: 1catmint1 | Status: DRAFT | Created: 2026-07-21

## Symptom

An installed library passes a consumer that reads its version, but a downstream
application fails as soon as it creates the main context or queries supported
assets. The full workload cannot be placed in the package test because it needs
user-supplied ROMs, firmware, models, or other data that the package must not
redistribute.

## Root cause

The external asset requirement applies to the complete workload, not
necessarily to every public API. Many such libraries expose an asset-free
control plane: capability inventories, context allocation and cleanup,
configuration selection, state queries, and a documented error when a caller
tries to start without the required assets.

A version-only test leaves that control plane unexecuted. Supplying invented,
truncated, or unrelated data is not a valid replacement because it exercises a
different input contract and may blur provenance or licensing boundaries.

## Fix

Use one real installed-package consumer to exercise the pre-asset lifecycle:

1. Query the public version and supported asset or machine inventories.
2. Create the primary context through the installed public API.
3. Verify its initial inactive state.
4. Change and read back a reversible configuration option.
5. Attempt the documented start operation without external assets and require
   the precise missing-asset result.
6. Confirm the failed start did not change the context to an active state.
7. Release the context and exit nonzero on any mismatch.

Run this consumer under the package manager's generated runtime environment.
The process is one logical test flow. Its checks remain internal assertions,
and repeating the same flow for shared and static packages does not increase
the logical count.

## Validation

For mt32emu 2.7.1, the consumer checks version and non-empty machine/ROM
inventories, creates a context, selects the floating-point renderer, requires
`MT32EMU_RC_MISSING_ROMS` from an open attempt without ROM images, confirms the
synth remains closed, and frees the context. A strict native build executed the
flow successfully, while OHOS/AArch64 shared and static builds both compiled
and linked the same source. Target execution remains a separate fresh-W3 gate.

This method does not claim audio synthesis without compatible control and PCM
ROM images. It provides meaningful package and lifecycle coverage while
preserving that boundary.
