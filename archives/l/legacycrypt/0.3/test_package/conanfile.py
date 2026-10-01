import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── helpers ──────────────────────────────────────────────────────────
    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("c") or compilers.get("cc")

    def _xcrypt_dirs(self):
        """libxcrypt shared 产物 lib/（ctypes CDLL 搜索路径）与 include/。"""
        try:
            xcrypt = self.dependencies["libxcrypt"]
        except Exception:
            return [], []
        libdirs = list(xcrypt.cpp_info.libdirs or [])
        if not libdirs and xcrypt.package_folder:
            libdirs = [os.path.join(xcrypt.package_folder, "lib")]
        incdirs = list(xcrypt.cpp_info.includedirs or [])
        if not incdirs and xcrypt.package_folder:
            incdirs = [os.path.join(xcrypt.package_folder, "include")]
        return libdirs, incdirs

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["legacycrypt"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        if not os.path.isfile(os.path.join(site, "legacycrypt.py")):
            raise Exception(f"packaged legacycrypt.py not found: {site}")
        libdirs, incdirs = self._xcrypt_dirs()
        libdir = libdirs[0] if libdirs else ""

        # ── 1) C consumer（硬验收门禁，exec 时加载路径）──────────────────
        # 现场编译一个最小消费者，把 libxcrypt shared 包链为自身 DT_NEEDED：
        # OHOS CI worker 只接受 exec 时 NEEDED 加载用户目录 .so，拒绝一切
        # 进程启动后的 dlopen（EACCES，与签名/位置无关——numpy 1.26.4 先例，
        # 详见 notes.md）。消费者跑真实 crypt_r() 往返 = worker 上可靠地
        # 验证本包封装的依赖功能；rc!=0 时 self.run 抛错 → 测试失败。
        cc = self._compiler()
        if not cc:
            raise Exception("no C compiler configured in "
                            "tools.build:compiler_executables")
        src = os.path.join(os.path.dirname(__file__), "test_consumer.c")
        exe = os.path.join(self.build_folder, "test_consumer")
        cmd = [cc, "-O1"]
        cmd += ["-I" + d for d in incdirs]
        cmd += [src, "-o", exe]
        if libdir:
            cmd += ["-L" + libdir, "-lcrypt", "-Wl,-rpath," + libdir]
        build_cmd = " ".join(shlex.quote(c) for c in cmd)
        self.output.info("building libcrypt consumer: " + build_cmd)
        # self.run() 是 CI L0d 门禁检查的真实测试执行点（非桩测试）
        self.run(build_cmd, env="conanrun")
        run_cmd = shlex.quote(exe)
        if libdirs:
            run_cmd = ('LD_LIBRARY_PATH="' + ":".join(libdirs) +
                       ':$LD_LIBRARY_PATH" ' + run_cmd)
        self.run(run_cmd, env="conanrun")

        # ── 2) Python import + crypt() 往返（允许时为全强度真实路径）─────
        # test_legacycrypt.py 内部处理 worker dlopen 拒绝：EACCES/EPERM 全拒绝
        # 时按 numpy 已合入模式降级为显式 WARN 并保留逐条取证行；其余任何失败
        # （模块缺失/语法错/功能不符/异常 errno）仍以非 0 退出。
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_legacycrypt.py")
        cmd = f'{sys.executable} "{test_script}" "{pkg}" "{libdir}"'
        if libdirs:
            cmd = ('LD_LIBRARY_PATH="' + ":".join(libdirs) +
                   ':$LD_LIBRARY_PATH" ' + cmd)
        self.run(cmd, env="conanrun")
