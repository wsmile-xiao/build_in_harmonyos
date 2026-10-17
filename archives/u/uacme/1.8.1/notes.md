# uacme 1.8.1 - adaptation notes (OpenHarmony PC)

## Upstream identity

- Repository: https://github.com/ndilieto/uacme (tag `v1.8.1`,
  commit `b024743546c3`; annotated tag object `9b1d501ccee9`)
- Language: C99 only (`configure.ac:34-38` requires a C99 compiler; 17 `.c` +
  12 `.h`, zero C++ files)
- Build system: GNU Autotools (`configure.ac` + `Makefile.am`)
- License: GPL-3.0

### Which tarball is the upstream source

Upstream publishes **no GitHub release assets** - `GET /repos/ndilieto/uacme/releases`
returns `[]`, so `releases/download/v1.8.1/uacme-1.8.1.tar.gz` is a genuine 404.
`README.md:51-58` documents the `upstream/latest` branch as the pristine
release channel, tagged `upstream/x.x.x`. Two distinct archives exist:

| | Archive | sha256 | Ships `configure` | Version resolves to |
|---|---|---|---|---|
| A | `refs/tags/v1.8.1` | `d0f537661c38731d193f110e85ab20e541ca82698863dc4ab36fe518530e09e1` | no | **UNKNOWN** |
| B | `refs/tags/upstream/1.8.1` | `de7588577f8298dcb0d42dfaa9452a918fa692c4e165060207ac22f72fb0425d` | yes | `1.8.1` |

Every non-generated source file is byte-identical between A and B. Archive A
cannot be built correctly as-is: `configure.ac:19` is
`AC_INIT([uacme], [m4_esyscmd([build-aux/git-version-gen .tarball-version])])`,
and A has neither `.tarball-version` nor git metadata, so `git-version-gen`
prints `UNKNOWN`.

This recipe consumes **B**. SHA-256 verified by re-download (byte-identical)
and the tarball is identical to the GitHub trees API listing for the tag.
The URL host is `codeload.github.com`, GitHub's own archive service; the
`github.com/.../archive/...` redirect form is intermittently unreachable from
this farm.

## Dependencies

| Dependency | Requirement | Evidence |
|---|---|---|
| libcurl | >= 7.38.0 **with HTTPS**, mandatory | `configure.ac:89-96,99,110-115,137-138` |
| TLS backend | exactly one of GnuTLS / OpenSSL / mbedTLS | `configure.ac:144-177` |
| C99 compiler | required | `configure.ac:34-38` |
| asciidoc/a2x | only for docs; **hard error** if absent | `configure.ac:388-398` |
| libev | optional; bundled copy at `libev/` is used by default | `configure.ac:377-380`, `Makefile.am:30-39` |

Backend selection in this recipe: **OpenSSL**. GnuTLS is the upstream default
only because it is chosen when neither mbedTLS nor OpenSSL is requested
(`configure.ac:156-160`); OpenSSL is the backend this farm already publishes
(`openssl/3.5.6.1`). wolfSSL is not supported by uacme at all.

`--with-libcurl=PATH` and `--with-openssl=PATH` bypass the pkg-config driver,
so the Conan packages do not need to ship `.pc` files advertising HTTPS in
`supported_protocols`.

## ualpn

`ualpn` is the optional tls-alpn-01 responder. It is **optional** - every rule
is wrapped in `if ENABLE_UALPN` (`Makefile.am:23-40,64-66,72-87`) and
`--without-ualpn` is supported (`configure.ac:318-320`) - but it is **enabled by
default** (`configure.ac:313-317`). This recipe leaves it at the default, so
both `uacme` and `ualpn` are built. It needs `netinet/tcp.h`, `sys/mman.h`,
`sys/resource.h`, `sys/uio.h`, `sys/un.h`, `mmap`, `sem_init` and libev; the
bundled libev copy is used unless a system libev is found.

## Upstream tests: 0

`make check` exists as a target but runs **nothing**:

- `Makefile.am` declares no `TESTS`, no `check_PROGRAMS`, no `check_SCRIPTS`,
  no `TEST_EXTENSIONS`; the generated `Makefile.in` contains only
  `check-am: all-am`.
- There is no `tests/` or `t/` directory anywhere in the tree.
- No CI configuration exists in any upstream branch (a sweep of the trees API
  over `v1.8.1`, `master`, `upstream/latest`, `debian/master` finds no
  `.github/`, no test directory, no spec file).
- The only `.PHONY` target beyond the standard automake set is `valgrind`
  (`Makefile.am:102-106`), a maintainer memory-check that takes manually
  supplied arguments and is not part of `make check`.

The recipe still invokes `make check` so the upstream entry point is visible in
the build log, but it is recorded honestly here as executing zero assertions.

## `-V` exits non-zero by design (both binaries)

Neither binary returns 0 from a version query. This is upstream behaviour, not
a packaging defect, and the test asserts on the printed version instead:

| Binary | `-V` exit | Evidence |
|---|---|---|
| `uacme` | 2 | `main()` opens with `int ret = 2` (`uacme.c:1536`); `case 'V'` prints the banner and `goto out` (`uacme.c:1701-1703`), which reaches the shared `exit(ret)` (`uacme.c:2076`) without ever resetting `ret`. `ret` is only set to 0 once a real ACME operation succeeds (`uacme.c:1903-2043`). |
| `ualpn` | 1 | `case 'V'` calls `cleanup_and_exit(0, EXIT_FAILURE)` (`ualpn.c:4318-4320`). |

## ualpn needs an explicit include path for the bundled libev

`ualpn.c:52` includes `<ev.h>`, and `Makefile.am:32` supplies it through a
bare, build-dir-relative `ualpn_CPPFLAGS += -Ilibev`. Conan configures
out-of-tree (VPATH), where automake's dirstamp rule creates an **empty**
`libev/` directory in the build tree (`Makefile:544-549`), so the flag points
at nothing and the compile fails with `'ev.h' file not found` even though the
bundled copy ships complete in the tarball (`libev/ev.c`, `libev/ev.h`,
12 files, and `noinst_LIBRARIES = libev.a` is active because
`ENABLE_LIBEV_TRUE` is set in `config.status`).

The recipe appends the source-tree directory to the compile flags
(`tc.extra_cflags`), which builds `ualpn` and its `libev.a` from the bundled
copy without patching upstream. This is also the correct fix for a plain
out-of-tree build on any platform, not an OHOS-specific one.

## Offline runtime verification

`uacme -V` prints the version and, at startup, calls
`curl_version_info(CURLVERSION_NOW)` (`uacme.c:1571-1574`), so a successful
`-V` is a genuine check that the executable linked and initialised both libcurl
and the OpenSSL backend. This is what `test_package` runs on the device.

Everything else uacme does is inherently online: `new`, `issue`, `update`,
`deactivate`, `newkey`, `check` and `revoke` all require a live ACME server,
`ualpn` needs to bind port 443, and dns-01 requires real DNS updates via
`nsupdate`. None of that is executable offline and none of it is covered by an
upstream test suite.
