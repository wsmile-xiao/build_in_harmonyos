#!/usr/bin/env python3
"""Conan recipe for Berkeley DB 5.3.28.

Berkeley DB uses autotools but requires running configure from the
build_unix/ subdirectory: cd build_unix && ../dist/configure --prefix=...
The source tarball contains a src/ directory with the actual source code.

R26: Not a system-name library, so shared builds are fine.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class Berkeleydb5Conan(ConanFile):
    name = "berkeley-db5"
    version = "5.3.28"
    description = "Berkeley DB 5.3.28 — embedded key/value database library"
    license = "Sleepycat"  # Berkeley DB Sleepycat Public License
    homepage = "https://www.oracle.com/database/technologies/related/berkeleydb.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Berkeley DB needs to run configure from build_unix/, not from source root.
        # The autotools.configure() helper runs ./configure at source root, which
        # doesn't work for this project. We pass args via configure_args for
        # consistency, then run configure manually in build().
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--with-repmgr-ssl=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        build_dir = os.path.join(src_dir, "build_unix")
        os.makedirs(build_dir, exist_ok=True)

        # Pre-patch dist/configure BEFORE running it.
        # Two problems force us to intercept configure BEFORE it runs:
        #
        # (A) configure probes `print -r --` as an echo mechanism. On HMDFS the
        #     probe succeeds (ksh-style `print` builtin exists in the probe shell),
        #     but config.status later runs in a context where `print` is unavailable
        #     → "print: command not found" spam and failure.
        #     Fix: rewrite configure so it never picks `print -r --`, forcing the
        #     POSIX `printf %s\n` fallback for both as_echo and ECHO.
        #
        # (B) configure's LAST step is `$SHELL $CONFIG_STATUS ...` — it execs the
        #     freshly-written config.status immediately. config.status creates temp
        #     awk scripts in ./confXXXX/ then executes them directly (`./subs1.awk`),
        #     but HMDFS denies execute permission on newly-created scripts and also
        #     blocks writes under umask 077 + setgid. We need to patch config.status
        #     BEFORE it runs, so we neuter the auto-exec in configure and re-run
        #     config.status ourselves after patching it below.
        configure = os.path.join(src_dir, "dist", "configure")
        if os.path.isfile(configure):
            with open(configure) as f:
                cfg = f.read()
            # (A) Force printf fallback — drop every `print -r --` probe branch.
            cfg = cfg.replace("as_echo='print -r --'", "as_echo='printf %s\\n'")
            cfg = cfg.replace("as_echo_n='print -rn --'", "as_echo_n='printf %s'")
            cfg = cfg.replace("ECHO='print -r --'", "ECHO='printf %s\\n'")
            cfg = cfg.replace("print -r --", "printf %s\\n")
            cfg = cfg.replace("print -rn --", "printf %s")
            # (B) Stop configure from auto-execing config.status. We re-run it
            #     manually after patching. The auto-exec line looks like:
            #       $SHELL $CONFIG_STATUS $ac_config_status_args || ac_cs_success
            #     Replace it with a no-op so configure exits cleanly first.
            import re as _re
            cfg = _re.sub(
                r'\$SHELL \$CONFIG_STATUS \$ac_config_status_args \|\| ac_cs_success',
                'echo "config.status deferred (HMDFS patch pending)"',
                cfg,
            )
            with open(configure, "w") as f:
                f.write(cfg)

        # Configure from build_unix/ using ../dist/configure
        # Conan's AutotoolsToolchain sets --prefix=/ for library packages,
        # and DESTDIR handles the actual install path.
        self.run(
            f"cd {build_dir} && ../dist/configure "
            f"--prefix=/ "
            f"--enable-static --enable-shared --with-repmgr-ssl=no",
            env="conanbuild"
        )

        # Patch config.status for HMDFS temp dir perms, THEN run it manually
        # (configure's auto-exec was neutered above).
        # Root cause of "subs1.awk: Permission denied": config.status creates temp
        # awk scripts in ./confXXXX/ (mktemp + umask 077). HMDFS setgid blocks
        # writes under 2700 perms → the `echo > "$ac_tmp/subs1.awk"` write fails.
        # Fix: redirect tmp to $TMPDIR and use umask 022 so writes succeed.
        # NOTE: do NOT rewrite awk script invocation to `awk -f` — every
        # `subs*.awk` occurrence in config.status is a redirection target
        # (">", ">>", "<"), not a direct execution. Patching those breaks
        # filenames. Once temp dir is writable, awk scripts run fine.
        config_status = os.path.join(build_dir, "config.status")
        if os.path.isfile(config_status):
            with open(config_status) as f:
                content = f.read()
            import re
            # mktemp temp dir: umask 077 → umask 022, use $TMPDIR (HMDFS setgid
            # blocks writes under 2700 perms). Use regex — literal replace
            # fails because of nested backticks/quotes in the real config.status.
            content = re.sub(
                r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null` &&',
                'tmp="${TMPDIR:-/tmp}"/conf$$-$RANDOM  &&',
                content,
            )
            content = re.sub(
                r'tmp=\./conf\$\$-\$RANDOM\n  \(umask 077 && mkdir "\$tmp"\)',
                'tmp="${TMPDIR:-/tmp}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
                content,
            )
            # Fallback: any remaining `umask 077 && mkdir "$tmp"` → umask 022
            content = re.sub(
                r'umask 077 && mkdir "\$tmp"',
                'umask 022 && mkdir -p "$tmp"',
                content,
            )
            # Defensive: if configure still emitted `print -r --`, swap it.
            content = content.replace("print -r --", "printf %s\\n")
            content = content.replace("print -rn --", "printf %s")
            with open(config_status, "w") as f:
                f.write(content)

            # Now manually run the patched config.status.
            self.run(f"cd {build_dir} && $SHELL ./config.status", env="conanbuild")

        self.run(f"cd {build_dir} && make -j1", env="conanbuild")
        self.run(
            f"cd {build_dir} && make install DESTDIR={self.package_folder}",
            env="conanbuild"
        )

    def package(self):
        # build() already handles install via DESTDIR
        pass

    def package_info(self):
        self.cpp_info.libs = ["db-5.3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 包同时交付 14 个 db_* 命令行工具（bin/），显式声明 bindirs 与安装目录一致
        # （R38：工具类型包必须可通过 commands.json 发现，L0k 依据 cpp_info.bindirs 判断）
        self.cpp_info.bindirs = ["bin"]
