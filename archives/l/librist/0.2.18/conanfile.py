#!/usr/bin/env python3
"""Conan recipe for librist 0.2.18 — RIST (Reliable Internet Stream
Transport) library, C, Meson build, BSD-2-Clause.

librist 是 RIST 协议的 C 实现（VideoLAN RIST 项目），用于低延迟
音视频流传输，被 FFmpeg/OBS 通过 librist 协议收发 RIST 流时使用。

OHOS 适配（路径 A，基础适配）:
- Meson 标准构建；cJSON 与 mbedtls 均使用上游自带的 contrib
  内嵌源码（-Dbuiltin_cjson=true -Dbuiltin_mbedtls=true），不引入
  外部 Conan 依赖（制品仓仅有 mbedtls/4.1.0，与 librist 0.2.18
  所需的 mbedtls 3.x API 不兼容；cJSON 为避免 pkg-config 名
  libcjson/cjson 映射分歧同样内嵌， deterministic）。
- 工具（built_tools）与 TUN 支持关闭：tools 需 libmicrohttpd，
  非库核心功能；在 OHOS 上保持最小依赖面。
- 上游测试：-Dtest=true，build() 末运行 `meson test` 全量套件
  （simple/main profile 收发测试 + srp 单元测试），并打印
  HMBS_UPSTREAM_TEST_RESULT 机器标记。
- cmocka 仅用于 srp_unit 测试，通过 test_requires 引入，不进入
  消费者依赖。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibristConan(ConanFile):
    name = "librist"
    version = "0.2.18"
    description = "Reliable Internet Stream Transport (RIST) library"
    license = "BSD-2-Clause"
    homepage = "https://code.videolan.org/rist/librist"
    url = "https://code.videolan.org/rist/librist"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

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
                f"librist is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        # Meson 在真机/CI 均不在全局 PATH（真机仅预装 cmake/make/ninja/
        # python3），必须走 ohpcd 已发布的 Conan 工具包，与 libavtp、
        # libdicom 等 Meson 配方一致用 meson/1.11.0。
        self.tool_requires("meson/1.11.0")
        # cmocka 只用于上游 test/rist/unit/srp_unit 单元测试，
        # 不得成为安装包的消费者依赖。
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        # Meson 要求源码目录与构建目录分离。
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # 上游自带 contrib 内嵌源码，不依赖外部包：
        # cJSON（避 pkg-config 名分歧）与 mbedtls（制品仓无兼容 3.x）。
        self._apply_project_option(tc, "builtin_cjson", "true")
        self._apply_project_option(tc, "builtin_mbedtls", "true")
        self._apply_project_option(tc, "use_mbedtls", "true")
        self._apply_project_option(tc, "use_gnutls", "false")
        # tools（rist-send/receive CLI）需 libmicrohttpd，非库核心，关闭。
        self._apply_project_option(tc, "built_tools", "false")
        # use_tun 仅上游较新版本存在（0.2.18 无此选项，传 -D 即报
        # Unknown option 中断 configure），缺失时跳过。
        self._apply_project_option(tc, "use_tun", "false")
        self._apply_project_option(tc, "fallback_builtin", "true")
        self._apply_project_option(tc, "static_analyze", "false")
        # 上游测试开关：必须开启，build() 内完整执行。
        self._apply_project_option(tc, "test", "true")
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        self._ensure_hmbs_tmpdir()
        self._repair_meson_compilers()
        self._inject_meson_archiver()

    def _apply_project_option(self, tc, name, value):
        """仅上游真实定义的选项才写入 MesonToolchain.project_options。

        0.2.18 的 meson_options.txt 无 use_tun（较新上游才引入），
        无条件传 -Duse_tun 会在 meson setup 直接报 Unknown option。
        此处解析源码树 meson_options.txt/meson.options 的 option()
        声明做交集过滤，缺失即跳过并打日志，不中断构建。
        """
        import re as _re
        _declared = set()
        for _fname in ("meson_options.txt", "meson.options"):
            _path = os.path.join(self.source_folder, _fname)
            if not os.path.isfile(_path):
                continue
            try:
                with open(_path, "r", encoding="utf-8",
                          errors="replace") as _f:
                    _declared.update(
                        _re.findall(r"""option\s*\(\s*['\"]([^'\"]+)['\"]""",
                                    _f.read()))
            except OSError:
                continue
        if _declared and name not in _declared:
            self.output.info(
                f"skip Meson option {name}: not declared by upstream "
                f"{self.version}")
            return
        tc.project_options[name] = value

    def build(self):
        apply_conandata_patches(self)
        self._ensure_hmbs_tmpdir()
        self._export_resolved_compilers()
        self._make_cmocka_visible_to_meson()
        self._fix_test_tools_dependencies()
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游官方测试（必做）：meson test 全量套件 ──
        passed = self._run_upstream_tests()
        if not passed:
            raise ConanInvalidConfiguration(
                "librist upstream meson test suite failed; see log and "
                "HMBS_UPSTREAM_TEST_RESULT marker above"
            )

    def _run_upstream_tests(self):
        """Run `meson test`, parse its summary, print the HMBS marker.

        Numbers come from meson's own stdout, never hardcoded. Expected
        Fail entries (should_fail:true) count as passed only when meson
        itself reports them so. Returns True when the suite passed.
        """
        import json as _json
        import re as _re
        import shutil as _shutil
        import subprocess

        env = os.environ.copy()
        # tool_requires（meson）的可执行文件只在 Conan build env 中，
        # 原生 subprocess 看不到：把 build 依赖的 bin/Scripts 目录前置
        # 到 PATH，保证此处与 Meson(self).configure() 看到同一 meson。
        # （libavtp 用 self.run 隐式携带该环境；此处需捕获输出做计数，
        # 故用 subprocess 并手动拼接 PATH。）
        self._ensure_hmbs_tmpdir()
        _tool_bins = []
        try:
            _cc = self._resolve_effective_compiler("c")
            if _cc:
                _cbindir = os.path.dirname(_cc)
                if os.path.isdir(_cbindir) and _cbindir not in _tool_bins:
                    _tool_bins.append(_cbindir)
        except Exception:
            pass
        try:
            for _dep in self.dependencies.build.values():
                _pkg = getattr(_dep, "package_folder", None)
                if not _pkg:
                    continue
                for _sub in ("bin", "Scripts"):
                    _p = os.path.join(_pkg, _sub)
                    if os.path.isdir(_p) and _p not in _tool_bins:
                        _tool_bins.append(_p)
        except Exception:
            _tool_bins = []
        if _tool_bins:
            env["PATH"] = os.pathsep.join(_tool_bins) + os.pathsep + env.get(
                "PATH", "")
        _meson_exe = _shutil.which("meson", path=env.get("PATH")) or "meson"
        cmd = [
            _meson_exe, "test", "-C", self.build_folder,
            "--print-errorlogs",
        ]
        # PkgConfigDeps 生成的 .pc（含 cmocka.pc）位于 generators 目录，
        # 显式加入 PKG_CONFIG_PATH，保证上游 test 发现逻辑可用。
        # TMPDIR/TMP/TEMP 沿用 hmbs 注入值（env 全量继承），不写只读 /tmp。
        _pc_path = os.path.join(self.generators_folder)
        env["PKG_CONFIG_PATH"] = _pc_path + os.pathsep + env.get(
            "PKG_CONFIG_PATH", "")
        raw = ""
        try:
            proc = subprocess.run(
                cmd, cwd=self.build_folder, env=env,
                capture_output=True, text=True, timeout=3000,
            )
            raw = (proc.stdout or "") + (proc.stderr or "")
            self.output.info(f"meson test exit code: {proc.returncode}")
            # 回显原始摘要行 + --print-errorlogs 的失败详情（失败测试名、
            # command/stdout/stderr 段），便于从 CI 日志直接定位失败者。
            # 套件全绿时不存在失败块，零额外输出。
            _detail = []
            _in_block = False
            _cap = 200
            for _line in raw.splitlines():
                _stripped = _line.strip()
                if _re.match(
                        r"\s*(Ok|Expected Fail|Fail|Unexpected Pass|"
                        r"Skipped|Timeout)\s*:", _line):
                    self.output.info(f"meson test summary: {_stripped}")
                    continue
                if _re.match(r"\s*--- (command|stdout|stderr) ---", _line):
                    _in_block = True
                elif _in_block and not _stripped:
                    _in_block = False
                if _in_block:
                    if len(_detail) < _cap:
                        _detail.append(_line)
                elif _re.search(r"\bFAILED\b|Unexpected Pass|Timeout", _line):
                    if len(_detail) < _cap:
                        _detail.append(_line)
            for _line in _detail:
                self.output.info(f"meson test detail: {_line.strip()}")
        except Exception as _e:
            self.output.warning(f"meson test subprocess failed: {_e}")
            raw = ""

        counts = {}
        for _m in _re.finditer(
                r"^\s*(Ok|Expected Fail|Fail|Unexpected Pass|Skipped|Timeout)"
                r"\s*:\s*(\d+)\s*$", raw, _re.MULTILINE):
            counts[_m.group(1)] = int(_m.group(2))
        ok = counts.get("Ok", 0)
        exp_fail = counts.get("Expected Fail", 0)
        fail = counts.get("Fail", 0)
        unexp = counts.get("Unexpected Pass", 0)
        skipped = counts.get("Skipped", 0)
        timeout = counts.get("Timeout", 0)
        total = ok + exp_fail + fail + unexp + skipped + timeout
        passed = ok + exp_fail
        failed = fail + unexp + timeout
        if total > 0 and failed == 0 and skipped == 0:
            _status = "passed"
            _reason = ("meson test full suite passed on HarmonyOS aarch64: "
                       f"{passed}/{total} (incl. Expected Fail {exp_fail})")
        elif total == 0:
            _status = "failed"
            _reason = ("meson test emitted no summary counts; raw output kept "
                       "above for diagnosis")
        else:
            _status = "failed"
            _reason = (f"meson test suite not fully green: ok={ok} "
                       f"expected_fail={exp_fail} fail={fail} "
                       f"unexpected_pass={unexp} skipped={skipped} "
                       f"timeout={timeout}")
        marker = {
            "status": _status,
            "framework": "meson-test",
            "command": "meson test -C <build_folder> --print-errorlogs",
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": _reason,
        }
        _msg = f'HMBS_UPSTREAM_TEST_RESULT={_json.dumps(marker)}'
        # 双通道发射（经验1）：结构化输出与直写输出同时发射，
        # 解析异常仍保证失败标记落地。
        print(_msg, flush=True)
        try:
            self.output.info(_msg)
        except Exception:
            pass
        # 持久化供 test_package 在缓存命中轮复发（ctre/ayatana-ido 先例）：
        # "Already installed!" 会跳过 build()，当轮日志无 marker 即判
        # incomplete，因此 package/res 必须携带真实 in-build 数字。
        try:
            with open(os.path.join(self.build_folder,
                                   "hmbs_upstream.json"),
                      "w", encoding="utf-8") as _fh:
                _json.dump(marker, _fh, ensure_ascii=False)
        except OSError as _e:
            self.output.warning(f"persist hmbs_upstream.json failed: {_e}")
        return marker["status"] == "passed"

    def _fix_test_tools_dependencies(self):
        _test_meson = os.path.join(
            self.source_folder, "test", "rist", "meson.build")
        if not os.path.isfile(_test_meson):
            return
        with open(_test_meson, "r", encoding="utf-8") as _f:
            _content = _f.read()
        if "tools_dependencies" not in _content:
            return
        _guard = ("# hmbs: tools_dependencies is defined only in "
                  "tools/meson.build (subdir gated by built_tools); "
                  "define fallback so -Dbuilt_tools=false keeps "
                  "library-only packaging while meson test still configures.\n"
                  "if not is_variable('tools_dependencies')\n"
                  "  tools_dependencies = []\n"
                  "endif\n")
        if "is_variable('tools_dependencies')" in _content:
            return
        with open(_test_meson, "w", encoding="utf-8",
                  newline="\n") as _f:
            _f.write(_guard + _content)
        self.output.info(
            "patched test/rist/meson.build: fallback tools_dependencies=[]")

    def _make_cmocka_visible_to_meson(self):
        """让上游 test/rist/unit/meson.build 能发现 Conan 的 cmocka。

        上游用 `meson.get_compiler('c').find_library('cmocka')` 探测，
        该方式不走 pkg-config，Conan 包路径对其不可见，srp_unit 测试
        会被静默跳过。改为 `dependency('cmocka')`（优先 pkg-config，
        PkgConfigDeps 已生成 cmocka.pc），找不到时 meson 行为与上游
        一致（跳过 srp_unit，不报错）。幂等，可重入。
        """
        _unit_meson = os.path.join(
            self.source_folder, "test", "rist", "unit", "meson.build")
        if not os.path.isfile(_unit_meson):
            return
        with open(_unit_meson, "r", encoding="utf-8") as _f:
            _content = _f.read()
        _old = ("cmocka = meson.get_compiler('c')"
                ".find_library('cmocka', required: false)")
        _new = ("cmocka = dependency('cmocka', required: false,"
                " method: 'pkg-config')\n"
                "if not cmocka.found()\n"
                "  cmocka = meson.get_compiler('c')"
                ".find_library('cmocka', required: false)\n"
                "endif")
        if _old in _content:
            with open(_unit_meson, "w", encoding="utf-8",
                      newline="\n") as _f:
                _f.write(_content.replace(_old, _new))
            self.output.info(
                "patched test/rist/unit/meson.build: cmocka via pkg-config")

    def package(self):
        meson = Meson(self)
        meson.install()
        self._fix_pkg_config_prefix()
        self._copy_licenses()
        self._persist_upstream_evidence()
        self._resign_shared_objects()

    def package_info(self):
        self.cpp_info.libs = ["rist"]
        self.cpp_info.includedirs = ["include", "include/librist"]
        self.cpp_info.set_property("pkg_config_name", "librist")
        self.cpp_info.set_property("cmake_file_name", "librist")
        self.cpp_info.set_property("cmake_target_name", "librist::librist")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]

    def _persist_upstream_evidence(self):
        # package/res 携带真实 in-build 上游数字，供 test_package 在
        # "Already installed!" 缓存命中轮复发（ctre/ayatana-ido 先例）。
        # 不重新定义测试口径：仅搬运 build() 已执行的 meson test 结果。
        from conan.tools.files import copy
        _src = os.path.join(self.build_folder, "hmbs_upstream.json")
        if os.path.isfile(_src):
            try:
                copy(self, "hmbs_upstream.json",
                     dst=os.path.join(self.package_folder, "res"),
                     src=self.build_folder)
                self.output.info("persisted res/hmbs_upstream.json")
            except Exception as _e:
                self.output.warning(f"copy hmbs_upstream.json failed: {_e}")
        else:
            self.output.warning(
                "hmbs_upstream.json missing in build folder; "
                "cache-hit rounds will lack upstream evidence")

    def _fix_pkg_config_prefix(self):
        pc_path = os.path.join(
            self.package_folder, "lib", "pkgconfig", "librist.pc")
        if not os.path.isfile(pc_path):
            return
        with open(pc_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        package_prefix = self.package_folder.replace("\\", "/")
        patched = content.replace("prefix=/\n", f"prefix={package_prefix}\n")
        patched = patched.replace(
            "prefix=/\r\n", f"prefix={package_prefix}\n")
        if patched != content:
            with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(patched)
            self.output.info("Patched librist.pc prefix to package folder")

    def _copy_licenses(self):
        from conan.tools.files import copy
        for _name in ("LICENSE", "COPYING", "LICENSES"):
            _src = os.path.join(self.source_folder, _name)
            if os.path.isfile(_src):
                copy(self, _name, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"),
                     keep_path=False)
            elif os.path.isdir(_src):
                copy(self, "*", src=_src,
                     dst=os.path.join(self.package_folder, "licenses", _name),
                     keep_path=True)

    def _resign_shared_objects(self):
        """OHOS 动态链接器要求 .so 具有效 .codesign 签名。

        meson 链接产物无签名时按 libsoup 先例重签；签名工具不存在
        （如本地预检）则跳过并告警，不阻断构建。
        """
        import glob as _glob
        _lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(_lib_dir):
            return
        _objcopy = shutil.which("llvm-objcopy")
        _signer = shutil.which("binary-sign-tool")
        if not _objcopy or not _signer:
            self.output.info(
                "skip .so re-sign: llvm-objcopy/binary-sign-tool not on PATH")
            return
        for _so in _glob.glob(os.path.join(_lib_dir, "librist.so*")):
            if os.path.islink(_so):
                continue
            self.run(f'llvm-objcopy --remove-section=.codesign "{_so}"')
            self.run(
                f'binary-sign-tool sign -inFile "{_so}" '
                f'-outFile "{_so}" -selfSign 1')
            self.output.info(f"re-signed {os.path.basename(_so)}")

    def _inject_meson_archiver(self):
        # OHOS：meson 经 PATH 找不到 llvm-ar 时向 native/cross
        # machine 文件注入绝对路径（zix/libsoup 先例）。
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            ar, ranlib = self._find_archiver_from_compiler_dir(bindir)
        if not ar and str(self.settings.os) == "OHOS":
            ar, ranlib = self._find_ohos_archiver()
        if not ar:
            ar = shutil.which("llvm-ar")
            if ar:
                _rl = shutil.which("llvm-ranlib")
                if _rl:
                    ranlib = _rl
        if not ar:
            return
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if os.path.isfile(path):
                self._patch_meson_machine_file(path, ar, ranlib)

    @staticmethod
    def _find_archiver_from_compiler_dir(bindir):
        if not bindir:
            return None, None
        ar = os.path.join(bindir, "llvm-ar")
        if not os.path.isfile(ar):
            return None, None
        ranlib = os.path.join(bindir, "llvm-ranlib")
        return ar, ranlib if os.path.isfile(ranlib) else None

    @staticmethod
    def _find_ohos_archiver():
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        if os.path.isfile(ar):
            return ar, ranlib if os.path.isfile(ranlib) else None
        _ar = shutil.which("llvm-ar")
        if _ar:
            _rl = shutil.which("llvm-ranlib")
            return _ar, _rl if _rl and os.path.isfile(_rl) else None
        return None, None

    def _ensure_hmbs_tmpdir(self):
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP"))
        if tmpdir:
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                pass
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir

    def _resolve_effective_compiler(self, kind):
        try:
            _exes = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            _exes = {}
        _configured = _exes.get(kind)
        if _configured and os.path.isfile(_configured):
            return _configured
        if _configured:
            _found = shutil.which(os.path.basename(_configured))
            if _found:
                return _found
        _env_key = "CC" if kind == "c" else "CXX"
        _env_val = os.environ.get(_env_key, "")
        if _env_val:
            _first = _env_val.split()[0].strip("\"'")
            if _first:
                if os.path.isfile(_first):
                    return _first
                _found = shutil.which(os.path.basename(_first))
                if _found:
                    return _found
                _found = shutil.which(_first)
                if _found:
                    return _found
        _default = "clang" if kind == "c" else "clang++"
        _found = shutil.which(_default)
        if _found:
            return _found
        return shutil.which("cc" if kind == "c" else "c++")

    def _export_resolved_compilers(self):
        try:
            _c = self._resolve_effective_compiler("c")
            _cxx = self._resolve_effective_compiler("cpp")
            if _c and os.path.isfile(_c):
                os.environ["CC"] = _c
                self.output.info(f"effective CC={_c}")
            if _cxx and os.path.isfile(_cxx):
                os.environ["CXX"] = _cxx
                self.output.info(f"effective CXX={_cxx}")
        except Exception as _e:
            self.output.warning(f"resolve compilers skipped: {_e}")

    def _repair_meson_compilers(self):
        import re as _re
        _c = self._resolve_effective_compiler("c")
        _cxx = self._resolve_effective_compiler("cpp") or _c
        if not _c or not os.path.isfile(_c):
            self.output.warning(
                "meson compiler repair skipped: no working C compiler on PATH")
            return
        _c = _c.replace("\\", "/")
        _cxx = (_cxx or _c).replace("\\", "/")
        self.output.info(f"resolved effective compilers: c={_c} cpp={_cxx}")
        for _filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            _path = os.path.join(self.generators_folder, _filename)
            if not os.path.isfile(_path):
                continue
            with open(_path, "r", encoding="utf-8") as _h:
                _content = _h.read()
            _orig = _content
            for _key, _new in (("c", _c), ("cpp", _cxx),
                               ("c_ld", _c), ("cpp_ld", _cxx)):
                _pat = _re.compile(
                    r"(?m)^(\s*" + _re.escape(_key)
                    + r"\s*=\s*\[\s*')([^']+)(')")
                def _repl(_m, _new=_new, _fn=_filename, _key=_key):
                    _old = _m.group(2)
                    if _old and os.path.isfile(_old):
                        return _m.group(0)
                    self.output.info(
                        f"patch {_fn} [{_key}]: '{_old}' -> '{_new}'")
                    return _m.group(1) + _new + _m.group(3)
                _content = _pat.sub(_repl, _content)
            for _stale in ("/data/service/hnp/bin/clang++",
                           "/data/service/hnp/bin/clang",
                           "/data/service/hnp/bin/cc",
                           "/data/service/hnp/bin/c++"):
                if _stale in _content and not os.path.isfile(_stale):
                    _base = os.path.basename(_stale)
                    _rp = _cxx if ("++" in _base or _base == "c++") else _c
                    _content = _content.replace(_stale, _rp)
                    self.output.info(
                        f"patch {_filename}: stale '{_stale}' -> '{_rp}'")
            if _content != _orig:
                with open(_path, "w", encoding="utf-8", newline="\n") as _h:
                    _h.write(_content)

    @staticmethod
    def _patch_meson_machine_file(path, ar, ranlib):
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content or "\nar =" in content:
            return
        insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))
