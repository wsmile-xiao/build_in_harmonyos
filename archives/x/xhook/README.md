# xhook

[iQIYI xhook](https://github.com/iqiyi/xhook) — a PLT/GOT hook library for
Android ELF executables and shared libraries, written in C. It redirects
PLT (procedure linkage table) calls, e.g. making every `malloc()` call from
a chosen `.so` go to your replacement function instead.

OHOS port notes: android liblog is bridged to HiLog (`libhilog_ndk.z.so`),
the JNI bridge is compiled out, and the hook engine itself is unchanged.
See the version directory's `notes.md` for details.
