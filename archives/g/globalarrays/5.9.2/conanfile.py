import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class GlobalArraysConan(ConanFile):
    name = "globalarrays"
    version = "5.9.2"
    description = (
        "Partitioned Global Address Space (PGAS) library for distributed arrays "
        "(Global Arrays Toolkit)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/GlobalArrays/ga"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    # 第二轮评审建议：适配 MPI 依赖（ohpcd 有 mpich/5.0.1 OHOS 二进制），
    # 替换原单进程 mpi_shim 降级方案，多进程/PGAS 能力真实可用。
    requires = "mpich/5.0.1"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "globalarrays currently supports only OHOS armv8"
            )

        # R33：CC/CXX 从 conf tools.build:compiler_executables 解析（profile 注入），
        # 次选 VirtualBuildEnv 的 os.environ，都无则抛 ConanException（不硬编码 fallback）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or os.environ.get("CC")
        cxx = compilers.get("cpp") or os.environ.get("CXX")
        if not cc or not cxx:
            raise ConanException(
                "CC/CXX must be provided via tools.build:compiler_executables "
                "conf or environment (R33)"
            )
        prefix = self.package_folder.replace("\\", "/")
        src = self.source_folder.replace("\\", "/")
        # 三态推导：config.guess 无法识别 HarmonyOS(uname)，必须显式 --build/--host。
        triplet = "aarch64-unknown-linux-ohos"

        # HMDFS 模式：mkdtemp 独立构建目录 + /bin/sh 脚本 + CONFIG_SHELL=/bin/sh。
        parent = tempfile.mkdtemp(prefix="ga-", dir=os.environ.get("TMPDIR") or self.build_folder)
        build_dir = os.path.join(parent, "src")
        shutil.copytree(self.source_folder, build_dir, symlinks=True)

        script = os.path.join(parent, "build.sh")
        # mpich 为 shared 库：configure 交叉编译检测（编译后运行小程序）需要
        # LD_LIBRARY_PATH 指向 mpich 的 lib，否则报 cannot run C compiled programs。
        mpich_lib = os.path.join(self.dependencies["mpich"].package_folder, "lib")
        lines = [
            "#!/bin/sh",
            "set -e",
            f'cd "{build_dir}"',
            f'export CC="{cc}"',
            f'export CXX="{cxx}"',
            'export CONFIG_SHELL="/bin/sh"',
            'export SHELL="/bin/sh"',
            f'export PATH="{os.path.dirname(cc)}:$PATH"',
            f'export LD_LIBRARY_PATH="{mpich_lib}:$LD_LIBRARY_PATH"',
            # --with-mpi：使用 mpich 依赖（mpicc 由 mpich 提供，conan 依赖环境注入 PATH）；
            # --disable-shared：纯静态产物，规避 libtool relink 破坏 ELF 签名；
            # --disable-openmp：避免 OpenMP 运行时依赖。
            f'./configure --prefix="{prefix}" '
            f'--build={triplet} --host={triplet} '
            "--with-mpi "
            "--disable-shared --enable-static --disable-openmp",
            "make -j1",
        ]
        with open(script, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(script, 0o755)
        self.run(f'"{script}"', env="conanbuild")

        # 把产物 staging 到 build_folder/stage（package() 从 stage 复制，
        # 不依赖 mkdtemp 临时路径）。
        stage = os.path.join(self.build_folder, "stage")
        stage_lib = os.path.join(stage, "lib")
        stage_inc = os.path.join(stage, "include")
        os.makedirs(stage_lib, exist_ok=True)
        os.makedirs(stage_inc, exist_ok=True)
        lib_dirs = ("global", "armci", "comex", "tcgmsg", "ma", "pario", "cmx")
        copied_libs = 0
        # libtool 把归档放在 .libs/ 子目录（如 .libs/libga.a），需递归扫描。
        scan_dirs = [build_dir, os.path.join(build_dir, ".libs")]
        for sub in lib_dirs:
            scan_dirs.append(os.path.join(build_dir, sub))
            scan_dirs.append(os.path.join(build_dir, sub, ".libs"))
        for cand in scan_dirs:
            if not os.path.isdir(cand):
                continue
            for name in sorted(os.listdir(cand)):
                p = os.path.join(cand, name)
                if name.endswith(".a") and os.path.isfile(p):
                    shutil.copy2(p, os.path.join(stage_lib, name))
                    copied_libs += 1
        if copied_libs == 0:
            raise ConanException("no static libraries found in build output")
        # 公共头文件：global/src/*.h（ga.h/global.h）+ ma/*.h + gaf2c/typesf2c.h。
        for h_dir in (os.path.join(build_dir, "global", "src"),
                      os.path.join(build_dir, "ma"),
                      os.path.join(build_dir, "gaf2c")):
            if not os.path.isdir(h_dir):
                continue
            for name in sorted(os.listdir(h_dir)):
                p = os.path.join(h_dir, name)
                if name.endswith(".h") and os.path.isfile(p):
                    shutil.copy2(p, os.path.join(stage_inc, name))

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        for name in sorted(os.listdir(os.path.join(stage, "lib"))):
            shutil.copy2(
                os.path.join(stage, "lib", name), os.path.join(lib_dir, name)
            )
        for name in sorted(os.listdir(os.path.join(stage, "include"))):
            shutil.copy2(
                os.path.join(stage, "include", name), os.path.join(inc_dir, name)
            )

    def package_info(self):
        # GA 构建产物：libga.a（内含 ma/pario/tcgmsg/comex/cmx 对象）+ libarmci.a。
        # MPI 由 mpich 依赖提供：cpp_info.requires 用 Conan 2 格式 "包名::组件名"
        # 引用外部包（mpich 无命名 components，default 组件名即包名 mpich；
        # CMakeDeps 侧自动映射到其 cmake_target_name MPI::MPI_C）。
        self.cpp_info.libs = ["ga", "armci"]
        self.cpp_info.requires = ["mpich::mpich"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
