#!/usr/bin/env python3
"""Conan recipe for rancid 3.14 — Really Awesome New Cisco confIg Differ.

rancid (https://shrubbery.net/rancid/) maintains CVS/Subversion/git controlled
copies of device configs.  It is a self-contained Autotools package installed
into its own prefix:

  bin/            — C helpers (par, hpuifilter) + a large set of Perl scripts
                    (rancid, alogin, cat5rancid, ... and the device *rancid /
                    *login scripts) and the lg (looking-glass) CGI helpers
  lib/rancid/     — Perl modules (rancid.pm, rancidcontrib.pm and one .pm per
                    supported device OS: ios/nxos/junos/f5rancid/...)
  etc/            — rancid.conf / rancid.types.base / lg.conf sample configs
  share/rancid/   — data files, .exp (expect/tcl login helpers) and docs
  share/man/      — man pages
  var/            — local state dir (created empty at install time)

Build (validated on Linux, then for OHOS):
  ./configure --prefix=/   (AutotoolsToolchain injects CC/CONFIG_SHELL)
  make -j1
  make install DESTDIR=<package_folder>

OHOS adaptation (single patch to the shipped generated `configure`):
  rancid ships a fully generated `configure` whose AC_PATH_PROG probes hard-
  fail (as_fn_error) when three *runtime* helper tools are absent:
    - expect   (Tcl script interpreter; used only by the `clogin`/`*login`
                expect-based login helpers at runtime — not needed to build)
    - mktemp   (used only to build the $PATH baked into etc/rancid.conf)
    - ping     (used only by the `lg`/looking-glass CGI helper)
  None of these three is required to *compile* anything; they are runtime
  dependencies of auxiliary login/looking-glass tools.  The patch turns those
  three hard configure errors into warnings and degrades the affected aux
  tools to empty values, mirroring how upstream already treats `sendmail`
  (WARNING, non-fatal).  When a tool IS present, configure behaves exactly as
  upstream (the patch only alters the "not found" branch).

  perl (>=5, Socket.pm >= 2.006) is a genuine hard dependency of every rancid
  script and is required for the whole tool to be useful; it is left as a hard
  requirement.

No upstream automated test suite exists (see test_package/MANIFEST.yml audit).
"""
from conan import ConanFile
import os
import shutil
import subprocess
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class RancidConan(ConanFile):
    name = "rancid"
    version = "3.14"
    description = (
        "rancid 3.14 — Really Awesome New Cisco confIg Differ: maintains "
        "version-controlled copies of device configs, with per-OS login and "
        "config-collection scripts (rancid/alcatel/arista/cisco/juniper/...) "
        "and the looking-glass (lg) CGI helpers"
    )
    license = "BSD-3-Clause"
    homepage = "https://www.shrubbery.net/rancid/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rancid is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Injects CC/CFLAGS and CONFIG_SHELL from the OHOS toolchain into the
        # conanbuild env used to run configure/make (R33 convention).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMFS: getcwd(3) 在部分 HMFS 挂载点不可用，configure 顶部的 `pwd`
        # 判定会报 "working directory cannot be determined"。预置 PWD 让
        # 生成的 configure 在 `pwd` 失败时回退到 $PWD（0002 补丁，同
        # adms 2.3.7 / nspr 4.37 / aribb24 1.0.4 已过门禁的同款适配）。
        os.environ["PWD"] = self.source_folder
        # In-source build (rancid ships its own Makefile.in/configure and the
        # generated scripts use $(srcdir)); same pattern as magicrescue.
        self.run("./configure --prefix=/", cwd=self.source_folder,
                 env="conanbuild")
        # R9: -j1
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # 真机 HMFS：configure 找到的 INSTALL 程序（HMBS 运行时 install shim）
        # 只支持 GNU 参数面的子集——单文件 `-c -m 755 src dst` 探针可过，但
        # automake 的 install-pkgdataDATA 等 `-m 644 <多文件> <目录>`（及 -d）
        # 调用直接以 Error 64 (EX_USAGE) 失败（`make[2]: *** [Makefile:418:
        # install-pkgdataDATA] Error 64`）。libapreq2 2.17 同指纹（Error 64，
        # 设备 install 不实现完整 GNU 参数面）：先探测可用的 install，并把
        # 确定性的 POSIX cp/mkdir/chmod 包装器经命令行 INSTALL=<wrapper> -c
        # + MKDIR_P=mkdir -p 传给 make install，替代 configure 烘焙的 INSTALL。
        sh = self._device_shell()
        make = ((os.environ.get("HMBS_MAKE", "") or "").strip()
                or shutil.which("make") or "make")
        pkg_env = self._clean_shell_env(dict(os.environ), sh)
        try:
            _pkg_tmp = self._hmbs_tmpdir()
        except Exception:
            _pkg_tmp = self.build_folder
        usable_install = self._probe_usable_install(sh, _pkg_tmp, pkg_env)
        try:
            wrapper_install = self._write_install_wrapper(_pkg_tmp, sh, pkg_env)
        except Exception as exc:
            self.output.warning("install wrapper skipped: %r" % exc)
            wrapper_install = ""
        chosen_install = wrapper_install or usable_install
        install_args = [make, "install", "SHELL=%s" % sh,
                        "DESTDIR=%s" % self.package_folder]
        if chosen_install:
            install_args.append("INSTALL=%s -c" % chosen_install)
            install_args.append("MKDIR_P=mkdir -p")
        subprocess.run(install_args, cwd=self.source_folder,
                       env=pkg_env, check=True)

    def _device_shell(self):
        # HMBS 统一注入 SHELL=/bin/sh（HNP bash 无法访问 HMFS 工作目录）。
        return (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                or "/bin/sh")

    def _hmbs_tmpdir(self):
        # HMBS 为任务注入独立 TMPDIR/TMP/TEMP（已被 write-probe 证明可写）。
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = (os.environ.get(key, "") or "").strip()
            if val:
                return val
        return self.build_folder

    def _clean_shell_env(self, env, sh):
        # 剔除会命中不可达 HNP bash 的 SHELL/CONFIG_SHELL，钉为设备 shell。
        for key in ("SHELL", "CONFIG_SHELL"):
            env[key] = sh
        return env

    def _probe_usable_install(self, sh, tmpdir, env):
        # 单文件 `-c -m 755 src dst` 探针：真机 HMFS install shim 可能返回 0
        # 却不产出目标文件，故须校验目标存在且非空。
        import tempfile as _tf
        probe_src = None
        try:
            fd, probe_src = _tf.mkstemp(dir=tmpdir, prefix="hmbs-install-probe-")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("hmbs-install-probe")
        except OSError as exc:
            self.output.warning("install probe source creation failed: %r" % exc)
            return ""
        ordered = []
        cand = (os.environ.get("HMBS_INSTALL", "") or "").strip()
        if cand and cand not in ordered:
            ordered.append(cand)
        for cand in ("/system/bin/install", "/bin/install",
                     "/usr/bin/install", "install"):
            if cand not in ordered:
                ordered.append(cand)
        try:
            which_install = shutil.which("install")
        except Exception:
            which_install = None
        if which_install and which_install not in ordered:
            ordered.append(which_install)
        for cand in ordered:
            try:
                if not cand or not os.path.isfile(cand):
                    continue
            except Exception:
                continue
            dest = probe_src + ".dest-%s" % os.path.basename(cand or "install")
            try:
                if os.path.isfile(dest):
                    os.unlink(dest)
            except OSError:
                pass
            try:
                proc = subprocess.run(
                    [cand, "-c", "-m", "755", probe_src, dest],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60)
                ok = (proc.returncode == 0 and os.path.isfile(dest)
                      and os.path.getsize(dest) > 0)
                self.output.info("install probe %r -> exit %d exists=%s" % (
                    cand, proc.returncode, os.path.isfile(dest)))
                try:
                    if os.path.isfile(dest):
                        os.unlink(dest)
                except OSError:
                    pass
                if ok:
                    try:
                        os.unlink(probe_src)
                    except OSError:
                        pass
                    self.output.info("usable INSTALL: %s" % cand)
                    return cand
            except Exception as exc:
                self.output.warning("install probe %r failed: %r" % (cand, exc))
                continue
        try:
            os.unlink(probe_src)
        except OSError:
            pass
        self.output.warning("no usable install program found (tried %s)" % ordered)
        return ""

    def _write_install_wrapper(self, tmpdir, sh, env):
        # 真机 install shim 不实现完整 GNU 参数面：install-pkgdataDATA 等
        # 多文件 `-m 644 f1 f2 ... dir/`（及 -d / -t / -D）调用报 Error 64。
        # 提供只依赖 cp/mkdir/chmod 的确定性 POSIX 包装器，覆盖 automake
        # 常见形式：-c（忽略）、-m MODE、-d（mkdir）、-t DIR、-D（建前导
        # 目录）、单/多文件拷贝。
        wrap_dir = os.path.join(tmpdir, "hmbs-install-wrap")
        try:
            os.makedirs(wrap_dir, exist_ok=True)
        except OSError:
            pass
        wrap = os.path.join(wrap_dir, "install")
        script = (
            "#!{sh}\n"
            "mode=\"\"\n"
            "dash_d=0\n"
            "dash_D=0\n"
            "dest_dir=\"\"\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -c) shift ;;\n"
            "    -m) mode=\"$2\"; shift 2 ;;\n"
            "    -m*) mode=\"${{1#-m}}\"; shift ;;\n"
            "    -d) dash_d=1; shift; break ;;\n"
            "    -D) dash_D=1; shift ;;\n"
            "    -t) dest_dir=\"$2\"; shift 2 ;;\n"
            "    -t*) dest_dir=\"${{1#-t}}\"; shift ;;\n"
            "    --) shift; break ;;\n"
            "    -*) echo \"hmbs-install-wrapper: unsupported option $1\" >&2; exit 64 ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "if [ \"$dash_d\" = \"1\" ]; then\n"
            "  if [ $# -eq 0 ]; then echo \"install -d: missing dir\" >&2; exit 64; fi\n"
            "  for d in \"$@\"; do mkdir -p \"$d\" || exit $?; done\n"
            "  exit 0\n"
            "fi\n"
            "if [ -n \"$dest_dir\" ]; then\n"
            "  mkdir -p \"$dest_dir\" || exit $?\n"
            "  if [ $# -eq 0 ]; then echo \"install -t: missing src\" >&2; exit 64; fi\n"
            "  for s in \"$@\"; do cp -p \"$s\" \"$dest_dir/\" || exit $?; done\n"
            "  if [ -n \"$mode\" ]; then chmod \"$mode\" \"$dest_dir/\"* 2>/dev/null || true; fi\n"
            "  exit 0\n"
            "fi\n"
            "if [ $# -lt 2 ]; then echo \"install: missing operand\" >&2; exit 64; fi\n"
            "dest=\"\"\n"
            "for last in \"$@\"; do dest=\"$last\"; done\n"
            "count=$#\n"
            "if [ -d \"$dest\" ]; then\n"
            "  for s in \"$@\"; do\n"
            "    if [ \"$s\" = \"$dest\" ] && [ \"$count\" -gt 1 ]; then continue; fi\n"
            "    if [ \"$s\" = \"$dest\" ]; then break; fi\n"
            "    cp -p \"$s\" \"$dest/\" || exit $?\n"
            "  done\n"
            "  if [ -n \"$mode\" ]; then\n"
            "    for s in \"$@\"; do\n"
            "      if [ \"$s\" = \"$dest\" ]; then continue; fi\n"
            "      chmod \"$mode\" \"$dest/$(basename \"$s\")\" 2>/dev/null || true\n"
            "    done\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$count\" -gt 2 ]; then echo \"install: multi-src without dir\" >&2; exit 64; fi\n"
            "src=\"$1\"\n"
            "if [ \"$dash_D\" = \"1\" ]; then\n"
            "  mkdir -p \"$(dirname \"$dest\")\" || exit $?\n"
            "else\n"
            "  case \"$dest\" in */*) mkdir -p \"$(dirname \"$dest\")\" || exit $? ;; esac\n"
            "fi\n"
            "cp -p \"$src\" \"$dest\" || exit $?\n"
            "if [ -n \"$mode\" ]; then chmod \"$mode\" \"$dest\" || exit $?; fi\n"
            "exit 0\n"
        ).format(sh=sh)
        try:
            with open(wrap, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(wrap, 0o755)
            except OSError:
                pass
        except OSError as exc:
            self.output.warning("install wrapper write failed: %r" % exc)
            return ""
        # 用 rancid 实际用到的 automake 形式探针，通过才信任。
        import tempfile as _tf2
        probe_ok = False
        try:
            fd, _psrc = _tf2.mkstemp(dir=tmpdir, prefix="hmbs-iwrap-a-")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("a")
            fd2, _psrc2 = _tf2.mkstemp(dir=tmpdir, prefix="hmbs-iwrap-b-")
            with os.fdopen(fd2, "w", encoding="utf-8") as handle:
                handle.write("b")
            _ddir = os.path.join(tmpdir, "hmbs-iwrap-d")
            try:
                shutil.rmtree(_ddir, ignore_errors=True)
            except OSError:
                pass
            os.makedirs(_ddir, exist_ok=True)
            cases = [
                ([wrap, "-c", "-m", "755", _psrc, _psrc + ".single"], True),
                ([wrap, "-c", "-m", "644", _psrc, _psrc + ".single644"], True),
                ([wrap, "-c", "-m", "644", _psrc, _psrc2, _ddir], False),
                ([wrap, "-d", os.path.join(_ddir, "sub")], False),
            ]
            all_ok = True
            for args, single in cases:
                proc = subprocess.run(
                    args, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, timeout=60)
                ok = (proc.returncode == 0)
                if ok and "-d" not in args:
                    last = args[-1]
                    if os.path.isdir(last):
                        ok = all(
                            os.path.isfile(os.path.join(
                                last, os.path.basename(a)))
                            for a in args[1:]
                            if not a.startswith("-")
                            and a not in ("644", "755")
                            and os.path.isfile(a))
                    else:
                        ok = os.path.isfile(last)
                if not ok:
                    all_ok = False
                    break
            probe_ok = all_ok
        except Exception as exc:
            self.output.warning("install wrapper probe failed: %r" % exc)
            probe_ok = False
        if not probe_ok:
            self.output.warning("install wrapper probe failed; not using wrapper")
            return ""
        self.output.info("install wrapper ready: %s" % wrap)
        return wrap

    def package_info(self):
        # Command-line / script toolset, not a linkable library.
        self.cpp_info.bindirs = ["bin"]
