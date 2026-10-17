import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps 生成 .pc 供 pkg-config 用；VirtualRunEnv/BuildEnv 给运行环境。
    # 显式声明 generators 会替换默认集，漏 VirtualRunEnv → conanrun 无 LD_LIBRARY_PATH。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig_cflags(self):
        """优先用 pkg-config 取编译标志 —— 真实消费方用法，比手拼 cpp_info 可靠。"""
        pc = "libiptcdata"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        # 鸿蒙设备上 subprocess 按裸名 exec 可能 ENOENT，必须解析成绝对路径。
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for _cand in ("/usr/bin/pkg-config", "/bin/pkg-config",
                          os.path.join(os.environ.get("CONAN_HOME", ""), "bin", "pkg-config")):
                if _cand and os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    exe = _cand
                    break
        if not exe:
            self.output.warning("找不到 pkg-config，回退 cpp_info")
            return ""
        try:
            out = subprocess.run([exe, "--cflags", pc], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                self.output.info("test_package 用 pkg-config --cflags %s" % pc)
                return out.stdout.strip()
            self.output.warning("pkg-config --cflags %s 无输出（rc=%s），回退 cpp_info"
                                % (pc, out.returncode))
        except (OSError, subprocess.SubprocessError) as e:
            self.output.warning("pkg-config 执行失败（%s），回退 cpp_info" % e)
        return ""

    def build(self):
        dep = self.dependencies["libiptcdata"].cpp_info
        inc = self._pkgconfig_cflags()
        if not inc:
            # 回退：从 cpp_info 拼装
            incs = []
            for _ref, _d in self.dependencies.items():
                for _p in _d.cpp_info.includedirs:
                    incs.append("-I" + _p)
            inc = " ".join(dict.fromkeys(incs))
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        cc = os.environ.get("CC", "clang")
        # C 测试不能收 C++ 标准开关；gnu 方言让 POSIX 函数在 musl 头里可见。
        std_flag = "-std=gnu99"
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # CONFIG_SHELL 由 profile 注入（鸿蒙环境指向设备 bash）；
        # 缺失时回退到本机 bash，最后回退 /bin/sh。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/bin/sh"
        # 显式拼 LD_LIBRARY_PATH：VirtualRunEnv 的 conanrunenv 在 shared 包
        # 上 libdirs 可能为空，-Wl,-rpath 也不总生效（pango 实撞的坑）。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_probe'",
                 env="conanrun")
