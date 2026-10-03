import os

from conan import ConanFile

required_conan_version = ">=2.0"


class LdplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ldpl"]
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(str(dep.package_folder), bindir)
        ldpl = os.path.join(bindir, "ldpl").replace("\\", "/")
        script = os.path.join(os.path.dirname(__file__), "test_ldpl.sh")
        script = script.replace("\\", "/")
        samples = os.path.join(os.path.dirname(__file__), "samples").replace("\\", "/")
        exe = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = (exe.get("cpp") or "clang++").replace("\\", "/")
        # LDPL_LIB_LOCATION 由依赖包的 runenv_info 注入（conanrun），证明包可重定位；
        # LDPL_CXX 必须显式给：OHOS 上没有名为 c++ 的前端，只有 SDK 的 clang++
        self.run('LDPL_CXX="{cxx}" sh "{script}" "{ldpl}" "{samples}"'.format(
            cxx=cxx, script=script, ldpl=ldpl, samples=samples), env="conanrun")
