# log4cpp 1.1.4 OpenHarmony Adaptation Notes

## Scope

- Build the upstream CMake target as a static `log4cpp` library.
- Generate the Autotools-derived `include/log4cpp/config.h` in the Conan recipe
  because upstream CMakeLists.txt does not run `configure`.
- Package headers and `liblog4cpp.a` for downstream consumers such as
  `fastnetmon`.

## Disabled / Not Included

- Syslog, remote syslog, and SMTP support are disabled in the generated config
  header to keep the first package focused on local logging APIs and avoid
  assuming OHOS syslog/socket mailer behavior.

## Validation

The official SourceForge tarball was downloaded and SHA256-verified as
`696113659e426540625274a8b251052cc04306d8ee5c42a0c7639f39ca90c9d6`.
It contains a single `log4cpp/` top-level directory. The recipe explicitly
uses `strip_root=False`, so `CMakeLists.txt`, `include/`, and the generated
`include/log4cpp/config.h` are addressed under
`self.source_folder/log4cpp`. This was verified in the Conan source cache
before running the consumer test.

Native validation environment:

- Ubuntu 26.04 LTS on WSL2, x86_64; Linux 6.6.87.2-microsoft-standard-WSL2
- GCC 15.2.0, GNU Make 4.4.1, CMake 4.2.3, Conan 2.31.1

The shipped Autotools build system was configured and executed from the
official 1.1.4 source tree:

```bash
./configure --disable-shared --enable-static
make -j2 check
```

Automake reported `TOTAL: 12`, `PASS: 12`, `FAIL: 0`, `SKIP: 0`,
`XFAIL: 0`, `XPASS: 0`, and `ERROR: 0`. The twelve entries are exactly the
ones registered in `tests/Makefile.am`; no upstream test was modified.

The final Conan consumer smoke test was executed from this recipe with:

```bash
conan create archives/l/log4cpp/1.1.4 --build=missing -s build_type=Release
```

It built and packaged `liblog4cpp.a`, resolved `log4cpp::log4cpp` via
`find_package(log4cpp CONFIG)`, and ran the consumer executable successfully.
The executable reported `Consumer smoke summary: 4/4 passed` for Category
priority filtering, OstreamAppender with BasicLayout, NDC push/pop, and the
Category stream API.

OpenHarmony CI #11624 also passed L0, L1, and the Conan test package. The
native results above are the evidence for the upstream runtime test count;
cross-built targets are not represented as native runtime results.
