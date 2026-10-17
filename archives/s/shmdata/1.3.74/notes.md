# Shmdata 1.3.74 on HarmonyOS PC

The target's seccomp filter terminates `shmget`/`semget` with SIGSYS. The recipe replaces the four private SysV backend files only in the Conan build-source copy: named POSIX shared-memory segments carry frames, and a process-shared pthread mutex/condition protects the two-counter writer/readers protocol. The public `Writer`, `Follower`, `sysVShm` and `sysVSem` class APIs remain intact.

The resize handoff requires a bounded attach retry: a reader can receive an update between `shm_unlink` of the old segment and creation of the next. The reader passes the expected frame size and refuses an undersized mapping. This is not a retry on SIGSYS; no SysV syscall remains in the adapted backend.

The registered 16 core CTest entries run unfiltered. GStreamer and Python integrations are optional and disabled with their corresponding components. Upstream tests retain their assertions; the recipe changes only paths from read-only `/tmp` to task-local `./sock-*`, repairs two nonstandard `duration_cast` calls and uses the system shell for the two scripted tests. Installed commands `sdflow` and `sdcrash` are declared at software level in `commands.json`.

The frozen target run and path B knowledge boundary are recorded in the PR description and the associated Issue. The reusable implementation insight is maintained in `knowledge/drafts/E6404-draft-8B7F`.
