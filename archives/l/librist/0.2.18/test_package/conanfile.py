#!/usr/bin/env python3
"""Conan test_package for librist 0.2.18 — L1 consumer test.

test() 编译并运行两个真实调用 librist API 的消费者程序：
  1. test_sender — librist_version/api_version + sender 生命周期；
  2. test_receiver — receiver 生命周期 + rist_parse_address2 解析。
任一失败（self.run 非零抛异常）即 conan create 失败；全部通过后
打印 HMBS_TEST_PACKAGE_RESULT 机器标记。
"""

import os
import shutil

from conan import ConanFile


class LibristTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cc(self):
        try:
            _exes = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            _exes = {}
        _c = _exes.get("c", "")
        if _c and os.path.isfile(_c):
            return _c
        if _c:
            _f = shutil.which(os.path.basename(_c))
            if _f:
                return _f
        _cc = os.environ.get("CC", "")
        if _cc:
            _first = _cc.split()[0].strip("'\"")
            if os.path.isfile(_first):
                return _first
            _f = shutil.which(os.path.basename(_first))
            if _f:
                return _f
        return shutil.which("clang") or "clang"

    def _compile_and_run(self, src_name, bin_name):
        dep = self.dependencies["librist"]
        inc = os.path.join(
            dep.package_folder, dep.cpp_info.includedirs[0])
        lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        src = os.path.join(os.path.dirname(__file__), src_name)
        _cc = self._resolve_cc()
        self.output.info(f"test_package effective CC={_cc}")
        compile_cmd = (
            f'"{_cc}" -I"{inc}" -L"{lib}" "{src}" -lrist -o {bin_name}'
        )
        run_cmd = f"./{bin_name}"
        self.run(compile_cmd, env="conanrun")
        self.run(run_cmd, env="conanrun")
        return f"{compile_cmd} && {run_cmd}"

    def test(self):
        cmd1 = self._compile_and_run("test_sender.c", "test_librist_sender")
        cmd2 = self._compile_and_run(
            "test_receiver.c", "test_librist_receiver")

        # HMBS 硬门禁要求 stdout 有一行合法 JSON 标记。能执行到此
        # 即两组编译+运行全部退出 0（self.run 非零抛异常），
        # discovered/passedCount 为本 test_package 真实用例数（2）。
        import json as _json
        marker = {
            "executed": True,
            "passed": True,
            "command": f"{cmd1} ; {cmd2}",
            "discovered": 2,
            "passedCount": 2,
        }
        _tmsg = f'HMBS_TEST_PACKAGE_RESULT={_json.dumps(marker)}'
        print(_tmsg, flush=True)
        try:
            self.output.info(_tmsg)
        except Exception:
            pass
        self._reemit_upstream_marker()

    def _reemit_upstream_marker(self):
        # 缓存命中复发：当 Conan 复用主包二进制时 build() 被跳过，
        # 其 HMBS_UPSTREAM_TEST_RESULT 不打印，当轮即判 incomplete。
        # 此处复发 package/res/hmbs_upstream.json（build() 真实执行
        # 的 meson test 数字），不重新定义测试口径（ayatana-ido 先例）。
        import json as _json
        _cand = None
        try:
            _dep = self.dependencies["librist"]
            _pf = getattr(_dep, "package_folder", None)
            if _pf:
                _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
        except Exception:
            _cand = None
        try:
            if _cand and os.path.isfile(_cand):
                with open(_cand, "r", encoding="utf-8") as _fh:
                    _data = _json.load(_fh)
                if isinstance(_data, dict) and _data.get("discovered"):
                    _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                             + _json.dumps(_data, ensure_ascii=False))
                    print(_umsg, flush=True)
                    try:
                        self.output.info(_umsg)
                    except Exception:
                        pass
                    return
            self.output.warning(
                "persisted hmbs_upstream.json missing; "
                "upstream evidence only available on fresh build")
        except Exception as _e:
            self.output.warning(f"upstream re-emit failed: {_e!r}")
