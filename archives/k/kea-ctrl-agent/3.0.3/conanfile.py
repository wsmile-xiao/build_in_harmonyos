#!/usr/bin/env python3
"""Conan recipe — kea-ctrl-agent 3.0.3 (ISC Kea Control Agent, Meson).

``kea-ctrl-agent`` is the RESTful control-channel front end ("Control Agent")
that ISC Kea ships: it exposes an HTTP/HTTPS endpoint, forwards the commands
of remote clients to the control channels of kea-dhcp4/kea-dhcp6/kea-d2 and
answers the Control Agent native commands (config-get, config-set, status-get,
shutdown, ...) itself.  Its sources live in ``src/bin/agent`` of the Kea 3.0.3
release tarball and the Meson target installs the executable into ``SBINDIR``.

Kea 3.0 builds the whole tree as a single Meson project, so the recipe builds
the upstream tree and packages the agent together with the Kea shared libraries
it loads at runtime (see ``kea_runtime_libs``).  Kea links its libraries
cumulatively (``LIBS_BUILT_SO_FAR``), so the run-time closure reaches deeper
than the agent's direct ``DT_NEEDED`` entries; the package ships the whole Kea
runtime set, the same list the merged ``kea-hook-bootp``/``kea-hook-ha`` 3.0.3
packages carry.

Family reuse: the portability patches shared with the sibling Kea 3.0.3
recipes are byte-identical — 0001/0002 normalize the top-level meson.build
platform branch and guard the musl/UAPI ``sockaddr_storage`` collision,
0003/0004 invoke the configure-time helper scripts through their
interpreters, 0005 honours TMPDIR in the shared test sandbox helper (the same
file as the kea-dhcp6 recipe's port).  0006 and 0007 are agent-specific:
0006 probe-tests the AF_UNIX pathname bind() that the command forwarding
tests need and skips the nine affected cases on hosts that cannot host such
sockets (probe-gated, see the patch header); 0007 falls back to TMPDIR when
the joined test socket path would exceed the ``sockaddr_un::sun_path`` length
limit, which deeply nested out-of-tree build directories can hit (every
connect() on such a path fails with ENAMETOOLONG).  Nothing is
package-specific in this recipe's build steps.

The Meson steps are invoked through ``sh "<meson wrapper>"`` instead of
executing the wrapper directly: the Conan Meson package ships ``bin/meson`` as
a shebang shell wrapper, and the HarmonyOS PC kernel refuses script execve
regardless of the executable bits, while ``sh`` reads the script itself.  The
same reason applies to the ``ca_process_tests.sh`` shell suite, which is run
through meson's ``--wrapper sh`` (the test command is a shell script, not an
ELF binary).  This is fully portable - the wrapper stays the same on regular
Linux build hosts, and ``ninja``/the compilers remain ELF binaries found on
PATH.
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


class KeaCtrlAgentConan(ConanFile):
    name = "kea-ctrl-agent"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 Control Agent (kea-ctrl-agent), the RESTful "
                   "control-channel front end of the Kea DHCP servers, with "
                   "the Kea runtime libraries it loads")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Upstream Meson test targets covering this package (src/bin/agent/tests):
    #  * kea-agent-tests      — gtest suite of the Control Agent units
    #                           (98 TEST/TEST_F macros, 2 upstream DISABLED_);
    #  * ca_process_tests.sh  — process-level shell suite ('shell-tests'),
    #                           7 named cases driving the real binary.
    # Nine of the executed gtest cases forward commands over a unix control
    # channel; they are probe-gated (patch 0006) and skip on hosts that cannot
    # host an AF_UNIX pathname socket instead of failing the run.
    upstream_test_suites = ("kea-agent-tests",)
    upstream_shell_suite = "ca_process_tests.sh"
    # Kea shared libraries loaded by the agent.  Kea links every library
    # against all libraries built so far (LIBS_BUILT_SO_FAR), so its run-time
    # closure is deeper than the direct DT_NEEDED list: the agent binary names
    # 9 Kea libraries and the recursive closure resolves to 16 (readelf walk
    # on the built artefact).  The package ships the whole Kea runtime set -
    # the same 20-library list as the merged kea-hook-bootp/kea-hook-ha 3.0.3
    # packages - so every packaged library finds its NEEDED names inside the
    # package and hook libraries loaded through libkea-hooks keep working
    # without an extra kea-* package.
    kea_runtime_libs = (
        "libkea-asiolink", "libkea-cc", "libkea-cfgrpt", "libkea-config",
        "libkea-cryptolink", "libkea-database", "libkea-dhcp", "libkea-dhcp_ddns",
        "libkea-dhcpsrv", "libkea-dns", "libkea-eval", "libkea-exceptions",
        "libkea-hooks", "libkea-http", "libkea-log", "libkea-log-interprocess",
        "libkea-process", "libkea-stats", "libkea-tcp", "libkea-util",
    )

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
            # Run only the two suites that cover the Control Agent.
            # --timeout-multiplier: on loaded OHOS workers the per-test budget
            # of the shell suite (which starts real agent processes and waits
            # for log lines with its own 10-20 s timeouts) needs headroom.
            self.run('{} test -v --timeout-multiplier 4 -C "{}" {}'.format(
                meson, self.build_folder, " ".join(self.upstream_test_suites)))
            # ca_process_tests.sh is a shell script: the HarmonyOS PC kernel
            # refuses script execve (see the module docstring), so meson is
            # told to run it through sh explicitly.
            self.run('{} test -v --timeout-multiplier 8 --wrapper sh '
                     '-C "{}" {}'.format(meson, self.build_folder,
                                         self.upstream_shell_suite))

    def _materialize_sonames(self):
        """Create the versioned soname files as real copies in the build tree.

        Meson links the Kea libraries with ``version: 'N.M.K'`` and publishes
        the soname ``libkea-X.so.N`` as a *symlink* to the real
        ``libkea-X.so.N.M.K`` file.  The HarmonyOS /storage sandbox denies
        symlink creation (``ln -s`` -> EPERM), so those links never appear and
        every loader lookup by NEEDED name fails with "Error loading shared
        library libkea-X.so.N" (the meson test binaries, and later the packaged
        agent at startup, all need the soname files).  Recreate them as copies:
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
        # Upstream installs the agent into SBINDIR; Conan packages keep
        # executables under bin/, which is what L0k/L2 and consumers expect.
        copy(self, "kea-ctrl-agent",
             src=os.path.join(self.build_folder, "src", "bin", "agent"),
             dst=os.path.join(self.package_folder, "bin"))
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
        # device: a copied file can land as 0 bytes, which breaks the loader's
        # NEEDED lookup at dlopen time (for the agent binary it would simply
        # not start).  Re-check the packaged binary and every packaged Kea
        # library and re-copy any empty one from the build tree; the re-copy
        # itself is verified as well - if the flush anomaly reproduces, the
        # package step fails instead of shipping a broken artefact.
        heal_map = {}
        for broot, _bdirs, bfiles in os.walk(os.path.join(self.build_folder, "src", "lib")):
            for bname in bfiles:
                heal_map.setdefault(bname, os.path.join(broot, bname))
        heal_map["kea-ctrl-agent"] = os.path.join(
            self.build_folder, "src", "bin", "agent", "kea-ctrl-agent")
        for name in (["kea-ctrl-agent"] + os.listdir(lib_dst)):
            if name != "kea-ctrl-agent" and not self._is_kea_runtime_lib(name):
                continue
            if name not in heal_map:
                continue
            sub = "bin" if name == "kea-ctrl-agent" else "lib"
            dst_path = os.path.join(self.package_folder, sub, name)
            if os.path.getsize(dst_path) == 0:
                for _attempt in range(3):
                    shutil.copyfile(heal_map[name], dst_path)
                    if os.path.getsize(dst_path) > 0:
                        break
                else:
                    raise ConanException(
                        "package(): {} is still 0 bytes after 3 re-copies from "
                        "the build tree (persistent /storage flush failure)".format(name))
                self.output.warning(
                    "package(): re-copied empty artifact {} from the build tree".format(name))

    def package_info(self):
        # Command-line tool: the executable goes on PATH and the Kea libraries
        # it loads at run time stay in lib/ so the generated run environment
        # resolves them (the binary's upstream install RPATH points at the
        # build-machine prefix, which a Conan package cannot rely on).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
