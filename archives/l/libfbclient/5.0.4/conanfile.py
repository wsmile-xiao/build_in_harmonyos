#!/usr/bin/env python3
"""Conan recipe — libfbclient 5.0.4 (Firebird 5.0.4 client library).

libfbclient is the Firebird client library: the Y-Valve API facade
(src/yvalve), the remote/network client (src/remote, SRP auth, ARC4) and the
shared common code (src/common) linked into a single shared object
`libfbclient.so.2` (SONAME `libfbclient.so.2`, file `libfbclient.so.5.0.4`).

Upstream build system: autotools (configure + make, builds/posix).
This recipe builds upstream's documented "client only" configuration
(`--enable-client-only`), which is exactly the client library - no engine,
no utilities - and therefore maps 1:1 to the Debian binary package
`libfbclient2`.

HarmonyOS (OHOS) adaptation notes
---------------------------------
* Source: the official release asset ships the *generated* `configure`
  script, so no autoreconf/automake/libtool bootstrap is required. The git
  tag tarball does not ship `configure`.
* E007 (triplet): `uname -s` returns `HarmonyOS`, which stock `config.guess`
  cannot parse ("unable to guess system type"). config.guess/config.sub are
  patched so the native build reports the standard triplet
  `aarch64-unknown-linux-ohos`; Firebird's own `aarch64*-*-linux*` case then
  selects PLATFORM=LINUX / MAKEFILE_PREFIX=linux_arm64 / CPU_TYPE=arm64.
  No `--build`/`--host` faking is used, so AC_RUN_IFELSE probes keep working
  (cross_compiling=no).
* E114 (umask): `config.status` creates its private temp dir with
  `umask 077` (mode 2700). On HMDFS a 2700 directory cannot be written into,
  so config.status dies with "Permission denied ... subs1.awk". The generated
  `configure` is patched to use `umask 000` (precedent: acl, abiword-plugin-*,
  air-quality-sensor).
* E002 (/tmp): OHOS mounts /tmp read-only; TMPDIR/TMP are exported to a
  writable directory through the toolchain environment so that configure,
  make and the bundled `unzip`-based tzdata step never fall back to /tmp.
* [cloop linker path] `extern/cloop/Makefile` links with `$(LIBS)` only and
  never forwards `$(LDFLAGS)`, assuming the dependencies live in the default
  system library directories. On OHOS all four dependencies come from Conan,
  so their `lib/` directories are exported through `LIBRARY_PATH` (link-time
  search path honoured by clang) instead of patching upstream makefiles.
* `--without-editline`: the aarch64 platform branch enables EDITLINE_FLG=Y,
  which forces a termcap (`tgetent`) probe. isql/line editing is not part of
  the client library, so the documented upstream switch is used instead of
  patching the configure logic.
* `make install` is NOT used: upstream's install target is broken in
  client-only mode (`builds/install/arch-specific/linux/Makefile.in` copies
  `install.sh` into the kit directory only when CLIENT_ONLY_FLG=N, yet still
  runs it) and it also copies debug symbols into `/`. This recipe packages the
  canonical install image `gen/Release/firebird`, which is exactly what the
  real Debian recipe does (`override_dh_auto_install: true`,
  `cp -a ./gen/Release/firebird debian/firebird-image`).
* All four third-party dependencies are linked statically into
  libfbclient.so (only `libc.so` remains in NEEDED), which keeps the client
  self-contained on OHOS.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfbclientConan(ConanFile):
    name = "libfbclient"
    version = "5.0.4"
    description = ("Firebird 5.0.4 client library (libfbclient.so.2: Y-Valve API, "
                   "remote/network client, common code)")
    license = "IDPL-1.0"
    homepage = "https://firebirdsql.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Conan 2: a genuinely shared library must declare "shared-library" (or a
    # "shared" option); plain "library" is rejected at package() time with
    # "Package type is 'library', but no 'shared' option declared".
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the client library itself
        # (see DEPENDENCY-REPORT: all four are consumable from the ohpcd remote).
        self.requires("icu4c/78")            # unicode/ucnv.h + -licuuc (hard configure check)
        self.requires("zlib/1.3.2")          # zlib.h at build time, dlopen("libz.so.1") at runtime
        self.requires("libtommath/1.3.0")    # -ltommath (BigInteger / SRP)
        self.requires("libtomcrypt/1.18.2")  # -ltomcrypt (TomCryptHash, WireCrypt)

    def layout(self):
        # Firebird's autotools build writes its object/image tree into the
        # source tree (gen/, temp/) and configure is not relocatable, so the
        # build must happen in-source (same pattern as adjtimex/at).
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        # R32: only Linux/OHOS are supported by this recipe.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfbclient supports Linux/OHOS, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        """E002: OHOS mounts /tmp read-only (erofs); autotools helpers fall
        back to /tmp and then fail. Prefer an already exported writable
        TMPDIR, else a per-package directory under $HOME."""
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP"):
            value = os.environ.get(var)
            if value and not value.startswith("/tmp"):
                return value
        tmpdir = os.path.expanduser("~/tmp/libfbclient")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args += [
            "--enable-client-only",
            "--without-editline",
            "--disable-rpath",
        ]
        env = tc.environment()
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        # [cloop linker path] extern/cloop/Makefile uses $(LIBS) without
        # $(LDFLAGS); expose the Conan dependency lib dirs as link search path.
        libdirs = []
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                if libdir and libdir not in libdirs:
                    libdirs.append(libdir)
        if libdirs:
            env.append("LIBRARY_PATH", os.pathsep.join(libdirs))
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Build and execute the upstream boost.test suite (client side).

        The upstream `tests` target also builds the engine test binary, which
        needs the engine and the gpre_full tool - neither exists in
        --enable-client-only mode (it dies at make.rules:102 with
        "gpre_current: No such file or directory"). The client-side binary
        `common_test` (src/common/tests + src/common/classes/tests, 13 cases)
        is therefore requested explicitly. TARGET=Release reproduces the
        Makefile's own `TARGET?=$(DefaultTarget)` (DefaultTarget is Release
        unless --enable-developer is used, which this recipe does not).
        A failing assertion fails the build.
        """
        gen_dir = os.path.join(self.build_folder, "gen")
        test_exe = os.path.join(gen_dir, "Release", "firebird", "tests", "common_test")
        self.run(f'make -f Makefile TARGET=Release "{test_exe}"', cwd=gen_dir)
        self.run(f'"{test_exe}" --log_level=test_suite --report_level=detailed', cwd=gen_dir)

    def package(self):
        # Package the canonical install image produced by make
        # (gen/Release/firebird), mirroring the real Debian recipe.
        image = os.path.join(self.build_folder, "gen", "Release", "firebird")
        copy(self, "libfbclient.so*", src=os.path.join(image, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*", src=os.path.join(image, "include"),
             dst=os.path.join(self.package_folder, "include"))
        # Client-side crypt plugin (ChaCha/WireCrypt), built in client-only mode.
        copy(self, "libChaCha.so", src=os.path.join(image, "plugins"),
             dst=os.path.join(self.package_folder, "plugins"))
        copy(self, "plugins.conf", src=image, dst=self.package_folder)
        # ICU time zone data used by the client (Firebird looks for
        # $(root)/tzdata next to the library).
        copy(self, "*", src=os.path.join(image, "tzdata"),
             dst=os.path.join(self.package_folder, "tzdata"))
        copy(self, "IDPL.txt", src=os.path.join(self.build_folder, "doc", "license"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fbclient"]
        self.cpp_info.set_property("cmake_file_name", "libfbclient")
        self.cpp_info.set_property("cmake_target_name", "libfbclient::libfbclient")
