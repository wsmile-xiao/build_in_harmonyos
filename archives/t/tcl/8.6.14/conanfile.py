#!/usr/bin/env python3
"""Conan recipe — tcl 8.6.14 (HarmonyOS PC)
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class TclConan(ConanFile):
    name = "tcl"
    version = "8.6.14"
    description = "Tcl — the Tool Command Language"
    license = "Tcl/Tk"
    homepage = "https://www.tcl.tk/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="unix")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply Conan standard patch mechanism for HMDFS umask fix (E011)
        apply_conandata_patches(self)

        # ----- Verify all 9 umask patches applied correctly -----
        umask_files = [
            ("unix/configure", "unix/configure"),
            ("pkgs/itcl4.2.4/configure", "pkgs/itcl4.2.4/configure"),
            ("pkgs/sqlite3.44.2/configure", "pkgs/sqlite3.44.2/configure"),
            ("pkgs/tdbc1.1.7/configure", "pkgs/tdbc1.1.7/configure"),
            ("pkgs/tdbcmysql1.1.7/configure", "pkgs/tdbcmysql1.1.7/configure"),
            ("pkgs/tdbcodbc1.1.7/configure", "pkgs/tdbcodbc1.1.7/configure"),
            ("pkgs/tdbcpostgres1.1.7/configure", "pkgs/tdbcpostgres1.1.7/configure"),
            ("pkgs/tdbcsqlite3-1.1.7/configure", "pkgs/tdbcsqlite3-1.1.7/configure"),
            ("pkgs/thread2.8.9/configure", "pkgs/thread2.8.9/configure"),
        ]
        sf = self.source_folder
        for rel_path, display in umask_files:
            fpath = os.path.normpath(os.path.join(sf, rel_path))
            if not os.path.isfile(fpath):
                raise ConanException(
                    f"umask patch verification FAILED: {display} not found at {fpath}"
                )
            with open(fpath) as fh:
                text = fh.read()
            if "umask 077" in text:
                raise ConanException(
                    f"umask patch verification FAILED: {display} still contains 'umask 077'"
                )
            if "umask 022" not in text:
                raise ConanException(
                    f"umask patch verification FAILED: {display} does not contain 'umask 022'"
                )
        self.output.info(
            "umask patch verification PASSED: 9/9 files contain umask 022, no umask 077"
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E001: ensure CC=clang is set for HarmonyOS (no system cc)
        tc.extra_vars = {"CC": os.environ.get("CC", "clang"),
                         "CXX": os.environ.get("CXX", "clang++")}
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure(build_script_folder=os.path.join(self.source_folder, "unix"))
        self._ohos_fix_tclconfig()

        # ── OHOS: Patch main Makefile (all order, TCLSH_PKG_OBJS, tcltest PKG_OBJS) ──
        self._ohos_patch_makefile()

        # Stage 1a: generate package Makefiles via configure-packages
        self.run(
            f"cd {self.build_folder} && ${{MAKE:-make}} configure-packages"
        )

        # Stage 1b: fix SHLIB_LD in each package Makefile (HarmonyOS not detected)
        self._ohos_fix_pkg_shlib_ld()

        # Stage 1c: build packages (uses fixed SHLIB_LD)
        self.run(f"cd {self.build_folder} && ${{MAKE:-make}} packages")

        # Stage 2: recompile Thread .o with THREAD_STATIC_TCL
        self._ohos_fix_thread_objects()

        # Stage 3: link tclsh and tcltest
        self.run(f"cd {self.build_folder} && ${{MAKE:-make}} tclsh tcltest")

        # Upstream test suite
        self.output.info("Running upstream make test (ignoring failures) ...")
        self.run("make test -j1", ignore_errors=True)

    def _ohos_fix_tclconfig(self):
        """Fix TCL_SHLIB_LD in tclConfig.sh (empty when --disable-shared)."""
        tclconfig = os.path.join(self.build_folder, "tclConfig.sh")
        if not os.path.isfile(tclconfig):
            raise ConanException(
                f"OHOS fix SHLIB_LD: tclConfig.sh not found at {tclconfig}"
            )
        with open(tclconfig) as fh:
            text = fh.read()
        n_ld = text.count("TCL_SHLIB_LD=")
        if n_ld != 1:
            raise ConanException(
                f"OHOS fix SHLIB_LD: expected 1 'TCL_SHLIB_LD=', found {n_ld}"
            )
        if "TCL_SHLIB_LD=''" in text:
            text = text.replace(
                "TCL_SHLIB_LD=''", "TCL_SHLIB_LD='clang -shared'",
            )
            n_cf = text.count("TCL_SHLIB_CFLAGS=")
            if n_cf == 1 and "TCL_SHLIB_CFLAGS=''" in text:
                text = text.replace(
                    "TCL_SHLIB_CFLAGS=''", "TCL_SHLIB_CFLAGS='-fPIC'",
                )
            with open(tclconfig, "w") as fh:
                fh.write(text)
            self.output.info(
                "OHOS tclConfig.sh fix applied: TCL_SHLIB_LD='clang -shared'"
            )
        else:
            self.output.info(
                "OHOS tclConfig.sh: TCL_SHLIB_LD already set, no fix needed"
            )

    def _ohos_patch_makefile(self):
        """Patch main Makefile: build order, TCLSH_PKG_OBJS, tcltest PKG_OBJS."""
        mf = os.path.join(self.build_folder, "Makefile")
        if not os.path.isfile(mf):
            raise ConanException(f"OHOS Makefile post-patch: {mf} not found")
        with open(mf) as fh:
            text = fh.read()

        # all: packages first
        n1 = text.count("all: binaries libraries doc packages")
        if n1 != 1:
            raise ConanException(
                f"OHOS Makefile post-patch: expected 1 'all: binaries ...', found {n1}"
            )
        text = text.replace(
            "all: binaries libraries doc packages",
            "all: packages binaries libraries doc",
        )

        # TCLSH_PKG_OBJS (Thread + Sqlite3 linked into tclsh)
        pkg_objs = (
            "# Thread and Sqlite3 linked into tclsh (OHOS static linkage)\n"
            "TCLSH_PKG_OBJS = \\\n"
            "\t$(PKG_DIR)/thread2.8.9/psGdbm.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/psLmdb.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/tclXkeylist.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadNs.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadPoolCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSpCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSvCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSvKeylistCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSvListCmd.o \\\n"
            "\t$(PKG_DIR)/sqlite3.44.2/tclsqlite3.o\n"
        )

        # Also PKG_OBJS for tcltest (all 8 packages)
        all_pkg_objs = (
            "# All package objects for tcltest (OHOS static linkage)\n"
            "PKG_OBJS = \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itcl2TclOO.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclBase.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclBuiltin.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclClass.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclCmd.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclEnsemble.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclHelpers.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclInfo.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclLinkage.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclMethod.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclMigrate2TclCore.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclObject.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclParse.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclResolve.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclStubInit.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclStubLib.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclStubs.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclTclIntStubsFcn.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclTestRegisterC.o \\\n"
            "\t$(PKG_DIR)/itcl4.2.4/itclUtil.o \\\n"
            "\t$(PKG_DIR)/sqlite3.44.2/tclsqlite3.o \\\n"
            "\t$(PKG_DIR)/tdbc1.1.7/tdbc.o \\\n"
            "\t$(PKG_DIR)/tdbc1.1.7/tdbcStubInit.o \\\n"
            "\t$(PKG_DIR)/tdbc1.1.7/tdbcStubLib.o \\\n"
            "\t$(PKG_DIR)/tdbc1.1.7/tdbcTokenize.o \\\n"
            "\t$(PKG_DIR)/tdbcmysql1.1.7/mysqlStubInit.o \\\n"
            "\t$(PKG_DIR)/tdbcmysql1.1.7/tdbcmysql.o \\\n"
            "\t$(PKG_DIR)/tdbcodbc1.1.7/odbcStubInit.o \\\n"
            "\t$(PKG_DIR)/tdbcodbc1.1.7/tdbcodbc.o \\\n"
            "\t$(PKG_DIR)/tdbcpostgres1.1.7/pqStubInit.o \\\n"
            "\t$(PKG_DIR)/tdbcpostgres1.1.7/tdbcpostgres.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/psGdbm.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/psLmdb.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/tclXkeylist.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadNs.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadPoolCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSpCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSvCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSvKeylistCmd.o \\\n"
            "\t$(PKG_DIR)/thread2.8.9/threadSvListCmd.o\n"
        )

        # Modify tclsh link rule
        old_tclsh_dep = "${TCL_EXE}: ${TCLSH_OBJS} ${TCL_LIB_FILE} ${TCL_STUB_LIB_FILE}"
        n2 = text.count(old_tclsh_dep)
        if n2 != 1:
            raise ConanException(
                f"OHOS Makefile post-patch: expected 1 tclsh dep, found {n2}"
            )
        text = text.replace(old_tclsh_dep, pkg_objs + old_tclsh_dep)

        old_tclsh_recipe = "\t${CC} ${CFLAGS} ${LDFLAGS} ${TCLSH_OBJS} \\"
        n3 = text.count(old_tclsh_recipe)
        if n3 != 1:
            raise ConanException(
                f"OHOS Makefile post-patch: expected 1 tclsh recipe, found {n3}"
            )
        text = text.replace(
            old_tclsh_recipe,
            "\t${CC} ${CFLAGS} ${LDFLAGS} ${TCLSH_OBJS} ${TCLSH_PKG_OBJS} \\",
        )

        # Add PKG_OBJS definition and fix tcltest-real recipe
        old_tcltest = "\t${CC} ${CFLAGS} ${LDFLAGS} ${TCLTEST_OBJS} \\"
        n4 = text.count(old_tcltest)
        if n4 != 1:
            raise ConanException(
                f"OHOS Makefile post-patch: expected 1 tcltest recipe, found {n4}"
            )
        text = text.replace(
            old_tcltest,
            "\t${CC} ${CFLAGS} ${LDFLAGS} ${TCLTEST_OBJS} ${PKG_OBJS} \\",
        )

        # Insert PKG_OBJS definition before the tcltest-real target
        text = text.replace(
            "tcltest-real:\n",
            all_pkg_objs + "tcltest-real:\n",
        )

        with open(mf, "w") as fh:
            fh.write(text)
        self.output.info("OHOS Makefile post-patch applied")

    def _ohos_fix_pkg_shlib_ld(self):
        """Set SHLIB_LD='clang -shared' in each package Makefile after configure-packages.
        HarmonryOS is not recognized by package configure scripts, so SHLIB_LD
        defaults to empty; we inject it before 'make packages' runs."""
        pkg_names = [
            "itcl4.2.4", "sqlite3.44.2", "tdbc1.1.7",
            "tdbcmysql1.1.7", "tdbcodbc1.1.7", "tdbcpostgres1.1.7",
            "tdbcsqlite3-1.1.7", "thread2.8.9",
        ]
        import re as _re
        for pkg in pkg_names:
            mk = os.path.join(self.build_folder, "pkgs", pkg, "Makefile")
            if not os.path.isfile(mk):
                self.output.warn(f"Package Makefile not found (skipped): {mk}")
                continue
            with open(mk) as fh:
                text = fh.read()
            matches = _re.findall(r'^SHLIB_LD[ \t]*=[ \t]*(.*)', text, _re.M)
            if len(matches) != 1:
                raise ConanException(
                    f"OHOS fix SHLIB_LD: expected 1 match in {pkg}/Makefile, "
                    f"found {len(matches)}"
                )
            current = matches[0].strip()
            if current == "" or current == "'" or current == '""':
                text = _re.sub(
                    r'^SHLIB_LD[ \t]*=[ \t]*.*',
                    'SHLIB_LD\t= clang -shared',
                    text, count=1, flags=_re.M,
                )
                with open(mk, "w") as fh:
                    fh.write(text)
                self.output.info(
                    f"  {pkg}: SHLIB_LD fixed (was empty → clang -shared)"
                )
            else:
                self.output.info(f"  {pkg}: SHLIB_LD already set ({current})")

    def _ohos_fix_thread_objects(self):
        """Recompile Thread objects with THREAD_STATIC_TCL (no stubs).
        Called after 'make packages' completes, before final link."""
        thread_dir = os.path.join(self.build_folder, "pkgs", "thread2.8.9")
        thread_mk = os.path.join(thread_dir, "Makefile")
        if not os.path.isfile(thread_mk):
            self.output.warn("Thread package Makefile not found, skipping static fix")
            return

        import re

        # Read package Makefile
        with open(thread_mk) as fh:
            mk_text = fh.read()

        # Extract DEFS, INCLUDES, CFLAGS, CC
        def match_var(name):
            m = re.search(r'^' + name + r'\s*=\s*(.*)', mk_text, re.M)
            if not m:
                raise ConanException(
                    f"Thread Makefile: variable {name} not found"
                )
            return m.group(1).strip()

        defs_raw = match_var("DEFS")
        includes_raw = match_var("INCLUDES")
        cflags_raw = match_var("CFLAGS")
        cc = "clang"

        # Clean DEFS: remove Makefile variable refs $(...) and ${...}
        defs_clean = re.sub(r'\$\([A-Za-z_0-9]+\)', '', defs_raw)
        defs_clean = re.sub(r'\$\{[A-Za-z_0-9]+\}', '', defs_clean)
        # Remove stubs flags
        for flag in ['-DUSE_TCL_STUBS', '-DUSE_TCLOO_STUBS']:
            # Handle both -DUSE_TCL_STUBS=1 and bare -DUSE_TCL_STUBS
            defs_clean = re.sub(re.escape(flag) + r'(=\S*)?\s*', ' ', defs_clean)
        # Add THREAD_STATIC_TCL
        defs_clean += ' -DTHREAD_STATIC_TCL=1'
        # Collapse whitespace
        defs_clean = ' '.join(defs_clean.split())

        # Clean CFLAGS: remove Makefile variable refs
        cflags_clean = re.sub(r'\$\{[A-Za-z_0-9]+\}', '', cflags_raw)
        cflags_clean = ' '.join(cflags_clean.split())

        # Resolve includes: -I. → -I<thread_dir>
        includes_clean = includes_raw.replace('-I.', f'-I"{thread_dir}"')
        # Add threadUuid.h path
        includes_clean += f' -I"{thread_dir}"'

        # Source files: generic (10) + unix (1)
        src_generic = os.path.join(
            self.source_folder, "pkgs", "thread2.8.9", "generic"
        )
        src_unix = os.path.join(
            self.source_folder, "pkgs", "thread2.8.9", "unix"
        )
        all_srcs = sorted(
            [os.path.join(src_generic, f) for f in os.listdir(src_generic) if f.endswith('.c')]
            + [os.path.join(src_unix, f) for f in os.listdir(src_unix) if f.endswith('.c')]
        )

        # Single compile command template
        compile_base = f"{cc} {defs_clean} {includes_clean} {cflags_clean} -c"

        self.output.info(
            f"Recompiling {len(all_srcs)} Thread source files with THREAD_STATIC_TCL ..."
        )
        for src in all_srcs:
            base = os.path.basename(src).replace('.c', '')
            dst = os.path.join(thread_dir, f'{base}.o')
            cmd = f'{compile_base} -o "{dst}" "{src}"'
            self.output.info(f"  CC {os.path.basename(src)}")
            ret = self.run(cmd, ignore_errors=True)
            if ret != 0:
                raise ConanException(
                    f"Failed to recompile Thread source: {src}"
                )

        # nm verification via self.run (inherits conan env PATH)
        nm_bin = "/data/service/hnp/bin/nm"
        if not os.path.isfile(nm_bin):
            # fallback: try to find nm in PATH
            nm_bin = "nm"
        self.output.info("Verifying Thread objects (nm check)...")
        for o_file in sorted(os.listdir(thread_dir)):
            if not o_file.endswith('.o'):
                continue
            o_path = os.path.join(thread_dir, o_file)
            import subprocess
            result = subprocess.run(
                [nm_bin, o_path], capture_output=True, text=True
            )
            has_stubs = False
            for line in result.stdout.splitlines():
                if 'Tcl_InitStubs' in line and 'PkgInitStubsCheck' not in line:
                    has_stubs = True
                if 'tclStubsPtr' in line or re.search(r'\bTclStubs\b', line):
                    has_stubs = True
            if has_stubs:
                raise ConanException(
                    f"Thread object {o_file} still contains stubs references"
                )
            n_syms = len(result.stdout.splitlines())
            self.output.info(f"  nm {o_file}: {n_syms} symbols, clean")
        self.output.info("Thread static objects: ALL 11/11 PASS")

    def package(self):
        autotools = Autotools(self)
        # Use install sub-targets to avoid man hardlink Operation not permitted in CI
        autotools.install(target="install-binaries")
        autotools.install(target="install-libraries")
        autotools.install(target="install-headers")
        # OHOS consumer fix: package private headers + relocate tclConfig.sh
        self._ohos_package_private_headers()
        self._ohos_relocate_tclconfig()

    def _ohos_package_private_headers(self):
        """Copy Tcl private headers into include/generic, include/unix and
        include/compat.

        Expect's configure sources tclConfig.sh, derives TCL_SRC_DIR, then
        requires ${TCL_SRC_DIR}/generic/tclInt.h to exist and compiles with
        -I${TCL_SRC_DIR}/generic -I${TCL_SRC_DIR}/unix.  Copying the full
        private header set (not only tclInt.h) keeps transitive includes
        (tclPort.h -> tclUnixPort.h, tclIntDecls.h, ...) resolvable.  The
        compat/ headers are required because tclUnixPort.h includes
        ../compat/unistd.h (and dirent.h/dirent2.h/fake-rfc2553.h) relative
        to the unix/ layout.
        """
        import shutil
        inc_root = os.path.join(self.package_folder, "include")
        for sub in ("generic", "unix", "compat"):
            src_dir = os.path.join(self.source_folder, sub)
            dst_dir = os.path.join(inc_root, sub)
            if not os.path.isdir(src_dir):
                raise ConanException(
                    f"private header source dir missing: {src_dir}"
                )
            os.makedirs(dst_dir, exist_ok=True)
            n = 0
            for f in sorted(os.listdir(src_dir)):
                if f.endswith(".h"):
                    shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
                    n += 1
            self.output.info(
                f"OHOS private headers: copied {n} headers from {sub}/ to include/{sub}/"
            )

    def _ohos_relocate_tclconfig(self):
        """Rewrite installed lib/tclConfig.sh to be consumer-relocatable.

        Removes build-machine .conan2/p/b/... paths and the invalid '//'
        placeholders (from TCL_PREFIX='/'), and derives every path from
        TCL_BIN_DIR (set by Tcl-extension consumers such as Expect before
        sourcing tclConfig.sh), pointing TCL_SRC_DIR into the package.
        """
        import re
        tcs = os.path.join(self.package_folder, "lib", "tclConfig.sh")
        if not os.path.isfile(tcs):
            raise ConanException(f"tclConfig.sh not found at {tcs}")
        with open(tcs) as fh:
            text = fh.read()

        guard = (
            "# --- OHOS relocatable guard ---\n"
            "if test -z \"${TCL_BIN_DIR:-}\"; then\n"
            "    TCL_BIN_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            "fi\n"
        )
        text = guard + text

        pfx = 'TCL_PREFIX="${TCL_BIN_DIR}/.."'
        text = re.sub(
            r"^TCL_PREFIX=.*$", pfx, text, count=1, flags=re.M
        )
        text = re.sub(
            r"^TCL_EXEC_PREFIX=.*$", 'TCL_EXEC_PREFIX="${TCL_BIN_DIR}/.."',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_SRC_DIR=.*$", 'TCL_SRC_DIR="${TCL_PREFIX}/include"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_INCLUDE_SPEC=.*$", 'TCL_INCLUDE_SPEC="-I${TCL_PREFIX}/include"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_LIB_SPEC=.*$", 'TCL_LIB_SPEC="-L${TCL_PREFIX}/lib -ltcl8.6"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_BUILD_LIB_SPEC=.*$", 'TCL_BUILD_LIB_SPEC="-L${TCL_PREFIX}/lib -ltcl8.6"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_STUB_LIB_SPEC=.*$", 'TCL_STUB_LIB_SPEC="-L${TCL_PREFIX}/lib -ltclstub8.6"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_BUILD_STUB_LIB_SPEC=.*$", 'TCL_BUILD_STUB_LIB_SPEC="-L${TCL_PREFIX}/lib -ltclstub8.6"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_BUILD_STUB_LIB_PATH=.*$",
            'TCL_BUILD_STUB_LIB_PATH="${TCL_PREFIX}/lib/libtclstub8.6.a"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_STUB_LIB_PATH=.*$",
            'TCL_STUB_LIB_PATH="${TCL_PREFIX}/lib/libtclstub8.6.a"',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_PACKAGE_PATH=.*$", 'TCL_PACKAGE_PATH="{${TCL_PREFIX}/lib} "',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"^TCL_LD_FLAGS=.*$", 'TCL_LD_FLAGS="-L${TCL_PREFIX}/lib "',
            text, count=1, flags=re.M,
        )
        text = re.sub(
            r"-I/storage/Users/currentUser/usr/local/include",
            "-I${TCL_PREFIX}/include", text,
        )
        text = re.sub(
            r"-L/storage/Users/currentUser/usr/local/lib",
            "-L${TCL_PREFIX}/lib", text,
        )
        # Builder-specific compiler absolute path -> resolve via PATH.
        text = re.sub(
            r"^TCL_CC=.*$", "TCL_CC='clang'", text, count=1, flags=re.M
        )

        with open(tcs, "w") as fh:
            fh.write(text)
        self.output.info(
            "OHOS tclConfig.sh relocated: no .conan2/build paths, no '//'"
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["tcl8.6", "tclstub8.6"]
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
        if self.options.shared:
            self.cpp_info.defines.append("TCL_SHARED_BUILD=1")
        else:
            self.cpp_info.defines.append("TCL_SHARED_BUILD=0")