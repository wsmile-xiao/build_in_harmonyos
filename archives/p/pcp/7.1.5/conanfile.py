#!/usr/bin/env python3
"""Conan recipe — PCP (Performance Co-Pilot) 7.1.5, minimal component set.

OHOS adaptation (path B knowledge extension):
- config.sub: add linux-ohos triplet (2 places)
- /tmp read-only (E002): mktemp scripts use ${TMPDIR:-/tmp}
- FILE opaque type: portable replacement for glibc struct copy in util.c (libpcp + libpcp3)
- rindex -> strrchr (OHOS libc has no BSD rindex)
- qsort_r: route OHOS to portable sort_r_simple (OHOS libc lacks qsort_r)
- CROSS_COMPILING=yes: skip .static executables (static link infeasible on OHOS)
- --with-make: PCP configure clears $MAKE by default then looks for 'gmake';
  the OHOS toolchain has no gmake alias, so pass the toolchain make path
- in-tree build: PCP's build system has no VPATH support (top-level
  GNUmakefile uses TOPDIR=. and recurses into in-tree SUBDIRS; C install
  rules take paths from prefix and ignore DESTDIR). configure/make/install
  all run in the source folder with --prefix=<package_folder> (repo
  in-tree pattern, cf. bison)
- PCP_CONF: point to build-tree pcp.conf (avoids /etc/pcp.conf which is not writable)
- LDFLAGS: -lpthread + -Wl,--allow-shlib-undefined (OHOS lld default is --no-allow-shlib-undefined)
- umask 077->007 in configure: hmdfs owner-inheritance makes umask-077 temp
  dirs (mode 700) owned by the cache uid, not writable by this process

Minimal component set (--without-*): core pmcd/pmlogger/pmstat/pmval + pmapi;
python3/perl/qt/optional PMDAs/systemd/selinux/secure-sockets/perfevent all disabled.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PcpConan(ConanFile):
    name = "pcp"
    version = "7.1.5"
    description = "Performance Co-Pilot (PCP) - system performance monitoring and management"
    license = "GPL-2.0"
    homepage = "https://performancecopilot.github.io"
    url = "https://github.com/performancecopilot/pcp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")
        self.requires("libxml2/2.15.3.1")
        self.requires("lmdb/0.9.35")
        self.requires("libuv/1.52.1.1")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # PCP's configure options — shared between generate() (toolchain env) and
    # build() (manual in-tree configure). Defined here as the single source.
    _CONFIGURE_FEATURES = [
        "--with-64bit",
        "--with-threads",
        "--without-perl",
        "--without-python3",
        "--without-qt",
        "--without-qt3d",
        "--without-x",
        "--without-systemd",
        "--without-selinux",
        "--without-secure-sockets",
        "--without-infiniband",
        "--without-static-probes",
        "--without-perfevent",
        "--without-pmdagfs2",
        "--without-pmdastatsd",
        "--without-pmdabpf",
        "--without-pmdabpftrace",
        "--without-pmdajson",
        "--without-pmdamongodb",
        "--without-pmdamysql",
        "--without-pmdanutcracker",
        "--without-pmdasnmp",
        "--without-dstat-symlink",
        "--without-gperftools",
    ]

    @staticmethod
    def _find_make():
        """Toolchain GNU make. shutil.which() may miss it in the generate()
        context (different PATH), so fall back to the known toolchain bin dir."""
        m = shutil.which("make")
        if m:
            return m
        for d in ("/data/service/hnp/bin", "/usr/local/bin", "/usr/bin"):
            cand = os.path.join(d, "make")
            if os.path.isfile(cand):
                return cand
        return None

    def generate(self):
        # Toolchain env only (CC/CXX/CFLAGS + tool_requires flex/bison PATH +
        # profile buildenv). configure itself is invoked manually in build()
        # (in-tree — see module docstring), so the toolchain's configure_args
        # are not used for the actual configure call.
        tc = AutotoolsToolchain(self)
        tc.generate()

        # NOTE (local AI review 2026-10-13): the former pcp_build_env script
        # was removed — this conan's self.run() only sources the aggregated
        # "conanbuild" env, so a standalone named script was never sourced.
        # TMPDIR/PCP_TMPFILE_DIR and the LDFLAGS relaxation flag are now
        # inlined on the configure/make/install commands in build()/package()
        # (deterministic, visible on the command line, identical on local W3
        # and CI). The consumer-side relaxation stays in package_info
        # (exelinkflags/sharedlinkflags).

    def _make_override_vars(self):
        """Make command-line overrides shared by build() and package().

        CROSS_COMPILING=yes + PCP_CONF + PCP_SORT_PROG + the four PM* recipe
        overrides (in-tree dynamic binaries, in-tree libs on the loader path).

        Why each piece (also needed by package(), not just build()):
        - CROSS_COMPILING=yes: empties STATICTARGETS, skipping the .static
          executables which cannot link on OHOS (static libpthread lacks
          pthread_cancel/pthread_setcancelstate — verified: pmieconf.static
          link fails with "undefined symbol: pthread_cancel"). Without it,
          `make install` (whose default_pcp prerequisite re-checks every
          target) rebuilds pmcpp.static & co and fails.
        - PM* overrides: with CROSS_COMPILING=yes builddefs switches
          PMIECONF/PMGENMAP/PMCPP/NEWHELP to "use the PCP installed on the
          build machine" (nothing installed on a clean worker). Command-line
          variables override makefile definitions and propagate to sub-makes;
          $(TOPDIR) expands in each sub-make's context. This restores the
          in-tree semantics of the non-cross branch, but with the just-built
          DYNAMIC binaries instead of the un-buildable .static ones.
        - PCP_ALT_CPP: pmns.c prefers $PCP_ALT_CPP over the installed pmcpp
          when preprocessing PMNS files; points at the in-tree dynamic pmcpp.
        - LD_LIBRARY_PATH: the in-tree dynamic binaries carry no RPATH (PCP
          upstream always runs in-tree tools via the .static binaries). Point
          the loader at the in-tree lib dirs; conan-managed dep lib paths
          already in $LD_LIBRARY_PATH are preserved (make $$ -> shell $).
        - PCP_SORT_PROG: referenced by makefiles but never defined as a make
          variable (normally comes from the developer's shell env); configure
          detected /system/bin/sort which is not reliably usable — pass the
          toybox sort explicitly.
        """
        in_tree_libs = ":".join(
            "$(TOPDIR)/src/{}/src".format(d) for d in (
                "libpcp", "libpcp3", "libpcp_archive", "libpcp_fault",
                "libpcp_import", "libpcp_mmv", "libpcp_pmda",
                "libpcp_trace", "libpcp_web",
            )
        )
        pcp_conf = os.path.join(self.source_folder, "src", "include", "pcp.conf")
        return (
            f'CROSS_COMPILING=yes PCP_CONF="{pcp_conf}" PCP_SORT_PROG=/usr/bin/sort '
            "'PMIECONF=PCP_CONF=$(TOPDIR)/src/include/pcp.conf "
            f"LD_LIBRARY_PATH={in_tree_libs}:$$LD_LIBRARY_PATH "
            "PCP_ALT_CPP=$(TOPDIR)/src/pmcpp/pmcpp $(TOPDIR)/src/pmieconf/pmieconf' "
            "'PMGENMAP=PCP_CONF=$(TOPDIR)/src/include/pcp.conf "
            "PCP_ALT_CPP=$(TOPDIR)/src/pmcpp/pmcpp sh ./pmgenmap.sh' "
            "'PMCPP=PCP_CONF=$(TOPDIR)/src/include/pcp.conf "
            f"LD_LIBRARY_PATH={in_tree_libs}:$$LD_LIBRARY_PATH "
            "PCP_ALT_CPP=$(TOPDIR)/src/pmcpp/pmcpp $(TOPDIR)/src/pmcpp/pmcpp' "
            "'NEWHELP=PCP_CONF=$(TOPDIR)/src/include/pcp.conf "
            f"LD_LIBRARY_PATH={in_tree_libs}:$$LD_LIBRARY_PATH "
            "PCP_ALT_CPP=$(TOPDIR)/src/pmcpp/pmcpp $(TOPDIR)/src/newhelp/newhelp'"
        )

    def build(self):
        apply_conandata_patches(self)
        # E002: /tmp is read-only on OHOS, and conan's build sandbox sets
        # TMPDIR to <build>/tmp which clang/config.guess cannot use. Force a
        # known-writable dir in the build process env (subprocess inherits).
        tmp_dir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = tmp_dir
        os.environ["PCP_TMPFILE_DIR"] = tmp_dir
        self.output.info(f"TMPDIR forced to {tmp_dir} (E002 /tmp read-only + conan sandbox)")
        # E490: ensure autotools helper scripts are executable (OHOS FS may
        # strip the +x bit on extraction).
        for script in ["configure", "config.guess", "config.sub", "install-sh"]:
            p = os.path.join(self.source_folder, script)
            if os.path.exists(p):
                os.chmod(p, 0o755)
        for sub in ("config", "aclocal"):
            d = os.path.join(self.source_folder, sub)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    fp = os.path.join(d, f)
                    if os.path.isfile(fp):
                        os.chmod(fp, 0o755)
        # OHOS hmdfs: new files inherit the PARENT directory's owner. The conan
        # cache is owned by another uid, so the umask-077 temp dirs that
        # configure/config.status create (mode 700) are not writable by this
        # process -> "Permission denied" on ./confXXXXXX/subs1.awk. Relax
        # umask 077 -> 007 (4 occurrences, all temp-dir creation): the temp
        # dirs become mode 770 and this process is in the parent dir's group
        # (setgid inheritance), so group-writable is sufficient.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r", encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
            n = content.count("umask 077")
            content = content.replace("umask 077", "umask 007")
            with open(configure_path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(content)
            self.output.info(f"umask 077 -> 007 in configure ({n} occurrences, hmdfs owner-inheritance workaround)")

        make_bin = self._find_make()
        if not make_bin:
            raise RuntimeError("GNU make not found (expected /data/service/hnp/bin/make)")

        # IN-TREE configure: PCP has no out-of-tree build support (top-level
        # GNUmakefile TOPDIR=. + in-tree SUBDIRS recursion; C install rules
        # take paths from prefix and ignore DESTDIR). --prefix points straight
        # at the conan package folder so `make install` populates it directly
        # (no shared /usr/local — R49 compliant, private per-package dir).
        # PCP configure clears $MAKE by default ('--with-make' default is
        # empty), then looks for 'gmake'; the toolchain has no gmake alias,
        # so pass the make path explicitly.
        shared_flag = "--enable-shared" if self.options.shared else "--disable-shared"
        configure_args = [
            f"--prefix={self.package_folder}",
            shared_flag,
            "--build=aarch64-linux-ohos",
            "--host=aarch64-linux-ohos",
            f"--with-make={make_bin}",
        ] + self._CONFIGURE_FEATURES
        configure_cmd = (
            f'cd "{self.source_folder}" && '
            f'TMPDIR="{tmp_dir}" PCP_TMPFILE_DIR="{tmp_dir}" '
            f"./configure " + " ".join(f'"{a}"' if " " in a else a for a in configure_args)
        )
        self.run(configure_cmd)

        # IN-TREE make (see _make_override_vars() for why each override exists).
        # LDFLAGS inlined on the command: no makefile overrides $(LDFLAGS)
        # (e.g. src/pmns/GNUmakefile:41 uses it directly), so the make process
        # env value reaches every link rule and sub-make. OHOS lld defaults to
        # --no-allow-shlib-undefined and libpcp*.so carry U pthread_cancel
        # (sysroot libc lacks it; device libc has it), so executable links
        # (pmnsmerge & co) need the relaxation.
        make_cmd = (
            f'cd "{self.source_folder}" && '
            f'TMPDIR="{tmp_dir}" LDFLAGS="-lpthread -Wl,--allow-shlib-undefined" '
            f'"{make_bin}" -j1 {self._make_override_vars()}'
        )
        self.output.info("Running in-tree make -j1 (in-tree only; PM* recipes overridden to in-tree dynamic binaries)")
        self.run(make_cmd)

    def package(self):
        # IN-TREE make install: prefix (= package folder) is baked into the
        # generated Makefiles at configure time; PCP's C install rules ignore
        # DESTDIR, so run from the source folder without DESTDIR. install-sh
        # tolerates the -o/-g chown failing for non-root (warns once).
        # The build() make overrides are REQUIRED here too (see
        # _make_override_vars): without CROSS_COMPILING=yes the `make
        # install` default_pcp prerequisite re-checks every target and
        # rebuilds the .static executables, which cannot link on OHOS.
        make_bin = self._find_make()
        if not make_bin:
            raise RuntimeError("GNU make not found (expected /data/service/hnp/bin/make)")
        # E002: same TMPDIR forcing as build() — package() runs in a separate
        # process and does not inherit build()'s os.environ changes. LDFLAGS
        # likewise inlined: if the install-time prerequisite re-check rebuilds
        # anything, its links need the relaxation flag too.
        tmp_dir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.run(
            f'cd "{self.source_folder}" && '
            f'TMPDIR="{tmp_dir}" LDFLAGS="-lpthread -Wl,--allow-shlib-undefined" '
            f'"{make_bin}" -j1 install {self._make_override_vars()}'
        )

    def package_info(self):
        # libpcp*.so may carry U pthread_cancel / U pthread_setcancelstate:
        # those symbols live in the device libc but not in the sysroot libc.
        # lld for the OHOS target defaults to --no-allow-shlib-undefined,
        # which can reject such .so at consumer link time — propagate the
        # relaxation flag to every consumer. (The build itself gets the flag
        # via the LDFLAGS inlined on its make/install commands.)
        self.cpp_info.exelinkflags = ["-Wl,--allow-shlib-undefined"]
        self.cpp_info.sharedlinkflags = ["-Wl,--allow-shlib-undefined"]
        # Only libraries that exist as linkable .so files in lib/ (CMakeDeps
        # verifies each entry). libpcp.so.3 is a legacy soname of libpcp (no
        # separate libpcp3 file), so it is not declared as its own lib.
        self.cpp_info.libs = [
            "pcp", "pcp_archive", "pcp_fault", "pcp_gui",
            "pcp_import", "pcp_mmv", "pcp_pmda", "pcp_trace", "pcp_web",
        ]
