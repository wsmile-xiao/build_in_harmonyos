from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
import os
import re
import shutil

# Install shim for HarmonyOS target FS (hmbs caps: chmod=0, hardlink=0, install_shim=true)
# configure detects install that supports -m (mode) but chmod is not available on HMDFS,
# so `install -c -m 644` fails. This shim ignores -m and uses cp/mkdir.
_INSTALL_SHIM = r"""#!/bin/sh
is_dir=0
mk_leading=0
files=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d) is_dir=1 ;;
    -D) mk_leading=1 ;;
    -m) shift ;;
    -m?*|--mode=*) ;;
    -c|-p|-v|-s) ;;
    -g|-o|-t) shift ;;
    --) shift
        while [ "$#" -gt 0 ]; do files="$files $1"; shift; done
        break ;;
    -*) ;;
    *) files="$files $1" ;;
  esac
  shift
done
files=$(echo "$files" | sed 's/^ *//')
[ -z "$files" ] && exit 0
if [ "$is_dir" = 1 ]; then
  for d in $files; do mkdir -p "$d" || exit 1; done
  exit 0
fi
set -- $files
count=$#
[ "$count" -lt 2 ] && exit 0
dest=""
for last in $files; do dest="$last"; done
if [ "$count" -ge 3 ]; then
  mkdir -p "$dest" || exit 1
elif [ "$mk_leading" = 1 ]; then
  mkdir -p "$(dirname "$dest")" || exit 1
fi
cp -f $files || exit 1
exit 0
"""


class LiblouisxmlConan(ConanFile):
    name = "liblouisxml"
    version = "2.4.0"
    description = "Braille transcription services for XML/HTML via liblouis"
    license = "GPL-3.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://github.com/liblouis/liblouisxml"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"liblouisxml supports Linux and OHOS, not {self.settings.os}")

    def requirements(self):
        # libxml2/2.15.3.1 is the OHOS-adapted Conan package (ohpcd registry, no
        # conancenter cmake tool_requires). 2.15.3 exists in conancenter and
        # pulls cmake/4.4.3 which has KeyError: 'OHOS' (recipe has no OHOS
        # sources). Pin to 2.15.3.1 to force ohpcd resolution and avoid the
        # cmake build failure seen in preflight logs.
        self.requires("libxml2/2.15.3.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        # main source
        get(self, **self.conan_data["sources"]["liblouisxml"], strip_root=True)
        # private liblouis source for bundling
        get(self, **self.conan_data["sources"]["liblouis"], strip_root=True,
            destination=os.path.join(self.source_folder, "liblouis_src"))

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        pcdeps = PkgConfigDeps(self)
        pcdeps.generate()

        tc = AutotoolsToolchain(self)
        # Disable python bindings (already patched, but keep configure from trying)
        tc.configure_args.append("--disable-dependency-tracking")
        # OHOS triplet compat: old config.sub (2022-01-09) does not know linux-ohos.
        # Use linux-gnu for --build/--host to stay compatible with bundled liblouis
        # config.sub while still using OHOS clang. Idempotent to avoid duplicate append.
        for arg in list(tc.configure_args):
            if "aarch64-unknown-linux-ohos" in arg:
                tc.configure_args.remove(arg)
        # AutotoolsToolchain will auto-add --host/--build for cross; ensure they are gnu if OHOS
        # We append explicit gnu triplet only if not already present to keep idempotency.
        # Note: manual liblouis configure also uses gnu triplet (see _build_liblouis).
        if self.settings.os == "OHOS":
            gnu_host = "aarch64-unknown-linux-gnu"
            gnu_build = "aarch64-unknown-linux-gnu"
            # Only add if not already in args
            has_host = any(a.startswith("--host=") for a in tc.configure_args)
            has_build = any(a.startswith("--build=") for a in tc.configure_args)
            if not has_host:
                tc.configure_args.append(f"--host={gnu_host}")
            if not has_build:
                tc.configure_args.append(f"--build={gnu_build}")
        # Ensure prefix is correct
        tc.generate()

        # Prepare environment for private liblouis prefix
        # HMBS injects TMPDIR/TEMP/TMP (e.g. /storage/.../runtime/liblouisxml-2.4.0/tmp)
        # and guarantees it is writable (HMDFS /tmp is read-only). Prefer the
        # HMBS-provided tmpdir when present, otherwise fall back to a
        # build-folder-local .tmp.  This satisfies the readonly_tmp gate.
        env = Environment()
        hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if hmbs_tmp and os.path.isdir(hmbs_tmp):
            tmpdir = hmbs_tmp
        else:
            tmpdir = os.path.join(self.build_folder, ".tmp")
            os.makedirs(tmpdir, exist_ok=True)
        # Ensure the directory exists even when HMBS tmpdir is used (hmbs creates it,
        # but be defensive for local builds).
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # HMDFS shell compat: ensure configure uses a sane shell that honours PWD fallback
        hmbs_shell = os.environ.get("SHELL") or os.environ.get("HMBS_SHELL") or "/bin/sh"
        env.define("SHELL", hmbs_shell)
        env.define("CONFIG_SHELL", hmbs_shell)
        env.vars(self).save_script("conanbuild_tmpdir")

    def _patch_autoconf_tmpdir(self, configure_path):
        """HMDFS/readonly /tmp fix: autoconf tmpdir/umask/hardcoded /tmp.

        Robust handling for HMFS read-only /tmp + HMDFS umask 077 permission
        issue.  Mirrors librasterlite2 0003-configure-task-tmpdir.patch:
         - umask 077 -> 022 (20001006 vs 20020083 UID mismatch makes 0700 unwritable)
         - mktemp -d "./confXXXXXX" -> "${TMPDIR:-.}/confXXXXXX" (writable TMPDIR, fallback .)
         - tmp=./conf$$-$RANDOM -> tmp=${TMPDIR:-.}/conf$$-$RANDOM
         - hardcoded /tmp -> ${TMPDIR:-/tmp}
        """
        if not os.path.isfile(configure_path):
            return
        try:
            data = open(configure_path, "r", encoding="utf-8", errors="replace").read()
            orig = data
            # 1) umask 077 -> 022 globally (HMDFS fix)
            data = data.replace("umask 077", "umask 022")
            # 2) mktemp templates in autoconf's secure tmpdir block
            #    Handle both quoted forms; use ${TMPDIR:-.} fallback to build dir if TMPDIR unset.
            data = data.replace('mktemp -d "./conf', 'mktemp -d "${TMPDIR:-.}/conf')
            data = data.replace("mktemp -d './conf", "mktemp -d '${TMPDIR:-.}/conf")
            data = data.replace('mktemp -d -q "./conf', 'mktemp -d -q "${TMPDIR:-.}/conf')
            data = data.replace("mktemp -d -q './conf", "mktemp -d -q '${TMPDIR:-.}/conf")
            # 3) Fallback mkdir branch: tmp=./conf$$-$RANDOM
            data = data.replace("tmp=./conf$$-$RANDOM", "tmp=${TMPDIR:-.}/conf$$-$RANDOM")
            data = data.replace('tmp="./conf$$-$RANDOM"', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"')
            # 4) Any remaining hardcoded /tmp (shell heredoc tmp, /tmp/sh*, /tmp/conf)
            #    Only replace literal /tmp/ to avoid double-patching ${TMPDIR:-/tmp}
            if "${TMPDIR:-/tmp}" not in data or data.count("/tmp/") > data.count("${TMPDIR:-/tmp}/"):
                data = data.replace('"/tmp/', '"${TMPDIR:-/tmp}/')
                data = data.replace("'/tmp/", "'${TMPDIR:-/tmp}/")
                # bare /tmp/sh and /tmp/conf without quotes
                data = data.replace("/tmp/sh", "${TMPDIR:-/tmp}/sh")
                data = data.replace("/tmp/conf", "${TMPDIR:-/tmp}/conf")
            if data != orig:
                open(configure_path, "w", encoding="utf-8").write(data)
                self.output.info(f"[ok] Patched autoconf TMPDIR/umask in {os.path.basename(configure_path)}")
        except Exception as e:
            self.output.warning(f"Failed to patch {configure_path}: {e}")

    def _patch_all_configure_tmpdir(self):
        """Walk source_folder and patch every configure/config.status for readonly /tmp."""
        for root, _, files in os.walk(self.source_folder):
            for fname in ("configure", "config.status"):
                if fname in files:
                    self._patch_autoconf_tmpdir(os.path.join(root, fname))
                    self._patch_configure_pwd(os.path.join(root, fname))

    def _patch_configure_pwd(self, configure_path):
        """HMDFS getcwd fix: configure pwd check must fall back to $PWD."""
        if not os.path.isfile(configure_path):
            return
        try:
            data = open(configure_path, "r", encoding="utf-8", errors="replace").read()
            orig = data
            data = data.replace(
                'ac_pwd=`pwd` && test -n \"$ac_pwd\" &&',
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\n'
                'test -n \"$ac_pwd\" &&')
            data = data.replace(
                'if (pwd) >/dev/null 2>&1 && test -n \"`pwd`\"',
                'if (pwd) >/dev/null 2>&1 || test -n \"$PWD\"')
            data = data.replace(
                'ac_pwd=`pwd`',
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"')
            data = data.replace(
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\" 2>/dev/null || ac_pwd=\"$PWD\"',
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"')
            if data != orig:
                open(configure_path, "w", encoding="utf-8").write(data)
                self.output.info(f"[ok] Patched configure PWD fallback in {os.path.basename(configure_path)}")
            else:
                self.output.warning(f"configure pwd-check pattern not found in {os.path.basename(configure_path)}; relying on PWD env")
        except Exception as e:
            self.output.warning(f"Failed to patch PWD in {configure_path}: {e}")

    def _patch_config_guess(self, cg_path):
        try:
            data = open(cg_path, "r", encoding="utf-8", errors="replace").read()
            orig = data
            if "__OHOS__" not in data:
                old = "#if defined(__ANDROID__)\n    LIBC=android"
                new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
                if old in data:
                    data = data.replace(old, new, 1)
            if "HarmonyOS" not in data:
                block = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    i?86)          MACHINE=i686 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                    '\t;;\n\n'
                    '    *:NetBSD:*:*)'
                )
                if "    *:NetBSD:*:*)" in data:
                    data = data.replace("    *:NetBSD:*:*)", block, 1)
            if data != orig:
                open(cg_path, "w", encoding="utf-8").write(data)
                self.output.info(f"[ok] Patched config.guess OHOS in {os.path.basename(os.path.dirname(cg_path))}")
        except Exception as e:
            self.output.warning(f"Failed to patch config.guess {cg_path}: {e}")

    def _patch_config_sub(self, cs_path):
        try:
            data = open(cs_path, "r", encoding="utf-8", errors="replace").read()
            orig = data
            if "ohos-linux" not in data:
                pat = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
                rep = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
                new_data, n = re.subn(pat, rep, data)
                if n > 0:
                    data = new_data
            if "ohos*" not in data:
                if "gnu* | android*" in data:
                    data = data.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            if "linux-ohos" not in data:
                new_data, n = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', data)
                if n > 0:
                    data = new_data
            if data != orig:
                open(cs_path, "w", encoding="utf-8").write(data)
                self.output.info(f"[ok] Patched config.sub OHOS in {os.path.basename(os.path.dirname(cs_path))}")
        except Exception as e:
            self.output.warning(f"Failed to patch config.sub {cs_path}: {e}")

    def _patch_config_for_ohos(self):
        """Patch all config.guess/sub under source_folder for OHOS."""
        for root, _, files in os.walk(self.source_folder):
            if "config.guess" in files and "config.sub" in files:
                self._patch_config_guess(os.path.join(root, "config.guess"))
                self._patch_config_sub(os.path.join(root, "config.sub"))
            # also handle bare copies
            if "config.guess" in files:
                # if sibling sub not in same dir, still patch guess
                try:
                    self._patch_config_guess(os.path.join(root, "config.guess"))
                except Exception:
                    pass

    def _patch_liblouisxml_config_h(self):
        """Ensure gnulib wrappers find _GL_CONFIG_H_INCLUDED in liblouisxml/config.h."""
        cfg = os.path.join(self.source_folder, "liblouisxml", "config.h.in")
        if os.path.isfile(cfg):
            try:
                txt = open(cfg, "r", encoding="utf-8", errors="replace").read()
                if "_GL_CONFIG_H_INCLUDED" not in txt:
                    # Insert define before first #undef so generated config.h defines it
                    if "#undef" in txt:
                        txt = txt.replace("#undef", "#define _GL_CONFIG_H_INCLUDED 1\n#undef", 1)
                        open(cfg, "w", encoding="utf-8").write(txt)
                        self.output.info("[ok] Patched liblouisxml/config.h.in _GL_CONFIG_H_INCLUDED")
            except Exception as e:
                self.output.warning(f"Failed to patch config.h.in: {e}")

    def _patch_gnulib_wrappers(self):
        """Post-configure: neutralize gnulib header guard that requires config.h first."""
        for root, _, files in os.walk(self.build_folder):
            if "gnulib" not in root:
                continue
            for fn in files:
                if not fn.endswith(".h"):
                    continue
                fpath = os.path.join(root, fn)
                try:
                    txt = open(fpath, "r", encoding="utf-8", errors="replace").read()
                    if "Please include config.h first" in txt:
                        txt = txt.replace('#if !_GL_CONFIG_H_INCLUDED\n #error "Please include config.h first."\n#endif', '')
                        txt = txt.replace('#if !_GL_CONFIG_H_INCLUDED\n#error "Please include config.h first."\n#endif', '')
                        if "Please include config.h first" in txt:
                            txt = txt.replace('Please include config.h first', 'config.h check patched for OHOS')
                        open(fpath, "w", encoding="utf-8").write(txt)
                        self.output.info(f"[ok] Patched gnulib wrapper {os.path.basename(fpath)}")
                except Exception:
                    pass

    def _patch_liblouisxml_attribute_unused(self):
        """liblouisxml 2.4.0 uses ATTRIBUTE_UNUSED but newer gnulib no longer defines it.
        Provide fallback definition after config.h include to fix clang error:
        liblouisxml.c:49:30: error: expected ')' """
        f = os.path.join(self.source_folder, "liblouisxml", "liblouisxml.c")
        if not os.path.isfile(f):
            return
        try:
            txt = open(f, "r", encoding="utf-8", errors="replace").read()
            if "ATTRIBUTE_UNUSED" in txt and "ifndef ATTRIBUTE_UNUSED" not in txt:
                # Insert fallback after first #include "config.h"
                if '#include "config.h"' in txt:
                    txt = txt.replace('#include "config.h"', '#include "config.h"\n#ifndef ATTRIBUTE_UNUSED\n# if defined(__GNUC__) && (__GNUC__ >= 3)\n#  define ATTRIBUTE_UNUSED __attribute__ ((__unused__))\n# else\n#  define ATTRIBUTE_UNUSED\n# endif\n#endif', 1)
                    open(f, "w", encoding="utf-8").write(txt)
                    self.output.info("[ok] Patched liblouisxml.c ATTRIBUTE_UNUSED fallback")
        except Exception as e:
            self.output.warning(f"Failed to patch ATTRIBUTE_UNUSED: {e}")

    def _patch_transcriber_implicit(self):
        """Fix transcriber.c:87 conflicting types for widecharcpy due to implicit declaration.
        widestrcpy() calls widecharcpy() before its definition without a prior prototype,
        causing clang to assume implicit int widecharcpy() and then conflict.
        Provide forward declaration after louisxml.h include."""
        f = os.path.join(self.source_folder, "liblouisxml", "transcriber.c")
        if not os.path.isfile(f):
            return
        try:
            txt = open(f, "r", encoding="utf-8", errors="replace").read()
            if "widecharcpy" in txt and "void widecharcpy(widechar* to, const widechar* from, int length);" not in txt:
                if '#include "louisxml.h"' in txt:
                    txt = txt.replace('#include "louisxml.h"', '#include "louisxml.h"\nvoid widecharcpy(widechar* to, const widechar* from, int length);\nvoid widestrcpy(widechar* to, const widechar* from);', 1)
                    open(f, "w", encoding="utf-8").write(txt)
                    self.output.info("[ok] Patched transcriber.c widecharcpy forward declaration")
                elif "void\nwidestrcpy" in txt:
                    txt = txt.replace("void\nwidestrcpy", "void widecharcpy(widechar* to, const widechar* from, int length);\nvoid\nwidestrcpy", 1)
                    open(f, "w", encoding="utf-8").write(txt)
                    self.output.info("[ok] Patched transcriber.c via widestrcpy anchor")
        except Exception as e:
            self.output.warning(f"Failed to patch transcriber.c: {e}")


    def _build_liblouis(self):
        """Build private liblouis as static library and install to private prefix."""
        src = os.path.join(self.source_folder, "liblouis_src")
        build_dir = os.path.join(self.build_folder, "liblouis_build")
        prefix = os.path.join(self.build_folder, "liblouis_prefix")
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(prefix, exist_ok=True)

        if os.path.isdir(prefix):
            shutil.rmtree(prefix)
            os.makedirs(prefix, exist_ok=True)

        # HMDFS getcwd fix: ensure PWD points to the build_dir before configure
        # (bash pwd falls back to $PWD when getcwd fails). Also ensure TMPDIR
        # is visible for autoconf temp dirs (HMDFS /tmp is read-only).
        try:
            os.chdir(build_dir)
        except Exception:
            pass
        os.environ["PWD"] = build_dir
        # Ensure TMPDIR env is exported for the child shell (conanbuild env already has it,
        # but also set in os.environ for direct sh invocation)
        hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if hmbs_tmp:
            os.environ["TMPDIR"] = hmbs_tmp
            os.environ["TMP"] = hmbs_tmp
            os.environ["TEMP"] = hmbs_tmp
        os.environ["SHELL"] = os.environ.get("SHELL", "/bin/sh")
        os.environ["CONFIG_SHELL"] = os.environ.get("CONFIG_SHELL", os.environ.get("SHELL", "/bin/sh"))

        # Use Autotools helper for private build to reuse toolchain env
        # We run configure via sh explicitly with conanbuild env
        # Explicit --build/--host with gnu triplet to avoid config.guess failure on HarmonyOS (old 2022 config.guess cannot guess HarmonyOS)
        gnu_triplet = "aarch64-unknown-linux-gnu"
        # liblouis is built as a static archive but linked into shared liblouisxml.so;
        # on aarch64 a non-PIC archive causes R_AARCH64_ADR_PREL_PG_HI21 errors.
        # Force PIC objects when the package is shared or fPIC is enabled.
        pic_cflags = ""
        try:
            if self.options.shared or self.options.get_safe("fPIC"):
                pic_cflags = "-fPIC -DPIC"
        except Exception:
            pic_cflags = "-fPIC -DPIC"
        extra_args = " --with-pic" if pic_cflags else ""
        if pic_cflags:
            base_cflags = os.environ.get("CFLAGS", "")
            base_cxxflags = os.environ.get("CXXFLAGS", "")
            cflags = f"{base_cflags} {pic_cflags}".strip() if base_cflags else pic_cflags
            cxxflags = f"{base_cxxflags} {pic_cflags}".strip() if base_cxxflags else pic_cflags
            # Inject via command prefix so configure sees them (conanbuild env is still applied)
            configure_cmd = f'CFLAGS="{cflags}" CXXFLAGS="{cxxflags}" sh {src}/configure --prefix={prefix} --disable-shared --enable-static --with-yaml=no --disable-dependency-tracking --build={gnu_triplet} --host={gnu_triplet}{extra_args}'
        else:
            configure_cmd = f"sh {src}/configure --prefix={prefix} --disable-shared --enable-static --with-yaml=no --disable-dependency-tracking --build={gnu_triplet} --host={gnu_triplet}{extra_args}"
        # Ensure conanbuild env is active for correct CC etc.
        self.run(configure_cmd, cwd=build_dir, env="conanbuild")
        if pic_cflags:
            # Ensure make also sees PIC flags (some sub-makes ignore configure CFLAGS)
            self.run(f'make -j1 MAKEINFO=true CFLAGS="{cflags}" CXXFLAGS="{cxxflags}"', cwd=build_dir, env="conanbuild")
        else:
            self.run("make -j1 MAKEINFO=true", cwd=build_dir, env="conanbuild")
        # HMFS/HMDFS: install -m (chmod) and hardlink not supported (hmbs caps chmod=0 hardlink=0)
        # Use shim that ignores -m and does cp/mkdir; libtool's install uses $INSTALL
        shim_path = os.path.join(self.build_folder, "install-shim-liblouis.sh")
        with open(shim_path, "w", encoding="utf-8") as f:
            f.write(_INSTALL_SHIM)
        # libtool requires INSTALL to be "$SHELL <shim>" form to be recognized
        self.run(f'make install -j1 MAKEINFO=true INSTALL="/bin/sh {shim_path}" INSTALL_DATA="/bin/sh {shim_path}"', cwd=build_dir, env="conanbuild")

        return prefix

    def build(self):
        # HMDFS platform workaround: shell and make both call getcwd() which
        # fails on HMDFS parent dirs (see preflight log: getcwd cannot access
        # parent directories). Export logical PWD and ensure we are chdir'ed
        # to build_folder so pwd fallback works. Also propagate TMPDIR/SHELL.
        try:
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if hmbs_tmp:
            os.environ["TMPDIR"] = hmbs_tmp
            os.environ["TMP"] = hmbs_tmp
            os.environ["TEMP"] = hmbs_tmp
        os.environ["SHELL"] = os.environ.get("SHELL", "/bin/sh")
        os.environ["CONFIG_SHELL"] = os.environ.get("CONFIG_SHELL", os.environ.get("SHELL", "/bin/sh"))

        apply_conandata_patches(self)
        # OHOS config.guess/sub: bundled liblouis 3.33 uses 2022-01-09 scripts that cannot guess HarmonyOS
        self._patch_config_for_ohos()
        # Fallback for python SUBDIRS removal: patch file now only touches
        # Makefile.am; Makefile.in header varies by automake version and would
        # fail patch application. Do robust in-place replacement here for both
        # files and for configure's AC_CONFIG_FILES.
        # NOTE: Only touch SUBDIRS line to avoid corrupting install-man etc.
        def _clean_subdirs_line(data):
            def repl_subdirs(m):
                full = m.group(0)
                # Preserve trailing newline if present
                has_nl = full.endswith('\n')
                line = full.rstrip('\n')
                if '=' not in line:
                    return full
                prefix, value = line.split('=', 1)
                # value contains tokens like " gnulib doc lbx_files ..."
                tokens = value.strip().split()
                filtered = [t for t in tokens if t not in ("doc", "man", "python")]
                new_line = f"{prefix.strip()} = {' '.join(filtered)}"
                if has_nl:
                    new_line += '\n'
                return new_line
            # Only modify SUBDIRS assignment, not global doc/man words (keep install-man)
            return re.sub(r'SUBDIRS\s*=.*\n?', repl_subdirs, data)
        for fname in ["Makefile.am", "Makefile.in"]:
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                try:
                    data = open(fpath, "r", encoding="utf-8", errors="replace").read()
                    orig = data
                    data = _clean_subdirs_line(data)
                    if data != orig:
                        open(fpath, "w", encoding="utf-8").write(data)
                        self.output.info(f"[ok] Patched {fname} remove python/doc/man from SUBDIRS")
                except Exception as e:
                    self.output.warning(f"Failed to patch {fpath}: {e}")
        # Fix configure still referencing python/Makefile (if patch didn't cover configure)
        # Remove python from AC_CONFIG_FILES if still present - careful not to corrupt case statement
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            try:
                data = open(configure_path, "r", encoding="utf-8", errors="replace").read()
                orig_cfg = data
                if "python/Makefile" in data:
                    # AC_CONFIG_FILES string: remove " python/Makefile" token only
                    data = data.replace(" python/Makefile", "")
                    # case branch: replace '"python/Makefile")' with empty pattern that never matches
                    # but keep syntax valid: turn into ' "__python_disabled__")'
                    data = data.replace('"python/Makefile")', '"__python_disabled__")')
                    data = data.replace("'python/Makefile')", "'__python_disabled__')")
                    # Also remove CONFIG_FILES insertion for python
                    data = data.replace('CONFIG_FILES="$CONFIG_FILES python/Makefile"', 'CONFIG_FILES="$CONFIG_FILES"')
                    data = data.replace("CONFIG_FILES='$CONFIG_FILES python/Makefile'", "CONFIG_FILES='$CONFIG_FILES'")
                    if data != orig_cfg:
                        open(configure_path, "w", encoding="utf-8").write(data)
                        self.output.info("[ok] Patched configure remove python/Makefile")
            except Exception as e:
                self.output.warning(f"Failed to patch configure python: {e}")
            # HMDFS/readonly /tmp fix: will be handled by _patch_all_configure_tmpdir() below
        # Also patch private liblouis doc/man out of SUBDIRS (same Signal 9 issue)
        # NOTE: targeted SUBDIRS cleaning to avoid corrupting install-man etc.
        def _clean_louis_subdirs(data):
            def repl(m):
                full = m.group(0)
                has_nl = full.endswith('\n')
                line = full.rstrip('\n')
                # Match SUBDIRS = ... or SUBDIRS += ...
                mm = re.match(r'(\s*SUBDIRS\s*)(\+?=)\s*(.*)', line)
                if not mm:
                    return full
                lhs, op, rhs = mm.groups()
                tokens = rhs.strip().split()
                filtered = [t for t in tokens if t not in ("doc", "man")]
                new_line = f"SUBDIRS {op} {' '.join(filtered)}"
                if has_nl:
                    new_line += '\n'
                return new_line
            return re.sub(r'SUBDIRS\s*\+?=\s*.*\n?', repl, data)
        for fname in ["Makefile.am", "Makefile.in"]:
            fpath = os.path.join(self.source_folder, "liblouis_src", fname)
            if os.path.isfile(fpath):
                try:
                    d = open(fpath, "r", encoding="utf-8", errors="replace").read()
                    orig = d
                    d = _clean_louis_subdirs(d)
                    if d != orig:
                        open(fpath, "w", encoding="utf-8").write(d)
                        self.output.info(f"[ok] Patched liblouis_src/{fname} remove doc/man from SUBDIRS")
                except Exception as e:
                    self.output.warning(f"Failed to patch {fpath}: {e}")
        # HMFS/HMDFS readonly /tmp + getcwd: patch every configure/config.status
        self._patch_all_configure_tmpdir()

        # Build private liblouis
        louis_prefix = self._build_liblouis()
        pkgconfig_dir = os.path.join(louis_prefix, "lib", "pkgconfig")
        # Also check lib64 variant (some builds use lib64)
        if not os.path.isdir(pkgconfig_dir):
            alt = os.path.join(louis_prefix, "lib64", "pkgconfig")
            if os.path.isdir(alt):
                pkgconfig_dir = alt

        # Ensure PKG_CONFIG_PATH includes private liblouis and libxml2
        # PkgConfigDeps already generated files in build_folder, but we need to prepend our private dir
        env_pkg = os.environ.get("PKG_CONFIG_PATH", "")
        combined = pkgconfig_dir + (":" + env_pkg if env_pkg else "")
        os.environ["PKG_CONFIG_PATH"] = combined

        # Patch liblouisxml config.h.in to define _GL_CONFIG_H_INCLUDED for gnulib wrappers
        self._patch_liblouisxml_config_h()
        self._patch_liblouisxml_attribute_unused()
        self._patch_transcriber_implicit()
        # Also set via Environment for Autotools
        # Configure and build liblouisxml
        autotools = Autotools(self)
        # Use CONFIG_SHELL=sh for OHOS compatibility
        # Autotools will automatically use the toolchain's configure args
        autotools.configure()
        # Post-configure: patch config.status for HMDFS/readonly /tmp (generated from configure)
        for root, _, files in os.walk(self.build_folder):
            if "config.status" in files:
                self._patch_autoconf_tmpdir(os.path.join(root, "config.status"))
                # config.status also contains ac_pwd and /tmp refs
                try:
                    cs = os.path.join(root, "config.status")
                    data = open(cs, "r", encoding="utf-8", errors="replace").read()
                    orig = data
                    # Same PWD fallback for config.status
                    data = data.replace('ac_pwd=`pwd`', 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
                    data = data.replace("/tmp/sh", "${TMPDIR:-/tmp}/sh")
                    data = data.replace("/tmp/conf", "${TMPDIR:-/tmp}/conf")
                    if data != orig:
                        open(cs, "w", encoding="utf-8").write(data)
                except Exception:
                    pass
        # Post-configure: patch generated gnulib headers that check _GL_CONFIG_H_INCLUDED
        self._patch_gnulib_wrappers()
        autotools.make(args=["-j1", "MAKEINFO=true"])
        # OHOS: sign built ELFs before make check (kernel requires .codesign, otherwise Permission denied)
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if os.path.isfile(sign_tool) and os.path.isfile(objcopy):
                for root, _, files in os.walk(self.build_folder):
                    for fn in files:
                        fpath = os.path.join(root, fn)
                        # Only sign real ELF executables / .so; skip scripts and symlinks
                        try:
                            if os.path.islink(fpath):
                                continue
                            # Quick heuristic: check ELF magic; also limit to known test/binary dirs to avoid signing .a/.o
                            with open(fpath, "rb") as fh:
                                if fh.read(4) != b"\x7fELF":
                                    continue
                        except Exception:
                            continue
                        try:
                            self.run(f'{objcopy} --remove-section .codesign "{fpath}" 2>/dev/null || true')
                            tmp_signed = fpath + ".signed"
                            self.run(f'{sign_tool} sign -inFile "{fpath}" -outFile "{tmp_signed}" -selfSign 1 2>/dev/null || true')
                            if os.path.isfile(tmp_signed):
                                try:
                                    os.replace(tmp_signed, fpath)
                                except Exception:
                                    try:
                                        shutil.move(tmp_signed, fpath)
                                    except Exception:
                                        pass
                                try:
                                    os.chmod(fpath, 0o755)
                                except Exception:
                                    pass
                        except Exception:
                            pass
        # Upstream test: make check (runs tests/check_version)
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception as e:
            # If check fails, still try to continue but log
            self.output.warning(f"make check failed: {e}")
            raise

    def package(self):
        # HMDFS: ensure PWD/TMPDIR/SHELL like build() for HMDFS getcwd/readonly /tmp
        try:
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if hmbs_tmp:
            os.environ["TMPDIR"] = hmbs_tmp
            os.environ["TMP"] = hmbs_tmp
            os.environ["TEMP"] = hmbs_tmp
        os.environ["SHELL"] = os.environ.get("SHELL", "/bin/sh")
        os.environ["CONFIG_SHELL"] = os.environ.get("CONFIG_SHELL", os.environ.get("SHELL", "/bin/sh"))

        # HMFS shim: if package install also hits chmod/hardlink, use same shim
        shim_path = os.path.join(self.build_folder, "install-shim-pkg.sh")
        installed = False
        try:
            with open(shim_path, "w", encoding="utf-8") as f:
                f.write(_INSTALL_SHIM)
            # First try: direct make with shim and MAKEINFO=true (changelog: shim handles chmod)
            self.run(f'make install -j1 MAKEINFO=true DESTDIR="{self.package_folder}" INSTALL="/bin/sh {shim_path}" INSTALL_DATA="/bin/sh {shim_path}"', cwd=self.build_folder, env="conanbuild")
            installed = True
        except Exception as e:
            self.output.warning(f"shim install failed (cwd={self.build_folder}): {e}; trying Autotools.install")
            try:
                autotools = Autotools(self)
                autotools.install(args=["-j1", "MAKEINFO=true"])
                installed = True
            except Exception as e2:
                self.output.warning(f"Autotools.install failed: {e2}; trying source_folder install")
                try:
                    self.run(f'make install -j1 MAKEINFO=true DESTDIR="{self.package_folder}" INSTALL="/bin/sh {shim_path}" INSTALL_DATA="/bin/sh {shim_path}"', cwd=self.source_folder, env="conanbuild")
                    installed = True
                except Exception as e3:
                    self.output.warning(f"source_folder install failed: {e3}; falling back to manual copy")
        # Verify install actually produced expected files; if not, force manual fallback
        try:
            pc_check = os.path.join(self.package_folder, "lib", "pkgconfig", "liblouisxml.pc")
            lib_dir_check = os.path.join(self.package_folder, "lib")
            has_lib = False
            if os.path.isdir(lib_dir_check):
                for fn in os.listdir(lib_dir_check):
                    if fn.startswith("liblouisxml.so"):
                        has_lib = True
                        break
            if installed and (not os.path.isfile(pc_check) or not has_lib):
                self.output.warning(f"make install reported success but pc/lib missing (pc={os.path.isfile(pc_check)} has_lib={has_lib}); forcing manual copy")
                installed = False
        except Exception:
            pass
        if not installed:
            # Manual fallback: copy built artifacts directly (HMDFS/chmod fallback)
            self.output.warning("make install failed or incomplete, using manual copy fallback")
            # liblouisxml shared library from .libs - search recursively for robustness
            try:
                # Prefer liblouisxml/.libs
                copy(self, "*.so*", src=os.path.join(self.build_folder, "liblouisxml", ".libs"), dst=os.path.join(self.package_folder, "lib"))
                copy(self, "*.a", src=os.path.join(self.build_folder, "liblouisxml", ".libs"), dst=os.path.join(self.package_folder, "lib"))
            except Exception:
                pass
            # Also search in build_folder tree for liblouisxml shared objects (handles VPATH variations)
            try:
                for root, _, files in os.walk(self.build_folder):
                    for fn in files:
                        if fn.startswith("liblouisxml.so") or fn == "liblouisxml.a":
                            src_path = os.path.join(root, fn)
                            try:
                                dst = os.path.join(self.package_folder, "lib", fn)
                                os.makedirs(os.path.dirname(dst), exist_ok=True)
                                shutil.copy2(src_path, dst)
                            except Exception:
                                pass
                for root, _, files in os.walk(self.source_folder):
                    for fn in files:
                        if fn.startswith("liblouisxml.so") or fn == "liblouisxml.a":
                            src_path = os.path.join(root, fn)
                            try:
                                dst = os.path.join(self.package_folder, "lib", fn)
                                if not os.path.isfile(dst) and not os.path.islink(dst):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.copy2(src_path, dst)
                            except Exception:
                                pass
            except Exception:
                pass
            try:
                lib_dir = os.path.join(self.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    real_so = None
                    for fn in os.listdir(lib_dir):
                        if fn == "liblouisxml.so.1.2.0":
                            real_so = os.path.join(lib_dir, fn)
                            break
                    if real_so is None:
                        for fn in os.listdir(lib_dir):
                            if fn.startswith("liblouisxml.so.") and fn.count(".") >= 3:
                                real_so = os.path.join(lib_dir, fn)
                                break
                    if real_so is None:
                        for fn in os.listdir(lib_dir):
                            if fn.startswith("liblouisxml.so."):
                                real_so = os.path.join(lib_dir, fn)
                                break
                    if real_so and os.path.isfile(real_so):
                        real_base = os.path.basename(real_so)
                        for link_name in ["liblouisxml.so.1", "liblouisxml.so"]:
                            link_path = os.path.join(lib_dir, link_name)
                            try:
                                if os.path.islink(link_path):
                                    target = os.readlink(link_path)
                                    if target == real_base:
                                        continue
                                    try:
                                        os.remove(link_path)
                                    except Exception:
                                        pass
                                elif os.path.isfile(link_path):
                                    try:
                                        if os.path.getsize(link_path) != os.path.getsize(real_so):
                                            os.remove(link_path)
                                        else:
                                            try:
                                                os.remove(link_path)
                                            except Exception:
                                                pass
                                    except Exception:
                                        try:
                                            os.remove(link_path)
                                        except Exception:
                                            pass
                                try:
                                    os.symlink(real_base, link_path)
                                except Exception:
                                    try:
                                        shutil.copy2(real_so, link_path)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
            except Exception:
                pass
            # Also try top-level .libs (in case lib is in build_folder directly)
            try:
                copy(self, "liblouisxml.so*", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
                copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
            except Exception:
                pass
            # Headers - ensure both include/liblouisxml and include for pkg-config Cflags compatibility
            try:
                copy(self, "*.h", src=os.path.join(self.source_folder, "liblouisxml"), dst=os.path.join(self.package_folder, "include", "liblouisxml"))
                copy(self, "*.h", src=os.path.join(self.build_folder, "liblouisxml"), dst=os.path.join(self.package_folder, "include", "liblouisxml"))
                # Also copy bare headers to include/ for consumers that do #include "liblouisxml.h" with -I.../include
                for hdr in ["liblouisxml.h", "louisxml.h"]:
                    for src_root in [os.path.join(self.source_folder, "liblouisxml"), os.path.join(self.build_folder, "liblouisxml")]:
                        src_file = os.path.join(src_root, hdr)
                        if os.path.isfile(src_file):
                            try:
                                dst_file = os.path.join(self.package_folder, "include", hdr)
                                if not os.path.isfile(dst_file):
                                    shutil.copy2(src_file, dst_file)
                            except Exception:
                                pass
            except Exception:
                pass
            # pkgconfig - search more broadly
            try:
                copy(self, "liblouisxml.pc", src=self.build_folder, dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
                copy(self, "liblouisxml.pc", src=self.source_folder, dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
                # Also search subdirs (e.g. liblouisxml/liblouisxml.pc)
                for root, _, files in os.walk(self.build_folder):
                    if "liblouisxml.pc" in files:
                        try:
                            copy(self, "liblouisxml.pc", src=root, dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
                        except Exception:
                            pass
            except Exception:
                pass
            # tools binaries - handle libtool wrappers correctly (copy real ELF from .libs, overwriting wrapper)
            try:
                for prog in ["xml2brl", "msword2brl", "rtf2brl", "pdf2brl"]:
                    real_found = False
                    candidates = []
                    for root, _, files in os.walk(self.build_folder):
                        if prog in files:
                            src_file = os.path.join(root, prog)
                            candidates.append(src_file)
                    candidates.sort(key=lambda x: (".libs" not in x, len(x)))
                    for src_file in candidates:
                        try:
                            with open(src_file, 'rb') as f:
                                header = f.read(4)
                            is_elf = header == b'\x7fELF'
                            if is_elf:
                                dst_file = os.path.join(self.package_folder, "bin", prog)
                                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                                if os.path.isfile(dst_file) or os.path.islink(dst_file):
                                    try:
                                        os.remove(dst_file)
                                    except Exception:
                                        pass
                                shutil.copy2(src_file, dst_file)
                                real_found = True
                                break
                        except Exception:
                            pass
                    if not real_found:
                        for root, _, files in os.walk(self.source_folder):
                            if prog in files:
                                src_file = os.path.join(root, prog)
                                try:
                                    with open(src_file, 'rb') as f:
                                        header = f.read(4)
                                    if header == b'\x7fELF':
                                        dst_file = os.path.join(self.package_folder, "bin", prog)
                                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                                        if os.path.isfile(dst_file) or os.path.islink(dst_file):
                                            try:
                                                os.remove(dst_file)
                                            except Exception:
                                                pass
                                        shutil.copy2(src_file, dst_file)
                                        real_found = True
                                        break
                                except Exception:
                                    pass
                    if not real_found:
                        try:
                            copy(self, prog, src=os.path.join(self.build_folder, "tools", ".libs"), dst=os.path.join(self.package_folder, "bin"))
                            dst_file = os.path.join(self.package_folder, "bin", prog)
                            if os.path.isfile(dst_file):
                                try:
                                    with open(dst_file, 'rb') as f:
                                        if f.read(4) != b'\x7fELF':
                                            for root, _, files in os.walk(self.build_folder):
                                                if prog in files:
                                                    src_file = os.path.join(root, prog)
                                                    try:
                                                        with open(src_file, 'rb') as sf:
                                                            if sf.read(4) == b'\x7fELF':
                                                                shutil.copy2(src_file, dst_file)
                                                                real_found = True
                                                                break
                                                    except Exception:
                                                        pass
                                            if real_found:
                                                continue
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        try:
                            dst_file = os.path.join(self.package_folder, "bin", prog)
                            if not os.path.isfile(dst_file):
                                copy(self, prog, src=os.path.join(self.build_folder, "tools"), dst=os.path.join(self.package_folder, "bin"))
                        except Exception:
                            pass
            except Exception:
                pass
            # lbx_files data
            try:
                copy(self, "*.sem", src=os.path.join(self.source_folder, "lbx_files"), dst=os.path.join(self.package_folder, "share", "liblouisxml", "lbx_files"))
                copy(self, "*.cfg", src=os.path.join(self.source_folder, "lbx_files"), dst=os.path.join(self.package_folder, "share", "liblouisxml", "lbx_files"))
            except Exception:
                pass
        # Copy private liblouis artifacts into package if needed (for static linking consumers)
        # The private prefix contains liblouis.a and headers; we also ship them for completeness
        louis_prefix = os.path.join(self.build_folder, "liblouis_prefix")
        if os.path.isdir(louis_prefix):
            # Copy liblouis static lib into package lib
            for lib in ["liblouis.a", "liblouis.so", "liblouis.so.*"]:
                try:
                    copy(self, lib, src=os.path.join(louis_prefix, "lib"), dst=os.path.join(self.package_folder, "lib"))
                    copy(self, lib, src=os.path.join(louis_prefix, "lib64"), dst=os.path.join(self.package_folder, "lib"))
                except Exception:
                    pass
            # Copy headers
            try:
                copy(self, "*.h", src=os.path.join(louis_prefix, "include"), dst=os.path.join(self.package_folder, "include"))
            except Exception:
                pass
            # Copy pkgconfig
            for pc in ["liblouis.pc"]:
                try:
                    copy(self, pc, src=os.path.join(louis_prefix, "lib", "pkgconfig"), dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
                    copy(self, pc, src=os.path.join(louis_prefix, "lib64", "pkgconfig"), dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
                except Exception:
                    pass

        # --- Post-process pkg-config files to be relocatable (prefix=) ---
        try:
            pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig_dir):
                for pc_name in os.listdir(pkgconfig_dir):
                    if not pc_name.endswith(".pc"):
                        continue
                    pc_path = os.path.join(pkgconfig_dir, pc_name)
                    try:
                        txt = open(pc_path, "r", encoding="utf-8", errors="replace").read()
                        orig = txt
                        txt = re.sub(r'^prefix=.*$', 'prefix=${pcfiledir}/../..', txt, flags=re.MULTILINE)
                        if 'libdir=${exec_prefix}/lib' not in txt and 'libdir=${prefix}/lib' not in txt:
                            txt = re.sub(r'^libdir=.*$', 'libdir=${exec_prefix}/lib', txt, flags=re.MULTILINE)
                        if 'includedir=${prefix}/include' not in txt:
                            txt = re.sub(r'^includedir=.*$', 'includedir=${prefix}/include', txt, flags=re.MULTILINE)
                        if txt != orig:
                            open(pc_path, "w", encoding="utf-8").write(txt)
                            self.output.info(f"[ok] Rewrote pc prefix relocatable: {pc_name}")
                    except Exception as e:
                        self.output.warning(f"Failed to rewrite {pc_name}: {e}")
                # Also ensure headers are duplicated for both include layouts
                try:
                    inc_sub = os.path.join(self.package_folder, "include", "liblouisxml")
                    inc_root = os.path.join(self.package_folder, "include")
                    if os.path.isdir(inc_sub):
                        for hdr in os.listdir(inc_sub):
                            if hdr.endswith(".h"):
                                src = os.path.join(inc_sub, hdr)
                                dst = os.path.join(inc_root, hdr)
                                if not os.path.isfile(dst) and os.path.isfile(src):
                                    try:
                                        shutil.copy2(src, dst)
                                    except Exception:
                                        pass
                except Exception:
                    pass
        except Exception as e:
            self.output.warning(f"pc rewrite failed: {e}")

        # Clean up .la files
        for pattern in ["*.la"]:
            files = []
            for root, dirs, filenames in os.walk(self.package_folder):
                for fn in filenames:
                    if fn.endswith(".la"):
                        files.append(os.path.join(root, fn))
            for f in files:
                try:
                    os.remove(f)
                except Exception:
                    pass

        # --- OHOS ELF signing: kernel requires .codesign for dlopen/exec (E082/E077) ---
        # Without this, test_package ./test and xml2brl fail with "Permission denied" on HMDFS.
        # Packaged .so and binaries must be self-signed via binary-sign-tool.
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if os.path.isfile(sign_tool) and os.path.isfile(objcopy):
                for base in [os.path.join(self.package_folder, "lib"), os.path.join(self.package_folder, "bin")]:
                    if not os.path.isdir(base):
                        continue
                    for root, _, files in os.walk(base):
                        for fn in files:
                            fpath = os.path.join(root, fn)
                            # Skip symlinks; only sign real ELF files
                            try:
                                if os.path.islink(fpath):
                                    continue
                                with open(fpath, "rb") as fh:
                                    if fh.read(4) != b"\x7fELF":
                                        continue
                            except Exception:
                                continue
                            try:
                                self.run(f'{objcopy} --remove-section .codesign "{fpath}" 2>/dev/null || true')
                                # Use temp file then mv to avoid in-place overwrite issues
                                tmp_signed = fpath + ".signed"
                                self.run(f'{sign_tool} sign -inFile "{fpath}" -outFile "{tmp_signed}" -selfSign 1')
                                try:
                                    os.replace(tmp_signed, fpath)
                                except Exception:
                                    try:
                                        shutil.move(tmp_signed, fpath)
                                    except Exception:
                                        pass
                                try:
                                    os.chmod(fpath, 0o755)
                                except Exception:
                                    pass  # HMBS_CAP_CHMOD=0 may deny chmod; signing already sets mode
                            except Exception as e:
                                self.output.warning(f"ELF sign failed for {fpath}: {e}")
            else:
                self.output.warning("binary-sign-tool/llvm-objcopy not found; packaged ELF will be unsigned (OHOS Permission denied)")

        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["louisxml", "louis"]
        self.cpp_info.requires = ["libxml2::libxml2"]
        self.cpp_info.set_property("pkg_config_name", "liblouisxml")
        self.cpp_info.set_property("cmake_file_name", "liblouisxml")
        self.cpp_info.set_property("cmake_target_name", "liblouisxml::liblouisxml")
        # PkgConfig path
        pkg_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pkg_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pkg_dir)
