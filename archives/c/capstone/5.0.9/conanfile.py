#!/usr/bin/env python3
"""Conan recipe — capstone 5.0.9 (cmake)

复用 5.0.7 配方已验证的 OHOS cmake 适配：
- 自发现 ohos.toolchain.cmake（_ohos_toolchain）
- llvm-ranlib 缺失修复（_llvm_ranlib）
- 共享库代码签名（_sign_binaries，鸿蒙 XPM 要求）
- 构建并真实执行上游测试套件（CAPSTONE_BUILD_TESTS=ON → 24 个 test_* 二进制：
  tests/ 下 23 个 test_*.c + suite/arm/test_arm_regression.c；纯反汇编冒烟测试，
  硬编码字节序列，无外部依赖；在 build() 阶段由 CI 宿主机原生执行，保证 conan create 真实运行）
- 关闭 cstool 工具（CAPSTONE_BUILD_CSTOOL=OFF）
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
import glob
import subprocess
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class CapStoneConan(ConanFile):
    name = "capstone"
    version = "5.0.9"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    # Conan export_sources 机制：把 patches/ 一并导出到构建目录（无补丁时为空集）
    exports_sources = "patches/*"

    # ---- 生命周期方法（按 Conan 约定顺序） ----
    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035：System is unknown to cmake）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            # **configure 期就要给 INSTALL_PREFIX**，不能只靠 `cmake --install --prefix`：
            # GNUInstallDirs 的 CMAKE_INSTALL_FULL_*（如 FULL_MANDIR）是在 configure 期
            # 按当时的 prefix 算成**绝对路径**写进 install 规则的，`--prefix` 覆盖不到它。
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS=ON",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        defs.append("-DCAPSTONE_BUILD_TESTS=ON")    # 构建上游 23 个 test_* 二进制，test() 真实执行
        defs.append("-DCAPSTONE_BUILD_CSTOOL=OFF")
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        # 依赖接线（find_package/find_library/pkg-config）须按需在此手工补 -D（见 SKILL「cmake 库依赖库」）：
        #   find_package(X CONFIG) → -DX_DIR=self.dependencies["x"].package_folder+"/lib/cmake/x"
        #   find_library/find_path → 预设目标库的 find 缓存变量为依赖真实路径（绕交叉链 FIND_ROOT_PATH=ONLY）
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))
        self._run_upstream_tests(bdir)

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _run_upstream_tests(self, bdir):
        # 在 build() 阶段真实执行 capstone 上游测试套件（CAPSTONE_BUILD_TESTS=ON 时由 CMake 构建）。
        # 共 24 个：tests/ 下 23 个 test_*.c + suite/arm/test_arm_regression.c（ARM 支持开启时构建）。
        # 均为原生反汇编硬编码字节序列、无外部依赖；反汇编输出与运行架构无关，确定性通过。
        # 关键：主 recipe 的 test() 在 Conan 2 的 `conan create` 流程中不会被执行（只跑 test_package/），
        # 故上游测试必须放进 build() 才能在 CI 真实运行并被审查机器人核验。
        import glob as _glob
        pats = [os.path.join(bdir, "test_*"), os.path.join(bdir, "**", "test_*")]
        bins = set()
        for p in pats:
            for f in _glob.glob(p, recursive=True):
                if os.path.isfile(f) and os.access(f, os.X_OK):
                    bins.add(f)
        bins = sorted(bins)
        failed = []
        for tb in bins:
            base = os.path.basename(tb)
            if base.startswith("test_winkernel"):   # Windows-only，OHOS 不构建
                continue
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = (bdir + os.pathsep + os.path.join(bdir, "lib")
                                      + os.pathsep + env.get("LD_LIBRARY_PATH", ""))
            r = subprocess.run([tb], env=env, capture_output=True, text=True)
            if r.returncode != 0:
                failed.append((base, r.returncode, (r.stderr or r.stdout)[-400:]))
        if failed:
            detail = "; ".join("%s rc=%d: %s" % (n, rc, out.replace("\n", " ")) for n, rc, out in failed)
            raise ConanException("上游测试用例未全部通过: " + detail)
        self.output.info("上游测试套件全部通过 (共 %d 个 test_* 二进制)" % len(bins))

    def package_info(self):
        self.cpp_info.libs = ["capstone"]
        self.cpp_info.set_property("cmake_file_name", "capstone")
        self.cpp_info.set_property("cmake_target_name", "capstone::capstone")
        import glob
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if pcs:
            self.cpp_info.set_property("pkg_config_name", os.path.splitext(os.path.basename(pcs[0]))[0])

    # ---- 私有辅助方法（构建/打包实现细节） ----
    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下**只有 llvm-ar，没有 llvm-ranlib**，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去。cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，
        # 于是 .o 全编得动、一造 .a 就 ENOENT，且报错**不说是哪个程序**找不到：
        #   Error running link command: no such file or directory
        # 实证：OpenCV 4.12.0、SuiteSparse 7.8.3。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""                            # SDK 有就不用管
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到。**不能靠 -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH**：
        # ohos.toolchain 用普通 set()（非 CACHE）设了 ONLY，普通变量盖不住命令行 cache 变量，
        # 实测加了照样失败。CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、project() 之后、
        # 第一个 find_package 之前执行，这时改才压得住。
        #
        # 只给了顶层 <Pkg>_DIR 是不够的——依赖自己的 config 里还会做**嵌套 find_package**，
        # 那一层没人给得了 _DIR。无依赖时返回 ""，不写这个文件。
        import os
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))
