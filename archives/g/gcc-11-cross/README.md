# GCC 11.5.0 Cross-Compiler (arm-none-eabi, C and C++)

GNU GCC 11.5.0 cross-compiler package for HarmonyOS PC (aarch64-linux-ohos).
The compiler is hosted on OHOS and targets the arm-none-eabi bare-metal
platform, emitting objects and static libraries for ARM microcontrollers. Both
the C and the C++ front ends are built, so `arm-none-eabi-gcc` and
`arm-none-eabi-g++` are provided together with `arm-none-eabi-cpp`,
`arm-none-eabi-c++`, `arm-none-eabi-gcc-11.5.0`, the GCC plugin wrappers
(`arm-none-eabi-gcc-ar`, `arm-none-eabi-gcc-nm`, `arm-none-eabi-gcc-ranlib`)
and the coverage tools (`arm-none-eabi-gcov`, `arm-none-eabi-gcov-dump`,
`arm-none-eabi-gcov-tool`).

The target is configured with `--enable-languages=c,c++`,
`--enable-multilib`, `--with-arch=armv7-a`, `--with-newlib`,
`--without-headers` and `--disable-bootstrap`. Bootstrap stages, sanitizers,
OpenMP, quadmath and Graphite/ISL are intentionally excluded so that the
package fits the CI build budget. The single-thread model
(`--disable-threads`, newlib without pthreads) is used deliberately: bare
`arm-none-eabi` newlib never defines `_POSIX_THREADS`, so a posix thread model
would only make libstdc++ select `gthr-posix.h` and require pthread
declarations the target does not provide.

With `--enable-multilib` the default `armv7-a` (A-profile, where `dmb` exists
so `__sync_synchronize` compiles to an instruction) is what links by default.
M-profile code such as `-mcpu=cortex-m3/-m4` or `-march=armv7-m` *compiles*
fine, but its objects cannot be linked against this package's libraries: the
upstream `t-arm-elf` `MULTILIB_MATCHES` maps those options onto the `thumb`
multilib directory, which here holds A-profile code, so `ld` reports
`conflicting architecture profiles M/A`. A true M-profile build requires
rebuilding the target libraries with
`--with-multilib-list=aprofile,rmprofile` and without `--with-arch=armv7-a`.

The recipe uses only the official GNU release tarballs (GCC plus the bundled
GMP/MPFR/MPC, and newlib), each pinned by `sha256` in `conandata.yml`. Downloads
go through a mirror list — the campus mirrors first, then `ftp.gnu.org` last —
because direct large-file transfers to `ftp.gnu.org` time out from the CI host;
the checksum guarantees the artefact is the official one regardless of which
mirror served it.

The compiler needs its companion target binutils package
`arm-none-eabi-binutils/2.46.1` on `PATH` to assemble and link; the assembler
and linker are not part of this package.

## Usage

Install both packages, then invoke the cross-compiler driver. The assembler and
linker are resolved from the companion `arm-none-eabi-binutils` package on
`PATH`; without it the driver's exec-prefix shims cannot find
`arm-none-eabi-as`/`ld` and compilation stops at the assemble step.

```sh
conan install --requires=gcc-11-cross/26 --requires=arm-none-eabi-binutils/2.46.1
arm-none-eabi-gcc --version
arm-none-eabi-g++ --version

# C, default target (armv7-a): compile and link
arm-none-eabi-gcc -c main.c -o main.o
arm-none-eabi-gcc main.o -o main.elf

# C++, linked against the packaged libstdc++
arm-none-eabi-g++ -std=c++17 -c app.cpp -o app.o
arm-none-eabi-g++ app.o -o app.elf

# Free-standing / M-profile compilation (produces objects; linking them is not
# supported by this build -- see the multilib note above)
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -c main.c -o main-m4.o
```

Code generated without an explicit `-mcpu`/`-march` links against the packaged
libraries. Passing `-mcpu=cortex-m3/-m4` or `-march=armv7-m` is fine for
compilation, but such objects cannot be linked here because the `thumb`
multilib holds A-profile code.

## References

- https://gcc.gnu.org/
- https://ftp.gnu.org/gnu/gcc/
