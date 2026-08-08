# E261: Retain the previous output when rollback sees an untrusted target

## Symptom

A signed artifact is exchanged into its public destination, but a concurrent
writer replaces that destination before rollback. Rollback then reports an
identity or symlink error, and unconditional temporary cleanup removes the
backup path that still contains the previous user output.

## Scope

Use this pattern for finalizers and transactional packagers that publish by
same-directory exchange and keep the old target in a temporary path until the
new target and its parent directory are durable.

## Root Cause

After exchange, the public target and the backup path have different duties:
the target should contain the signed postimage, while the backup carries the
preimage. Checking only one side, catching only `OSError`, or verifying the
committed file through a later pathname read leaves identity gaps. A symlink,
non-regular file, same-byte different inode, or domain identity error can skip
recovery and let path-only cleanup delete the preimage.

## Fix

1. Preserve and verify the preimage and signed-postimage identities.
2. Treat both OS failures and domain identity errors as recovery conditions.
3. Leave an unrecognized concurrent target untouched.
4. Move the verified preimage to a unique recovery path with a no-replace
   rename and verify it again after the move.
5. After directory `fsync`, reopen the committed target with no-follow
   semantics and bind its identity and hash to the same descriptor.
6. Clean only objects whose current identities were recorded by this
   invocation.

## Forbidden Shortcuts

- Do not exchange an unrecognized target back into a temporary path.
- Do not catch only `OSError` around a domain identity checker.
- Do not unlink temporary pathnames without matching recorded identities.

## Validation

Inject regular replacement, symlink replacement where supported, explicit
identity failure, and same-byte different-inode replacement after exchange.
Every case must fail closed, preserve the concurrent target, and retain the old
output exactly once under a recovery name.

GraalVM 25.0.3 implements this in
`archives/g/graalvm/25.0.3/files/native_image_finalizer.py`; PR #3928 exercises
rollback, output CAS, cleanup CAS, finalizer CAS, and post-commit recovery.

## Related Knowledge

- E260 binds interpreter validation to execution; this entry binds publication
  and rollback to the identities accepted by the transaction.
