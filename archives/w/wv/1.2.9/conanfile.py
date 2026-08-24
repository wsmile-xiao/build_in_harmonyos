#!/usr/bin/env python3
"""Conan recipe for wv 1.2.9 (wvWare Word document filter library)."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class WvConan(ConanFile):
    name = "wv"
    version = "1.2.9"
    description = "Tools and library for reading Microsoft Word documents"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/AbiWord/wv"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wv is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        public_traits = {
            "transitive_headers": True,
            "transitive_libs": True,
        }
        self.requires("glib/2.84.0.1.1", force=True, **public_traits)
        self.requires("libgsf/1.14.58", **public_traits)
        self.requires("libxml2/2.15.3.1", force=True, **public_traits)
        self.requires("libpng/1.6.58", **public_traits)
        self.requires("zlib/1.3.1.1", force=True, **public_traits)
        # GLib's shared objects retain references to these private libraries.
        # Promote them so native OHOS links can resolve the full shared-library
        # closure instead of relying on stale libtool paths from libgsf.
        self.requires("libffi/3.4.4", **public_traits)
        self.requires("pcre2/10.45", **public_traits)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _glib_proxy_libintl_path(self):
        glib_libdir = os.path.join(
            self.dependencies["glib"].package_folder, "lib")
        intl_path = next((
            os.path.join(glib_libdir, name)
            for name in ("libintl.so", "libintl.a")
            if os.path.isfile(os.path.join(glib_libdir, name))), "")
        if not intl_path:
            raise ConanInvalidConfiguration(
                "GLib package does not provide proxy libintl")
        return intl_path

    def _ohos_glib_link_flags(self):
        flags = []

        def append_unique(flag):
            if flag not in flags:
                flags.append(flag)

        for dependency_name in ("libffi", "pcre2"):
            dependency = self.dependencies[dependency_name]
            cpp_infos = [dependency.cpp_info]
            cpp_infos.extend(dependency.cpp_info.components.values())
            for cpp_info in cpp_infos:
                for libdir in cpp_info.libdirs:
                    append_unique("-L{}".format(libdir))
                for library in cpp_info.libs:
                    append_unique("-l{}".format(library))

        # Published GLib keeps proxy-libintl private even though its shared
        # objects retain g_libintl_* references. The absolute path keeps old
        # libtool from redirecting it through stale dependency metadata.
        append_unique(self._glib_proxy_libintl_path())
        return " ".join(flags)

    def generate(self):
        # The release tarball ships generated configure/Makefile.in files, so
        # no Autotools tool requirements are needed for a release build.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()
        if str(self.settings.os) == "OHOS":
            tools = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            compiler = tools.get("c", "clang")
            tool_dir = os.path.dirname(compiler)
            env = Environment()
            if tool_dir:
                env.prepend_path("PATH", tool_dir)
            for variable, executable in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "NM": "llvm-nm",
                "RANLIB": "llvm-ranlib",
                "STRIP": "llvm-strip",
                "OBJDUMP": "llvm-objdump",
            }.items():
                path = os.path.join(tool_dir, executable)
                if os.path.exists(path):
                    env.define_path(variable, path)
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
            if pkg_config:
                env.define_path("PKG_CONFIG", pkg_config)
                pkgconf_libdir = os.path.abspath(os.path.join(
                    os.path.dirname(pkg_config), "..", "lib"))
                if os.path.isdir(pkgconf_libdir):
                    env.prepend_path(
                        "LD_LIBRARY_PATH", pkgconf_libdir)
            sdk_llvm_libdirs = sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"),
                reverse=True)
            if sdk_llvm_libdirs:
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libdirs[0])
            make = shutil.which("make")
            if not make:
                make_candidates = sorted(glob.glob(
                    "/data/service/hnp/make.org/make_*/bin/make"),
                    reverse=True)
                if make_candidates:
                    make = make_candidates[0]
            if make:
                env.prepend_path("PATH", os.path.dirname(make))
            env.vars(self).save_script("wv_linker")

    def _write_install_shim(self):
        # OHOS HMDFS rejects chmod from toybox install and can make the
        # bundled install-sh fail while creating package directories. The
        # package step only needs mkdir/cp semantics, so use the repository's
        # established install shim with chmod treated as best effort.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
            "set -eu\n"
            "mode=\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -p|-c) shift ;;\n"
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
            "    --) shift; break ;;\n"
            "    -*) shift ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "[ $# -ge 2 ] || exit 2\n"
            "dest=\n"
            "for arg in \"$@\"; do dest=$arg; done\n"
            "count=$(($# - 1))\n"
            "mkdir -p \"$(dirname \"$dest\")\"\n"
            "i=1\n"
            "for src in \"$@\"; do\n"
            "  [ $i -gt $count ] && break\n"
            "  cp -f \"$src\" \"$dest\"\n"
            "  if [ -n \"$mode\" ]; then\n"
            "    if [ -d \"$dest\" ]; then\n"
            "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
            "    else\n"
            "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        fd = os.open(
            install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(script)
        return install

    def _redirect_install_to_shim(self, shim_install):
        # wv's old Automake output is named GNUmakefile. Redirect both its
        # file-copy command and install_sh/mkdir helpers after configure so
        # package() never invokes the HMDFS-incompatible upstream scripts.
        replacements = {
            "INSTALL = ": "INSTALL = {}".format(shim_install),
            "install_sh = ": "install_sh = {}".format(shim_install),
            "mkdir_p = ": "mkdir_p = {} -d".format(shim_install),
            "MKDIR_P = ": "MKDIR_P = {} -d".format(shim_install),
        }
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name not in ("Makefile", "GNUmakefile"):
                    continue
                makefile = os.path.join(root, name)
                with open(
                        makefile, "r", encoding="utf-8",
                        errors="ignore") as stream:
                    lines = stream.readlines()
                changed = False
                output = []
                for line in lines:
                    stripped = line.lstrip()
                    replacement = next((
                        value for prefix, value in replacements.items()
                        if stripped.startswith(prefix)), None)
                    if replacement is None:
                        output.append(line)
                        continue
                    ending = (
                        "\r\n" if line.endswith("\r\n")
                        else "\n" if line.endswith("\n")
                        else "")
                    indent = line[:len(line) - len(stripped)]
                    output.append(indent + replacement + ending)
                    changed = True
                if changed:
                    with open(makefile, "w", encoding="utf-8") as stream:
                        stream.writelines(output)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # HMDFS preserves a setgid directory mode that makes Autoconf's
            # umask-077 config.status helpers inaccessible even to the owner.
            # The generated files are build-only, so normal 022 permissions
            # are sufficient and avoid the subs1.awk permission failure.
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            "umask 077", "umask 022")
            self.run('sh "{}/configure" {}'.format(
                self.source_folder, autotools._configure_args))
        else:
            autotools.configure()
        if str(self.settings.os) == "OHOS":
            install_shim = self._write_install_shim()
            self._redirect_install_to_shim(install_shim)
            # Published GLib-chain packages retain non-relocatable libtool
            # archives whose dependency_libs entries point at //lib/*.la.
            # Keep them for Autoconf probes, then remove only the metadata so
            # old wv libtool selects the colocated shared objects during make.
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    for archive in glob.glob(os.path.join(libdir, "*.la")):
                        os.remove(archive)
                        self.output.info(
                            "removed broken libtool archive: {}/{}".format(
                                dependency.ref, os.path.basename(archive)))
        make_args = ["-j1"]
        if str(self.settings.os) == "OHOS":
            make_args.append(
                "LIBS=" + shlex.quote(self._ohos_glib_link_flags()))
        autotools.make(args=make_args)

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # Do not ship libtool metadata; consumers use Conan metadata instead.
        for libtool_file in ("libwv.la", "libwv-1.2.la"):
            path = os.path.join(self.package_folder, "lib", libtool_file)
            if os.path.exists(path):
                os.remove(path)

    def package_info(self):
        self.cpp_info.libs = ["wv"]
        self.cpp_info.requires = [
            "glib::glib",
            "libgsf::libgsf",
            "libxml2::libxml2",
            "libpng::libpng",
            "zlib::zlib",
            "libffi::libffi",
            "pcre2::pcre2",
        ]
        if str(self.settings.os) == "OHOS":
            # GLib's published Conan metadata does not export proxy-libintl,
            # while libwv.so retains g_libintl_* references. Add its package
            # directory to the consumer search path and place -lintl after
            # libwv through system_libs so CMakeDeps/PkgConfigDeps consumers
            # receive the same closure used by the upstream make build.
            intl_libdir = os.path.dirname(
                self._glib_proxy_libintl_path())
            self.cpp_info.system_libs = ["intl"]
            self.cpp_info.sharedlinkflags = ["-L{}".format(intl_libdir)]
            self.cpp_info.exelinkflags = ["-L{}".format(intl_libdir)]
        self.cpp_info.includedirs = ["include", "include/wv"]
        self.cpp_info.set_property("pkg_config_name", "wv-1.0")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/wv"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
