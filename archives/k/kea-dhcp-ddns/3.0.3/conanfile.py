#!/usr/bin/env python3
"""Conan recipe — kea-dhcp-ddns 3.0.3 (ISC Kea DHCP-DDNS daemon, Meson).

``kea-dhcp-ddns`` is the DHCP-DDNS (nicknamed D2) daemon that receives
NameChangeRequests from the kea-dhcp4/kea-dhcp6 servers and performs the
(TSIG-signed) DNS dynamic updates on their behalf; its sources live in
``src/bin/d2`` of the Kea 3.0.3 release tarball and the Meson target installs
the executable into ``SBINDIR``.  Kea 3.0 replaced Autotools with Meson and
builds the whole tree as a single project, so the recipe builds the upstream
tree and packages the daemon together with the Kea shared libraries it loads
at runtime (see ``kea_runtime_libs``).

Family reuse: this daemon lives in the same Kea 3.0.3 source tree as the
merged kea-hook-limits/kea-hook-ping-check/kea-hook-flex-option/kea-hook-bootp/
kea-hook-ha/kea-hook-flex-id hook recipes and the merged kea-perfdhcp/kea-shell
component recipes.  Patches 0001-0004 are byte-identical with the family
templates (0001 normalizes the Meson system name, 0002 fixes the musl/UAPI
``sockaddr_storage`` collision, 0003/0004 route the configure-time scripts
through their interpreters; md5-verified against the merged kea-hook-ha and
kea-hook-flex-id archives).  Patch 0005 is new for this package: the
OpenHarmony PC packaging tool-chain (the device conan-verify smoke gate and
the CI smoke test) probes packaged executables with ``--version`` and
``--help``, which upstream's daemons do not accept (the stock ``getopt``
option string is ``dvVWc:t:X`` only), so the shipped daemon would be flagged
as not running.  The patch makes ``DControllerBase::parseArgs`` accept both
spellings as pure aliases of the existing handling -- ``--version`` prints
the version exactly like ``-v`` and ``--help`` prints the usage text, both
exiting successfully -- changing no other behaviour.  The kea-hook-ha
``getifaddrs()`` fallback patch (its own 0005) is deliberately NOT carried:
the D2 daemon and its tests never construct ``IfaceMgr`` (``src/bin/d2`` and
``src/lib/d2srv`` contain no reference to it), so that code path is
unreachable here.

The Meson steps are invoked through ``sh "<meson wrapper>"`` instead of
executing the wrapper directly: the Conan Meson package ships ``bin/meson`` as
a shebang shell wrapper, and the HarmonyOS PC kernel refuses script execve
regardless of the executable bits, while ``sh`` reads the script itself.  For
the same reason the upstream process-level shell suite ``d2_process_tests.sh``
(which ``meson test`` would exec directly) is run through ``sh`` from
:meth:`_run_process_shell_tests`.  This is fully portable - the wrapper stays
the same on regular Linux build hosts, and ``ninja``/the compilers remain ELF
binaries found on PATH.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class KeaDhcpDdnsConan(ConanFile):
    name = "kea-dhcp-ddns"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 DHCP-DDNS (D2) daemon (kea-dhcp-ddns), "
                   "with the Kea runtime libraries it loads")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Kea shared libraries shipped with the daemon: the complete loader closure
    # of the kea-dhcp-ddns binary - the DT_NEEDED of the daemon plus the
    # transitive DT_NEEDED of those libraries - resolved with readelf on the
    # built artefact.  20 libraries; the server-only libraries (dhcpsrv/eval,
    # needed only by the kea-dhcp4/kea-dhcp6 daemons), the configuration
    # back-ends (mysql/pgsql), yang and testutils are not in the closure.
    kea_runtime_libs = (
        "libkea-asiodns", "libkea-asiolink", "libkea-cc", "libkea-cfgrpt",
        "libkea-config", "libkea-cryptolink", "libkea-d2srv",
        "libkea-database", "libkea-dhcp", "libkea-dhcp_ddns", "libkea-dns",
        "libkea-exceptions", "libkea-hooks", "libkea-http", "libkea-log",
        "libkea-log-interprocess", "libkea-process", "libkea-stats",
        "libkea-tcp", "libkea-util",
    )
    # Upstream Meson test suites covering the daemon (src/bin/d2/tests): the
    # gtest unit suite 'kea-d2-tests' (424 cases).  The process-level shell
    # suite 'shell-tests' (d2_process_tests.sh, 10 scenarios) is registered in
    # the same tests/meson.build and is driven from
    # :meth:`_run_process_shell_tests` through sh (the OHOS kernel refuses the
    # direct script execve that ``meson test`` would perform).
    upstream_test_suites = ("kea-d2-tests",)

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
        # -j 8: the OHOS app sandbox caps concurrent processes; ninja defaults
        # to the 20-core count (~45 live spawns) and dies with posix_spawn
        # EAGAIN mid-compile.
        self.run('{} compile -C "{}" -j 8'.format(meson, self.build_folder))
        self._materialize_sonames()
        if self.options.tests:
            # -v reports the per-case results; --timeout-multiplier 4 matches
            # the family recipes (long error-path cases on loaded workers).
            self.run('{} test -v --timeout-multiplier 4 -C "{}" {}'.format(
                meson, self.build_folder, " ".join(self.upstream_test_suites)))
            self._run_process_shell_tests()

    def _run_process_shell_tests(self):
        """Run upstream's d2_process_tests.sh (Meson suite 'shell-tests').

        The script is generated by configure_file and registered with
        ``test()`` in src/bin/d2/tests/meson.build, so ``meson test`` would
        exec the script file directly - which the HarmonyOS PC kernel refuses
        (the same script-execve restriction patches 0003/0004 fix in the
        configure phase).  Running it through /bin/sh with the workdir meson
        registers (the script's own directory) executes the identical ten
        scenarios: the real daemon is started on 127.0.0.1:53001 and driven
        through SIGHUP/SIGINT/SIGTERM, with the PID and lock files redirected
        into the build tree via KEA_PIDFILE_DIR / KEA_LOCKFILE_DIR (both
        exported by the upstream dhcp_test_lib.sh).
        """
        shell_dir = os.path.join(self.build_folder, "src", "bin", "d2", "tests")
        script = os.path.join(shell_dir, "d2_process_tests.sh")
        self.run('sh "{}"'.format(script), cwd=shell_dir)

    def _materialize_sonames(self):
        """Create the versioned soname files as real copies in the build tree.

        Meson links the Kea libraries with ``version: 'N.M.K'`` and publishes
        the soname ``libkea-X.so.N`` as a *symlink* to the real
        ``libkea-X.so.N.M.K`` file.  The HarmonyOS /storage sandbox denies
        symlink creation (``ln -s`` -> EPERM), so those links never appear and
        every loader lookup by NEEDED name fails with "Error loading shared
        library libkea-X.so.N" (the meson test binaries, the process-level
        shell suite that starts the real daemon, and later the packaged
        daemon, all need the soname files).  Recreate them as copies:
        idempotent, and on regular Linux hosts where meson already made the
        symlink the copy is skipped, keeping one physical library per name.
        """
        lib_root = os.path.join(self.build_folder, "src", "lib")
        for root, _dirs, files in os.walk(lib_root):
            for name in files:
                # meson's SHSYM intermediates (libkea-X.so.N.M.K.symbols) match
                # the pattern below and would become a bogus soname copy inside
                # their .p/ build dir; same skip as _is_kea_runtime_lib.
                if name.endswith(".symbols"):
                    continue
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
        # Upstream installs the daemon into SBINDIR; Conan packages keep
        # executables under bin/, which is what the generated run environment
        # and consumers expect.
        bin_dst = os.path.join(self.package_folder, "bin")
        copy(self, "kea-dhcp-ddns",
             src=os.path.join(self.build_folder, "src", "bin", "d2"),
             dst=bin_dst)
        # Kea runtime libraries.  Recreate the upstream soname symlinks instead
        # of letting the copy follow them, which would store every library
        # several times over.
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
        # device: a copied artifact can land as a 0-byte file, which breaks
        # the loader (daemon startup) and the consumer tests.  Re-check the
        # daemon binary and every packaged Kea library and re-copy any empty
        # one from the build tree; the re-copy itself is verified as well -
        # if the flush anomaly reproduces, the package step fails instead of
        # shipping a 0-byte artifact.
        src_map = {}
        for broot, _bdirs, bfiles in os.walk(os.path.join(self.build_folder, "src", "lib")):
            for bname in bfiles:
                src_map.setdefault(bname, os.path.join(broot, bname))
        src_map["kea-dhcp-ddns"] = os.path.join(self.build_folder, "src", "bin", "d2",
                                                "kea-dhcp-ddns")
        heal_targets = [os.path.join(bin_dst, "kea-dhcp-ddns")]
        heal_targets += [os.path.join(lib_dst, n) for n in os.listdir(lib_dst)
                         if self._is_kea_runtime_lib(n)]
        for dst_path in heal_targets:
            name = os.path.basename(dst_path)
            if not os.path.isfile(dst_path) or name not in src_map:
                continue
            if os.path.getsize(dst_path) == 0:
                for _attempt in range(3):
                    shutil.copyfile(src_map[name], dst_path)
                    if os.path.getsize(dst_path) > 0:
                        break
                else:
                    raise ConanException(
                        "package(): {} is still 0 bytes after 3 re-copies from "
                        "the build tree (persistent /storage flush failure)".format(name))
                self.output.warning(
                    "package(): re-copied empty artifact {} from the build tree".format(name))

    def package_info(self):
        # Command-line tool: the daemon goes on PATH and the Kea libraries it
        # loads at run time stay in lib/ so the generated run environment
        # resolves them (the binary's upstream install RPATH points at the
        # build-machine prefix, which a Conan package cannot rely on).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
