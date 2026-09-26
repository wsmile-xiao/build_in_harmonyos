#!/usr/bin/env python3
"""Conan recipe — libbpp-phyl-omics 2.4.1 (CMake).

Bio++ Phylogenetic Omics：在 bpp-phyl 与 bpp-seq-omics 之上提供 MAF(多重比对)
树重建/簇统计等系统发育-组学迭代器，是 Bio++ 家族 `bpp-core → bpp-seq →
(bpp-seq-omics | bpp-phyl) → bpp-phyl-omics` 链上的一环。

上游构建两个目标（`bpp-phyl-omics-static` / `bpp-phyl-omics-shared`，OUTPUT_NAME
均为 `bpp-phyl-omics`，SOVERSION=3）；**上游 v2.4.1 没有 test/ 目录、没有任何测试
目标**（无 enable_testing / BUILD_TESTING / add_test / ctest），因此本配方不做上游
测试执行（详见 test_package/MANIFEST.yml 的 upstream_test_audit），仅以 test_package
的消费者断言验证链接与公开符号。

依赖（顶层 `find_package(bpp-seq-omics 3.0.0 REQUIRED)` + `find_package(bpp-phyl
12.0.0 REQUIRED)`）：
* `libbpp-seq-omics/2.4.1` —— Conan 依赖，已发布到 ohpcd
* `libbpp-phyl/2.4.1` —— **未发布到 ohpcd**：对其声明 `requires()` 会在依赖图
  解析阶段直接失败（L0i/R36，见真机日志 `Package 'libbpp-phyl/2.4.1' not
  resolved`）。沿用同族先例 `libbpp-seq` vendor `bpp-core` 的做法，把
  **libbpp-phyl 源码 vendor 进本配方**（conandata.yml `bpp_phyl` 条目），先
  构建到私有前缀 `bpp-phyl-prefix`，phyl-omics 通过 CMAKE_PREFIX_PATH 找到它。
  构建所需的 bpp-seq/bpp-core config 来自已发布的 `libbpp-seq/2.4.1`（包内合并
  bpp-core 的库与 CMake 配置），本配方在 vendored phyl configure 时注入
  `bpp-seq_DIR` / `bpp-core_DIR`（指向 libbpp-seq 的 shim）。
* `libbpp-seq/2.4.1` —— 已发布（包内合并了 bpp-core 的库与 CMake 配置），
  声明为直接依赖，供 vendored bpp-phyl 的 `find_package(bpp-seq)` 与最终消费者。

沿用的同族结论（libbpp-seq-omics / libbpp-phyl / libbpp-raa 逐条踩过）：
* `cmake_minimum_required(2.8.11)` 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
* 上游 `set(CMAKE_CXX_FLAGS …)` 会覆盖 Conan 注入的 --target/--sysroot，交叉编译
  时必须改用 `CMAKE_<LANG>_COMPILER_TARGET` / `CMAKE_SYSROOT` 注入（见 E543）；
  真机原生构建时 profile 不带这些 flag，此段自动为空
* 依赖包按 shared=False 裁剪 .so 后，其 CMake 导出文件仍引用 shared target → 下游
  find_package 报 "references ... .so but this file does not exist"，需在构建内做
  一份剔除 shared 目标的 shim（不改依赖缓存），并把 BPP_LIBS_SHARED 重定向到 static
* `find_package(bpp-seq-omics/bpp-phyl/bpp-seq)` 依赖上游 `lib/cmake/<name>` 里的
  config 文件；CMakeDeps 生成的 `libbpp-*.cmake` 名字对不上，必须显式注入
  `<name>_DIR`（本配方对 seq-omics / phyl / seq / core 四个 config 统一注入）
* Conan 包名用 `libbpp-phyl-omics` 前缀，避免 CMakeDeps 产物遮蔽上游
  bpp-phyl-omics-config.cmake
"""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class LibbppPhylOmicsConan(ConanFile):
    name = "libbpp-phyl-omics"
    version = "2.4.1"
    description = ("Bio++ Phylogenetic Omics: MAF tree reconstruction and "
                   "cluster statistics iterators on top of bpp-phyl and bpp-seq-omics")
    license = "CECILL-2.1"
    homepage = "https://github.com/BioPP/bpp-phyl-omics"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # 依赖的 CMake 包配置名（连同传递依赖的 bpp-seq / bpp-core，从两个 Conan 依赖包的
    # shim 里收集）。**不含 bpp-phyl**：libbpp-phyl/2.4.1 未发布到 ohpcd，按同族
    # libbpp-seq vendor bpp-core 的先例改由源码 vendor（见 _build_bundled_bpp_phyl），
    # 其 bpp-phyl-config.cmake 经 vendored 前缀的 CMAKE_PREFIX_PATH 提供。
    _DEP_CMAKE_NAMES = ("bpp-seq-omics", "bpp-seq", "bpp-core")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 公开头文件（经 bpp-seq-omics / bpp-seq）包含 Bpp/Seq 头，
        # 消费者编译时会用到；libbpp-seq 包内已合并 bpp-core 的库与 CMake 配置。
        #
        # **不再声明 libbpp-phyl**：其 /2.4.1 未发布到 ohpcd，requires() 会在
        # 依赖图解析阶段报 "Package 'libbpp-phyl/2.4.1' not resolved"。改为在
        # source() 里 vendor libbpp-phyl 源码、build() 里先构建到私有前缀
        # （同族先例 libbpp-seq vendor bpp-core，见 _build_bundled_bpp_phyl）。
        self.requires("libbpp-seq-omics/2.4.1",
                      transitive_headers=True, transitive_libs=True)
        # 直接声明 libbpp-seq 以便 generate()/build() 能访问其包目录做 shim，
        # 它同时为 vendored bpp-phyl 提供 bpp-seq/bpp-core 的 CMake config。
        self.requires("libbpp-seq/2.4.1",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 同族先例 libbpp-seq vendor bpp-core：libbpp-phyl/2.4.1 未发布到 ohpcd，
        # 声明 requires() 会在依赖图解析阶段失败，这里把它的源码 vendor 进构建目录，
        # 在 build() 里先构建到私有前缀（见 _build_bundled_bpp_phyl）。
        get(
            self,
            **self.conan_data["bpp_phyl"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "bpp-phyl-src"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            bool(self.options.shared)
            or bool(self.options.get_safe("fPIC", True)))
        # 上游声明 cmake_minimum_required(VERSION 2.8.11)。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"

        # ★ 交叉编译关键（E543）：上游 set(CMAKE_CXX_FLAGS …) 覆盖 --target/--sysroot。
        # 原生构建（设备上 build==host）profile 不设这些 flag，此段自动为空。
        cxxflags = self.conf.get("tools.build:cxxflags", default=[], check_type=list) or []
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list) or []
        target = next((f.split("=", 1)[1] for f in (cxxflags + cflags)
                       if f.startswith("--target=")), None)
        sysroot = next((f.split("=", 1)[1] for f in (cxxflags + cflags)
                        if f.startswith("--sysroot=")), None)
        if target:
            tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = target
            tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = target
            self.output.info(
                f"upstream overwrites CMAKE_CXX_FLAGS; injecting target via "
                f"CMAKE_<LANG>_COMPILER_TARGET={target}")
        if sysroot:
            tc.cache_variables["CMAKE_SYSROOT"] = sysroot

        # 对依赖包做 CMake 导出 shim，并统一注入各 <name>_DIR：
        # find_package(bpp-seq-omics/bpp-seq/bpp-core) REQUIRED 只能靠上游包配置满足。
        shim_dirs = self._collect_dep_cmake_dirs()
        self._shim_dirs = shim_dirs
        for name in self._DEP_CMAKE_NAMES:
            if name in shim_dirs:
                tc.cache_variables[f"{name}_DIR"] = shim_dirs[name]
                self.output.info(f"{name}_DIR -> {shim_dirs[name]}")
        # vendored libbpp-phyl 私有前缀（build() 里先构建好，configure 时才被读取，
        # 存在与否不影响 generate()）。find_package(bpp-phyl 12.0.0 REQUIRED) 靠
        # CMAKE_PREFIX_PATH 找到 <prefix>/lib{,64}/cmake/bpp-phyl（lib vs lib64 皆可）。
        phyl_prefix = os.path.join(self.build_folder, "bpp-phyl-prefix").replace("\\", "/")
        tc.cache_variables["CMAKE_PREFIX_PATH"] = phyl_prefix
        tc.generate()
        CMakeDeps(self).generate()

    def _collect_dep_cmake_dirs(self):
        """为每个直接 Conan 依赖包复制一份 shim，收集其 lib/cmake 下的 config 目录。

        **不含 libbpp-phyl**（未发布，改由源码 vendor）；vendored bpp-phyl 依赖
        bpp-seq/bpp-core 的 config 正好也来自 libbpp-seq 的 shim（bpp-core 合并进
        libbpp-seq 包）。
        """
        shim_dirs = {}
        for dep_name in ("libbpp-seq-omics", "libbpp-seq"):
            shim = self._prepare_cmake_shim(dep_name)
            if not shim:
                continue
            for root, _dirs, _files in os.walk(shim):
                if not os.path.basename(root).startswith("cmake"):
                    continue
                for sub in os.listdir(root):
                    cfg = os.path.join(root, sub, f"{sub}-config.cmake")
                    if os.path.isfile(cfg):
                        shim_dirs.setdefault(sub, os.path.join(root, sub).replace("\\", "/"))
        return shim_dirs

    def _prepare_cmake_shim(self, dep_name):
        """把依赖包复制到构建目录，并修掉其 CMake 导出文件里指向已裁剪 .so 的 shared 目标。

        依赖包按 shared=False 打包时裁掉了 *.so，但其 CMake 导出文件仍把
        `<name>-shared` 列为 imported target 并指向不存在的 .so。CMake 的 import
        check 会在 `find_package()` 时直接报 "references the file ... but this file
        does not exist" 而 configure 失败。

        **不改依赖缓存**，只在本次构建内复制一份、剔除 shared 目标，并把
        `<name>_DIR` 指过去。整包复制保持 `${_IMPORT_PREFIX}` 与 .a / 头文件相对
        位置不变。`set(BPP_LIBS_SHARED … <name>-shared)` 那一行不能删（上游
        src/CMakeLists 给 shared 库目标链接依赖），把它**重定向到 static 目标**——
        静态归档都 PIC，可安全链进共享库。
        """
        try:
            dep = self.dependencies[dep_name]
        except Exception:                                            # noqa: BLE001
            self.output.warning(f"dependency {dep_name} not in graph; skipping shim")
            return None
        source = getattr(dep, "package_folder", None)
        if not source:
            return None
        shim = os.path.join(self.build_folder, f"{dep_name}-shim")
        if os.path.isdir(shim):
            shutil.rmtree(shim, ignore_errors=True)
        shutil.copytree(source, shim)
        stripped = 0
        for cmake_root in (os.path.join(shim, "lib", "cmake"),
                           os.path.join(shim, "lib64", "cmake")):
            if not os.path.isdir(cmake_root):
                continue
            for name in os.listdir(cmake_root):
                directory = os.path.join(cmake_root, name)
                if not os.path.isdir(directory):
                    continue
                for entry in os.listdir(directory):
                    if not entry.endswith(".cmake"):
                        continue
                    path = os.path.join(directory, entry)
                    if entry == f"{name}-config.cmake":
                        if self._strip_shared_from_config(path, name):
                            stripped += 1
                    elif entry.startswith(f"{name}-targets"):
                        if self._strip_shared_target(path, name):
                            stripped += 1
        self.output.info(
            f"cmake shim {dep_name}: copied package to {shim}, "
            f"stripped shared targets in {stripped} export file(s); "
            f"dependency cache is not modified")
        return shim

    @staticmethod
    def _strip_shared_from_config(path, name):
        """修掉 config 文件里对 <name>-shared 目标的直接引用。

        各 biopp config（bpp-seq-omics-config.cmake / bpp-phyl-config.cmake /
        bpp-seq-config.cmake / bpp-core-config.cmake）会做
        `get_property (shared-location TARGET <name>-shared PROPERTY LOCATION)`；
        该 imported target 被移除后这一行会让 find_package() 直接报
        "Target ... has not been created"。但 `set(BPP_LIBS_SHARED … <name>-shared)`
        不能删空（上游依赖 `${BPP_LIBS_SHARED}` 拿 INTERFACE include 路径），故把
        `<name>-shared` 重定向到 `<name>-static`。
        """
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        kept = [line for line in lines if f"TARGET {name}-shared" not in line]
        kept = [line.replace(f"{name}-shared", f"{name}-static") for line in kept]
        if kept != lines:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.writelines(kept)
            return True
        return False

    @staticmethod
    def _strip_shared_target(path, name):
        """从一份 CMake 导出文件里移除 <name>-shared 目标及其 import check 项。"""
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        original = text
        text = re.sub(rf"(\bIN ITEMS\s+{re.escape(name)}-static)\s+{re.escape(name)}-shared\)",
                      r"\1)", text)
        text = re.sub(
            rf'# Create imported target {re.escape(name)}-shared\n.*?\n\)\n',
            "", text, flags=re.S)
        text = re.sub(
            rf'# Import target "{re.escape(name)}-shared".*?list\(APPEND _cmake_import_check_files_for_{re.escape(name)}-shared[^\n]*\n',
            "", text, flags=re.S)
        if text != original:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            return True
        return False

    def build(self):
        apply_conandata_patches(self)
        # 先构建 vendored libbpp-phyl（源码 vendor，见 _build_bundled_bpp_phyl），
        # 再构建本包。phyl-omics 的 find_package(bpp-phyl 12.0.0 REQUIRED) 在
        # configure 时经 CMAKE_PREFIX_PATH 找到 venored 前缀。
        self._build_bundled_bpp_phyl()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游无自动化测试：对真实源码树做测试审计，作为 HMBS 门禁的机器证据。
        # no_tests 标记本身由 test_package 阶段产生（对齐 aribb24/osmctools 先例）。
        self._audit_upstream_tests()

    def _cmake_bin(self):
        """解析 cmake 可执行文件（同族 libbpp-seq 做法）。

        裸 subprocess.run() 不继承 Conan 聚合的 buildenv（conanbuild.sh）；优先
        HMBS conf / HMBS env / PATH，再回退 HNP 工具目录。
        """
        try:
            conf_path = self.conf.get("user.hmbs:cmake_path", default=None, check_type=str)
        except Exception:                                            # noqa: BLE001
            conf_path = None
        for cand in (conf_path, os.environ.get("HMBS_CMAKE"), os.environ.get("CMAKE")):
            if cand and os.path.isfile(cand):
                return cand
        found = shutil.which("cmake")
        if found:
            return found
        for cand in (
            "/data/service/hnp/bin/cmake",
            "/storage/Users/currentUser/usr/local/bin/cmake",
            "/usr/local/bin/cmake",
            "/usr/bin/cmake",
        ):
            if os.path.isfile(cand):
                return cand
        self.output.warning("cmake not found via conf/env/PATH/HNP fallbacks; trying bare 'cmake'")
        return "cmake"

    def _build_bundled_bpp_phyl(self):
        """Configure/build/install vendored libbpp-phyl 2.4.1 进私有前缀。

        沿用同族先例 libbpp-seq/_build_bundled_bpp_core 的构建骨架。libbpp-phyl
        的 CMake 里 `find_package(bpp-seq 12.0.0 REQUIRED)`，其 bpp-seq/bpp-core
        config 来自已发布的 libbpp-seq/2.4.1 的 shim（见 generate() 收集的
        self._shim_dirs）；对 vendored 前缀单独 configure，注入这两个 _DIR 与
        CMAKE_PREFIX_PATH。
        """
        phyl_src = os.path.join(self.source_folder, "bpp-phyl-src")
        phyl_build = os.path.join(self.build_folder, "bpp-phyl-build")
        phyl_prefix = os.path.join(self.build_folder, "bpp-phyl-prefix")
        if not os.path.isdir(phyl_src):
            raise RuntimeError("vendored libbpp-phyl sources missing: %s" % phyl_src)
        os.makedirs(phyl_build, exist_ok=True)
        os.makedirs(phyl_prefix, exist_ok=True)
        candidates = [
            os.path.join(self.generators_folder, "conan_toolchain.cmake"),
            os.path.join(self.build_folder, "conan_toolchain.cmake"),
            os.path.join(self.build_folder, "build", "conan_toolchain.cmake"),
        ]
        toolchain = next((p for p in candidates if os.path.isfile(p)), candidates[0])
        cmake_bin = self._cmake_bin()
        self.output.info("vendored bpp-phyl cmake binary: %s" % cmake_bin)
        self.output.info("vendored bpp-phyl toolchain: %s" % toolchain)
        build_type = str(self.settings.build_type)
        pic = bool(self.options.shared) or bool(self.options.get_safe("fPIC", True))
        # bpp-seq / bpp-core 的 config 来自 libbpp-seq shim（bpp-core 合并其中）。
        seq_dir = self._shim_dirs.get("bpp-seq")
        core_dir = self._shim_dirs.get("bpp-core")
        configure_cmd = [
            cmake_bin,
            "-S", phyl_src,
            "-B", phyl_build,
            "-DCMAKE_TOOLCHAIN_FILE=" + toolchain,
            "-DCMAKE_INSTALL_PREFIX=" + phyl_prefix,
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_INSTALL_RPATH=$ORIGIN",
            "-DBUILD_TESTING=OFF",
            "-DCMAKE_BUILD_TYPE=" + build_type,
            "-DCMAKE_POSITION_INDEPENDENT_CODE=" + ("ON" if pic else "OFF"),
        ]
        if seq_dir:
            configure_cmd.append("-Dbpp-seq_DIR=" + seq_dir)
        if core_dir:
            configure_cmd.append("-Dbpp-core_DIR=" + core_dir)
        self.output.info("vendored bpp-phyl configure: " + " ".join(configure_cmd))
        proc = subprocess.run(
            configure_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )
        self.output.info((proc.stdout or "")[-3000:])
        if proc.returncode != 0:
            raise RuntimeError("vendored bpp-phyl configure failed")
        build_cmd = [cmake_bin, "--build", phyl_build, "--parallel", "1"]
        self.output.info("vendored bpp-phyl build: " + " ".join(build_cmd))
        proc = subprocess.run(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=2400,
        )
        self.output.info((proc.stdout or "")[-3000:])
        if proc.returncode != 0:
            raise RuntimeError("vendored bpp-phyl build failed")
        install_cmd = [cmake_bin, "--install", phyl_build]
        self.output.info("vendored bpp-phyl install: " + " ".join(install_cmd))
        proc = subprocess.run(
            install_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )
        self.output.info((proc.stdout or "")[-2000:])
        if proc.returncode != 0:
            raise RuntimeError("vendored bpp-phyl install failed")
        # Sanity: phyl-omics 的 find_package(bpp-phyl) 需要的 config 必须存在。
        cfg = os.path.join(phyl_prefix, "lib", "cmake", "bpp-phyl", "bpp-phyl-config.cmake")
        cfg_alt = os.path.join(phyl_prefix, "lib64", "cmake", "bpp-phyl", "bpp-phyl-config.cmake")
        if not (os.path.isfile(cfg) or os.path.isfile(cfg_alt)):
            self.output.warning("vendored bpp-phyl config not found at %s" % cfg)
        return phyl_prefix

    def _audit_upstream_tests(self):
        """在本配方所构建的真实源码树上 grep 测试目标（机器证据）。"""
        src = self.source_folder
        audit_cmd = (
            "grep -rInE 'enable_testing|add_test|BUILD_TESTING|ctest|"
            "check_PROGRAMS|check-local' \"%s\" 2>/dev/null || true"
            % os.path.join(src, "CMakeLists.txt")
        )
        self.output.info("[audit] phyl-omics upstream test audit:")
        self.run(audit_cmd)

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 保留 vendored libbpp-phyl 的许可证。
        phyl_src = os.path.join(self.source_folder, "bpp-phyl-src")
        if os.path.isdir(phyl_src):
            copy(self, "COPYING*", src=phyl_src,
                 dst=os.path.join(self.package_folder, "licenses"))
            copy(self, "LICENSE*", src=phyl_src,
                 dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # 把 vendored libbpp-phyl 的安装（库/头/CMake 配置）合并进本包，
        # 这样消费者 find_package(bpp-phyl) 与链接 bpp-phyl 都能工作（对齐
        # libbpp-seq 把 vendored bpp-core 合并进自身包的先例）。
        phyl_prefix = os.path.join(self.build_folder, "bpp-phyl-prefix")
        if os.path.isdir(phyl_prefix):
            copy(self, "*", src=phyl_prefix, dst=self.package_folder)
        # 上游总是同时装 static 与 shared；按 shared 选项裁掉消费者用不到的一套，
        # 避免下游误链到在 OHOS 上加载失败的 shared 产物（vendored bpp-phyl 同样处理）。
        self._prune_unrequested_variant()

    def _prune_unrequested_variant(self):
        import glob
        patterns = (("*.so", "*.so.*"),) if not self.options.shared else (("*.a",),)
        for libdir in (os.path.join(self.package_folder, "lib"),
                       os.path.join(self.package_folder, "lib64")):
            if not os.path.isdir(libdir):
                continue
            for group in patterns:
                for pattern in group:
                    for victim in glob.glob(os.path.join(libdir, pattern)):
                        try:
                            os.remove(victim)
                            self.output.info(
                                f"package: pruned {os.path.basename(victim)}")
                        except OSError as error:
                            self.output.warning(f"package: cannot prune {victim} ({error})")

    def package_info(self):
        # vendored libbpp-phyl 的静态归档合并进本包，故与本库一并列出（链接顺序：
        # bpp-phyl-omics 先、其依赖 bpp-phyl 次之）。
        self.cpp_info.libs = ["bpp-phyl-omics", "bpp-phyl"]
        # 保留上游 bpp-phyl-omics-config.cmake 的查找语义，故 Conan 侧用 libbpp-phyl-omics 名。
        self.cpp_info.set_property("cmake_file_name", "libbpp-phyl-omics")
        self.cpp_info.set_property("cmake_target_name", "libbpp-phyl-omics::libbpp-phyl-omics")
        self.cpp_info.set_property("pkg_config_name", "libbpp-phyl-omics")
        # 消费者最终链接需要完整依赖闭合（Conan 依赖：seq-omics / seq / core）；
        # vendored bpp-phyl 已并入本包 libs，不再是独立的 Conan 依赖，不进 requires。
        self.cpp_info.requires = [
            "libbpp-seq-omics::libbpp-seq-omics",
            "libbpp-seq::libbpp-seq",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
