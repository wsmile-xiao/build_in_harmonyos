#!/usr/bin/env python3
"""Conan recipe for the LADSPA SDK 1.17.

The LADSPA SDK ships the ``ladspa.h`` audio plugin API header, five example
LADSPA plugin shared objects (amp, delay, filter, noise, sine) and three host
tools (analyseplugin, applyplugin, listplugins). The build reuses the upstream
``src/Makefile`` verbatim; OHOS adaptation is done purely through make-variable
overrides (install directories, compiler, flags) — no source patch is needed.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LadspaSdkConan(ConanFile):
    name = "ladspa-sdk"
    version = "1.17"
    description = (
        "LADSPA SDK: the ladspa.h audio plugin API header, five example "
        "LADSPA plugins and three host tools (analyseplugin, applyplugin, "
        "listplugins)."
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://www.ladspa.org/"
    url = ""
    topics = ("ladspa", "audio", "plugin", "dsp", "sdk")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ladspa-sdk is supported only on Linux/OHOS"
            )

    def requirements(self):
        # The three host tools link libsndfile (wave I/O). Plugins and the
        # header have no runtime dependency.
        self.requires("libsndfile/1.2.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #

    def _compiler_paths(self):
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        cc = cpp = None
        if ce:
            try:
                d = json.loads(ce) if isinstance(ce, str) else ce
                cc = d.get("c")
                cpp = d.get("cpp")
            except Exception:
                pass
        # The profile may advertise an absolute compiler path that is a dead
        # symlink in the build environment — make only resolves bare names via
        # PATH. Use the conf path only if it is a real executable file;
        # otherwise fall back to the bare name, which PATH (augmented by
        # conanbuild.sh) resolves.
        def _resolve(candidate, fallback):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            return fallback
        cc = _resolve(cc, os.environ.get("CC") or "clang")
        cpp = _resolve(cpp, os.environ.get("CXX") or os.environ.get("CPP") or "clang++")
        return cc, cpp

    def _sndfile_dirs(self):
        # libsndfile exposes a component-based cpp_info, so read the aggregated
        # includedirs/libdirs (which may be relative like "include") and anchor
        # them to the dependency's package_folder — matching the repo
        # convention in abiword-plugin-eml. Falls back to the package's
        # include/lib layout directly if cpp_info is empty.
        dep = self.dependencies["libsndfile"]
        pf = getattr(dep, "package_folder", None) or ""
        inc = None
        lib = None
        dirs = getattr(dep.cpp_info, "includedirs", None) or []
        if dirs:
            d = dirs[0]
            inc = d if (os.path.isabs(d) or not pf) else os.path.join(pf, d)
        elif pf and os.path.isdir(os.path.join(pf, "include")):
            inc = os.path.join(pf, "include")
        dirs = getattr(dep.cpp_info, "libdirs", None) or []
        if dirs:
            d = dirs[0]
            lib = d if (os.path.isabs(d) or not pf) else os.path.join(pf, d)
        elif pf and os.path.isdir(os.path.join(pf, "lib")):
            lib = os.path.join(pf, "lib")
        return inc, lib

    # ------------------------------------------------------------------ #

    def build(self):
        cc, cpp = self._compiler_paths()
        sndfile_inc, sndfile_lib = self._sndfile_dirs()

        # Override the upstream INSTALL dirs (which default to /usr/...) with a
        # private stage tree; package() copies from it into the Conan package.
        stage = os.path.join(self.build_folder, "stage")
        install_plugins = os.path.join(stage, "lib", "ladspa")
        install_include = os.path.join(stage, "include")
        install_binary = os.path.join(stage, "bin")

        # The OHOS clang wrapper injects -Wl,--code-sign, -fuse-ld=lld and a
        # sysroot -L even during compile (-c) steps. Upstream builds with
        # -Werror, so -Wunused-command-line-argument turns those stray linker
        # flags into fatal errors. Downgrade exactly that one warning so the
        # unpatched upstream Makefile compiles cleanly on OHOS.
        sndfile_inc_flag = f"-I{sndfile_inc}" if sndfile_inc else ""
        sndfile_lib_flag = f"-L{sndfile_lib}" if sndfile_lib else ""
        cflags = (
            f"-I. {sndfile_inc_flag} -Wall -Werror -O2 -fPIC "
            f"-Wno-error=unused-command-line-argument "
            f"-DDEFAULT_LADSPA_PATH={install_plugins}"
        )
        cxxflags = cflags
        libraries = f"-ldl -lm {sndfile_lib_flag} -lsndfile"

        # Each make variable is quoted with shlex.quote so spaces inside
        # CFLAGS/CXXFLAGS (e.g. "-I. -I<path> -Wall ...") are not split by the
        # shell into separate make arguments — which previously made make
        # interpret "-I<abs>" as its own --include-dir flag and print help.
        make_vars = [
            "CC=" + shlex.quote(cc),
            "CPP=" + shlex.quote(cpp),
            "CFLAGS=" + shlex.quote(cflags),
            "CXXFLAGS=" + shlex.quote(cxxflags),
            "LIBRARIES=" + shlex.quote(libraries),
            "INSTALL_PLUGINS_DIR=" + shlex.quote(install_plugins),
            "INSTALL_INCLUDE_DIR=" + shlex.quote(install_include),
            "INSTALL_BINARY_DIR=" + shlex.quote(install_binary),
        ]

        src_dir = os.path.join(self.source_folder, "src")
        # `install` depends on `targets`, so this builds plugins + tools and
        # then copies header, plugins and tools into the stage tree.
        self.run("make -C {} -j1 clean".format(shlex.quote(src_dir)))
        self.run("make -C {} -j1 install ".format(shlex.quote(src_dir)) + " ".join(make_vars))

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "ladspa.h",
             src=os.path.join(stage, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.so",
             src=os.path.join(stage, "lib", "ladspa"),
             dst=os.path.join(self.package_folder, "lib", "ladspa"))
        for tool in ("analyseplugin", "applyplugin", "listplugins"):
            copy(self, tool,
                 src=os.path.join(stage, "bin"),
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # ladspa.h is a header-only API; plugins are dlopen()'d, not linked.
        # Consumers writing a LADSPA host need -ldl to dlopen plugin .so files.
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["dl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "ladspa-sdk")
        self.cpp_info.set_property("cmake_target_name", "ladspa-sdk::ladspa-sdk")
        # Let host tools and consumers find the installed example plugins.
        self.runenv_info.prepend_path(
            "LADSPA_PATH", os.path.join(self.package_folder, "lib", "ladspa"))
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
