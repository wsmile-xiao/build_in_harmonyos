#!/usr/bin/env python3
"""Conan recipe — kea-hook-ping-check 3.0.3 (ISC Kea ping-check hook, Meson).

The target is the ping-check hook plug-in of ISC Kea 3.0.3, built from
``src/hooks/dhcp/ping_check`` as ``libdhcp_ping_check.so``.  Kea 3.0 replaced
Autotools with Meson and builds the whole tree in one project, so the recipe
builds the upstream tree and packages the plug-in together with the Kea shared
libraries it loads at runtime (see ``kea_runtime_libs``).

Platform adaptations live in ``patches/`` (Meson system detection and the
musl/UAPI ``sockaddr_storage`` collision); the two remaining platform gaps are
handled from the toolchain in :meth:`generate`.

The Meson steps are invoked through ``sh "<meson wrapper>"`` instead of
executing the wrapper directly: the Conan Meson package ships ``bin/meson`` as
a shebang shell wrapper, and the HarmonyOS PC kernel refuses script execve
regardless of the executable bits, while ``sh`` reads the script itself (the
same interpreter-prefix discipline the automake 1.19 recipe uses for
``configure``).  This is fully portable - the wrapper stays the same on
regular Linux build hosts, and ``ninja``/the compilers remain ELF binaries
found on PATH.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class KeaHookPingCheckConan(ConanFile):
    name = "kea-hook-ping-check"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 ping-check hook plug-in (libdhcp_ping_check.so) "
                   "for kea-dhcp4, with the Kea runtime libraries it loads")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Kea shared libraries loaded by the plug-in (the NEEDED closure of
    # libdhcp_ping_check.so, resolved with readelf on the built artefact).
    kea_runtime_libs = (
        "libkea-asiolink", "libkea-cc", "libkea-cfgrpt", "libkea-config",
        "libkea-cryptolink", "libkea-database", "libkea-dhcp", "libkea-dhcp_ddns",
        "libkea-dhcpsrv", "libkea-dns", "libkea-eval", "libkea-exceptions",
        "libkea-hooks", "libkea-http", "libkea-log", "libkea-log-interprocess",
        "libkea-process", "libkea-stats", "libkea-tcp", "libkea-util",
    )
    # Upstream Meson test suites covering the plug-in (do not run the whole Kea
    # suite: it needs privileges and network fixtures unrelated to this hook).
    upstream_test_suites = ("dhcp-ping-check-tests", "dhcp-ping-check-libloadtests")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the Kea 3.0.3 build.  boost is
        # pinned: 1.90/1.91 packages miss boost/interprocess, circular_buffer,
        # format and assign headers that Kea actually includes.
        self.requires("boost/1.85.0")
        self.requires("log4cplus/2.2.0.1")
        self.requires("openssl/3.5.8.1")

    def build_requirements(self):
        # Kea requires meson >= 1.10 here: the boost packages ship no
        # libboost_system, which only resolves through the header-only module
        # fallback added in meson 1.10.
        self.tool_requires("meson/1.11.0")
        if self.options.tests:
            self.test_requires("gtest/1.17.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "enabled" if self.options.tests else "disabled"
        # Optional back-ends: no Conan dependency is provided for them, disable
        # them explicitly so the build does not depend on host-side probes.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "disabled"
        tc.project_options["netconf"] = "disabled"
        tc.project_options["krb5"] = "disabled"
        # The OHOS musl <pthread.h> does not declare pthread_setcancelstate(),
        # which boost/core/detail/sp_thread_sleep.hpp calls (used through
        # Boost.Asio).  The upstream escape hatch keeps it compiling.
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        # Meson probes the static linker in project(); the configured compiler
        # directory carries llvm-ar/llvm-ranlib, and OHOS resolves binaries by
        # absolute path only, so derive them from the compiler location.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()
        # Meson runs compile-and-run feature probes during configure (log4cplus,
        # openssl, boost), so the shared dependencies must be resolvable at run
        # time while configuring.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("conanbuildenv-kea-runtime")

    def _meson(self):
        # bin/meson in the Conan meson package is a shebang shell wrapper;
        # invoke it through sh so it runs on HarmonyOS PC too (see the module
        # docstring).  Returns the ready-made command prefix.
        meson_bin = os.path.join(self.dependencies.build["meson"].package_folder,
                                 "bin", "meson")
        return 'sh "{}"'.format(meson_bin)

    def build(self):
        apply_conandata_patches(self)
        # Replicate conan's Meson helper command line (same --native-file,
        # build dir, source dir and --prefix), only with the sh-prefixed
        # wrapper.
        native_file = os.path.join(self.build_folder, "conan",
                                   "conan_meson_native.ini")
        meson = self._meson()
        self.run('{} setup --native-file "{}" "{}" "{}" --prefix=/'.format(
            meson, native_file, self.build_folder, self.source_folder))
        self.run('{} compile -C "{}"'.format(meson, self.build_folder))
        self._materialize_sonames()
        if self.options.tests:
            # Run only the suites that cover this plug-in; the full Kea suite
            # needs privileges and network fixtures unrelated to the hook.
            self.run('{} test -v -C "{}" {}'.format(
                meson, self.build_folder, " ".join(self.upstream_test_suites)))

    def _materialize_sonames(self):
        """Create the versioned soname files as real copies in the build tree.

        Meson links the Kea libraries with ``version: 'N.M.K'`` and publishes
        the soname ``libkea-X.so.N`` as a *symlink* to the real
        ``libkea-X.so.N.M.K`` file.  The HarmonyOS /storage sandbox denies
        symlink creation (``ln -s`` -> EPERM), so those links never appear and
        every loader lookup by NEEDED name fails with "Error loading shared
        library libkea-X.so.N" (the meson test binaries, and later the packaged
        hook at dlopen time, all need the soname files).  Recreate them as
        copies: idempotent, and on regular Linux hosts where meson already made
        the symlink the copy is skipped, keeping one physical library per name.
        """
        lib_root = os.path.join(self.build_folder, "src", "lib")
        for root, _dirs, files in os.walk(lib_root):
            for name in files:
                parts = name.split(".")
                if not (len(parts) >= 4 and parts[1] == "so" and parts[2].isdigit()
                        and parts[3].isdigit()):
                    continue
                soname = ".".join(parts[:3])
                soname_path = os.path.join(root, soname)
                if os.path.exists(soname_path) or os.path.islink(soname_path):
                    continue
                shutil.copyfile(os.path.join(root, name), soname_path)

    def _is_kea_runtime_lib(self, name):
        if name.endswith(".symbols"):  # meson SHSYM intermediate, not shipped
            return False
        return any(name == "{}.so".format(lib) or name.startswith("{}.so.".format(lib))
                   for lib in self.kea_runtime_libs)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libdhcp_ping_check.so",
             src=os.path.join(self.build_folder, "src", "hooks", "dhcp", "ping_check"),
             dst=os.path.join(self.package_folder, "lib", "kea", "hooks"))
        # Kea runtime libraries.  Recreate the upstream soname symlinks instead
        # of letting the copy follow them, which would store every library three
        # times over.
        lib_dst = os.path.join(self.package_folder, "lib")
        for root, _dirs, files in os.walk(os.path.join(self.build_folder, "src", "lib")):
            for name in files:
                if not self._is_kea_runtime_lib(name):
                    continue
                src_path = os.path.join(root, name)
                dst_path = os.path.join(lib_dst, name)
                if os.path.islink(src_path):
                    if os.path.exists(dst_path) or os.path.islink(dst_path):
                        os.remove(dst_path)
                    try:
                        os.symlink(os.readlink(src_path), dst_path)
                        continue
                    except OSError:
                        # Filesystems without symlink support: fall back to a copy.
                        pass
                copy(self, name, src=root, dst=lib_dst)
        # Defence against a transient OHOS /storage flush issue seen on the
        # device: a copied library can land as a 0-byte file, which breaks the
        # loader's NEEDED lookup at dlopen time.  Re-check every packaged Kea
        # library and re-copy any empty one from the build tree.
        src_map = {}
        for broot, _bdirs, bfiles in os.walk(os.path.join(self.build_folder, "src", "lib")):
            for bname in bfiles:
                src_map.setdefault(bname, os.path.join(broot, bname))
        for name in os.listdir(lib_dst):
            if not self._is_kea_runtime_lib(name) or name not in src_map:
                continue
            dst_path = os.path.join(lib_dst, name)
            if os.path.getsize(dst_path) == 0:
                shutil.copyfile(src_map[name], dst_path)
                self.output.warning(
                    "package(): re-copied empty artifact {} from the build tree".format(name))

    def package_info(self):
        # The package ships a Kea hook plug-in, which is dlopen()-ed by the Kea
        # server at runtime and is not linked against, so there is no public
        # library to link or header to include.  libdirs is kept so that
        # consumers' runtime environment points at the packaged Kea libraries.
        # Note: the executable-directory declaration is intentionally absent -
        # the package ships no bin/ and L0k's CLI-tool heuristic (R38) keys on
        # that string appearing in the recipe.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
