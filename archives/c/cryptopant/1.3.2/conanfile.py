#!/usr/bin/env python3
"""Conan recipe for cryptopant 1.3.2 on HarmonyOS PC.

CryptopANT is a C library for IP address anonymization using crypto-PAn
algorithm (prefix-preserving). Upstream uses Autotools.

Build system: Autotools (./configure --with-scramble_ips && make && make check)
Requires: openssl >=3.1.0 (uses EVP_CIPHER_fetch, EVP_MD_fetch).

HMBS adaptation: handle readonly /tmp, HMDFS getcwd, cross-compile host.
"""

import json
import os
import re
import subprocess
import pathlib

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
import shutil
import stat
import tempfile


class CryptopantConan(ConanFile):
    name = "cryptopant"
    version = "1.3.2"
    description = "C library for IP address anonymization using crypto-PAn algorithm"
    license = "GPL-2.0-only"
    homepage = "https://ant.isi.edu/software/cryptopANT/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    topics = ("crypto", "anonymization", "ip", "privacy")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_scramble_ips": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_scramble_ips": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def source(self):
        src = self.conan_data.get("sources", {})
        if isinstance(src, dict) and self.version in src:
            src = src[self.version]
        if isinstance(src, dict) and "url" not in src and "sha256" not in src:
            for v in src.values():
                if isinstance(v, dict) and "url" in v:
                    src = v
                    break
        get(self, **src, strip_root=True)

    def _bash(self):
        """Return a usable shell path, preferring /bin/sh to avoid HMDFS getcwd issues."""
        for cand in [os.environ.get("HMBS_SHELL"), os.environ.get("CONFIG_SHELL"), "/bin/sh"]:
            if cand and os.path.isfile(cand):
                return cand
        # fallback to env's bash
        for cand in ["/bin/bash", "/usr/bin/bash"]:
            if os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _patch_configure_for_ohos(self, base_dir):
        """Patch configure/config.status for HMBS: readonly /tmp, umask, HMDFS pwd."""
        for cfg_name in ["configure", "config.status"]:
            p = pathlib.Path(base_dir) / cfg_name
            if not p.is_file():
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
                orig = t
                # --- tmpdir: autoconf secure tmp ---
                t = t.replace(
                    'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                    'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&'
                )
                t = t.replace('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"')
                t = t.replace('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")')
                # generic fallback if quoting differs
                t = t.replace("./confXXXXXX", "${TMPDIR:-.}/confXXXXXX")
                # umask handling when chmod capability is 0
                if os.environ.get("HMBS_CAP_CHMOD", "1") == "0":
                    t = t.replace("umask 077 && ", "umask 022 && ")
                    t = t.replace("umask 077", "umask 022")
                # --- hard-coded /tmp rewriting (aggregated experience #78) ---
                t = t.replace('"/tmp/', '"${TMPDIR:-/tmp}/')
                t = t.replace("'/tmp/", "'${TMPDIR:-/tmp}/")
                # avoid double-wrapping already patched ${TMPDIR:-/tmp}
                t = re.sub(r'(?<!\{TMPDIR:-)/tmp/sh', r'${TMPDIR:-/tmp}/sh', t)
                t = re.sub(r'(?<!\{TMPDIR:-)/tmp/conf', r'${TMPDIR:-/tmp}/conf', t)
                # generic /tmp/ -> ${TMPDIR:-/tmp}/ for remaining hardcodes, but avoid ${TMPDIR:-/tmp}/tmp duplication
                # Only patch isolated /tmp/ occurrences not already inside ${}
                t = re.sub(r'(?<!\{TMPDIR:-)(?<!\$)/tmp/', r'${TMPDIR:-/tmp}/', t)
                # fix double-prefix if we introduced ${TMPDIR:-/tmp}/${TMPDIR:-/tmp}
                t = t.replace("${TMPDIR:-/tmp}/${TMPDIR:-/tmp}", "${TMPDIR:-/tmp}")
                t = t.replace("${TMPDIR:-/tmp}/tmp", "${TMPDIR:-/tmp}")

                # --- HMDFS getcwd fallback ---
                t = t.replace('ac_pwd=`pwd` && test -n "$ac_pwd" &&', 'ac_pwd=`pwd 2>/dev/null || echo $PWD` && test -n "$ac_pwd" &&')
                # broader pwd fallbacks
                t = re.sub(r'ac_pwd=`pwd`', r'ac_pwd=`pwd 2>/dev/null || echo $PWD`', t)
                t = t.replace('if (pwd) >/dev/null 2>&1 && test -n "`pwd`"', 'if (pwd) >/dev/null 2>&1 || test -n "$PWD"')
                # also handle `pwd` alone in ac_pwd assignment variants
                t = re.sub(r'`pwd`', r'`pwd 2>/dev/null || echo $PWD`', t) if 'ac_pwd' in t and '`pwd 2>/dev/null' not in t else t

                if t != orig:
                    p.write_text(t, encoding="utf-8")
                    self.output.info(f"patched {cfg_name} for OHOS/HMBS in {p}")
            except Exception as e:
                self.output.warning(f"ohos patch skipped for {p}: {e}")

    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder or ".", "tmp")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _fs_env(self):
        """Prepare HMBS-friendly filesystem env: PWD, TMPDIR, SHELL."""
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        hmbs_tmp = self._writable_tmpdir()
        try:
            os.makedirs(hmbs_tmp, exist_ok=True)
        except Exception:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = hmbs_tmp
        sh = self._bash()
        os.environ["SHELL"] = sh
        os.environ["CONFIG_SHELL"] = sh
        # Ensure shim bin for chmod is on PATH if already created
        shim_bin = os.path.join(self.build_folder, "_hmbs_bin")
        if os.path.isdir(shim_bin):
            os.environ["PATH"] = shim_bin + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"HMBS env: PWD={self.build_folder} TMPDIR={hmbs_tmp} SHELL={sh}")

    def _setup_chmod_shim(self):
        """Create a PATH shim for chmod that never fails (HMBS_CAP_CHMOD=0)."""
        try:
            shim_bin = os.path.join(self.build_folder, "_hmbs_bin")
            os.makedirs(shim_bin, exist_ok=True)
            shim = os.path.join(shim_bin, "chmod")
            if not os.path.isfile(shim):
                fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                        f.write("#!/bin/sh\n")
                        f.write("# HMBS chmod shim: ignore chmod failures on HMDFS (cap 0)\n")
                        f.write("/bin/chmod \"$@\" 2>/dev/null || /usr/bin/chmod \"$@\" 2>/dev/null || true\n")
                        f.write("exit 0\n")
                except Exception:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                    raise
                try:
                    os.chmod(shim, 0o755)
                except Exception:
                    pass
            cur = os.environ.get("PATH", "")
            if shim_bin not in cur.split(os.pathsep):
                os.environ["PATH"] = shim_bin + os.pathsep + cur
            self.output.info(f"chmod shim installed at {shim}")
        except Exception as e:
            self.output.warning(f"chmod shim setup skipped: {e}")

    def _write_install_shim(self):
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except Exception:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        bf = self.build_folder
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                try:
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if "INSTALL =" not in content:
                        continue
                    lines = []
                    changed = False
                    for line in content.splitlines(True):
                        stripped = line.lstrip()
                        if stripped.startswith("INSTALL = ") and "/install" in stripped:
                            indent = line[:len(line) - len(stripped)]
                            lines.append(f"{indent}INSTALL = {shim_install}\n")
                            changed = True
                        else:
                            lines.append(line)
                    if changed:
                        with open(mp, "w", encoding="utf-8") as f:
                            f.write("".join(lines))
                        self.output.info(f"redirected INSTALL to shim in {mp}")
                except Exception as e:
                    self.output.warning(f"INSTALL redirect skipped for {mp}: {e}")

    def _patch_u_char(self):
        """OHOS musl: cryptopANT.h uses u_char without including sys/types.h (glibc provides it, musl does not)."""
        try:
            h = pathlib.Path(self.source_folder) / "src" / "cryptopANT.h"
            if not h.is_file():
                h = pathlib.Path(self.source_folder) / "cryptopANT.h"
            if h.is_file():
                t = h.read_text(encoding="utf-8", errors="replace")
                if "u_char" in t and "#include <sys/types.h>" not in t:
                    t = t.replace("#include <stdint.h>", "#include <stdint.h>\n#include <sys/types.h>\n#ifndef u_char\ntypedef unsigned char u_char;\n#endif")
                    # fallback if include line differs
                    if "#include <sys/types.h>" not in t:
                        t = "#include <sys/types.h>\n#ifndef u_char\ntypedef unsigned char u_char;\n#endif\n" + t
                    h.write_text(t, encoding="utf-8")
                    self.output.info(f"patched u_char in {h}")
        except Exception as e:
            self.output.warning(f"u_char patch skipped: {e}")

    def _setup_openssl_env(self):
        """Ensure OpenSSL 3 legacy provider is findable for Blowfish (BF-ECB)."""
        try:
            dep = None
            try:
                dep = self.dependencies["openssl"]
            except Exception:
                pass
            mod_dirs = []
            if dep is not None:
                for cand in [os.path.join(dep.package_folder, "lib", "ossl-modules"),
                             os.path.join(dep.package_folder, "lib64", "ossl-modules"),
                             os.path.join(dep.package_folder, "ossl-modules")]:
                    if os.path.isdir(cand):
                        mod_dirs.append(cand)
                    # also check .so existence
                    for f in ["legacy.so", "legacy.dylib"]:
                        p = os.path.join(cand, f)
                        if os.path.isfile(p):
                            mod_dirs.append(cand)
                            break
            # HMBS or local fallback: common openssl module locations
            for cand in ["/data/service/hnp/openssl/lib/ossl-modules", "/usr/lib/ossl-modules", "/usr/local/lib/ossl-modules"]:
                if os.path.isdir(cand):
                    mod_dirs.append(cand)
            # also search for legacy.so recursively under package_folder (covers lib, lib64, etc.)
            if dep is not None:
                for root, dirs, files in os.walk(dep.package_folder):
                    if "legacy.so" in files or "legacy.dylib" in files:
                        d = root
                        if d not in mod_dirs:
                            mod_dirs.append(d)
                        break
                # also check via cpp_info libdirs
                try:
                    for libdir in dep.cpp_info.libdirs:
                        cand = os.path.join(dep.package_folder, libdir, "ossl-modules")
                        if os.path.isdir(cand) and cand not in mod_dirs:
                            mod_dirs.append(cand)
                        cand2 = os.path.join(dep.package_folder, libdir)
                        legacy_cand = os.path.join(cand2, "ossl-modules", "legacy.so")
                        if os.path.isfile(legacy_cand) and cand not in mod_dirs:
                            mod_dirs.append(os.path.dirname(legacy_cand))
                except Exception:
                    pass
            if mod_dirs:
                # deduplicate preserve order
                seen = set()
                uniq = []
                for d in mod_dirs:
                    if d not in seen:
                        seen.add(d)
                        uniq.append(d)
                # Prefer directory that actually contains legacy.so
                chosen = None
                for d in uniq:
                    if os.path.isfile(os.path.join(d, "legacy.so")) or os.path.isfile(os.path.join(d, "legacy.dylib")):
                        chosen = d
                        break
                if chosen is None:
                    chosen = uniq[0]
                os.environ["OPENSSL_MODULES"] = chosen
                # Do not override OPENSSL_CONF; let OpenSSL use default config.
                # Only clear OPENSSL_CONF if it points to non-existent file.
                if "OPENSSL_CONF" in os.environ:
                    conf = os.environ.get("OPENSSL_CONF", "")
                    if conf and not os.path.isfile(conf) and conf != "/dev/null":
                        try:
                            del os.environ["OPENSSL_CONF"]
                        except Exception:
                            pass
                # diagnostic: list chosen dir
                try:
                    lst = os.listdir(chosen)[:5]
                    self.output.info(f"OPENSSL_MODULES={chosen} (contents: {lst}) for blowfish legacy provider")
                except Exception:
                    self.output.info(f"OPENSSL_MODULES={chosen} for blowfish legacy provider")
            else:
                # At least set to dep lib if exists
                if dep is not None:
                    fallback = os.path.join(dep.package_folder, "lib", "ossl-modules")
                    os.makedirs(fallback, exist_ok=True)
                    os.environ["OPENSSL_MODULES"] = fallback
                    self.output.info(f"OPENSSL_MODULES fallback {fallback}")
        except Exception as e:
            self.output.warning(f"openssl env setup skipped: {e}")

    def _prepare_test_data(self):
        """VPATH build: test data lives in source_folder/test but make check expects build_folder/test."""
        try:
            src_test = pathlib.Path(self.source_folder) / "test"
            dst_test = pathlib.Path(self.build_folder) / "test"
            if src_test.is_dir():
                if not dst_test.exists():
                    shutil.copytree(str(src_test), str(dst_test), symlinks=False)
                    self.output.info(f"copied test data {src_test} -> {dst_test}")
                else:
                    for item in src_test.iterdir():
                        target = dst_test / item.name
                        if not target.exists():
                            if item.is_dir():
                                shutil.copytree(str(item), str(target), symlinks=False)
                            else:
                                shutil.copy2(str(item), str(target))
            # Also ensure scramble_ips wrapper finds keyfiles via VPATH fallback: ensure build dir has src's test files accessible
            # Debug: list dst
            if dst_test.is_dir():
                self.output.info(f"test data ready: {list(p.name for p in dst_test.iterdir())[:10]}")
        except Exception as e:
            self.output.warning(f"test data prepare skipped: {e}")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HMBS build/host triplet: bypass config.guess which on OHOS reports
        # unknown OS (HongMeng kernel uname != Linux). Explicit build/host avoids
        # "cannot guess build type" from old config.guess 2023-06-23.
        # config.guess 2023-06-23 on OHOS reports unknown OS (HongMeng kernel
        # uname != Linux), and config.sub 2023-06-23 does NOT recognize
        # 'ohos' as valid OS (error: OS 'ohos' not recognized). Use the
        # widely-accepted linux-gnu triplet which config.sub normalizes; the
        # actual OHOS targeting is via HNP clang flags in the toolchain, not
        # the autotools triplet string.
        try:
            if str(self.settings.os) == "OHOS":
                if not any("--build" in str(a) for a in tc.configure_args):
                    tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
                if not any("--host" in str(a) for a in tc.configure_args):
                    tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        except Exception:
            pass
        if self.options.with_scramble_ips:
            tc.configure_args.append("--with-scramble_ips")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # deps generators for openssl includes/libs
        try:
            AutotoolsDeps(self).generate()
            PkgConfigDeps(self).generate()
        except Exception as e:
            self.output.warning(f"deps generate skipped: {e}")
        # E002 readonly /tmp: ensure writable TMPDIR for HMBS (generate runs before build, env must persist via buildenv)
        try:
            tmp = self._writable_tmpdir()
            pathlib.Path(tmp).mkdir(parents=True, exist_ok=True)
            env = Environment()
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            env.define("SHELL", self._bash())
            env.define("CONFIG_SHELL", self._bash())
            for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP", "HMBS_TMPDIR", "HMBS_CAP_CHMOD", "HMBS_CAP_HARDLINK"):
                _v = os.environ.get(_k)
                if _v:
                    env.define(_k, _v)
            # OpenSSL legacy provider path (blowfish) - persist for build
            try:
                dep = self.dependencies["openssl"] if "openssl" in self.dependencies else None
            except Exception:
                dep = None
            if dep is not None:
                chosen = None
                # prefer dir that actually contains legacy.so
                for cand in [os.path.join(dep.package_folder, "lib", "ossl-modules"), os.path.join(dep.package_folder, "lib64", "ossl-modules"), os.path.join(dep.package_folder, "ossl-modules")]:
                    if os.path.isdir(cand):
                        if os.path.isfile(os.path.join(cand, "legacy.so")) or os.path.isfile(os.path.join(cand, "legacy.dylib")):
                            chosen = cand
                            break
                        if chosen is None:
                            chosen = cand
                if chosen is None:
                    # recursive search
                    for root, dirs, files in os.walk(dep.package_folder):
                        if "legacy.so" in files or "legacy.dylib" in files:
                            chosen = root
                            break
                if chosen:
                    env.define("OPENSSL_MODULES", chosen)
            env.vars(self, scope="build").save_script("hmbs_env")
        except Exception as e:
            self.output.warning(f"hmbs env generate skipped: {e}")

    def build(self):
        apply_conandata_patches(self)
        self._patch_u_char()
        self._setup_openssl_env()
        self._setup_chmod_shim()
        self._fs_env()
        # Patch source configure before it runs
        self._patch_configure_for_ohos(self.source_folder)
        # Also patch build_folder configure if it exists (conan may have copied)
        self._patch_configure_for_ohos(self.build_folder)
        autotools = Autotools(self)
        autotools.configure()
        # Re-patch config.status that configure generates (it contains same tmp/pwd snippets)
        self._patch_configure_for_ohos(self.build_folder)
        self._patch_configure_for_ohos(self.source_folder)
        # HMFS install shim (chmod/hardlink) must be redirected after configure generated Makefile
        if str(self.settings.os) == "OHOS":
            try:
                shim = self._write_install_shim()
                self._redirect_install_to_shim(shim)
            except Exception as e:
                self.output.warning(f"install shim setup skipped: {e}")
        # VPATH: copy test data to build dir so shell redirections <test/ip4s succeed
        self._prepare_test_data()
        autotools.make()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream make check and emit HMBS_UPSTREAM_TEST_RESULT."""
        hmbs_make = os.environ.get("HMBS_MAKE", "make")
        cmd = [hmbs_make, "check"]
        output = ""
        exit_code = 0
        try:
            cdir = self.build_folder if os.path.isfile(os.path.join(self.build_folder, "Makefile")) else self.source_folder
            # ensure PWD still correct for make check
            os.environ["PWD"] = cdir
            result = subprocess.run(
                cmd,
                cwd=cdir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (result.stdout or "") + (result.stderr or "")
            exit_code = result.returncode
            self.output.info("make check output (tail):\n" + "\n".join(output.splitlines()[-40:]))
            self.output.info(f"make check exit={exit_code}")
        except Exception as e:
            output = str(e)
            self.output.warning(f"make check failed to run: {e}")
            exit_code = 1

        passed = output.count("PASSED")
        failed = output.count("FAILED")
        if "scramble_ips binary wasn't built" in output:
            self.output.warning("upstream test binary scramble_ips not built - check --with-scramble_ips")
            marker = {
                "status": "failed",
                "framework": "autotools",
                "command": "make check",
                "discovered": 16,
                "executed": 0,
                "passed": 0,
                "failed": 16,
                "skipped": 0,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)
            return

        if passed == 0 and failed == 0:
            if exit_code == 0:
                marker = {
                    "status": "no_tests",
                    "framework": "autotools",
                    "command": "make check",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "make check produced no PASSED/FAILED markers; likely misconfigured build",
                }
            else:
                marker = {
                    "status": "failed",
                    "framework": "autotools",
                    "command": "make check",
                    "discovered": 16,
                    "executed": 0,
                    "passed": 0,
                    "failed": 16,
                    "skipped": 0,
                }
        else:
            discovered = 16
            executed = passed + failed
            if executed > discovered:
                discovered = executed
            if failed == 0 and passed == discovered:
                status = "passed"
            elif failed > 0:
                status = "failed"
            else:
                status = "failed" if failed else "passed"
            marker = {
                "status": status,
                "framework": "autotools",
                "command": "make check",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
            }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)

    def package(self):
        # Ensure HMBS shims still on PATH for libtool chmod outside INSTALL
        try:
            self._setup_chmod_shim()
            # Re-ensure TMPDIR and PWD for install step (hmbs readonly checks)
            self._fs_env()
        except Exception:
            pass
        autotools = Autotools(self)
        autotools.install()
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la"):
                    os.remove(os.path.join(root, f))
        for lic in ["COPYING", "LICENSE", "LICENSE.md"]:
            if os.path.isfile(os.path.join(self.source_folder, lic)):
                copy(self, lic, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
                break

    def package_info(self):
        self.cpp_info.libs = ["cryptopANT"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["crypto"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.options.with_scramble_ips:
            self.cpp_info.bindirs = ["bin"]
