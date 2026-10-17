#!/usr/bin/env python3
"""Conan recipe — expect 5.45.4 (HarmonyOS PC)

All patches are applied via apply_conan_data_patches (standard conan mechanism).
Patches 0001-0009 use standard unified diff format with diff -ruN headers.
"""
from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os as _os


class ExpectConan(ConanFile):
    name = "expect"
    version = "5.45.4"
    description = "Expect — automated interaction tool for Unix/Linux systems"
    license = "MIT"
    homepage = "https://core.tcl-lang.org/expect/index"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("tcl/8.6.14")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--with-tcl=" + _os.path.join(
            self.dependencies["tcl"].package_folder, "lib"))
        # Bypass old config.guess (2003) which doesn't recognize HarmonyOS
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        # Pre-patch Makefile.in for -lz (patch 0001 targets post-configure Makefile,
        # so we handle it here before configure instead).
        self.run(r"sed -i 's|@TCL_DL_LIBS@ @PKG_LIBS@ @MATH_LIBS@|& -lz|' Makefile.in",
                  cwd=self.source_folder)

        # Apply patches FIRST (patches 0002-0008) before source-modifying fixes
        apply_conandata_patches(self)

        # Fix mktemp to use $HOME/tmp (patch 0002 applies the same change but
        # leaves umask 077; this sed fixes the rest of configure scripts)
        self.run(r"find . -name configure -exec sed -i "
                  r"'s|mktemp -d \"./confXXXXXX\"|mkdir -p \"$HOME/tmp/conf_$$\" \&\& echo \"$HOME/tmp/conf_$$\"|g' {} +",
                  cwd=self.source_folder)

        # Strip umask 077 from all configure scripts (UID mapping: the filesystem
        # maps UIDs, so umask-077 dirs (700) are owned by the mapped UID and NOT
        # writable by the actual process UID).
        self.run(r"find . -name configure -exec sed -i 's/umask 077 && //g' {} +",
                  cwd=self.source_folder)

        # 1) Configure with --no-create so we can patch config.status before it runs
        tcl_lib = _os.path.join(self.dependencies["tcl"].package_folder, "lib")
        cfg_cmd = (
            "export TMPDIR=$HOME/tmp; "
            "chmod 755 . 2>/dev/null; "
            "./configure --no-create "
            "--disable-shared "
            f"--with-tcl={tcl_lib} "
            "--build=aarch64-unknown-linux-gnu"
        )
        self.run(cfg_cmd, cwd=self.source_folder)
        # 2) Patch generated config.status to strip umask 077 (UID mapping issue)
        self.run(r"sed -i 's/umask 077 && //g' config.status", cwd=self.source_folder)
        # 3) Run config.status to generate Makefile
        self.run("./config.status", cwd=self.source_folder)

        # Fix TCL_LIB_SPEC baked into the generated Makefile: the tcl package
        # was configured with prefix '/' so it emits '-L//lib -ltcl8.6', which
        # is not resolvable. Point it at the real tcl package lib dir.
        tcl_pkg_lib2 = _os.path.join(self.dependencies["tcl"].package_folder, "lib")
        self.run(r"sed -i 's|-L//lib -ltcl8.6|-L%s -ltcl8.6|g; s|-Wl,-rpath,//lib|-Wl,-rpath,%s|g' Makefile" % (tcl_pkg_lib2, tcl_pkg_lib2),
                 cwd=self.source_folder)

        # Remove USE_TCL_STUBS from generated Makefile (static Tcl doesn't support stubs)
        self.run(r"sed -i 's/-DUSE_TCL_STUBS=1 //g' Makefile", cwd=self.source_folder)

        # Build with -Wno-error flags to suppress musl/clang warnings (E063).
        # TCL_LIB_SPEC from the tcl fallback package points to //lib (empty
        # prefix); override it to the real tcl package lib dir for linking.
        tcl_pkg_lib = _os.path.join(self.dependencies["tcl"].package_folder, "lib")
        self.run("make -j1 CFLAGS='-Wno-error=int-conversion -Wno-error=incompatible-pointer-types -Wno-error=deprecated-non-prototype -Wno-error=unused-but-set-variable -Wno-error=unused-variable -Wno-error=unused-function -Wno-error=knr-promoted-parameter -Wno-error=#warnings -Wno-error=implicit-int' LIBS='-lz' TCL_LIB_SPEC='-L%s -ltcl8.6'" % tcl_pkg_lib, cwd=self.source_folder)

        # Run upstream test suite via expect binary (tclsh 'load' not available in static Tcl build)
        tcl_pkg_lib_run = _os.path.join(self.dependencies["tcl"].package_folder, "lib")
        tclsh_bin = _os.path.join(self.dependencies["tcl"].package_folder, "bin", "tclsh8.6")
        awk_failed = "{for (i=1; i<=NF; i++) if ($i == \"Failed\") print $(i+1)}"
        self.run(f"""export TMPDIR=$HOME/tmp
mkdir -p "$HOME/tmp"
# 验证测试子进程使用的 TMPDIR 目录确实可写（OHOS /tmp 只读）
if [ ! -d "$HOME/tmp" ] || [ ! -w "$HOME/tmp" ]; then
  echo "TMPDIR not writable: $HOME/tmp" >> tests/upstream-test-report.log
  exit 1
fi
export TCL_LIBRARY={_os.path.join(tcl_pkg_lib_run, "tcl8.6")}
export LD_LIBRARY_PATH={tcl_pkg_lib_run}:$LD_LIBRARY_PATH
REPORT=tests/upstream-test-report.log
: > "$REPORT"

echo "=== [1] static tclsh tests/all.tcl ===" >> "$REPORT"
if {tclsh_bin} tests/all.tcl >> "$REPORT" 2>&1; then
  echo "tclsh tests/all.tcl: OK" >> "$REPORT"
else
  echo "tclsh tests/all.tcl: FAILED (static Tcl cannot dynamically load Expect extension)" >> "$REPORT"
fi

echo "=== [2] ./expect tests/all.tcl (upstream cases) ===" >> "$REPORT"
./expect tests/all.tcl >> "$REPORT" 2>&1
RC=$?
echo "expect exit code: $RC" >> "$REPORT"

grep -E 'Total.*Passed.*Skipped.*Failed' "$REPORT" | tail -3 >> "$REPORT"
FAILED_N=$(grep -E 'Total.*Passed.*Skipped.*Failed' "$REPORT" | tail -1 | awk '{awk_failed}')
[ -z "$FAILED_N" ] && FAILED_N=0
echo "UPSTREAM RESULT: rc=$RC failed=$FAILED_N" >> "$REPORT"
cat "$REPORT"
if [ "$RC" -ne 0 ] || [ "$FAILED_N" -gt 0 ]; then
  exit 1
fi
""", cwd=self.source_folder)

    def package(self):
        # expect Makefile has no install target; copy binary and lib manually.
        _os.makedirs(_os.path.join(self.package_folder, "bin"), exist_ok=True)
        _os.makedirs(_os.path.join(self.package_folder, "lib"), exist_ok=True)
        copy(self, "expect",
             src=self.source_folder,
             dst=_os.path.join(self.package_folder, "bin"))
        for lib in _os.listdir(self.source_folder):
            if lib.endswith(".a") or lib.endswith(".so"):
                copy(self, lib,
                     src=self.source_folder,
                     dst=_os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = []
        # expect dynamically links libtcl8.6.so; consumers (test_package) need
        # the tcl package libdir on LD_LIBRARY_PATH to load it at runtime.
        # In the package-info context `package_folder` / `immutable_package_folder`
        # can be None (graph-time evaluation). The dependency's `cpp_info.libdirs`
        # is resolved by Conan against the installed package layout, so use it
        # (only when absolute) to propagate the Tcl runtime dir to consumers.
        tcl_cpp = self.dependencies["tcl"].cpp_info
        tcl_libdirs = getattr(tcl_cpp, "libdirs", None) or []
        if tcl_libdirs and _os.path.isabs(tcl_libdirs[0]):
            tcl_runtime_lib = tcl_libdirs[0]
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", tcl_runtime_lib)
            # expect embeds Tcl and needs the tcl package library (init.tcl etc.)
            # at runtime; export TCL_LIBRARY so consumers (test_package) run it.
            tcl_runtime = _os.path.join(tcl_runtime_lib, "tcl8.6")
            self.runenv_info.define("TCL_LIBRARY", tcl_runtime)
