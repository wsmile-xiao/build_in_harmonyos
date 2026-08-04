import os
import shutil
import subprocess
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps 让下面的 pkg-config 能找到依赖的 .pc。
    # **VirtualRunEnv / VirtualBuildEnv 必须一并写上**：显式给 generators 会
    # **替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv 就没有 conanrun 环境，
    # test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH，
    # 表现为编译链接全过、跑起来报 `Error loading shared library ...`（实撞）。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig(self, what):
        """跑 pkg-config 取 --cflags 或 --libs。取不到返回空串，由调用方回退。"""
        pc = "hwloc" or "hwloc"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for _cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    exe = _cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _pkgconfig_cflags(self):
        """优先用 pkg-config 取编译标志 —— 这才是真实消费方的用法。

        为什么不再手工从 cpp_info 拼 -I：那条路是打地鼠。头文件的实际位置
        有太多形态，而各包 cpp_info 的声明完整度参差：
          · pango   头在 include/pango-1.0/
          · glib    头在 include/glib-2.0/，**而 glibconfig.h 在 lib/glib-2.0/include/**（lib 侧！）
          · fribidi 头在 include/fribidi/
        逐条加扫描规则永远追不上；而 conan 生成的 .pc 里这些路径本来就是齐的。
        取不到 .pc 时才回退到 cpp_info 拼装。
        """
        out = self._pkgconfig("--cflags")
        if out:
            self.output.info("test_package 用 pkg-config --cflags")
        else:
            self.output.warning("pkg-config --cflags 取不到，回退 cpp_info")
        return out

    def build(self):
        dep = self.dependencies["hwloc"].cpp_info
        inc = self._pkgconfig_cflags()
        if not inc:
            # 回退：从 cpp_info 拼，并补一层版本化 include 子目录
            incs = []
            for _ref, _d in self.dependencies.items():
                for _p in _d.cpp_info.includedirs:
                    incs.append("-I" + _p)
                    if not os.path.isdir(_p):
                        continue
                    for _name in sorted(os.listdir(_p)):
                        _sub = os.path.join(_p, _name)
                        if os.path.isdir(_sub) and any(
                                f.endswith((".h", ".hpp", ".hh", ".hxx"))
                                for f in os.listdir(_sub)):
                            incs.append("-I" + _sub)
            inc = " ".join(dict.fromkeys(incs))
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libhwloc.so")
        cc = os.environ.get("CC", "clang")
        # C 测试**不能**收 C++ 标准开关（clang 报 not allowed with 'C'）。
        # musl 上还要用 gnu 方言：严格 ISO 方言不定义 _POSIX_C_SOURCE，
        # POSIX 函数（clock_gettime 等）在 musl 头里就不声明。
        std_flag = "-std=gnu99"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # 优先 pkg-config --libs（理由同 cpp 分支）；保留 -ldl 供 dlopen 探针用。
        _pcl = self._pkgconfig("--libs")
        _libs = _pcl.split() if _pcl else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + _libs
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # **显式拼 LD_LIBRARY_PATH**，不能只依赖 conanrun：
        # VirtualRunEnv 生成的 conanrunenv 里 libdirs 可能是空的（本仓已记录：
        # shared=False 发布的包 conan 视为静态、不写 libdirs，但包里确实装了 .so），
        # 而链接期的 -Wl,-rpath 也不总起作用。
        # 症状是编译链接全过、一跑就 `Error loading shared library ...`（pango 实撞）。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_probe'",
                 env="conanrun")
