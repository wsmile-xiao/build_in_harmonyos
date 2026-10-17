#!/usr/bin/env python3
"""Conan recipe for aegean 0.16.0 — AEGeAn Toolkit (genome annotation analysis).

AEGeAn 是 C 工具集（parseval/locuspocus/gaeval 等）+ libaegean.a，Makefile 构建。
硬依赖 GenomeTools 库（genometools 1.6.5，src 里 #include "genometools.h"、
Makefile 链接 -lgenometools）——项目未单独适配 genometools，故配方内自包含
构建 genometools（静态库 .a + 头文件组装到 <prefix>/include/genometools/）。
cairo=no 禁用 AnnotationSketch（可选依赖，减依赖面）；
errorcheck=no 兼容 clang C2x 对旧式函数声明（无原型）的弃用警告。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AegeanConan(ConanFile):
    name = "aegean"
    version = "0.16.0"
    description = "AEGeAn Toolkit: analysis and evaluation of genome annotations"
    license = "ISC"
    homepage = "https://github.com/BrendelGroup/AEGeAn"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)
        # aegean 构建 in-source（Makefile 直接在源码目录生成 obj/bin）
        self.folders.build = "."

    def source(self):
        # aegean 源码（URL 无 .tar.gz 扩展名，需 filename 指定以便 conan 正确解压）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="aegean-0.16.0.tar.gz")
        # genometools 源码（自包含依赖，构建期使用）
        get(self, **self.conan_data["genometools"], strip_root=True,
            destination="genometools", filename="genometools-1.6.5.tar.gz")

    def _build_genometools(self, cc):
        """构建 genometools 静态库并组装头文件到 gt_prefix。"""
        gt_src = os.path.join(self.source_folder, "genometools")
        gt_prefix = os.path.join(self.build_folder, "gt-install")
        os.makedirs(os.path.join(gt_prefix, "lib"), exist_ok=True)
        os.makedirs(os.path.join(gt_prefix, "include", "genometools"), exist_ok=True)
        # 构建静态库（避开 libgenometools.so 的 expat 符号冲突，aegean 用 .a 即可）
        self.run(f"make CC={cc} cairo=no opt=no -C {gt_src} lib/libgenometools.a")
        # 组装头文件到 <prefix>/include/genometools/（aegean INCS 期望该结构）
        src_inc = os.path.join(gt_prefix, "include", "genometools")
        copy(self, "genometools.h", src=gt_src + "/src", dst=src_inc)
        copy(self, "gtr.h", src=gt_src + "/src", dst=src_inc)
        copy(self, "gtt.h", src=gt_src + "/src", dst=src_inc)
        copy(self, "gt_config.h", src=gt_src + "/obj", dst=src_inc)
        for sub in ("core", "extended", "annotationsketch", "ltr", "match",
                    "gtlua", "mgth", "tools", "examples", "external"):
            sub_src = os.path.join(gt_src, "src", sub)
            if os.path.isdir(sub_src):
                dst_sub = os.path.join(src_inc, sub)
                os.makedirs(dst_sub, exist_ok=True)
                for h in os.listdir(sub_src):
                    if h.endswith("_api.h"):
                        copy(self, h, src=sub_src, dst=dst_sub)
        # 静态库
        copy(self, "libgenometools.a", src=gt_src + "/lib",
             dst=os.path.join(gt_prefix, "lib"))
        return gt_prefix

    def build(self):
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # aegean 的 data/scripts/*.py（version.py/align-convert.py）shebang 为
        # #!/usr/bin/env python，OHOS 仅有 python3——建 python -> python3 链接并
        # 加入 PATH，供 make test 阶段的 align-convert.py 使用
        bin_link = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_link, exist_ok=True)
        python3_path = shutil.which("python3") or "/storage/Users/currentUser/usr/local/bin/python3"
        python_link = os.path.join(bin_link, "python")
        if not os.path.exists(python_link):
            os.symlink(python3_path, python_link)
        env = ["PATH=" + bin_link + os.pathsep + os.environ.get("PATH", "")]
        # 1) 自包含构建 genometools 依赖
        gt_prefix = self._build_genometools(cc)
        # 2) 预生成 inc/core/AgnVersion.h（version.py shebang 为 #!/usr/bin/env python，
        #    OHOS 无 python 命令；Makefile 的 AgnVersion.h 无依赖目标，文件已存在则跳过
        #    生成，故此处用 python3 手动生成一次即可）
        py = python3_path
        self.run(f'{py} data/scripts/version.py > inc/core/AgnVersion.h')
        # 3) 构建 aegean（prefix 指向 gt-install 供 INCS/LDFLAGS 查找 genometools）
        #    errorcheck=no：aegean 旧代码无原型函数声明，clang C2x -Werror 弃用警告会失败
        self.run(f"make CC={cc} cairo=no errorcheck=no prefix={gt_prefix}")
        # 4) 跑上游测试（make test = agn-test：unittests + 各工具功能测试 + 9 个 shell 脚本）
        #    align-convert.sh 调 data/scripts/align-convert.py（shebang #!/usr/bin/env python），
        #    命令内联 export PATH 确保 env python 能找到 bin_link/python（conanbuild.sh 会
        #    重置 PATH，self.run 的 env 参数不生效，故用内联 export）
        self.run(f"export PATH={bin_link}:$PATH; "
                 f"make CC={cc} cairo=no errorcheck=no prefix={gt_prefix} test")

    def package(self):
        # 打包 aegean 工具 + 静态库 + 头文件 + share 数据
        bin_dir = os.path.join(self.build_folder, "bin")
        for exe in ("parseval", "canon-gff3", "locuspocus", "gaeval",
                    "xtractore", "pmrna", "tidygff3"):
            src = os.path.join(bin_dir, exe)
            if os.path.exists(src):
                copy(self, exe, src=bin_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libaegean.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.build_folder, "inc", "core"),
             dst=os.path.join(self.package_folder, "include", "aegean"))
        if os.path.isdir(os.path.join(self.build_folder, "data", "share")):
            copy(self, "*", src=os.path.join(self.build_folder, "data", "share"),
                 dst=os.path.join(self.package_folder, "share", "aegean"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["aegean"]
