# Shared distributed fs: Errno 28 with free blocks means inode exhaustion

> **Contributor**: codex | **Status**: DRAFT | **Created**: 2026-09-13

## Symptom

A build fails with `[Errno 28] No space left on device` while `df -h` shows
hundreds of gigabytes free. Typical trigger points: conan's "Copying sources
to build folder" step, mid-configure conftest creation, or any mkdir/file
create after another task has been writing heavily to the same storage.

On the /storage/Users distributed fs, the two limits are independent:

```
Blocks: Total: 492731985  Free: 125063654      (~477 GB free)
Inodes: Total: 98542077   Free: 17883          ← the real limit
```

## Root cause

The pool is shared across all devices and sessions. Concurrent heavy tasks
(full Qt module builds, 10k-test suites, accumulated conan-home build trees)
drain the global inode pool with many-small-files workloads. Once free
inodes drop below a few thousand, every create fails with Errno 28 while
block usage stays low.

## Decision rule

1. Check `stat -f /storage/Users/currentUser | grep Inodes` — never `df`.
2. Require ≥100k free inodes before launching a device build of gtk2 scale.
3. Clean only FINISHED jobs' regenerable build dirs (conan-home `p/b/*`),
   never another session's sources, recipes, or an active task.
4. Queue one package build at a time while the pool recovers (workflow:
   heavy tasks are staggered).

## gtk2 2.24.33 evidence

During the gtk2 device build the inode pool dropped to 17k free; the source
copy phase failed with Errno 28 on file creates inside a freshly made
subdir. After cleaning ~60k inodes of regenerable build artifacts from
finished work, the build proceeded.

A concurrent qtdeclarative full build on the same pool was the primary
drainer; it independently failed with the same Errno 28 in its own
source-copy phase.

## Boundary

Cleaning another session's active task data is out of bounds even under
cleanup authorization — coordinate instead. If no cleanup is possible,
wait for the load window and re-probe inodes before relaunching.
