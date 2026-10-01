import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ---------------------------------------------------------------- helpers
    def _locate(self, name):
        """在 test_package 可能落地的几个目录里找源文件。"""
        for folder in (self.build_folder, self.source_folder, self.recipe_folder):
            if folder:
                cand = os.path.join(folder, name)
                if os.path.isfile(cand):
                    return cand
        raise FileNotFoundError(
            "{0} 未找到：test_package 源码未随用例导出？".format(name))

    def _shell(self):
        return "/system/bin/sh" if os.path.exists("/system/bin/sh") else "sh"

    # ------------------------------------------------------------------ build
    def build(self):
        # 编译真实消费者程序：既 #include 公共头（依赖包 include/），又链接库
        # （依赖包 lib/）——CI 的 L1e 会把两个目录都移走再跑一次，两处都要真实依赖。
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        cc = (self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("c")
              or os.environ.get("CC") or "clang")
        self.run('{cc} "{src}" -o consumer {inc} {ld} {rp} -lgsl -lgslcblas -lm'.format(
            cc=cc, src=self._locate("consumer.c"),
            inc=" ".join(incs), ld=" ".join(linkdirs), rp=" ".join(rpaths)))

    # ------------------------------------------------------------------- test
    def test(self):
        if cross_building(self):
            # 显式标记为 SKIP（而非静默 return），便于日志/门禁区分「跳过」与「通过」。
            # 正常 CI 路径不会到这里：ci/conan/build_and_test.sh 对 host 与 build 使用同一
            # profile（-pr:h 与 -pr:b 同值），W3 实测 6/6 全部真实执行。
            self.output.warning(
                "SKIP(HC-*): cross-building 场景不执行鸿蒙消费者用例，仅完成编译+链接")
            return
        # HarmonyOS PC 的动态加载器不跟随符号链接解析 DT_NEEDED：libtool 安装出来的
        # libgsl.so -> libgsl.so.25 -> libgsl.so.25.1.0 这类软链会让 consumer 运行期
        # 报 "Error loading shared library libgsl.so.25"。故把每个 .so 名字都按实体
        # 文件摊平复制到临时目录，再由 test.sh 用 LD_LIBRARY_PATH 指过去。
        run_dir = self._stage_runtime_dir()
        try:
            self.run('{sh} "{script}" "{d}"'.format(
                sh=self._shell(), script=self._locate("test.sh"), d=run_dir))
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def _stage_runtime_dir(self):
        tmp_root = os.environ.get("TMPDIR") or tempfile.gettempdir()
        try:
            dst = tempfile.mkdtemp(prefix="gsl-test-", dir=tmp_root)
        except OSError:
            dst = tempfile.mkdtemp(prefix="gsl-test-", dir=self.build_folder)
        for _ref, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                if not libdir or not os.path.isdir(libdir):
                    continue
                for name in sorted(os.listdir(libdir)):
                    if ".so" not in name:
                        continue
                    real = os.path.realpath(os.path.join(libdir, name))
                    target = os.path.join(dst, name)
                    if os.path.isfile(real) and not os.path.exists(target):
                        shutil.copy2(real, target)
        shutil.copy2(os.path.join(self.build_folder, "consumer"),
                     os.path.join(dst, "consumer"))
        os.chmod(os.path.join(dst, "consumer"), 0o755)
        return dst
