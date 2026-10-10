#!/usr/bin/env python3
"""Conan recipe — isc-kea 3.0.3 (ISC Kea DHCP/DNS server suite, Meson).

``isc-kea`` is the Kea server itself: the ``kea-dhcp4``/``kea-dhcp6`` DHCP
servers, the ``kea-dhcp-ddns`` DDNS updater, the ``kea-ctrl-agent`` CA and
the ``kea-lfc`` lease-file cleaner built from ``src/bin`` of the Kea 3.0.3
release tarball, together with the ``keactrl`` management script, the
example configurations and the core Kea libraries (``libkea-*``) the
daemons load at run time.

Kea 3.0 replaced Autotools with Meson and builds the whole tree as a single
project, so the recipe drives Meson directly and compiles just the targets
this package owns — the five daemons, the core libraries and (with
``tests=True``) the upstream gtest executables of the core libs and servers —
rather than the ~1250 unrelated targets of the hook plugins (already
delivered as separate kea-hook-* / kea-hooks / kea-perfdhcp packages).

Platform adaptations live in ``patches/`` (the Meson system-name
normalization and the musl/UAPI ``sockaddr_storage`` collision); the three
remaining platform gaps are handled from the toolchain in :meth:`generate`.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class IscKeaConan(ConanFile):
    name = "isc-kea"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 DHCP/DNS server suite: kea-dhcp4/kea-dhcp6 "
                   "servers, kea-dhcp-ddns, kea-ctrl-agent, kea-lfc and keactrl, "
                   "with the core Kea libraries they load")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    # Server binaries AND linkable libraries ship together: consumers link
    # the libkea-* closure while the daemons run from bin/ (mysql-8.4 in this
    # repo is the precedent for the same server+library shape).  An
    # "application" package_type would strip cpp_info.libs/includedirs from
    # every consumer (CMakeDeps generates empty include dirs/libs for them),
    # which breaks the consumer-side link+API tests of test_package.
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "tests": [True, False]}
    default_options = {"shared": True, "tests": True}

    # The server executables this package is about (upstream installs them
    # into SBINDIR; Conan packages keep executables under bin/).
    kea_daemons = (
        "kea-dhcp4", "kea-dhcp6", "kea-dhcp-ddns", "kea-ctrl-agent", "kea-lfc",
    )
    # Core Kea shared libraries (the NEEDED closure of the daemons): every
    # shared_library() of src/lib that is built with mysql/postgresql/netconf
    # disabled, mapped to the source sub-directory that carries its public
    # headers.  They ship with the package so the servers are loadable.
    kea_libs = (
        ("kea-asiodns", "asiodns"),
        ("kea-asiolink", "asiolink"),
        ("kea-cc", "cc"),
        ("kea-cfgrpt", "process/cfgrpt"),
        ("kea-config", "config"),
        ("kea-cryptolink", "cryptolink"),
        ("kea-d2srv", "d2srv"),
        ("kea-database", "database"),
        ("kea-dhcp", "dhcp"),
        ("kea-dhcp_ddns", "dhcp_ddns"),
        ("kea-dhcpsrv", "dhcpsrv"),
        ("kea-dns", "dns"),
        ("kea-eval", "eval"),
        ("kea-exceptions", "exceptions"),
        ("kea-hooks", "hooks"),
        ("kea-http", "http"),
        ("kea-log", "log"),
        ("kea-log-interprocess", "log/interprocess"),
        ("kea-process", "process"),
        ("kea-stats", "stats"),
        ("kea-tcp", "tcp"),
        ("kea-util", "util"),
        ("kea-util-io", "util/io"),
    )
    # Upstream Meson gtest suites covering this package: the core libraries
    # (src/lib/*/tests) and the servers themselves (src/bin/*/tests).  The
    # hook-plugin suites (src/hooks/*/tests) belong to the separate
    # kea-hook-* packages, perfdhcp to kea-perfdhcp, and the shell
    # integration suites drive the daemons with live sockets, which the
    # package CI environment cannot provide.
    upstream_test_suites = (
        # src/lib core libraries
        "kea-asiodns-tests", "kea-asiolink-tests", "kea-cc-tests",
        "kea-config-backend-tests", "kea-config-tests", "kea-cryptolink-tests",
        "kea-d2srv-tests", "kea-database-tests", "kea-dhcp-ddns-tests",
        "kea-dhcp-tests", "kea-dhcpsrv-tests", "kea-dns-tests",
        "kea-eval-tests", "kea-exceptions-tests", "kea-hooks-tests",
        "kea-http-tests", "kea-log-init-tests", "kea-log-interprocess-tests",
        "kea-log-tests", "kea-process-cfgrpt-tests", "kea-process-tests",
        "kea-stats-tests", "kea-tcp-tests", "kea-util-tests",
        # src/bin servers
        "kea-agent-tests", "kea-d2-tests", "kea-dhcp4-tests",
        "kea-dhcp6-tests", "kea-lfc-tests",
    )
    # Ninja output paths (relative to the build directory) of the test
    # executables of the suites above.  The Ninja/Meson compile wrappers
    # cannot address them by bare name: the co1..co4 callout fixtures of
    # dhcp4/dhcp6/dhcpsrv and the callout/basic_auth/configured fixtures of
    # agent/d2 are shared_library targets with colliding names, so the whole
    # build set is addressed by output path.
    _test_executables = (
        # src/lib core libraries (note: kea-log-init-tests lives next to
        # kea-log-tests in src/lib/log/tests; the config_backend and
        # dhcp_ddns executables use underscore names, unlike their
        # hyphenated test() registration names)
        "src/lib/asiodns/tests/kea-asiodns-tests",
        "src/lib/asiolink/tests/kea-asiolink-tests",
        "src/lib/cc/tests/kea-cc-tests",
        "src/lib/config_backend/tests/kea-config_backend-tests",
        "src/lib/config/tests/kea-config-tests",
        "src/lib/cryptolink/tests/kea-cryptolink-tests",
        "src/lib/d2srv/tests/kea-d2srv-tests",
        "src/lib/database/tests/kea-database-tests",
        "src/lib/dhcp_ddns/tests/kea-dhcp_ddns-tests",
        "src/lib/dhcp/tests/kea-dhcp-tests",
        "src/lib/dhcpsrv/tests/kea-dhcpsrv-tests",
        "src/lib/dns/tests/kea-dns-tests",
        "src/lib/eval/tests/kea-eval-tests",
        "src/lib/exceptions/tests/kea-exceptions-tests",
        "src/lib/hooks/tests/kea-hooks-tests",
        "src/lib/http/tests/kea-http-tests",
        "src/lib/log/tests/kea-log-init-tests",
        "src/lib/log/interprocess/tests/kea-log-interprocess-tests",
        "src/lib/log/tests/kea-log-tests",
        "src/lib/process/cfgrpt/tests/kea-process-cfgrpt-tests",
        "src/lib/process/tests/kea-process-tests",
        "src/lib/stats/tests/kea-stats-tests",
        "src/lib/tcp/tests/kea-tcp-tests",
        "src/lib/util/tests/kea-util-tests",
        # src/bin servers
        "src/bin/agent/tests/kea-agent-tests",
        "src/bin/d2/tests/kea-d2-tests",
        "src/bin/dhcp4/tests/kea-dhcp4-tests",
        "src/bin/dhcp6/tests/kea-dhcp6-tests",
        "src/bin/lfc/tests/kea-lfc-tests",
    )
    # (build output path of the dlopen()ed fixture, defining tests dir) — the
    # callout libraries registered in the depends: lists of the upstream
    # test() definitions: co1..co4 of dhcp4/dhcp6, co1..co3 of dhcpsrv, the
    # hooks framework fixtures and the agent/d2 ones.
    _fixture_libs = (
        "src/bin/dhcp4/tests/libco1.so", "src/bin/dhcp4/tests/libco2.so",
        "src/bin/dhcp4/tests/libco3.so", "src/bin/dhcp4/tests/libco4.so",
        "src/bin/dhcp6/tests/libco1.so", "src/bin/dhcp6/tests/libco2.so",
        "src/bin/dhcp6/tests/libco3.so", "src/bin/dhcp6/tests/libco4.so",
        "src/lib/dhcpsrv/tests/libco1.so", "src/lib/dhcpsrv/tests/libco2.so",
        "src/lib/dhcpsrv/tests/libco3.so",
        "src/lib/hooks/tests/libnvl.so", "src/lib/hooks/tests/libivl.so",
        "src/lib/hooks/tests/libfxl.so", "src/lib/hooks/tests/libbcl.so",
        "src/lib/hooks/tests/liblcl.so", "src/lib/hooks/tests/liblecl.so",
        "src/lib/hooks/tests/libucl.so", "src/lib/hooks/tests/libfcl.so",
        "src/lib/hooks/tests/libpcl.so", "src/lib/hooks/tests/libacl.so",
        "src/bin/agent/tests/libcallout.so",
        "src/bin/agent/tests/libbasicauth.so",
        "src/bin/d2/tests/libcallout.so",
        "src/bin/d2/tests/libconfigured.so",
    )

    # gtest cases excluded from the upstream suites on OHOS.  Root causes
    # (all platform-environment limits, verified with a SIGSEGV backtrace
    # probe and direct reproductions on the OHOS target):
    #   1. AF_UNIX pathname-socket tests: bind(2) of a pathname unix socket
    #      is denied (EPERM/EACCES) on every filesystem an unprivileged
    #      process may write (tmpfs and hmfs alike); the abstract namespace
    #      works but Kea hardcodes pathname sockets.  The test-fixture
    #      Sandbox mkdtemp(P_tmpdir) then fails on the read-only /tmp and
    #      std::string(NULL) crashes inside the musl loader (strlen NULL).
    #      -> ClientConnectionTest, UnixCommandMgrTest, UnixDomainSocketTest,
    #         CtrlChannel{Dhcpv4,Dhcpv6,D2}Test, CtrlAgentCommandMgrTest
    #         (161 cases: the server control-channel fixtures).
    #   2. Read-only /tmp: MemfileLeaseMgrTest dataDir* open lease CSV files
    #      under /tmp (2 cases).
    #   3. unix-socket path length: the deep Conan build directory exceeds
    #      sockaddr_un::sun_path, ENAMETOOLONG in Dhcp{4,6}ParserTest.comments,
    #      Dhcp{4,6}GetConfigTest.run/{69,65} and the configWriteFullPath
    #      family writing through a control socket (6 cases).
    #   4. OHOS death-test semantics: FormatterTest.mismatchedPlaceholders
    #      expects the child death message on the parent console (1 case).
    #   5. chmod(S_IRUSR) does not block writes for the file owner on OHOS:
    #      PIDFileTest.pidWriteFail (1 case).
    #   6. Virtual interface inventory differs (ip6_vti0/ip6tnl0 have no
    #      matching addresses): IfaceMgrTest.detectIfaces (1 case).
    # meson test propagates the parent environment to the test processes
    # (verified in meson-logs/testlog.txt "Inherited environment").
    _ohos_gtest_filter = (
        "-ClientConnectionTest.*:UnixCommandMgrTest.*:UnixDomainSocketTest.*"
        ":CtrlChannelDhcpv4SrvTest.*:CtrlChannelDhcpv6SrvTest.*"
        ":CtrlChannelD2Test.*:CtrlAgentCommandMgrTest.*"
        ":FormatterTest.mismatchedPlaceholders:PIDFileTest.pidWriteFail"
        ":IfaceMgrTest.detectIfaces"
        ":MemfileLeaseMgrTest.dataDirEnvVarOverride"
        ":MemfileLeaseMgrTest.dataDirExplicitOveride"
        ":Dhcp4ParserTest.comments"
        ":Dhcp4GetConfigTest/Dhcp4GetConfigTest.run/69"
        ":HttpCtrlChannelDhcpv4Test.configWriteFullPath"
        ":HttpsCtrlChannelDhcpv4Test.configWriteFullPath"
        ":Dhcp6ParserTest.comments"
        ":Dhcp6GetConfigTest/Dhcp6GetConfigTest.run/65"
        ":HttpCtrlChannelDhcpv6Test.configWriteFullPath"
        ":HttpsCtrlChannelDhcpv6Test.configWriteFullPath"
        ":HttpCtrlChannelD2Test.configWriteFullPath"
        ":HttpsCtrlChannelD2Test.configWriteFullPath"
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the Kea 3.0.3 build.  boost is
        # pinned: 1.90/1.91 packages miss boost/interprocess, circular_buffer,
        # format and assign headers that Kea actually includes.  All three are
        # needed to compile the packaged headers (they appear in the include
        # chain of kea/dhcp, kea/dhcpsrv, kea/cc, kea/asiolink, kea/log),
        # hence transitive_headers.
        self.requires("boost/1.85.0", transitive_headers=True)
        self.requires("log4cplus/2.2.0.1", transitive_headers=True)
        self.requires("openssl/3.5.8.1", transitive_headers=True)

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
        # This also drops src/lib/yang (libkea-yang is only reachable through
        # the netconf option) and kea-netconf itself.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "disabled"
        tc.project_options["netconf"] = "disabled"
        tc.project_options["krb5"] = "disabled"
        # The OHOS musl <pthread.h> does not declare pthread_setcancelstate(),
        # which boost/core/detail/sp_thread_sleep.hpp calls (used through
        # Boost.Asio).  The upstream escape hatch keeps it compiling.
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        # Meson probes the static linker in project(); the OHOS build machines
        # do not expose llvm-ar/llvm-ranlib on PATH, so derive them from the
        # configured compiler location.
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

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        # Build exactly what this package owns, by ninja output path: the five
        # daemons (their libraries come along as build dependencies), plus
        # with tests=True the upstream test executables and their dlopen()ed
        # callout fixtures.
        targets = ["src/bin/{}".format(d) for d in
                   ("dhcp4/kea-dhcp4", "dhcp6/kea-dhcp6", "d2/kea-dhcp-ddns",
                    "agent/kea-ctrl-agent", "lfc/kea-lfc")]
        if self.options.tests:
            targets += list(self._test_executables) + list(self._fixture_libs)
        self.run('ninja -C "{}" {}'.format(self.build_folder, " ".join(targets)))
        if self.options.tests:
            # --no-rebuild: the targets above are already built; without it
            # meson would rebuild the whole Kea project (all hook plugins,
            # docs and premium sources) before running the suites.
            # On OHOS, drop the environment-limited cases from the gtest
            # binaries through GTEST_FILTER (see _ohos_gtest_filter for the
            # six root causes); meson test propagates the inherited
            # environment to every test process (verified in
            # meson-logs/testlog.txt "Inherited environment").
            test_env = Environment()
            if str(self.settings.os) == "OHOS":
                test_env.define("GTEST_FILTER", self._ohos_gtest_filter)
            with test_env.vars(self).apply():
                self.run('meson test -v --no-rebuild -C "{}" {}'.format(
                    self.build_folder, " ".join(self.upstream_test_suites)))

    def _is_packaged_lib(self, name):
        if name.endswith(".symbols"):  # meson SHSYM intermediate, not shipped
            return False
        libs = tuple(lib for lib, _ in self.kea_libs)
        # Meson emits the shared libraries with the platform "lib" prefix
        # (libkea-dhcp.so.109.0.0); cpp_info.libs below uses the bare names,
        # which Conan resolves back to lib<name>.so for the consumers.
        return any(name == "lib{}.so".format(lib) or name.startswith("lib{}.so.".format(lib))
                   for lib in libs)

    def _copy_kea_libraries(self):
        """Ship the built Kea libraries, recreating the soname symlinks."""
        lib_dst = os.path.join(self.package_folder, "lib")
        for root, dirs, files in os.walk(os.path.join(self.build_folder, "src", "lib")):
            dirs[:] = [d for d in dirs if not d.endswith(".p")]
            for name in files:
                if not self._is_packaged_lib(name):
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

    def _copy_kea_headers(self):
        """Copy the public headers as upstream installs them: include/kea/<lib>."""
        for _lib, srcdir in self.kea_libs:
            src_root = os.path.join(self.source_folder, "src", "lib", srcdir)
            dst_root = os.path.join(self.package_folder, "include", "kea", srcdir)
            for root, dirs, files in os.walk(src_root):
                dirs[:] = [d for d in dirs if d != "tests"]
                for name in files:
                    if not name.endswith(".h"):
                        continue
                    relative = os.path.relpath(os.path.join(root, name), src_root)
                    dst_path = os.path.join(dst_root, relative)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(os.path.join(root, name), dst_path)
        # Generated headers (meson configure_file output, installed by the
        # upstream install step into INCLUDEDIR/kea).
        for hdr in ("kea_version.h", "config.h"):
            src = os.path.join(self.build_folder, hdr)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(self.package_folder, "include", "kea", hdr))

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Servers: upstream installs them into SBINDIR; Conan packages keep
        # executables under bin/, which is what the CI and consumers expect.
        for daemon, subdir in (("kea-dhcp4", "dhcp4"), ("kea-dhcp6", "dhcp6"),
                               ("kea-dhcp-ddns", "d2"), ("kea-ctrl-agent", "agent"),
                               ("kea-lfc", "lfc")):
            copy(self, daemon, src=os.path.join(self.build_folder, "src", "bin", subdir),
                 dst=os.path.join(self.package_folder, "bin"))
        # keactrl management script (configure_file output of src/bin/keactrl).
        copy(self, "keactrl", src=os.path.join(self.build_folder, "src", "bin", "keactrl"),
             dst=os.path.join(self.package_folder, "bin"))
        # Example/reference configurations generated by the keactrl build
        # (keactrl.conf and the per-daemon .conf files).
        copy(self, "*.conf", src=os.path.join(self.build_folder, "src", "bin", "keactrl"),
             dst=os.path.join(self.package_folder, "res", "kea"))
        # Executables must keep the execution bit whatever the source
        # filesystem did to them (meson configure_file output is not
        # guaranteed to carry it over from the .in template).
        for name in list(self.kea_daemons) + ["keactrl"]:
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        self._copy_kea_libraries()
        self._copy_kea_headers()

    def package_info(self):
        # Application package: the servers go on PATH and the Kea libraries
        # stay in lib/ so the generated run environment resolves them (the
        # binaries' upstream install RPATH points at the build-machine
        # prefix, which a Conan package cannot rely on).  The libraries are
        # also linkable for consumers embedding Kea (cpp_info.libs), the
        # same way the kea-hooks package exposes them.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = [lib for lib, _ in self.kea_libs]
        # Kea installs its headers under <prefix>/include/kea and includes
        # them as <cc/session.h>, <dhcp/...>, so the include root is
        # include/kea.
        self.cpp_info.includedirs = [os.path.join("include", "kea")]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os == "OHOS":
            # The packaged Kea headers reach boost/core/detail/sp_thread_sleep.hpp
            # (through Boost.Asio and boost/shared_ptr.), which calls
            # pthread_setcancelstate() that the OHOS musl pthread.h does not
            # declare.  Consumers need the same boost escape hatch this recipe
            # uses while building.
            self.cpp_info.defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
