#!/usr/bin/env python3
"""Conan recipe for sqsh 2.5.16.1 — Sybase/MSSQL CLI shell (HarmonyOS PC)."""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class SqshConan(ConanFile):
    name = "sqsh"
    version = "2.5.16.1"
    description = "sqsh - Unix/Linux replacement for Sybase's isql (interactive SQL shell)"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/sqsh/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        config_dir = os.path.join(self.recipe_folder, "config")
        if os.path.isdir(config_dir):
            for fname in os.listdir(config_dir):
                if fname.startswith("config."):
                    shutil.copy2(os.path.join(config_dir, fname), self.export_sources_folder)

    def requirements(self):
        self.requires("freetds/1.4.23")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        autoconf_dir = os.path.join(self.source_folder, "autoconf")
        if os.path.isdir(autoconf_dir):
            for fname in ("config.guess", "config.sub"):
                src = os.path.join(self.export_sources_folder, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(autoconf_dir, fname))

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-readline")
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--without-motif")
        tc.configure_args.append("--without-static")
        tc.configure_args.append("--without-debug")
        freetdeps = self.dependencies["freetds"]
        freetds_prefix = freetdeps.package_folder
        tc.configure_args.append(f"--with-sybase={freetds_prefix}")
        tc.extra_cflags.append(f"-I{freetds_prefix}/include")
        tc.extra_ldflags.append(f"-L{freetds_prefix}/lib")
        tc.extra_cflags.extend([
            "-DCS_TDS_80=7400", "-DCS_SEC_CHANBIND=9178",
            "-DCS_SEC_CONFIDENTIALITY=9135", "-DCS_SEC_INTEGRITY=9179",
            "-DCS_SEC_DATAORIGIN=9180", "-DCS_SEC_DETECTSEQ=9181",
            "-DCS_SEC_DETECTREPLAY=9182", "-DCS_SEC_KEYTAB=9183",
            "-DCS_SEC_MECHANISM=9184", "-DCS_SEC_CREDTIMEOUT=9185",
            "-DCS_UNEXPIRED=9186",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        compiler_execs = self.conf.get("tools.build:compiler_executables", default={})
        clang = compiler_execs.get("c", "/data/service/hnp/bin/clang")
        freetds_dep = self.dependencies["freetds"]
        freetds_lib = os.path.join(freetds_dep.package_folder, "lib")
        if os.path.isdir(freetds_lib):
            import subprocess as _sp
            for libname in ("ct", "sybdb"):
                static_lib = os.path.join(freetds_lib, f"lib{libname}.a")
                shared_lib = os.path.join(freetds_lib, f"lib{libname}.so")
                if os.path.exists(static_lib) and (not os.path.exists(shared_lib) or os.path.islink(shared_lib)):
                    if os.path.islink(shared_lib):
                        os.remove(shared_lib)
                    tmp_dir = os.path.join(self.build_folder, f"tmp-{libname}")
                    os.makedirs(tmp_dir, exist_ok=True)
                    _sp.run(["ar", "x", static_lib], cwd=tmp_dir, check=True)
                    so_objs = [os.path.join(tmp_dir, f) for f in sorted(os.listdir(tmp_dir)) if f.endswith(".o")]
                    _sp.run([clang, "-shared", "-o", shared_lib] + so_objs + ["-ldl", "-lm"], check=True)
        autotools = Autotools(self)
        configure_args = " ".join(autotools.configure_args) if hasattr(autotools, 'configure_args') else ""
        sybase_prefix = freetds_dep.package_folder

        # In-source build: sqsh's Makefile is not VPATH-aware, so we build
        # directly in the source folder.
        #
        # CRITICAL: `make` cannot be used on OHOS — its posix_spawn jobserver
        # causes child clang processes to die silently (exit 1/2 with no output).
        # Instead, compile every .c directly with clang and link manually.
        freetds_inc = f"{freetds_dep.package_folder}/include"
        freetds_lib = freetds_dep.package_folder + "/lib"
        cppflags_val = "-DSYB_LP64 -DNDEBUG"
        cflags_base = (
            f"-O3 -std=gnu89 -Wno-deprecated-non-prototype -I{freetds_inc} "
            f"-DCS_TDS_80=7400 -DCS_SEC_CHANBIND=9178 "
            f"-DCS_SEC_CONFIDENTIALITY=9135 -DCS_SEC_INTEGRITY=9179 "
            f"-DCS_SEC_DATAORIGIN=9180 -DCS_SEC_DETECTSEQ=9181 "
            f"-DCS_SEC_DETECTREPLAY=9182 -DCS_SEC_KEYTAB=9183 "
            f"-DCS_SEC_MECHANISM=9184 -DCS_SEC_CREDTIMEOUT=9185 "
            f"-DCS_UNEXPIRED=9186"
        )

        build_script = f'''#!/bin/bash
set -ex
cd "{self.source_folder}"

export PATH="/data/service/hnp/bin:/system/bin:/bin:$PATH"
export SHELL="/bin/sh"
export CONFIG_SHELL="/bin/sh"
export SYBASE="{sybase_prefix}"

# ── Step 1: configure ──
# E011/E114: HMDFS UID 映射导致 `umask 077`+`mktemp -d ./confXXXXXX` 产生的
# 0700 目录对进程不可写（chmod 无效），config.status 无法创建 subs1.awk。
# 改 umask 022 使临时目录 0755（build 目录在 HMDFS 上时必必需）。
sed -i 's/umask 077/umask 022/g' configure
bash configure {configure_args}

# ── Step 2: Patch config.h ──
sed -i 's/^#define HAVE_READLINE_H 1/\\/\\* #undef HAVE_READLINE_H \\*\\//' src/config.h
sed -i 's/^#define HAVE_READLINE 1/\\/\\* #undef HAVE_READLINE \\*\\//' src/config.h
sed -i 's/^#define HAVE_RL_COMPLETION_MATCHES 1/\\/\\* #undef HAVE_RL_COMPLETION_MATCHES \\*\\//' src/config.h
sed -i 's/^#define HAVE_SHADOW_H 1/\\/\\* #undef HAVE_SHADOW_H \\*\\//' src/config.h

# ── Step 3: Compile all .c files directly (bypass make) ──
cd src
CLC="{clang}"
INC="{freetds_inc}"
FB="{cppflags_val}"
CB="{cflags_base}"
LDFLAGS="-L{freetds_lib}"

compile() {{
    $CLC $CB $FB -I"$INC" -c -o "$1.o" "$1.c" 2>&1
}}

# cmd_*
for f in cmd_alias cmd_bcp cmd_buf cmd_connect cmd_do cmd_echo cmd_exit cmd_for cmd_func cmd_go cmd_help cmd_history cmd_if cmd_input cmd_jobs cmd_kill cmd_lock cmd_loop cmd_misc cmd_read cmd_reconnect cmd_redraw cmd_reset cmd_return cmd_rpc cmd_run cmd_set cmd_shell cmd_show cmd_sleep cmd_wait cmd_warranty cmd_while; do compile "$f"; done

# dsp_*
for f in dsp dsp_bcp dsp_csv dsp_conv dsp_desc dsp_horiz dsp_html dsp_meta dsp_none dsp_out dsp_pretty dsp_vert dsp_x; do compile "$f"; done

# var_*
for f in var_ctlib var_date var_debug var_dsp var_hist var_misc var_passwd var_readline var_thresh; do compile "$f"; done
# sqsh_*
for f in sqsh_alias sqsh_args sqsh_avl sqsh_buf sqsh_cmd sqsh_compat sqsh_debug sqsh_env sqsh_error sqsh_expand sqsh_fd sqsh_filter sqsh_fork sqsh_func sqsh_getopt sqsh_global sqsh_history sqsh_init sqsh_job sqsh_readline sqsh_sig sqsh_sigcld sqsh_stdin sqsh_strchr sqsh_tok sqsh_varbuf; do compile "$f"; done
# sqsh_main
compile sqsh_main

# ── Step 4: Build sqsh_parser library ──
cd sqsh_parser
$CLC $CB $FB -I"$INC" -c -o sqsh_parser.o sqsh_parser.c 2>&1
$CLC $CB $FB -I"$INC" -c -o tsql.o tsql.c 2>&1
$CLC $CB $FB -I"$INC" -c -o tsql.yy.o tsql.yy.c 2>&1
ar -rcsv sqsh_parser.a sqsh_parser.o tsql.o tsql.yy.o
cd ..

# ── Step 5: Link sqsh ──
# Static link against libct.a: FreeTDS on OHPC ships only static .a libs and
# the OHOS musl loader cannot resolve a locally-crafted libct.so at runtime
# (E: "Error loading shared library libct.so"). Embedding CT-lib keeps sqsh
# self-contained (no runtime .so dependency).
$CLC $LDFLAGS \\
    cmd_alias.o cmd_bcp.o cmd_buf.o cmd_connect.o cmd_do.o cmd_echo.o cmd_exit.o cmd_for.o cmd_func.o cmd_go.o cmd_help.o cmd_history.o cmd_if.o cmd_input.o cmd_jobs.o cmd_kill.o cmd_lock.o cmd_loop.o cmd_misc.o cmd_read.o cmd_reconnect.o cmd_redraw.o cmd_reset.o cmd_return.o cmd_rpc.o cmd_run.o cmd_set.o cmd_shell.o cmd_show.o cmd_sleep.o cmd_wait.o cmd_warranty.o cmd_while.o \\
    var_ctlib.o var_date.o var_debug.o var_dsp.o var_hist.o var_misc.o var_passwd.o var_readline.o var_thresh.o \\
    dsp.o dsp_bcp.o dsp_csv.o dsp_conv.o dsp_desc.o dsp_horiz.o dsp_html.o dsp_meta.o dsp_none.o dsp_out.o dsp_pretty.o dsp_vert.o dsp_x.o \\
    sqsh_alias.o sqsh_args.o sqsh_avl.o sqsh_buf.o sqsh_cmd.o sqsh_compat.o sqsh_debug.o sqsh_env.o sqsh_error.o sqsh_expand.o sqsh_fd.o sqsh_filter.o sqsh_fork.o sqsh_func.o sqsh_getopt.o sqsh_global.o sqsh_history.o sqsh_init.o sqsh_job.o sqsh_readline.o sqsh_sig.o sqsh_sigcld.o sqsh_stdin.o sqsh_strchr.o sqsh_tok.o sqsh_varbuf.o \\
    sqsh_main.o \\
    -l:libct.a -ldl -lm sqsh_parser/sqsh_parser.a \\
    -o sqsh
'''

        script_path = os.path.join(self.build_folder, "ohc-build.sh")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(script_path, 'w') as f:
            f.write(build_script)
        os.chmod(script_path, 0o755)

        # Run the build script
        self.run(f"bash {script_path}")

    def package(self):
        sqsh_bin = os.path.join(self.source_folder, "src", "sqsh")
        if os.path.isfile(sqsh_bin):
            bindir = os.path.join(self.package_folder, "bin")
            os.makedirs(bindir, exist_ok=True)
            shutil.copy2(sqsh_bin, os.path.join(bindir, "sqsh"))
            self.output.info(f"sqsh binary installed to {bindir}")
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "licenses", "sqsh"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "sqsh")
        self.cpp_info.set_property("cmake_target_name", "sqsh::sqsh")
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
