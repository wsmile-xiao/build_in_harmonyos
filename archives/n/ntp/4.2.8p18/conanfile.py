#!/usr/bin/env python3
"""Conan recipe for NTP 4.2.8p18 — Network Time Protocol CLI tools.

Produces: ntpq, ntpdate, ntpdc, sntp (CLI tools for NTP queries/setup).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NtpConan(ConanFile):
    name = "ntp"
    version = "4.2.8p18"
    description = "Network Time Protocol reference implementation — CLI tools (ntpq, ntpdate, ntpdc, sntp)"
    license = "NTP"
    homepage = "https://www.ntp.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # ntp is a suite of CLI tools, not a system same-name library
        # --enable-local-libopts: use bundled libopts (no external dependency)
        # --enable-local-libevent: use bundled libevent (no external dependency)
        # --without-ntpsnmpd: disable SNMP agent (not needed for CLI tools)
        # --without-crypto: disable OpenSSL crypto dependency
        # --with-yielding-select=yes: cross-compile fix for select() yielding
        # --disable-dependency-tracking: avoid OOM during depfiles bootstrap
        # --with-hardenfile=/dev/null: skip hardening flags detection
        tc.configure_args.append("--enable-local-libopts")
        tc.configure_args.append("--enable-local-libevent")
        tc.configure_args.append("--without-ntpsnmpd")
        tc.configure_args.append("--without-crypto")
        tc.configure_args.append("--disable-linuxcaps")
        tc.configure_args.append("--with-yielding-select=yes")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("--with-hardenfile=/dev/null")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix CONFIG_SHELL from profile that may point to non-existent path
        bash_path = shutil.which("bash") or "/bin/sh"
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            if content.startswith("#!"):
                shebang = content.split("\n", 1)[0]
                rest = content.split("\n", 1)[1] if "\n" in content else ""
                fallback = (
                    f'{shebang}\n'
                    f'# Override invalid paths from Conan profile\n'
                    f'if [ ! -x "$CONFIG_SHELL" ] 2>/dev/null; then\n'
                    f'  CONFIG_SHELL={bash_path}\n'
                    f'  export CONFIG_SHELL\n'
                    f'fi\n'
                    f'if [ ! -x "$SHELL" ] 2>/dev/null; then\n'
                    f'  SHELL={bash_path}\n'
                    f'  export SHELL\n'
                    f'fi\n'
                    f'if [ -n "$CC" ] && [ ! -x "$CC" ] 2>/dev/null; then\n'
                    f'  CC=clang\n'
                    f'  export CC\n'
                    f'fi\n'
                    f'if [ -n "$CXX" ] && [ ! -x "$CXX" ] 2>/dev/null; then\n'
                    f'  CXX=clang++\n'
                    f'  export CXX\n'
                    f'fi\n'
                )
                content = fallback + rest
                with open(configure_path, "w") as f:
                    f.write(content)
        # Also fix sntp sub-configure
        sntp_configure = os.path.join(self.source_folder, "sntp", "configure")
        if os.path.exists(sntp_configure):
            with open(sntp_configure, "r") as f:
                content = f.read()
            if content.startswith("#!"):
                shebang = content.split("\n", 1)[0]
                rest = content.split("\n", 1)[1] if "\n" in content else ""
                fallback = (
                    f'{shebang}\n'
                    f'# Override invalid paths from Conan profile\n'
                    f'if [ ! -x "$CONFIG_SHELL" ] 2>/dev/null; then\n'
                    f'  CONFIG_SHELL={bash_path}\n'
                    f'  export CONFIG_SHELL\n'
                    f'fi\n'
                    f'if [ ! -x "$SHELL" ] 2>/dev/null; then\n'
                    f'  SHELL={bash_path}\n'
                    f'  export SHELL\n'
                    f'fi\n'
                )
                content = fallback + rest
                with open(sntp_configure, "w") as f:
                    f.write(content)
        os.environ["CONFIG_SHELL"] = bash_path
        os.environ["SHELL"] = bash_path
        # Fix umask 077 issue on HMDFS (E002-related)
        for fn in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(p, "w") as f:
                    f.write(content)
        # Also fix sntp configure and config.status
        for fn in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, "sntp", fn)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(p, "w") as f:
                    f.write(content)
        # Fix genHardFlags/genLocInfo scripts shebang
        for script_rel in ["scripts/genHardFlags", "sntp/scripts/genLocInfo", "scripts/cvo.sh", "scripts/build/checkChangeLog"]:
            for base in [self.source_folder]:
                p = os.path.join(base, script_rel)
                if os.path.exists(p):
                    with open(p, "r") as f:
                        content = f.read()
                    content = content.replace("#!/system/bin/sh", "#!/bin/sh")
                    content = content.replace("#!/data/service/hnp/bin/bash", "#!/bin/sh")
                    with open(p, "w") as f:
                        f.write(content)
        # Fix configure scripts to skip genHardFlags/genLocInfo failures in source folder
        for cfg_rel in ["configure", "sntp/configure", "config.status"]:
            for base in [self.source_folder]:
                p = os.path.join(base, cfg_rel)
                if os.path.exists(p):
                    with open(p, "r") as f:
                        content = f.read()
                    content = content.replace(
                        'scripts/genHardFlags -d "$SENTINEL_DIR"',
                        'true'
                    )
                    content = content.replace(
                        'scripts/genHardFlags -d "$SENTINEL_DIR" -f "$with_hardenfile"',
                        'true'
                    )
                    content = content.replace(
                        'scripts/genLocInfo -d "$SENTINEL_DIR"',
                        'true'
                    )
                    content = content.replace(
                        'scripts/genLocInfo -d "$SENTINEL_DIR" -f "$with_locfile"',
                        'true'
                    )
                    with open(p, "w") as f:
                        f.write(content)
        # Make configure executable and run it manually
        build_dir = self.build_folder
        src_dir = self.source_folder
        # The build root (parent of build_folder) has the source files
        build_root = os.path.dirname(build_dir) if build_dir else src_dir
        
        # Create mktemp wrapper in build root (needed by config.status)
        mktemp_path = os.path.join(build_root, "mktemp")
        if not os.path.exists(mktemp_path):
            with open(mktemp_path, "w") as f:
                f.write('#!/bin/sh\n')
                f.write(f'd="{build_root}/conf$$"\n')
                f.write('mkdir -p "$d" 2>/dev/null\n')
                f.write('echo "$d"\n')
                f.write('exit 0\n')
            os.chmod(mktemp_path, 0o755)
        # Add build root to PATH
        os.environ["PATH"] = build_root + ":" + os.environ.get("PATH", "")
        
        # Also fix genHardFlags/genLocInfo in build root using sed
        for cfg_rel in ["configure", "sntp/configure"]:
            for base in [build_root, src_dir]:
                p = os.path.join(base, cfg_rel)
                if os.path.exists(p):
                    # Use sed to replace genHardFlags/genLocInfo invocations
                    os.system(f'sed -i "s|scripts/genHardFlags -d .SENTINEL_DIR.|true|g" "{p}" 2>/dev/null')
                    os.system(f'sed -i "s|scripts/genLocInfo -d .SENTINEL_DIR.|true|g" "{p}" 2>/dev/null')
                    # Also fix the case statement that follows
                    os.system(f'sed -i "s|as_fn_error .? .Problem with genHardFlags!.*|echo \\"genHardFlags skipped for OHOS\\"|" "{p}" 2>/dev/null')
                    os.system(f'sed -i "s|as_fn_error .? .Problem with genLocInfo!.*|echo \\"genLocInfo skipped for OHOS\\"|" "{p}" 2>/dev/null')
        # Fix shebangs in build root
        for script_rel in ["scripts/genHardFlags", "sntp/scripts/genLocInfo", "scripts/cvo.sh", "scripts/build/checkChangeLog"]:
            p = os.path.join(build_root, script_rel)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("#!/system/bin/sh", "#!/bin/sh")
                with open(p, "w") as f:
                    f.write(content)
                os.chmod(p, os.stat(p).st_mode | 0o111)
        # Make all scripts executable in build root
        os.system(f'find {build_root} -name "*.sh" -o -name "configure" -o -name "config.status" | xargs chmod +x 2>/dev/null; true')
        
        # Copy configure to build root and make executable
        import shutil as _shutil, stat as _stat
        cfg_src = os.path.join(src_dir, "configure")
        cfg_dst = os.path.join(build_root, "configure")
        if os.path.exists(cfg_src) and not os.path.exists(cfg_dst):
            _shutil.copy2(cfg_src, cfg_dst)
        os.system(f'chmod +x {cfg_dst} 2>/dev/null; true')
        # Run configure from build_root (where source files are)
        os.chdir(build_root)
        # Create .checkChangeLog stamp to skip the checkChangeLog step
        open(os.path.join(build_root, ".checkChangeLog"), "w").close()
        # Also fix the Makefile to skip checkChangeLog and scripts issues
        mf = os.path.join(build_root, "Makefile")
        if os.path.exists(mf):
            os.system(f'sed -i "s|./scripts/build/checkChangeLog|/bin/sh ./scripts/build/checkChangeLog|g" "{mf}" 2>/dev/null')
            os.system(f'sed -i "s|\t\\./config\\.status|\t/bin/sh ./config.status|g" "{mf}" 2>/dev/null')
            os.system(f'sed -i "s|\\.\\./\\.\\./config\\.status|/bin/sh ../../config.status|g" "{mf}" 2>/dev/null')
        # Also fix all sub-Makefiles for config.status references
        for root, dirs, files in os.walk(build_root):
            for f in files:
                if f == 'Makefile':
                    path = os.path.join(root, f)
                    with open(path, "r") as fh:
                        content = fh.read()
                    # Replace direct config.status invocation with /bin/sh
                    content = content.replace("\t../../config.status", "\t/bin/sh ../../config.status")
                    content = content.replace("\t./config.status", "\t/bin/sh ./config.status")
                    content = content.replace("&& ../../config.status", "&& /bin/sh ../../config.status")
                    with open(path, "w") as fh:
                        fh.write(content)
        # Create missing double-dot .in files for all script directories (VPATH issue)
        for root, dirs, files in os.walk(build_root):
            for f in files:
                if f.endswith('.in') and not f.endswith('..in'):
                    src = os.path.join(root, f)
                    dst = os.path.join(root, f.replace('.in', '..in'))
                    if not os.path.exists(dst):
                        try:
                            import shutil as _shutil
                            _shutil.copy2(src, dst)
                        except OSError as _e:
                            self.output.warning(f"Failed to create placeholder {dst}: {_e}")
        # R33: 从 Conan Toolchain 获取编译器路径，不硬编码。
        # profile 通过 tools.build:compiler_executables conf 注入 c/cpp 路径；
        # AutotoolsToolchain 也会把这些写入 conanautotools toolchain 文件。
        # 这里读取 conf 作为 CC/CXX 传给手动 configure（build() 为手动 os.system 驱动）。
        ce = self.conf.get("tools.build:compiler_executables", default={})
        cc = ce.get("c") or os.environ.get("CC") or "clang"
        cxx = ce.get("cpp") or os.environ.get("CXX") or "clang++"
        configure_cmd = f'CC={cc} CXX={cxx} {bash_path} {cfg_dst} --build=aarch64-linux-gnu --host=aarch64-linux-ohos --prefix=/ --bindir=${{prefix}}/bin --sbindir=${{prefix}}/bin --libdir=${{prefix}}/lib --includedir=${{prefix}}/include --enable-local-libopts --enable-local-libevent --without-ntpsnmpd --without-crypto --disable-linuxcaps --with-yielding-select=yes --disable-dependency-tracking --with-hardenfile=/dev/null'
        ret = os.system(configure_cmd)
        if ret != 0:
            raise RuntimeError(f"configure failed with exit code {ret >> 8 if ret > 0 else 0}")
        # Fix config.status generated by configure
        for cs_file in ["config.status"]:
            cs = os.path.join(build_root, cs_file)
            if os.path.exists(cs):
                with open(cs, "r") as f:
                    cs_content = f.read()
                # Fix shebang to use /bin/sh
                cs_content = cs_content.replace("#!/data/service/hnp/bin/bash", "#!/bin/sh")
                cs_content = cs_content.replace("#!/system/bin/sh", "#!/bin/sh")
                with open(cs, "w") as f:
                    f.write(cs_content)
                os.chmod(cs, os.stat(cs).st_mode | 0o111)
        # Also fix sntp config.status
        for sub in ["sntp", "sntp/libevent", "sntp/libopts"]:
            cs = os.path.join(build_root, sub, "config.status")
            if os.path.exists(cs):
                with open(cs, "r") as f:
                    cs_content = f.read()
                cs_content = cs_content.replace("#!/data/service/hnp/bin/bash", "#!/bin/sh")
                cs_content = cs_content.replace("#!/system/bin/sh", "#!/bin/sh")
                with open(cs, "w") as f:
                    f.write(cs_content)
                os.chmod(cs, os.stat(cs).st_mode | 0o111)
        # Make all scripts executable in build root
        os.system(f'find {build_root} -name "config.status" -o -name "configure" -o -name "*.sh" | xargs chmod +x 2>/dev/null; true')
        # Also fix ALL config.status files to use /bin/sh shebang
        for root, dirs, files in os.walk(build_root):
            for f in files:
                if f == 'config.status':
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r") as fh:
                            content = fh.read()
                        content = content.replace("#!/data/service/hnp/bin/bash", "#!/bin/sh")
                        content = content.replace("#!/system/bin/sh", "#!/bin/sh")
                        with open(path, "w") as fh:
                            fh.write(content)
                        os.chmod(path, os.stat(path).st_mode | 0o111)
                    except (OSError, IOError) as _e:
                        self.output.warning(f"Failed to patch config.status {path}: {_e}")
        # Fix OHOS genLocInfo skip: configure runs `scripts/genLocInfo` to detect
        # man page format, but that script only outputs `GENLOCINFO=OK`+`LOCINFO=`
        # (incomplete — missing SNTP_MS/MANTAGFMT/etc.), so on OHOS it's skipped
        # and all `*_MS` + `MANTAGFMT` Makefile vars stay empty. This turns
        # Makefile rule `sntp.$(SNTP_MS): sntp.$(MANTAGFMT).in` into a dead rule
        # `sntp.: sntp..in` (dot-suffixed target depending on nonexistent
        # `sntp..in`), failing with: "No rule to make target 'sntp..in', needed
        # by 'sntp.'". Same pattern affects ntpd/ntpq/ntpsweep/etc. man pages.
        # Fix: patch every Makefile in the build tree to give the empty `*_MS`
        # vars and `MANTAGFMT` a default value `man` (the .man.in templates exist).
        import re as _re
        _ms_re = _re.compile(r'^([A-Z_]+_MS)\s*=\s*$', _re.MULTILINE)
        _mf_re = _re.compile(r'^(MANTAGFMT)\s*=\s*$', _re.MULTILINE)
        # Delete dead `am__append_N = xxx.` lines: when *_MS vars are empty at
        # configure time, @WANT_XXX_MS_FALSE@ activates am__append that adds
        # `xxx.` (dot-suffixed) to all-am deps — a dead target with no rule.
        # Patching *_MS post-configure fixes the man rule (line 951) but NOT
        # these already-baked am__append lines, so strip them directly.
        _append_re = _re.compile(r'^(am__append_\d+\s*=\s*)[^\n]*\.\s*$', _re.MULTILINE)
        # Also clear `man_MANS = xxx.$(*_MS)`: some Makefile.in (ntpsweep/
        # ntptrace/update-leap) lack the `### Manpage` config.status rule that
        # calc_tickadj has, so even with MANTAGFMT=man the `xxx.man` target has
        # no rule → "No rule to make target 'xxx.man'". Cross-compile doesn't
        # need man pages, so drop them from MANS entirely.
        _man_mans_re = _re.compile(r'^(man_MANS\s*=\s*)[^\n]*\$\([A-Z_]+_MS\)[^\n]*$', _re.MULTILINE)
        _noinst_mans_re = _re.compile(r'^(noinst_MANS\s*=\s*)[^\n]*\$\([A-Z_]+_MS\)[^\n]*$', _re.MULTILINE)
        _patched_count = 0
        for _root, _dirs, _files in os.walk(build_root):
            for _fn in _files:
                if _fn != "Makefile":
                    continue
                _mp = os.path.join(_root, _fn)
                try:
                    with open(_mp) as _f:
                        _content = _f.read()
                except Exception:
                    continue
                _new = _ms_re.sub(r'\1 = man', _content)
                _new = _mf_re.sub(r'\1 = man', _new)
                _new = _append_re.sub(r'\1', _new)
                _new = _man_mans_re.sub(r'\1', _new)
                _new = _noinst_mans_re.sub(r'\1', _new)
                if _new != _content:
                    try:
                        with open(_mp, "w") as _f:
                            _f.write(_new)
                        _patched_count += 1
                        self.output.info(f"Patched Makefile: {_mp}")
                    except Exception as _e:
                        self.output.warning(f"Failed to patch {_mp}: {_e}")
        self.output.info(f"genLocInfo fix: patched {_patched_count} Makefiles (default man *_MS/MANTAGFMT + stripped dead am__append dot targets + cleared man_MANS lacking rules)")
        # OHOS libc has adjtimex() (struct timex*) but not adjtime() (struct timeval*).
        # ntp libntp/systime.c calls adjtime() directly → link error
        # "undefined symbol: adjtime". Write an adjtime shim that delegates to
        # adjtimex(), and add it to libntp's Makefile.am + Makefile.in so it's
        # compiled into libntp.a. (Done as in-build patch instead of a unified
        # diff patch — avoids fragile diff context/whitespace issues.)
        _shim_path = os.path.join(build_root, "libntp", "adjtime_ohos.c")
        if not os.path.exists(_shim_path):
            _shim_src = '''/* adjtime() shim for OHOS - libc has adjtimex() not adjtime() */
#ifdef HAVE_CONFIG_H
# include <config.h>
#endif
#include <sys/time.h>
#include <sys/timex.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#ifndef ADJ_OFFSET_MICRO
#define ADJ_OFFSET_MICRO 0x2000
#endif
int adjtime(const struct timeval *delta, struct timeval *olddelta)
{
\tstruct timex tx;
\tint rc;
\tif (delta != NULL) {
\t\tmemset(&tx, 0, sizeof(tx));
\t\ttx.modes = ADJ_OFFSET_MICRO;
\t\ttx.offset = delta->tv_sec * 1000000L + delta->tv_usec;
\t\trc = adjtimex(&tx);
\t\tif (rc < 0) return -1;
\t}
\tif (olddelta != NULL) {
\t\tmemset(&tx, 0, sizeof(tx));
\t\ttx.modes = 0;
\t\trc = adjtimex(&tx);
\t\tif (rc < 0) return -1;
\t\tlong us = tx.offset;
\t\tif (us < 0) {
\t\t\tolddelta->tv_sec = -((-us) / 1000000L);
\t\t\tolddelta->tv_usec = -((-us) % 1000000L);
\t\t\tif (olddelta->tv_usec < 0) { olddelta->tv_sec -= 1; olddelta->tv_usec += 1000000; }
\t\t} else {
\t\t\tolddelta->tv_sec = us / 1000000L;
\t\t\tolddelta->tv_usec = us % 1000000L;
\t\t}
\t}
\treturn 0;
}
'''
            try:
                with open(_shim_path, "w") as _f:
                    _f.write(_shim_src)
                self.output.info("adjtime shim: created libntp/adjtime_ohos.c")
            except Exception as _e:
                self.output.warning(f"adjtime shim: failed to create: {_e}")
        # Register adjtime_ohos.c in libntp Makefile.am + Makefile.in
        def _add_shim_to_makefile(_mp):
            try:
                with open(_mp) as _f:
                    _c = _f.read()
            except Exception:
                return False
            _changed = False
            # am__objects_5 line (Makefile.in): add adjtime_ohos.$(OBJEXT) after adjtime.$(OBJEXT)
            if "adjtime_ohos" not in _c and "adjtime.$(OBJEXT) adjtime_ohos.$(OBJEXT)" not in _c:
                _c2 = _c.replace("adjtime.$(OBJEXT) \\\n", "adjtime.$(OBJEXT) adjtime_ohos.$(OBJEXT) \\\n", 1)
                if _c2 != _c: _c = _c2; _changed = True
            # libntp_a_SRCS / SOURCES_DIST: add adjtime_ohos.c line after adjtime.c line
            if "adjtime_ohos.c" not in _c:
                for _pat in ["\tadjtime.c\t\t\t\t\t\t\t\\\n", "\tadjtime.c\t\t\t\t\t\\\n", "\tadjtime.c\t\t\t\t\\\n"]:
                    _ins = _pat.replace("adjtime.c", "adjtime_ohos.c")
                    _c2 = _c.replace(_pat, _pat + _ins, 1)
                    if _c2 != _c: _c = _c2; _changed = True; break
                # also handle SOURCES_DIST one-liner form
                if "adjtime_ohos.c" not in _c and " adjtime.c " in _c:
                    _c2 = _c.replace(" adjtime.c ", " adjtime.c adjtime_ohos.c ", 1)
                    if _c2 != _c: _c = _c2; _changed = True
            # DEPDIR: add adjtime_ohos.Po after adjtime.Po
            if "adjtime_ohos.Po" not in _c:
                _dep = '@am__quote@./$(DEPDIR)/adjtime.Po@am__quote@ # am--include-marker\n'
                _ins = '@AMDEP_TRUE@@am__include@ @am__quote@./$(DEPDIR)/adjtime_ohos.Po@am__quote@ # am--include-marker\n'
                _c2 = _c.replace(_dep, _dep + _ins, 1)
                if _c2 != _c: _c = _c2; _changed = True
            if _changed:
                try:
                    with open(_mp, "w") as _f:
                        _f.write(_c)
                except Exception:
                    pass
            return _changed
        _am = os.path.join(build_root, "libntp", "Makefile.am")
        _in = os.path.join(build_root, "libntp", "Makefile.in")
        for _mp in (_am, _in):
            if os.path.exists(_mp) and _add_shim_to_makefile(_mp):
                self.output.info(f"adjtime shim: registered in {os.path.relpath(_mp, build_root)}")
        # OHOS libc also lacks getpass() — ntp's own machines.c has a getpass()
        # impl but it's guarded by #if SYS_WINNT||SYS_VXWORKS||MPE, so OHOS
        # doesn't compile it. ssl_init.c:250 calls getpass() unconditionally →
        # "undefined symbol: getpass" at link time (ntpq/ntpdc/sntp fail).
        # Write a getpass shim that reads from /dev/tty (falling back to stdin).
        _getpass_path = os.path.join(build_root, "libntp", "getpass_ohos.c")
        if not os.path.exists(_getpass_path):
            _getpass_src = '''/* getpass() shim for OHOS - libc lacks getpass().
 * machines.c has an impl but it is guarded by SYS_WINNT||SYS_VXWORKS||MPE,
 * so OHOS doesn't compile it. ssl_init.c calls getpass() unconditionally. */
#ifdef HAVE_CONFIG_H
# include <config.h>
#endif
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <termios.h>
char *getpass(const char *prompt)
{
\tstatic char buf[256];
\tFILE *tty = fopen("/dev/tty", "r+");
\tFILE *in = tty ? tty : stdin;
\tFILE *out = tty ? tty : stderr;
\tstruct termios oldt, newt;
\tint has_term = 0;
\tint term_fd = -1;
\tsize_t n;
\tif (prompt && *prompt) {
\t\tfputs(prompt, out);
\t\tfflush(out);
\t}
\t/* Disable echo on the input we're actually using (tty or stdin).
\t * When /dev/tty is available, echo must be disabled on that tty fd,
\t * not stdin — otherwise the password is echoed in plain text. */
\tterm_fd = fileno(in);
\tif (term_fd >= 0 && tcgetattr(term_fd, &oldt) == 0) {
\t\tnewt = oldt;
\t\tnewt.c_lflag &= ~(ECHO);
\t\ttcsetattr(term_fd, TCSAFLUSH, &newt);
\t\thas_term = 1;
\t}
\tif (fgets(buf, sizeof(buf), in) == NULL) {
\t\tbuf[0] = '\\0';
\t} else {
\t\tn = strlen(buf);
\t\twhile (n > 0 && (buf[n-1] == '\\n' || buf[n-1] == '\\r'))
\t\t\tbuf[--n] = '\\0';
\t}
\tif (has_term)
\t\ttcsetattr(term_fd, TCSAFLUSH, &oldt);
\tif (tty) {
\t\tfputc('\\n', out);
\t\tfflush(out);
\t\tfclose(tty);
\t}
\treturn buf;
}
'''
            try:
                with open(_getpass_path, "w") as _f:
                    _f.write(_getpass_src)
                self.output.info("getpass shim: created libntp/getpass_ohos.c")
            except Exception as _e:
                self.output.warning(f"getpass shim: failed to create: {_e}")
        # Register getpass_ohos.c in libntp Makefile.am + Makefile.in.
        def _add_getpass_to_makefile(_mp):
            try:
                with open(_mp) as _f:
                    _c = _f.read()
            except Exception:
                return False
            if "getpass_ohos" in _c:
                return False
            _changed = False
            # am__objects_5 line: add getpass_ohos.$(OBJEXT) after machines.$(OBJEXT)
            _c2 = _c.replace("machines.$(OBJEXT)", "machines.$(OBJEXT) getpass_ohos.$(OBJEXT)", 1)
            if _c2 != _c: _c = _c2; _changed = True
            # libntp_a_SRCS / SOURCES_DIST: add getpass_ohos.c line after machines.c line
            for _pat in ["\tmachines.c\t\t\t\t\\\n", "\tmachines.c\t\t\\\n", "\tmachines.c\\\n"]:
                _ins = _pat.replace("machines.c", "getpass_ohos.c")
                _c2 = _c.replace(_pat, _pat + _ins, 1)
                if _c2 != _c: _c = _c2; _changed = True; break
            # DEPDIR: add getpass_ohos.Po after machines.Po
            _dep = '@am__quote@./$(DEPDIR)/machines.Po@am__quote@ # am--include-marker\n'
            _ins = '@AMDEP_TRUE@@am__include@ @am__quote@./$(DEPDIR)/getpass_ohos.Po@am__quote@ # am--include-marker\n'
            _c2 = _c.replace(_dep, _dep + _ins, 1)
            if _c2 != _c: _c = _c2; _changed = True
            if _changed:
                try:
                    with open(_mp, "w") as _f:
                        _f.write(_c)
                except Exception:
                    pass
            return _changed
        for _mp in (_am, _in):
            if os.path.exists(_mp) and _add_getpass_to_makefile(_mp):
                self.output.info(f"getpass shim: registered in {os.path.relpath(_mp, build_root)}")
        # Run make from build_root. Capture output tail so CI log shows the real
        # failing target line (CI truncates to "all-recursive Error 1" otherwise).
        import subprocess as _sp
        _proc = _sp.run(
            ["make", "-j1"],
            cwd=build_root,
            stdout=_sp.PIPE,
            stderr=_sp.STDOUT,
            text=True,
            errors="replace",
        )
        _lines = _proc.stdout.splitlines() if _proc.stdout else []
        for _ln in _lines[-120:]:
            self.output.info(_ln)
        ret = _proc.returncode
        if ret != 0:
            self.output.warning(f"top-level make returned exit code {ret}; will attempt subdir builds")
        # HMDFS getcwd/chdir errors break the top-level `make` SUBDIRS recursion
        # (it enters tests/ntpq instead of ntpq/, so binaries never link). Also,
        # configure leaves NTPQ_DB / NTPD_DB / etc. EMPTY on cross-compile, so
        # `bin_PROGRAMS = $(NTPQ_DB)` is empty and `make all` skips linking
        # (ntpq is only in EXTRA_PROGRAMS). Build each executable by EXPLICIT
        # target name so the LINK rule runs regardless.
        # subdir → list of explicit make targets (executable basenames)
        _build_targets = {
            "libntp":    ["all"],
            "libparse":  ["all"],
            "ntpd":      ["ntpd"],
            "ntpq":      ["ntpq"],
            "ntpdate":   ["ntpdate"],
            "ntpdc":     ["ntpdc"],
            "ntptime":   ["ntptime"],
            "ntp-keygen":["ntp-keygen"],
            "ntpsnmpd":  ["ntpsnmpd"],
            "sntp":      ["sntp"],
            "util":      ["tickadj", "propdelay", "calc_tickadj"],
            "scripts":   ["all"],
            "adjtimed":  ["all"],
        }
        _failed = []
        for _d, _targets in _build_targets.items():
            _dpath = os.path.join(build_root, _d)
            if not os.path.isdir(_dpath):
                continue
            if not os.path.exists(os.path.join(_dpath, "Makefile")):
                continue
            for _tgt in _targets:
                _proc2 = _sp.run(
                    ["make", "-j1", _tgt],
                    cwd=_dpath,
                    stdout=_sp.PIPE,
                    stderr=_sp.STDOUT,
                    text=True,
                    errors="replace",
                )
                _lns2 = _proc2.stdout.splitlines() if _proc2.stdout else []
                for _ln in _lns2[-25:]:
                    self.output.info(_ln)
                if _proc2.returncode != 0:
                    _failed.append(f"{_d}/{_tgt}")
                    self.output.warning(f"subdir make {_d}/{_tgt}: exit {_proc2.returncode}")
        if _failed:
            self.output.warning(f"subdir make failed for: {_failed}")
        # Core tools this recipe declares/packages. If any of them failed to
        # link, the build is incomplete — raise so a broken package can never
        # be marked built/published (AI review #182833197). Additional tools
        # (ntpd/ntpsnmpd/propdelay/calc_tickadj) are out of scope: their
        # subdir make failures stay warnings and don't fail the build.
        _required = ["ntpq", "ntpdate", "ntpdc", "sntp"]
        _missing = [
            n for n in _required
            if not os.path.exists(os.path.join(build_root, n, n))
        ]
        if _missing:
            raise RuntimeError(f"required binaries not linked: {_missing}")
        for _n in _required:
            self.output.info(f"linked {_n}: {os.path.join(build_root, _n, _n)}")

    def package(self):
        # autotools.install() / `make install` is unreliable on HMDFS:
        #   1. build_folder (build-release/) Makefile lacks install target
        #   2. configure --prefix=/ → absolute /bin /libexec /share paths,
        #      "mkdir '/libexec': Permission denied"
        #   3. DESTDIR relocate works for DATA but the HMDFS getcwd/chdir errors
        #      break install-recursive, so bin_PROGRAMS never get installed
        #      (package bin/ ends up empty).
        # Bypass `make install` entirely: copy the already-linked executables
        # straight from each source subdir of build_root into package_folder/bin.
        # build_root is a build()-local var, so recompute here the same way.
        _build_root = os.path.dirname(self.build_folder)
        import shutil as _sh
        _bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(_bin_dst, exist_ok=True)
        # Map source subdir → executable name(s) produced there.
        _bin_map = {
            "ntpd": ["ntpd", "ntpdsim"],
            "ntpq": ["ntpq"],
            "ntpdate": ["ntpdate"],
            "ntpdc": ["ntpdc"],
            "ntptime": ["ntptime"],
            "ntp-keygen": ["ntp-keygen"],
            "ntpsnmpd": ["ntpsnmpd"],
            "sntp": ["sntp"],
            "util": ["tickadj", "propdelay", "calc_tickadj", "ntptime"],
            "scripts": ["ntpsweep", "ntptrace", "ntp-wait"],
        }
        _copied = []
        for _sub, _bins in _bin_map.items():
            _subdir = os.path.join(_build_root, _sub)
            if not os.path.isdir(_subdir):
                continue
            for _b in _bins:
                _src = os.path.join(_subdir, _b)
                # try with common executable extensions
                for _cand in (_src, _src + ".exe", os.path.join(_subdir, _b + ".exe")):
                    if os.path.isfile(_cand):
                        try:
                            with open(_cand, "rb") as _f:
                                _magic = _f.read(4)
                        except Exception:
                            _magic = b""
                        if _magic == b"\x7fELF":
                            _dst = os.path.join(_bin_dst, _b)
                            _sh.copy2(_cand, _dst)
                            _copied.append(_b)
                            self.output.info(f"packaged bin: {_b} <- {_sub}/")
                        break
        # Also pick up any scripts (ntpsweep/ntptrace/ntp-wait are perl scripts,
        # not ELF) from scripts/ — copy by name match.
        _scripts_dir = os.path.join(_build_root, "scripts")
        if os.path.isdir(_scripts_dir):
            for _b in ("ntpsweep", "ntptrace", "ntp-wait"):
                _src = os.path.join(_scripts_dir, _b)
                if os.path.isfile(_src) and _b not in _copied:
                    try:
                        _dst = os.path.join(_bin_dst, _b)
                        _sh.copy2(_src, _dst)
                        _copied.append(_b)
                        self.output.info(f"packaged script: {_b}")
                    except Exception as _e:
                        self.output.warning(f"failed to package {_b}: {_e}")
        if not _copied:
            raise RuntimeError("no binaries packaged — build did not produce executables")
        self.output.info(f"package(): copied {len(_copied)} binaries/scripts: {sorted(_copied)}")

    def package_info(self):
        # ntp is a suite of CLI tools, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]