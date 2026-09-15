#!/usr/bin/env python3
"""Conan recipe for Berkeley DB (classic) 6.2.32.

Berkeley DB classic 6.x line (Sleepycat-era lineage, independent from the
Oracle Berkeley DB 12c/18c/19c packages already archived under different
names). Upstream: https://download.oracle.com/berkeley-db/db-6.2.32.tar.gz

Build system: autoconf, but BDB-specific — configure lives in dist/ and must
be invoked from the build_unix/ subdirectory:
    cd build_unix && ../dist/configure --prefix=...

Patches (all verified on OHOS aarch64):
  0001 dist/config.guess — add *:HarmonyOS:*:* branch (E007), emit
      aarch64-unknown-linux-ohos
  0002 dist/config.sub — accept linux-ohos in KERNEL-OS list and OS list
  0003 dist/configure — force POSIX printf instead of `print -r --` echo
      probe. On the HMDFS developer shell the probe succeeds (ksh-style
      `print` builtin), but config.status later runs in a context where
      `print` is unavailable → "print: command not found" spam and a
      corrupted libtool script (archive_expsym_cmds mangled → libtool
      syntax errors during make).
  0004 src/dbinc/db_cxx.in — #undef atomic_init before <iostream>.
      dbinc/atomic.h defines atomic_init(p, val) as a macro; libc++
      <atomic> declares atomic_init as a function → compile error with
      clang/libc++ when --enable-cxx is used.

Runtime-only fix (build(), not a patch): config.status creates temp awk
scripts in ./confXXXXXX with umask 077; HMDFS setgid dirs deny writes
under those perms → "can't create ./confXXXX/subs1.awk: Permission
denied". config.status is a generated file (R6: never patch generated
files), so it is rewritten in-place right after configure runs, before
it is executed: temp dir redirected to $TMPDIR, umask 022.

R26: not a system-name library (libdb-6.2 does not exist in /lib or
/lib64 of the OHOS system image), shared+static both built, default
static.

R38: the package also ships 15 command line utilities (db_archive ...).
bindirs is declared and commands.json is present at the software level.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class DbConan(ConanFile):
    name = "db"
    version = "6.2.32"
    description = "Berkeley DB classic 6.2.32 - embedded key/value database library (C API + C++ API + db_* utilities)"
    license = "AGPL-3.0"  # Berkeley DB 6.x is AGPL-3.0 (Sleepycat license applied to 5.x and earlier)
    homepage = "https://www.oracle.com/database/technologies/related/berkeleydb.html"
    url = "https://download.oracle.com/berkeley-db/db-6.2.32.tar.gz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_cxx": [True, False],
    }
    default_options = {
        "shared": False,
        "enable_cxx": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # basic_layout not used; BDB requires out-of-tree build in
        # build_unix/ under the source root (in-tree build dir pattern).
        self.folders.source = "src"
        self.folders.build = "src/build_unix"

    def requirements(self):
        pass  # no external dependencies

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Upstream tarball ships a stale dist/configure.orig (leftover of
        # db-6.2.29). Conan's patch tool backs up dist/configure to
        # dist/configure.orig before applying 0003 — the pre-existing file
        # makes that backup fail ("can't backup original file ... aborting").
        # Remove the upstream leftover.
        stale = os.path.join(self.source_folder, "dist", "configure.orig")
        if os.path.isfile(stale):
            os.remove(stale)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--with-repmgr-ssl=no")
        if self.options.enable_cxx:
            tc.configure_args.append("--enable-cxx")
        # TCL API not built: the OHOS tcl conan package ships a static
        # tclsh whose `load` command is unavailable, so the upstream TCL
        # test suite is not executable in this environment anyway.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        build_dir = os.path.join(src_dir, "build_unix")
        os.makedirs(build_dir, exist_ok=True)

        configure = os.path.join(src_dir, "dist", "configure")

        # Stop configure from auto-executing config.status: we need to
        # rewrite its temp-dir handling for HMDFS before it runs (same
        # approach as the berkeley-db5 archive). configure is a source
        # file, but this is a runtime neuter — the canonical HMDFS fix
        # for config.status itself lives below and patches a *generated*
        # file, which must not be shipped as a patch (R6).
        with open(configure) as f:
            cfg = f.read()
        cfg = re.sub(
            r'\$SHELL "\$CONFIG_STATUS"\s*\|\|\|\s*as_fn_error',
            'echo "config.status deferred (HMDFS patch pending)"',
            cfg,
        )
        # Also match the classic "$SHELL $CONFIG_STATUS $ac_config_status_args || ac_cs_success=false"
        cfg = re.sub(
            r'\$SHELL \$CONFIG_STATUS \$ac_config_status_args \|\| ac_cs_success=',
            'echo "config.status deferred (HMDFS patch pending)"; ac_cs_success=',
            cfg,
        )
        # And the quoted variant "$SHELL "$CONFIG_STATUS" $ac_config_status_args || ac_cs_success=false"
        cfg = re.sub(
            r'\$SHELL "\$CONFIG_STATUS" \$ac_config_status_args \|\| ac_cs_success=',
            'echo "config.status deferred (HMDFS patch pending)"; ac_cs_success=',
            cfg,
        )
        # The if-block ends with "$ac_cs_success || as_fn_exit 1"; with the
        # exec deferred, success must stay true. The substitutions above
        # keep the original "false" suffix which would make configure
        # exit 1, so flip the sentinel explicitly.
        cfg = cfg.replace(
            'echo "config.status deferred (HMDFS patch pending)"; ac_cs_success=false',
            'echo "config.status deferred (HMDFS patch pending)"; ac_cs_success=:',
        )
        with open(configure, "w") as f:
            f.write(cfg)

        # Configure from build_unix/ (BDB-specific layout).
        self.run(
            f'cd "{build_dir}" && "{configure}"'
            f" --prefix=/"
            f" --enable-static --enable-shared --with-repmgr-ssl=no"
            + (" --enable-cxx" if self.options.enable_cxx else ""),
            env="conanbuild",
        )

        # config.status is a *generated* file (R6): rewrite its temp-dir
        # creation before running it, instead of shipping a patch for a
        # file that does not exist in the source tarball.
        # Why: upstream creates ./confXXXXXX with `umask 077 && mktemp -d`.
        # Both the developer machine (HMDFS setgid build dirs) and the CI
        # worker (buildbot rewrites TMPDIR to $HOME/.cache/tmp on HMDFS:
        # build #43222 died with "Permission denied" on subs1.awk inside
        # the mktemp-created 0700 dir) deny writes there. Fix: redirect the
        # temp dir into a pre-created 0777 directory under build_unix/ (the
        # very filesystem make already writes to), drop the umask and
        # chmod the directory open after creation.
        cs_tmp = os.path.join(build_dir, "cstmp")
        os.makedirs(cs_tmp, exist_ok=True)
        try:
            os.chmod(cs_tmp, 0o777)
        except OSError:
            pass
        config_status = os.path.join(build_dir, "config.status")
        if os.path.isfile(config_status):
            with open(config_status) as f:
                content = f.read()
            # mktemp branch: redirect into $DB_CSTMP, drop umask 077
            content = re.sub(
                r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\)',
                'tmp=`(mktemp -d "$DB_CSTMP/confXXXXXX")',
                content,
            )
            content = re.sub(
                r'tmp=`\(umask 077 && mktemp -d "(\$\{TMPDIR[^"]*\})"',
                r'tmp=`(mktemp -d "\1"',
                content,
            )
            # fallback branch: keep umask 022 + point at $DB_CSTMP too
            content = re.sub(
                r'tmp=\./conf\$\$-\$RANDOM\n  \(umask 077 && mkdir "\$tmp"\)',
                'tmp="$DB_CSTMP"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
                content,
            )
            content = re.sub(
                r'umask 077 && mkdir "\$tmp"',
                'umask 022 && mkdir -p "$tmp"',
                content,
            )
            # safety net: open up the mode of whatever directory was chosen
            content = content.replace(
                'ac_tmp=$tmp',
                'ac_tmp=$tmp\nchmod 0755 "$ac_tmp" 2>/dev/null || true',
                1,
            )
            with open(config_status, "w") as f:
                f.write(content)
            # Re-run the patched config.status to (re)generate Makefile etc.
            # DB_CSTMP is exported inline so the conanbuild environment
            # (whatever TMPDIR it carries) cannot re-route the temp dir.
            self.run(
                f'cd "{build_dir}" && export DB_CSTMP="{cs_tmp}"'
                f' && TMPDIR="{cs_tmp}" $SHELL ./config.status',
                env="conanbuild",
            )

        self.run(f'cd "{build_dir}" && make -j1', env="conanbuild")
        self.run(
            f'cd "{build_dir}" && make install DESTDIR="{self.package_folder}"',
            env="conanbuild",
        )

    def package(self):
        # build() already installed via DESTDIR
        pass

    def package_info(self):
        # Components only: setting package-level cpp_info.libs *and*
        # components makes CMakeDeps' aggregate target db::db collect the
        # libs of every component — a pure-C consumer would then end up
        # with a DT_NEEDED on libdb_cxx-6.2.so. Declaring only components
        # keeps db::db == libdb-6.2 (C API) and db::db_cxx == the C++ API.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.options.enable_cxx:
            self.cpp_info.components["db"].libs = ["db-6.2"]
            self.cpp_info.components["db_cxx"].libs = ["db_cxx-6.2"]
            self.cpp_info.components["db_cxx"].requires = ["db"]
        else:
            self.cpp_info.components["db"].libs = ["db-6.2"]
        # 15 command line utilities ship in bin/ (R38 -> commands.json)
        self.cpp_info.bindirs = ["bin"]
