#!/usr/bin/env python3
"""Conan test_package — saint 2.5.0 CLI 工具功能验证。

通过 test.sh 执行 11 项真实断言（五个二进制安装/可执行、-v 版本、
saint-reformat 真实数据重排、四个 MCMC 工具 usage 冒烟）。
saint 的 5 个可执行都动态链接 libgsl.so/libgslcblas.so，因此以 conanrun
环境运行（VirtualRunEnv 会把 gsl 的 libdir 注入 LD_LIBRARY_PATH）。
"""
import os

from conan import ConanFile


class SaintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True：让 saint 的 bin/ 进入 conanrun 的 PATH，且传播 gsl 运行闭包。
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        # 解析 saint package 的 bindir（绝对路径），传给 test.sh 作为 BINDIR。
        saint_dep = self.dependencies.get("saint")
        bin_dir = ""
        if saint_dep is not None:
            try:
                rel = saint_dep.cpp_info.bindirs[0] if saint_dep.cpp_info.bindirs else "bin"
            except Exception:
                rel = "bin"
            cand = rel if os.path.isabs(rel) else os.path.join(
                saint_dep.package_folder, rel)
            bin_dir = cand if os.path.isdir(cand) else os.path.join(
                saint_dep.package_folder, "bin")
            self.output.info("saint package_folder=%s bindir=%s" % (
                saint_dep.package_folder, bin_dir))
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # OHOS /tmp 只读(erofs)：先给一个可写 TMPDIR，test.sh 也自行回退。
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")
