import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

CONSUMER_CHECK_COUNT = 2


def _is_runnable_compiler(cand):
    # isfile/X_OK 在 HMDFS 上不可信（主包 debsig-verify/0.34 同沙箱路线），
    # 仅 --version rc==0 且输出非空才算可用（pcre2/10.47 先例）。
    if not cand or not os.path.isfile(cand):
        return False
    try:
        proc = subprocess.run(
            [cand, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


class XmlsecTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # cmake 4.4.3 无 Platform/HarmonyOS.cmake，CMAKE_SYSTEM_NAME 随
        # profile 取 HarmonyOS 即报 "System is unknown to cmake"；强制
        # Linux 平台别名（ayatana-ido/0.10.4-v2 同机先例）。消费者冒烟
        # 无 OHOS 专有分支，静态链接 flag 仍由 toolchain 注入，别名安全。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # profile 的 tools.build:compiler_executables 指向
        # /data/service/hnp/bin/clang，在预检沙箱内不可用（与主包
        # _validated_cc 同一结论）；不可用时回退到 PATH/HMBS 解析的
        # clang（与主包真机验证通过的编译器同源），不改测试口径。
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        _conf_c = _exes.get("c") if isinstance(_exes, dict) else None
        if _conf_c and _is_runnable_compiler(_conf_c):
            self.output.info("test_package using conf compiler: {}"
                             .format(_conf_c))
        else:
            if _conf_c:
                self.output.warning(
                    "conf compiler '{}' unusable; falling back to PATH"
                    .format(_conf_c))
            for _cand in (os.environ.get("HMBS_CC"),
                          os.environ.get("CC"),
                          shutil.which("clang")):
                if _is_runnable_compiler(_cand):
                    tc.variables["CMAKE_C_COMPILER"] = _cand
                    self.output.info(
                        "test_package fallback compiler: {}".format(_cand))
                    break
            else:
                self.output.warning(
                    "no runnable fallback clang; keeping toolchain default")
        tc.generate()

    def _ensure_writable_tmp(self):
        # 真机 /tmp 只读（readonly_tmp）：test_package 的 cmake/ctest 与
        # 被测二进制都不允许触碰 /tmp，优先复用 HMBS 注入的可写 TMPDIR。
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(key)
            if cand and os.path.isdir(cand):
                tmp = cand
                break
        else:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        # 真机曾报 tar/gzip fork Out of memory：串行编译降低峰值内存
        #（oclgrind/26.03.1 先例：主包与消费者构建均显式单任务，不降优化、
        # 不改断言与测试口径）。主包 make 已 -j1，此处补齐消费者侧。
        cmake.build(build_tool_args=["-j1"])

    def _reemit_upstream_result(self):
        # Cache-hit re-emit: when Conan reuses the main-package binary,
        # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
        # prints. Re-print the persisted real result (written by build()
        # into package res/hmbs_upstream.json) every run. Missing file
        # only warns, never fabricates (ayatana-ido/ctre precedent).
        try:
            _upstream = None
            try:
                _dep = self.dependencies["xmlsec"]
                _pf = getattr(_dep, "package_folder", None)
                if _pf:
                    _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
                    if os.path.isfile(_cand):
                        with open(_cand, "r", encoding="utf-8") as _fh:
                            _upstream = json.load(_fh)
            except Exception:
                _upstream = None
            if isinstance(_upstream, dict) and _upstream.get("discovered"):
                _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_upstream, ensure_ascii=False))
                try:
                    print(_umsg, flush=True)
                except Exception:
                    pass
                self.output.info(_umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
        except Exception as _e:
            self.output.warning("upstream re-emit failed: %r" % (_e,))

    def test(self):
        if can_run(self):
            self._ensure_writable_tmp()
            bin_path = None
            for root, _, files in os.walk(self.build_folder):
                if "test_package" in files:
                    cand = os.path.join(root, "test_package")
                    if os.path.isfile(cand):
                        bin_path = cand
                        break
            if bin_path is None:
                marker = {
                    "executed": True,
                    "passed": False,
                    "command": "./test_package",
                    "discovered": CONSUMER_CHECK_COUNT,
                    "passedCount": 0,
                }
                _tmsg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
                try:
                    print(_tmsg, flush=True)
                except Exception:
                    pass
                self.output.info(_tmsg)
                self._reemit_upstream_result()
                raise RuntimeError("test_package binary missing")
            proc = subprocess.run(
                [bin_path],
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            out = proc.stdout or ""
            self.output.info(out[-2000:])
            ok_count = out.count("CHECK-OK:")
            marker = {
                "executed": True,
                "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
                "command": "./test_package",
                "discovered": CONSUMER_CHECK_COUNT,
                "passedCount": ok_count,
            }
            _tmsg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            try:
                print(_tmsg, flush=True)
            except Exception:
                pass
            self.output.info(_tmsg)
            self._reemit_upstream_result()
            if not marker["passed"]:
                raise RuntimeError("consumer test failed: rc=%s ok=%s/%s" % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT))
            # L0d 合规：显式 self.run() 执行被测二进制（已由 subprocess 计数验证）。
            self.run(bin_path, env="conanrun")
