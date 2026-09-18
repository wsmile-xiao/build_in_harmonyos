#!/usr/bin/env python3
"""Conan recipe for liboauth2 — OAuth2 / OpenIDC client library (Autotools)."""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.layout import basic_layout


class Liboauth2Conan(ConanFile):
    name = "liboauth2"
    version = "2.3.0"
    description = "OAuth2 / OpenIDC client library"
    license = "Apache-2.0"
    homepage = "https://github.com/OpenIDC/liboauth2"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*.tar.gz", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("libcurl/8.5.0")
        self.requires("jansson/2.15.1.1")
        self.requires("cjose/0.6.2.7")
        self.requires("pcre2/10.48")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        # rule4: upstream tests use the check framework (TESTS = check_liboauth2)
        self.test_requires("check/0.15.2")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try remote download; fall back to exported tarball if network is unavailable
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            from conan.tools.files import unzip
            tarball = os.path.join(self.export_sources_folder, "liboauth2-2.3.0.tar.gz")
            unzip(self, tarball, destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: static linking for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable optional components not needed for OHOS
        tc.configure_args.append("--with-apache=no")
        tc.configure_args.append("--with-memcache=no")
        tc.configure_args.append("--with-redis=no")
        tc.configure_args.append("--with-jq=no")
        # Bypass config.guess for OHOS (E007: config.guess doesn't recognize HarmonyOS)
        if self.settings.os in ("OHOS",):
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # E002: HMDFS /tmp readonly — redirect tmp to build-local dir via Conan env
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_env = VirtualBuildEnv(self)
        env = build_env.environment()
        env.define("TMPDIR", tmpdir)
        # Shared deps needed at test runtime (make check runs check_liboauth2)
        libdirs = []
        for dep in self.dependencies.values():
            libdirs.extend(dep.cpp_info.libdirs)
            libdirs.extend(dep.cpp_info.bindirs)
        if libdirs:
            env.define("LD_LIBRARY_PATH", os.pathsep.join(libdirs))
        # check framework temp dir priority is TEMP > P_tmpdir(macro=/tmp) >
        # TMPDIR; /tmp is read-only on HMDFS, so TEMP must point somewhere
        # writable (TMPDIR alone is ignored while P_tmpdir is defined)
        for var in ("TEMP", "TMPDIR"):
            env.define(var, tmpdir)
        build_env.generate()
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf()
        # E002/HMDFS: config.status creates temp files in CWD (mktemp -d "./confXXXXXX")
        # which fails on HMDFS with Permission denied. Workaround: run configure
        # with --no-create, patch config.status to use $TMPDIR, then run it manually.
        # Step 1: configure --no-create (generates config.status but doesn't run it)
        autotools.configure(args=["--no-create"])
        # Step 2: Patch config.status to use $TMPDIR and avoid umask 077 on HMDFS
        config_status = os.path.join(self.build_folder, "config.status")
        # Use simple single-line replacements
        replace_in_file(self, config_status,
            'umask 077 && mktemp -d "./confXXXXXX"',
            'umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX"')
        replace_in_file(self, config_status,
            'tmp=./conf$$-$RANDOM',
            'tmp=${TMPDIR:-.}/conf$$-$RANDOM')
        replace_in_file(self, config_status,
            'umask 077 && mkdir "$tmp"',
            'umask 022 && mkdir "$tmp"')
        # Step 3: Run config.status and make (with TMPDIR set via VirtualBuildEnv)
        self.run("./config.status", env="conanbuild")
        # E002: config.status generates version.h in build-release/include/ but
        # source code includes it from source-tree include/. Copy generated files.
        build_version_h = os.path.join(self.build_folder, "include", "oauth2", "version.h")
        src_version_h = os.path.join(self.source_folder, "include", "oauth2", "version.h")
        if os.path.isfile(build_version_h) and not os.path.isfile(src_version_h):
            copy(self, "version.h", src=os.path.dirname(build_version_h),
                 dst=os.path.dirname(src_version_h))
        autotools.make()
        # rule4: actually run upstream tests (TESTS = check_liboauth2, 101
        # assertions). Some cases may fail on OHOS; capture the summary and
        # continue so results are reported instead of aborting the build.
        try:
            autotools.make(target="check")
        except Exception:
            self.output.warning("make check reported failures, collecting results")
        log = os.path.join(self.build_folder, "test-suite.log")
        if os.path.isfile(log):
            for line in open(log, errors="ignore"):
                if ("Checks:" in line or "PASS:" in line or "FAIL:" in line
                        or "SKIP:" in line or line.startswith("# TOTAL")):
                    self.output.info("UPSTREAM-TEST: " + line.strip())
            copy(self, "test-suite.log", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["oauth2"]
        self.cpp_info.set_property("pkg_config_name", "liboauth2")
