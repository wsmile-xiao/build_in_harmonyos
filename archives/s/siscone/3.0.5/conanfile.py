#!/usr/bin/env python3
"""Conan recipe — siscone 3.0.5 (Autotools)."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SisconeConan(ConanFile):
    name = "siscone"
    version = "3.0.5"
    description = "Seedless Infrared-Safe Cone jet finder"
    license = "GPL-2.0-or-later"
    homepage = "https://siscone.hepforge.org/"
    url = "https://gitlab.com/fastjet/siscone"
    topics = ("hep", "jets", "cone-algorithm", "physics")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "siscone only supports Linux/OHOS, got %s" % self.settings.os
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        tc.generate()
        # True-machine guard: repo profile pins SHELL/CONFIG_SHELL to
        # /data/service/hnp/bin/bash, which is "inaccessible or not found"
        # on some HMBS hosts (this build: configure[157] dies Error 127
        # before any compile). HMBS injects SHELL=/bin/sh (capabilities
        # shell=/bin/sh). A build-scope env script wins over profile
        # [buildenv]; inline os.environ tweaks in build() alone do not
        # (bwm/0.6.3 + classads DRAFT-6487 precedent).
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        _cc, _cxx, _lbl = self._resolve_compiler()
        if _cc:
            env.define("CC", _cc)
        if _cxx:
            env.define("CXX", _cxx)
        env.vars(self, scope="build").save_script("siscone_hmos_fix")
        self.output.info(
            "siscone_hmos_fix: SHELL/CONFIG_SHELL=%s TMPDIR=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, _lbl, _cc, _cxx)
        )

    def _usable_shell(self):
        # Hard-prefer /bin/sh; never return the HNP bash path even if
        # isfile() is true for it (it may exist yet be non-executable).
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # Priority: HMBS task-local TMPDIR/TMP/TEMP, then HMBS_TMPDIR/
        # HMBS_INSTALL; never fall back to read-only /tmp (readonly_tmp).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _resolve_compiler(self):
        # Profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang, absent on some HMBS hosts.
        # Keep conf value when the file exists; otherwise fall back to
        # PATH/SDK-resolved clang (pure isfile probing, no X_OK per R49).
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = []
        for d in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if d and d not in cand_dirs:
                cand_dirs.append(d)
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
                    if sib not in cand_dirs:
                        cand_dirs.append(sib)
        except Exception:
            pass
        found_cc, found_cxx = "", ""
        for name in cc_names:
            w = shutil.which(name)
            if _ok(w):
                found_cc = w
                break
        for name in cxx_names:
            w = shutil.which(name)
            if _ok(w):
                found_cxx = w
                break
        if not found_cc or not found_cxx:
            for d in cand_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for n in cc_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cc = p
                            break
                if not found_cxx:
                    for n in cxx_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cxx = p
                            break
                if found_cc and found_cxx:
                    break
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            sib = cc + "++"
            if _ok(sib):
                cxx = sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _patch_ohos_autotools(self):
        """Replace config.guess/config.sub with OHOS-aware shims (E007).

        siscone 3.0.5 ships a 2018-era config.guess that cannot guess
        HarmonyOS (uname -s = HarmonyOS) -> "cannot guess build type".
        Inline regex patching proved fragile across guess versions
        (this build: still unrecognized after patch attempt), so
        overwrite every config.guess/config.sub under the source tree
        with minimal self-contained shims (dap/3.9 + dcfldd/1.9.3
        precedent): guess maps HarmonyOS|OHOS to
        <machine>-unknown-linux-ohos, sub passes the triplet through.
        Explicit --build/--host (see build()) skips guess entirely;
        the sub shim guarantees canonicalization accepts linux-ohos.
        """
        guess_body = (
            '#!/bin/sh\n'
            '# OHOS-aware config.guess (self-contained)\n'
            'machine=$(uname -m 2>/dev/null || echo unknown)\n'
            'system=$(uname -s 2>/dev/null || echo unknown)\n'
            'case "$system" in\n'
            '    HarmonyOS|OHOS)\n'
            '        echo "${machine}-unknown-linux-ohos"\n'
            '        ;;\n'
            '    *)\n'
            '        echo "${machine}-unknown-linux-gnu"\n'
            '        ;;\n'
            'esac\n'
            'exit 0\n'
        )
        sub_body = (
            '#!/bin/sh\n'
            '# OHOS-aware config.sub (self-contained)\n'
            '# Always pass through the input triplet\n'
            'if [ $# -eq 0 ] || [ -z "$1" ]; then\n'
            '    echo "aarch64-unknown-linux-ohos"\n'
            '    exit 0\n'
            'fi\n'
            'echo "$1"\n'
            'exit 0\n'
        )
        for root, _dirs, files in os.walk(self.source_folder):
            for name, body in (("config.guess", guess_body),
                               ("config.sub", sub_body)):
                if name not in files:
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(body)
                except OSError:
                    continue
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
                self.output.info("replaced %s with OHOS-aware shim" % path)

    def _write_install_shim(self):
        # HMBS runtime install shim (install_shim:true) does not
        # materialize libtool static-archive installs on HMDFS
        # (HMBS_CAP_CHMOD=0/HARDLINK=0): this build fails at
        #   install -c .libs/libsiscone.a <pkg>/lib/libsiscone.a
        #   chmod 644 <pkg>/lib/libsiscone.a -> No such file or directory
        # i.e. the shim skipped the copy (missing mkdir -p semantics),
        # so libtool's follow-up chmod sees nothing. Write a cp/mkdir
        # shim (single + multi source, mkdir -p, chmod || true) and
        # redirect generated Makefiles' INSTALL to it (cxxtools/3.0.0 +
        # jpcre2/10.32.01 precedent). No tests skipped.
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
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else chmod \"$mode\" \"$dest\" 2>/dev/null || true; fi\n"
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
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: HMFS ignores chmod
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable; automake routes libtool
        # --mode=install through $(INSTALL) too, so replacing INSTALL
        # covers the .a installs in one pass. siscone builds in-source,
        # so walk source_folder AND build_folder (cxxtools walks only
        # build_folder for its out-of-source layout).
        seen = set()
        for base in (self.source_folder, self.build_folder):
            if not base or base in seen:
                continue
            seen.add(base)
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                if "Makefile" not in files:
                    continue
                mp = os.path.join(root, "Makefile")
                try:
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8", newline="\n") as f:
                        f.write("".join(lines))
        self.output.info("[ok] OHOS port: redirected INSTALL to shim %s" % shim_install)

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)
        self._patch_ohos_autotools()
        for root, _dirs, files in os.walk(self.source_folder):
            if "configure" not in files:
                continue
            cfg = os.path.join(root, "configure")
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 000"))
        # Do NOT use Autotools.configure()/make(): that helper runs via
        # env="conanbuild", which re-exports the profile's stale
        # CONFIG_SHELL=/data/service/hnp/bin/bash AFTER our override
        # (bwm/0.6.3 second-attempt lesson). Run explicitly via the usable
        # shell with inline exports AFTER conanbuild.sh is sourced.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        cc, cxx, lbl = self._resolve_compiler()
        self.output.info(
            "siscone build shell=%s tmpdir=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, lbl, cc, cxx)
        )
        prefix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
            % (shell, shell, tmpdir, tmpdir, tmpdir)
        )
        if cc:
            prefix += 'export CC="%s" && ' % cc
            os.environ["CC"] = cc
        if cxx:
            prefix += 'export CXX="%s" && ' % cxx
            os.environ["CXX"] = cxx
        if self.options.shared:
            static_flags = "--disable-static --enable-shared"
        else:
            static_flags = "--enable-static --disable-shared"
        conf_args = (
            "--prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' "
            "'--libdir=${prefix}/lib' '--includedir=${prefix}/include' "
            "'--oldincludedir=${prefix}/include' " + static_flags
        )
        # E007 companion: explicit triplets skip config.guess entirely
        # (e2fsprogs/1.47.4 precedent). Native build==host on OHOS.
        if self.settings.os == "OHOS":
            _arch = str(self.settings.arch)
            if _arch in ("x86_64", "x64"):
                _machine = "x86_64"
            else:
                _machine = "aarch64"
            _triplet = "%s-unknown-linux-ohos" % _machine
            conf_args += " --build=%s --host=%s" % (_triplet, _triplet)
            self.output.info("siscone OHOS triplets: %s" % _triplet)
        cfg_dir = self.source_folder
        try:
            os.chmod(os.path.join(cfg_dir, "configure"), 0o755)
        except OSError:
            pass
        self.run(prefix + '"%s" ./configure %s' % (shell, conf_args),
                 cwd=cfg_dir, env="conanbuild")
        # HMDFS install compat: configure bakes a system `install`
        # that silently drops libtool .a installs on the device
        # (HMBS_CAP_CHMOD=0/HARDLINK=0). Redirect before make so the
        # build tree and the later `make install` use cp/mkdir semantics.
        try:
            self._redirect_install_to_shim(self._write_install_shim())
        except Exception as exc:
            self.output.warning("install shim redirect failed, using system install: %r" % exc)
        self.run(prefix + 'make -j1', cwd=cfg_dir, env="conanbuild")
        # Upstream test (N=1): examples/test.cpp is the single upstream
        # test program (built as examples/test by the autotools build;
        # `make check` alone is a no-op — no TESTS registered — so run
        # the built binary explicitly for a real evidence trail).
        # Review rule4: real N=1 must be declared and executed, never
        # reported as no_tests.
        self.run(prefix + 'make check', cwd=cfg_dir, env="conanbuild")
        _upstream_candidates = [
            os.path.join(cfg_dir, 'examples', 'test'),
            os.path.join(cfg_dir, 'examples', '.libs', 'test'),
            os.path.join(self.build_folder, 'examples', 'test'),
        ]
        _upstream_bin = ''
        for _cand in _upstream_candidates:
            try:
                if os.path.isfile(_cand):
                    _upstream_bin = _cand
                    break
            except Exception:
                continue
        if _upstream_bin:
            try:
                os.chmod(_upstream_bin, 0o755)
            except OSError:
                pass
            # OHOS ELF needs signing to execute (same as test_package);
            # best-effort: sign if the device signer exists, else try raw.
            try:
                _signer = '/data/service/hnp/bin/binary-sign-tool'
                _objcopy = '/data/service/hnp/bin/llvm-objcopy'
                if os.path.isfile(_signer) and os.path.isfile(_upstream_bin):
                    self.run(_objcopy + ' --remove-section .codesign ' + chr(34) + _upstream_bin + chr(34) + ' 2>/dev/null',
                             ignore_errors=True)
                    _tmp = _upstream_bin + '.signed'
                    self.run(_signer + ' sign -inFile ' + chr(34) + _upstream_bin + chr(34) + ' -outFile ' + chr(34) + _tmp + chr(34) + ' -selfSign 1')
                    if os.path.exists(_tmp):
                        shutil.move(_tmp, _upstream_bin)
                    try:
                        os.chmod(_upstream_bin, 0o755)
                    except OSError:
                        pass
            except Exception as exc:
                self.output.warning('sign upstream test binary failed: %r' % exc)
            self.output.info('running upstream test binary: %s' % _upstream_bin)
            self.run(prefix + chr(34) + _upstream_bin + chr(34), cwd=os.path.dirname(_upstream_bin),
                     env='conanbuild')
        else:
            self.output.warning(
                'upstream test binary examples/test not found after make; '
                'test_package recompiles examples/test.cpp against the '
                'installed libs for the HMBS_UPSTREAM_TEST_RESULT evidence')

    def package(self):
        os.umask(0)
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
            % (shell, shell, tmpdir, tmpdir, tmpdir)
        )
        cfg_dir = self.source_folder if os.path.isfile(
            os.path.join(self.source_folder, "Makefile")) else self.build_folder
        # Install-shim gate (see _write_install_shim): redirect before
        # make install so libtool .a installs go through the mkdir -p +
        # chmod-tolerant shim (package() may run without build() on
        # cache-hit rebuilds, so redirect here as well).
        try:
            self._redirect_install_to_shim(self._write_install_shim())
        except Exception as exc:
            self.output.warning("install shim redirect failed, using system install: %r" % exc)
        self.run(fix + 'make install DESTDIR="%s"' % self.package_folder,
                 cwd=cfg_dir, env="conanbuild")
        # Drop libtool archives: copy() with identical src/dst raises
        # ("must have different values"), and isfile() never matches a
        # wildcard, so expand with glob and unlink directly.
        for pattern in ("*.la",):
            for stale in glob.glob(os.path.join(self.package_folder, "lib", pattern)):
                try:
                    os.unlink(stale)
                except OSError:
                    pass
        copy(self, 'COPYING*', src=self.source_folder,
             dst=os.path.join(self.package_folder, 'licenses'))
        copy(self, 'LICENSE*', src=self.source_folder,
             dst=os.path.join(self.package_folder, 'licenses'))
        # Ship the single upstream test source for test_package re-run
        # (rule4 N=1 evidence: examples/test.cpp compiled against the
        # installed libs and executed in test_package).
        try:
            copy(self, 'test.cpp', src=os.path.join(self.source_folder, 'examples'),
                 dst=os.path.join(self.package_folder, 'share', 'siscone_upstream_test'))
        except Exception as exc:
            self.output.warning('ship upstream test.cpp failed: %r' % exc)

    def package_info(self):
        self.cpp_info.libs = ["siscone", "siscone_spherical"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
