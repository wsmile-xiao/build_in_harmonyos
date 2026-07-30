# E242: Preserve operation errors across resource cleanup

> Contributor: 1catmint1 | Status: DRAFT | Created: 2026-07-20

## Symptom

A stateful C API opens a resource successfully, then a later read, write,
parse, encode, or decode operation fails. The diagnostic still prints zero or
an unrelated close error. Another implementation closes the resource first
and then reads its error field, introducing a use-after-free.

## Root cause

Many C APIs have more than one error channel. Open and close functions can use
an integer out-parameter, while operations on a live resource store their last
error in the handle or context. The open out-parameter remains a successful
zero after a later operation failure. Closing can overwrite a reused
out-parameter and can free the object that owns the operation error.

## Fix

1. Read the public header and implementation to identify the owner of errors
   for open, live-handle operations, and close.
2. Keep separate variables for the open and close out-parameters.
3. When an operation returns failure, read or snapshot the documented handle
   error before calling close.
4. Close and clean up with its own error variable, without replacing the
   original diagnostic.
5. Add deterministic failure consumers in separate processes. Require a
   successful open, an operation failure, a nonzero handle error, and an
   unchanged successful open error.

Do not infer this contract from one successful round trip. Do not fabricate a
failure with a mock when the real public API can reach the state safely.

## Validation

giflib 6.1.3 uses `GifFileType::Error` for failures after a file has opened,
while `EGifOpenFileName`, `DGifOpenFileName`, and the close functions expose
separate integer out-parameters. Two independent consumers exercise the real
library: one writes a second screen descriptor after a successful first write;
the other slurps a GIF truncated after a valid header, logical screen, color
table, and image descriptor. Both operations fail with a nonzero live-object
error while the open out-parameter remains zero. A third process preserves the
normal encode/decode round trip.

## Boundary

This pattern applies only after the API contract confirms distinct error
owners. APIs with a single thread-local or return-code error channel require a
different test oracle.
