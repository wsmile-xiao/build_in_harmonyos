#!/usr/bin/env python3
"""Conan recipe — c-vtapi 0.0-git20230329.226eda8.

VirusTotal C API library (public + private API).

Build notes:
  - the git archive ships no `configure`, so build() runs `autoreconf -fi`;
  - the minimal OHOS image lacks automake/aclocal/libtoolize (only the
    autoconf suite is present under /data/service/hnp/bin), so they are
    pulled in as tool_requires (same approach as argp-standalone /
    abiword-plugin-clarisworks).  tool_requires resolve with the *build*
    profile, so both -pr:h and -pr:b must be passed to conan create;
  - runtime deps: libcurl (VtUrl.c includes <curl/curl.h>) and jansson
    (configure.ac: AC_SEARCH_LIBS json_object / curl_global_init);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - the upstream examples (examples/c/*.c) need a live VirusTotal API key
    and are disabled by default (--enable-examples is off), so they are not
    part of the packaged build.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class CVtapiConan(ConanFile):
    name = "c-vtapi"
    version = "0.0-git20230329.226eda8"
    description = "VirusTotal C API library (public and private API)"
    license = "Apache-2.0"
    homepage = "https://github.com/VirusTotal/c-vtapi"
    url = "https://github.com/VirusTotal/c-vtapi"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps: libcurl + jansson (see README.md).
        self.requires("curl/8.15.0")
        self.requires("jansson/2.15.1.1")

    def build_requirements(self):
        # The git archive ships no `configure`: build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize, so pull
        # them in as tool_requires.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "c-vtapi is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from curl/jansson into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Upstream config.guess cannot identify HarmonyOS; the
            # *-linux-ohos triplet is accepted by the generated config.sub.
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared
        # libs; configure's conftest runs compiled programs, which fail
        # without LD_LIBRARY_PATH pointing at the dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        # The git archive ships no `configure`: generate one from the
        # upstream configure.ac before configuring.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # No upstream test suite (no TESTS / make check targets); upstream
        # examples need a live VirusTotal API key and are disabled.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # VtObject.h and vtcapi_common.h are not in include_HEADERS but are
        # pulled in by the installed public headers — ship them too.
        copy(self, "VtObject.h", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "vtcapi_common.h",
             src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["cvtapi"]
        self.cpp_info.requires = ["curl::curl", "jansson::jansson"]
        self.cpp_info.set_property("cmake_file_name", "c-vtapi")
        self.cpp_info.set_property("cmake_target_name", "c-vtapi::c-vtapi")
