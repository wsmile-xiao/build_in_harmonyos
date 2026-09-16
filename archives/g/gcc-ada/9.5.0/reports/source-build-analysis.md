# GCC Ada/GNAT 9.5.0 source and build analysis

## Source provenance

- Official archive:
  `https://ftp.gnu.org/gnu/gcc/gcc-9.5.0/gcc-9.5.0.tar.xz`
- Size: 72,462,752 bytes
- SHA256:
  `27769f64ef1d4cd5e2be8682c0c93f9887983e6cfd1a927ce5a0a2915a95cf8f`
- Build system: GCC top-level Autoconf, Ada language make fragments, and the
  `libada` target-library subdirectory.

GCC's official prerequisite script selects GMP 6.1.0, MPFR 3.1.4, and MPC
1.0.3. The recipe downloads those exact sources into the GCC tree.

## Bootstrap graph

```text
checksum-pinned Alpine AArch64/musl GNAT 9.3 seed
  -> seed Ada compile-only probe against the OHOS SDK sysroot
  -> GCC 9.5 common backend + C frontend + gnat1 + GNAT tools
  -> target libgcc
  -> target libgnat/libgnarl + Ada include/ALI files
  -> relocatable packaged GCC/GNAT toolchain
  -> consumer compile, bind, link, sign, tasking execution
```

Clang and the published `gcc/9.5.0` package cannot replace the seed: neither
contains `gnat1`, and GCC's Ada make fragments compile Ada sources with an
existing GNAT compiler and invoke `gnatmake`, `gnatbind`, and `gnatlink`.

## HarmonyOS platform baseline

Package-owned copies of the published C compiler transforms provide:

- `aarch64-linux-ohos` config.sub/configfsf.sub handling;
- mapping the OHOS target to GCC's AArch64 musl configuration;
- the `__OHOS__` target builtin;
- HMDFS-compatible configure umask behavior;
- OHOS SDK sysroot and target header discovery;
- compiler wrappers that sign freshly linked host executables;
- signing barriers before generated GCC tools execute;
- a relocatable installed GCC driver wrapper.

The Ada recipe extends the baseline with seed signing/self-test and a separate
libada build/install phase.

## Configure and phase boundaries

The native target is configured with:

```text
--enable-languages=c,ada
--enable-threads=posix
--enable-libada
--disable-bootstrap
--disable-multilib
--disable-shared
--disable-lto
--disable-plugin
--disable-nls
--without-isl
--with-sysroot=<OHOS SDK sysroot>
```

The recipe deliberately separates `all-gcc`, `all-target-libgcc`, and
`all-target-libada`, signing the build tree between phases. That placement is
required because HarmonyOS may reject a generated host tool before a final
package-stage signing pass can run.

## Runtime selection and risks

GCC 9.5's Ada `Makefile.rtl` matches `aarch64-linux-ohos` through its AArch64
Linux rule. It selects the POSIX/Linux tasking runtime and `-lpthread -lrt`.
Generated `System.OS_Constants` values reduce hard-coded pthread-layout risk,
but the device build/run must still probe:

- `pthread_rwlockattr_setkind_np`;
- weak affinity APIs;
- `sigaltstack`;
- clock APIs;
- the known OHOS `pthread_cancel` omission;
- task creation, rendezvous, protected objects, and exception propagation.

## Required final artifacts

- `bin/gcc`, GNAT driver and utility programs;
- `libexec/gcc/<target>/9.5.0/gnat1`;
- target `libgcc.a`, `libgnat.a`, and `libgnarl.a`;
- versioned `adainclude` source files and `adalib` ALI/object files;
- license texts and relocatable compiler search paths.

The final package must contain none of the Alpine seed files.
