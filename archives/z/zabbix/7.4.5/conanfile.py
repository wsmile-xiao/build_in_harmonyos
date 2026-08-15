#!/usr/bin/env python3
"""Conan recipe - zabbix 7.4.5 (Autotools: bootstrap + configure + make).

Enterprise-class open source monitoring solution. This recipe builds the
zabbix agent daemon (zabbix_agentd), zabbix_get and zabbix_sender for
HarmonyOS PC arm64, and runs the upstream cmocka unit tests.

Source: official GitHub source archive (tag 7.4.5), which contains tests/ but
no pre-generated configure. The recipe bootstraps configure via bootstrap.sh
(automake is pulled in as a tool_requires), then builds and runs the cmocka
tests.

Dependencies:
  - openssl/3.5.6.1.1  (TLS support)
  - pcre2/10.45         (regular expression support)
  - zlib/1.3.1          (compression support)
  - cmocka/2.0.2        (upstream unit test framework)
  - libyaml/0.2.5       (test mock data YAML parsing)

Tool requirements:
  - automake/1.18       (bootstrap: generate configure from configure.ac)

Platform adaptations are handled via feature detection at the configure.ac /
m4 level (see patches/0001-resolver-capability-detection.patch), not via
hard-coding generated configure scripts.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout


class ZabbixConan(ConanFile):
    name = "zabbix"
    version = "7.4.5"
    description = "Enterprise-class open source monitoring solution"
    license = "AGPL-3.0"
    homepage = "https://www.zabbix.com"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "test_runner.py", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")
        self.requires("cmocka/2.0.2")
        self.requires("libyaml/0.2.5")

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zabbix is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _configure_args(self):
        openssl_root = self.dependencies["openssl"].package_folder
        zlib_root = self.dependencies["zlib"].package_folder
        cmocka_root = self.dependencies["cmocka"].package_folder
        libyaml_root = self.dependencies["libyaml"].package_folder

        # Compute the GNU triplet via Conan's official mapping instead of
        # hard-coding "aarch64-linux-gnu" (a glibc triplet). For os=OHOS the
        # adapter maps it to aarch64-linux-ohos, which is what the OHOS clang
        # uses for its target/sysroot selection.
        triplet = _get_gnu_triplet(
            str(self.settings.os), str(self.settings.arch), str(self.settings.compiler)
        )["triplet"]

        return [
            "--prefix=/",
            "--build=" + triplet,
            "--host=" + triplet,
            "--enable-agent",
            "--disable-server",
            "--disable-proxy",
            "--disable-agent2",
            "--disable-java",
            "--disable-webservice",
            "--without-mysql",
            "--without-postgresql",
            "--without-sqlite3",
            "--without-libxml2",
            "--without-unixodbc",
            "--without-net-snmp",
            "--without-ssh2",
            "--without-ssh",
            "--without-openipmi",
            "--without-ares",
            "--without-libevent",
            "--without-gnutls",
            "--without-libmodbus",
            "--without-ldap",
            "--without-libcurl",
            "--without-iconv",
            "--with-openssl=" + openssl_root,
            "--with-zlib=" + zlib_root,
            "--with-cmocka=" + cmocka_root,
            "--with-libyaml=" + libyaml_root,
        ]

    def generate(self):
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

        # PkgConfigDeps emits pcre2.pc (Name: pcre2), but Zabbix's m4/pcre2.m4
        # looks up "libpcre2-8" via pkg-config. Write a correctly-prefixed
        # libpcre2-8.pc and expose it through PKG_CONFIG_PATH.
        pcre2_root = self.dependencies["pcre2"].package_folder
        libpcre2_pc = os.path.join(self.generators_folder, "libpcre2-8.pc")
        save(self, libpcre2_pc,
             "prefix=" + pcre2_root + "\n"
             "libdir=${prefix}/lib\n"
             "includedir=${prefix}/include\n\n"
             "Name: libpcre2-8\n"
             "Description: PCRE2 - Perl compatible regular expressions C library (8-bit)\n"
             "Version: 10.45\n"
             "Libs: -L${libdir} -lpcre2-8\n"
             "Cflags: -I${includedir} -DPCRE2_STATIC\n"
             )
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)

        tc = AutotoolsToolchain(self)
        # clang folds realloc(NULL, n) into malloc(n), which bypasses the
        # --wrap=realloc linker wrapping used by the zbx_realloc cmocka test
        # (got_size stays 0). Disable the builtin so the wrap actually triggers.
        #
        # Several test-directory Makefile.am files omit $(TLS_CFLAGS)/$(CMOCKA_CFLAGS)
        # /$(YAML_CFLAGS) (include) and the matching -L flags, so their sources
        # fail to find <openssl/ssl.h> and to link -lssl/-lcrypto/-lcmocka/-lyaml
        # when these libraries are not installed in system paths. Add the
        # include/lib dirs globally so every test directory compiles & links.
        openssl_root = self.dependencies["openssl"].package_folder
        cmocka_root = self.dependencies["cmocka"].package_folder
        libyaml_root = self.dependencies["libyaml"].package_folder
        tc.extra_cflags = [
            "-fno-builtin-realloc",
            "-I" + os.path.join(openssl_root, "include"),
            "-I" + os.path.join(cmocka_root, "include"),
            "-I" + os.path.join(libyaml_root, "include"),
        ]
        tc.extra_ldflags = [
            "-L" + os.path.join(openssl_root, "lib"),
            "-L" + os.path.join(cmocka_root, "lib"),
            "-L" + os.path.join(libyaml_root, "lib"),
        ]
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def _fix_umask(self):
        # HMDFS ownership model: mktemp/mkdir with umask 077 create dirs owned
        # by file_manager that are unwritable. Patch the bootstrapped configure.
        cfg_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg_path):
            content = load(self, cfg_path)
            content = content.replace("umask 077 && mktemp", "umask 000 && mktemp")
            content = content.replace("umask 077 && mkdir", "umask 000 && mkdir")
            save(self, cfg_path, content)

    def build(self):
        automake_bin = os.path.join(
            self.dependencies.build["automake"].package_folder, "bin"
        )
        os.environ["PATH"] = automake_bin + os.pathsep + os.environ.get("PATH", "")

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        old_tmp = os.environ.get("TMPDIR", "")
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir

        try:
            with chdir(self, self.source_folder):
                # 1. Bootstrap: generate configure (tests enabled).
                self.run("sh bootstrap.sh tests", env="conanbuild")

                # 2. Patch umask for HMDFS.
                self._fix_umask()

                # 3. Configure + build.
                self.run("./configure " + " ".join(self._configure_args()),
                         env="conanbuild")
                self.run("make -j2", env="conanbuild")

                # 4. Build the cmocka unit tests (best effort: some
                #    server-only library tests cannot build in agent-only mode).
                self.run("make tests_build", env="conanbuild", ignore_errors=True)

                # 5. Run the compiled cmocka tests via the PyYAML runner.
                #    Non-zero exit (some platform-limited tests fail, e.g. time
                #    zone/DST tests on OHOS) must not abort the package build;
                #    the summary is printed and recorded for the PR report.
                runner = os.path.join(self.source_folder, "test_runner.py")
                self.run("python3 %s tests --verbose" % runner, env="conanbuild",
                         ignore_errors=True)
        finally:
            if old_tmp:
                os.environ["TMPDIR"] = old_tmp
            else:
                os.environ.pop("TMPDIR", None)
            os.environ.pop("TMP", None)

    def package(self):
        # In-source build: Makefile lives in source_folder, so run make install
        # from there. Use -j1 to avoid make jobserver mkfifo on HMDFS.
        with chdir(self, self.source_folder):
            self.run(
                "make install DESTDIR={} -j1".format(self.package_folder),
                env="conanbuild",
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
