#!/usr/bin/env python3
"""Conan recipe — bart-view 0.3.00 (Makefile, GTK3 image viewer for BART).

bart-view (mrirecon/view) 是 BART（Berkeley Advanced Reconstruction Toolbox，
MRI 重建工具箱）的配套图像查看器，构建两个可执行文件：
  - view    : GTK3 多维图像查看器
  - cfl2png : CFL(.hdr/.cfl) → PNG 导出工具

上游用裸 Makefile 构建，链接 GTK3（pkg-config gtk+-3.0）与 BART 工具箱
静态库（libmisc.a / libgeom.a / libnum.a，经 BART_TOOLBOX_PATH 定位）。

OHOS 适配要点:
- BART 工具箱未以 Conan 包发布（制品仓 bart/1.0.00 仅含 bin/bart，不导出
  头文件与静态库）→ 按仓库 vendored 先例，构建期下载 BART v1.0.00 官方源码
  并就地构建 bart-view 所需的三 个静态库（misc / geom / num）；
- BART 源码的 clang 兼容修复（label-at-end、case 后声明补块作用域、
  opts.c/mmio.c 精确块）与 bart/1.0.00 recipe 一致；BART 1.0.00 删除了
  misc.h 的 UNUSED 宏（0.9.00 及以前存在），bart-view 依赖该宏 →
  构建期在 vendored BART 的 misc.h 中恢复；
- BART 头文件（misc/nested.h）用 clang blocks 实现嵌套函数，需 -fblocks，
  而鸿蒙无 libBlocksRuntime → 复用 bart/1.0.00 的最小 stub 提供 _Block_* 符号；
- cfl2png.c 使用 rindex()（musl 未声明）→ 改为等价的 strrchr()。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

BART_DIR = "bart-toolbox"
BART_LIBS = ["lib/libmisc.a", "lib/libgeom.a", "lib/libnum.a"]


class BartViewConan(ConanFile):
    name = "bart-view"
    version = "0.3.00"
    description = "bart-view - GTK3 image viewer for BART multi-dimensional data"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mrirecon/view"
    url = "https://github.com/mrirecon/view"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bart-view does not support os={self.settings.os}")

    def export_sources(self):
        # compat/（blocks_runtime_stub.c）随配方传递——鸿蒙无 libBlocksRuntime，
        # BART 头文件用 clang blocks，链接需其符号
        copy(self, "compat/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # GTK3: pkg-config gtk+-3.0（含 cairo/pango/gdk-pixbuf/atk/glib 链）
        self.requires("gtk/3.24.43")
        # view/cfl2png 的 PNG 导出经 BART misc/png.c → 链接 libpng16
        self.requires("libpng/1.6.58")
        # BART num/ 的 fftw3 单精度接口（libfftw3f）
        self.requires("fftw3f/3.3.9")
        # BART num/blas.c、num/lapack.c 的 cblas / lapacke 符号
        self.requires("openblas/0.3.33")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        bart = self.conan_data["vendored"]["bart"]
        get(self, url=bart["url"], sha256=bart["sha256"], strip_root=True,
            destination=os.path.join(self.source_folder, BART_DIR))

    def generate(self):
        # gtk+-3.0.pc 等由 PkgConfigDeps 生成；显式把生成目录注入
        # PKG_CONFIG_PATH（PkgConfigDeps 不自动设置该变量），供 bart-view
        # Makefile 的 `pkg-config --cflags/--libs gtk+-3.0` 使用。
        PkgConfigDeps(self).generate()
        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("conanbuild_pkgconfig")

    def _cc(self):
        # R33: 编译器一律从 Conan conf 获取，不依赖 shell 环境变量
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return ccs.get("c") or "clang"

    def _bart_dir(self):
        return os.path.join(self.source_folder, BART_DIR)

    def _patch_shebang(self, root):
        # 鸿蒙无 /bin/bash（bash 在 /data/service/hnp/bin）——BART 的 .sh
        # 脚本 shebang 为绝对路径 #!/bin/bash，直接执行报 No such file。
        # 这些脚本 sh 兼容，统一改为 #!/bin/sh。
        patched = 0
        for base, _, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith(".sh"):
                    continue
                path = os.path.join(base, fname)
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                if content.startswith("#!/bin/bash"):
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write("#!/bin/sh" + content[len("#!/bin/bash"):])
                    patched += 1
        self.output.info(f"patched {patched} BART .sh shebang -> #!/bin/sh")

    def _patch_bart_build_files(self, bart):
        # Makefile：gcc --version 硬编码（鸿蒙无 gcc）→ $(CC) --version
        makefile = os.path.join(bart, "Makefile")
        with open(makefile, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "shell gcc --version" in content:
            content = content.replace(
                "shell gcc --version", "shell $(CC) --version")
            self.output.info("patched BART Makefile: gcc --version -> $(CC) --version")
        # ld.lld 不识别 -no-warn-execstack；鸿蒙无 libBlocksRuntime 且静态库
        # 构建不链接——移除这两条 LDFLAGS
        content = content.replace("LDFLAGS += -Wl,-no-warn-execstack\n", "")
        content = content.replace("LDFLAGS += -lBlocksRuntime\n", "")
        with open(makefile, "w", encoding="utf-8") as handle:
            handle.write(content)
        # ar_lock.sh：鸿蒙 flock 不支持 -c → 构建用 -j1 串行，直接调 ar
        arlock = os.path.join(bart, "ar_lock.sh")
        with open(arlock, "r", encoding="utf-8") as handle:
            content = handle.read()
        old = "flock ${LOCKDIR}/.`basename $2`.lock -c \"ar $*\""
        if old in content:
            content = content.replace(old, "ar $*")
            with open(arlock, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info("patched BART ar_lock.sh: flock -> direct ar")

    def _patch_bart_unused_macro(self, bart):
        # BART 1.0.00 删除了 misc/misc.h 的 UNUSED 宏（v0.9.00 及以前存在），
        # 而 bart-view 的 view.c/draw.c 依赖它（上游 README 要求 BART >= 0.8.00）。
        # 恢复该宏，使 bart-view 与 vendored BART 1.0.00 头文件兼容。
        misc_h = os.path.join(bart, "src", "misc", "misc.h")
        with open(misc_h, "r", encoding="utf-8") as handle:
            content = handle.read()
        anchor = ("#define MIN(x, y) ({ __typeof(x) __x = (x); "
                  "__typeof(y) __y = (y); (__x < __y) ? __x : __y; })")
        if "UNUSED(x)" not in content and anchor in content:
            content = content.replace(
                anchor, "#define UNUSED(x) (void)(x)\n\n" + anchor, 1)
            with open(misc_h, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info("patched BART misc.h: restored UNUSED macro")

    def _patch_bart_sources(self, bart):
        # clang 15 相比 GCC 更严格（GCC 宽松接受），以下为随 bart/1.0.00
        # recipe 一致的适配修复，仅触及 BART 源码，不涉及 bart-view 源码。
        src_dir = os.path.join(bart, "src")

        # 1) label at end of compound statement：`default:` / `case X:` / goto
        #    标签后（可含空行）直接 } 无语句 → 补空语句 ;
        # 2) case 后带初始化器声明需块作用域 → 给 case 标签加 { 并在分支末尾补 }
        src_files = []
        for base, _, filenames in os.walk(src_dir):
            for fname in filenames:
                if fname.endswith(".c"):
                    src_files.append(os.path.join(base, fname))

        label_fixed = 0
        for path in src_files:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            orig = content
            content = re.sub(
                r"(default:|case [A-Za-z0-9_]+:|[A-Za-z_][A-Za-z0-9_]*:)"
                r"((?:\n[ \t]*)+[ \t]*\})",
                r"\1\n\t\t\t;\2", content)
            if content != orig:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                label_fixed += 1
        if label_fixed:
            self.output.info(f"patched {label_fixed} BART src/**/*.c label-at-end")

        decl_re = re.compile(
            r"^[ \t]+(?:(?:static |const |volatile |register |extern )?"
            r"(?:struct|const|int|long|float|double|char|unsigned|complex|bool"
            r"|size_t|ssize_t|auto|__auto_type)"
            r"(?:\s+(?:long|int|short|char|float|double|struct))?)\s+"
            r"[A-Za-z_][A-Za-z0-9_]*(\[[^\]]*\])?\s*(?:=|;|\()")
        case_fixed = 0
        for path in src_files:
            # simulation.c 多个同名 case 分支（fall-through），通用修复易误伤
            # ——bart-view 仅需 misc/geom/num，不编译 src/simu，直接跳过
            if path.endswith(os.path.join("simu", "simulation.c")):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            changed = False
            idx = 0
            while idx < len(lines):
                match = re.match(r"^([ \t]+)case ([^:]+):\n$", lines[idx])
                if match and "case " + match.group(2).strip() + ": {" not in lines[idx]:
                    look = idx + 1
                    while look < len(lines) and (
                        lines[look].strip() == ""
                        or lines[look].lstrip().startswith("//")
                    ):
                        look += 1
                    if look < len(lines) and decl_re.match(lines[look]):
                        lines[idx] = lines[idx].rstrip("\n") + " {\n"
                        scan = idx + 1
                        last_break = None
                        while scan < len(lines):
                            if re.match(r"^\t+case |^\t+default:", lines[scan]):
                                break
                            if lines[scan].rstrip().endswith("break;"):
                                last_break = scan
                            scan += 1
                        if last_break is not None:
                            indent = re.match(
                                r"^([ \t]+)", lines[last_break]).group(1)
                            lines.insert(last_break + 1, indent + "}\n")
                            changed = True
                        elif scan < len(lines):
                            lines.insert(scan, "\t}\n")
                            changed = True
                        idx = look
                idx += 1
            if changed:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.writelines(lines)
                case_fixed += 1
        if case_fixed:
            self.output.info(f"patched {case_fixed} BART src/**/*.c case-decl scopes")

        # 3) opts.c：外层 switch 三组 case 的声明补块 + [[fallthrough]]（C23
        #    属性，gnu17 不识别）改为注释；内层 switch 的 OPT_*_VECN 声明补块，
        #    并为被块作用域隔离的 count 补声明
        opts_c = os.path.join(src_dir, "misc", "opts.c")
        with open(opts_c, "r", encoding="utf-8") as handle:
            opts = handle.read()
        orig = opts
        opts = opts.replace(
            "\t\tcase OPT_VEC2:\n\t\tcase OPT_VEC3:\n\t\tcase OPT_VECN:"
            "\n\n\t\t\tlong (*vn)[];",
            "\t\tcase OPT_VEC2:\n\t\tcase OPT_VEC3:\n\t\tcase OPT_VECN: {"
            "\n\n\t\t\tlong (*vn)[];")
        opts = opts.replace(
            "\t\t\tbreak;\n\n\t\tcase OPT_FLOAT_VEC2:",
            "\t\t\tbreak;\n\t\t}\n\n\t\tcase OPT_FLOAT_VEC2:")
        opts = opts.replace(
            "\t\tcase OPT_FLOAT_VEC2:\n\t\tcase OPT_FLOAT_VEC3:"
            "\n\t\tcase OPT_FLOAT_VEC4:\n\t\tcase OPT_FLOAT_VECN:"
            "\n\n\t\t\tfloat (*fvn)[];",
            "\t\tcase OPT_FLOAT_VEC2:\n\t\tcase OPT_FLOAT_VEC3:"
            "\n\t\tcase OPT_FLOAT_VEC4:\n\t\tcase OPT_FLOAT_VECN: {"
            "\n\n\t\t\tfloat (*fvn)[];")
        opts = opts.replace(
            "\t\t\tbreak;\n\n\t\tcase OPT_DOUBLE_VEC3:",
            "\t\t\tbreak;\n\t\t}\n\n\t\tcase OPT_DOUBLE_VEC3:")
        opts = opts.replace(
            "\t\tcase OPT_DOUBLE_VEC3:\n\t\tcase OPT_DOUBLE_VECN:"
            "\n\n\t\t\tdouble (*dvn)[];",
            "\t\tcase OPT_DOUBLE_VEC3:\n\t\tcase OPT_DOUBLE_VECN: {"
            "\n\n\t\t\tdouble (*dvn)[];")
        opts = opts.replace(
            "\t\t\tbreak;\n\n\n\t\tcase OPT_STRING:",
            "\t\t\tbreak;\n\t\t}\n\n\n\t\tcase OPT_STRING:")
        opts = opts.replace("\t\t\t[[fallthrough]];", "\t\t\t/* fallthrough */;")
        for tag in ("OPT_VECN", "OPT_FLOAT_VECN", "OPT_DOUBLE_VECN"):
            opts = opts.replace(
                f"\t\t\tcase {tag}:\n\n\t\t\t\tstruct opt_vec_s *ovn = opts[i].ptr;",
                f"\t\t\tcase {tag}: {{\n\n\t\t\t\tstruct opt_vec_s *ovn = opts[i].ptr;")
        opts = opts.replace(
            "\t\t\t\tcount = *ovn->count;\n\t\t\t\tbreak;\n\n\t\t\tdefault:",
            "\t\t\t\tcount = *ovn->count;\n\t\t\t\tbreak;\n\t\t\t}\n\n\t\t\tdefault:")
        opts = opts.replace(
            "\t\t\tfloat (*fvn)[];\n\t\t\tcount = 2;",
            "\t\t\tfloat (*fvn)[];\n\t\t\tint count;\n\t\t\tcount = 2;")
        opts = opts.replace(
            "\t\t\tdouble (*dvn)[];\n\t\t\tcount = 3;",
            "\t\t\tdouble (*dvn)[];\n\t\t\tint count;\n\t\t\tcount = 3;")
        if opts != orig:
            with open(opts_c, "w", encoding="utf-8") as handle:
                handle.write(opts)
            self.output.info("patched BART misc/opts.c: block scopes + fallthrough")
        else:
            self.output.info("WARN: BART misc/opts.c patch patterns not found")

        # 4) mmio.c：case FILE_TYPE_CFL 后的 char name_bdy[1024] 声明补块作用域
        mmio_c = os.path.join(src_dir, "misc", "mmio.c")
        with open(mmio_c, "r", encoding="utf-8") as handle:
            mmio = handle.read()
        orig = mmio
        mmio = mmio.replace(
            "\t\tcase FILE_TYPE_CFL:\n\n\t\t\tchar name_bdy[1024];",
            "\t\tcase FILE_TYPE_CFL: {\n\n\t\t\tchar name_bdy[1024];")
        mmio = mmio.replace(
            "\t\t\taddr = (priv ? private_cfl : shared_cfl)"
            "(D, dimensions, name_bdy);\n\t\t}",
            "\t\t\taddr = (priv ? private_cfl : shared_cfl)"
            "(D, dimensions, name_bdy);\n\t\t}\n\t\t}")
        if mmio != orig:
            with open(mmio_c, "w", encoding="utf-8") as handle:
                handle.write(mmio)
            self.output.info("patched BART misc/mmio.c: FILE_TYPE_CFL block scope")
        else:
            self.output.info("WARN: BART misc/mmio.c patch patterns not found")

    def _build_bart_toolbox(self, cc):
        bart = self._bart_dir()
        fftw_inc = os.path.join(self.dependencies["fftw3f"].package_folder, "include")
        blas_inc = os.path.join(self.dependencies["openblas"].package_folder, "include")
        png_inc = os.path.join(self.dependencies["libpng"].package_folder, "include")
        zlib_folder = self.dependencies["zlib"].package_folder
        # BART Makefile 用 FFTW_BASE / BLAS_BASE 定位 FFTW3 单精度与 cblas/lapacke
        fftw_base = self.dependencies["fftw3f"].package_folder
        blas_base = self.dependencies["openblas"].package_folder
        os.environ["CFLAGS"] = "-O2 -ffp-contract=off"
        os.environ["CPPFLAGS"] = (
            f"-Wall -Wextra -I{fftw_inc} -I{blas_inc} "
            f"-I{png_inc} -I{os.path.join(zlib_folder, 'include')}")
        self.run(
            f"make -j1 SHELL=/bin/sh CC={cc} "
            f"FFTW_BASE={fftw_base} BLAS_BASE={blas_base} "
            "PNG=1 FFTWTHREADS=0 CUDA=0 DEBUG_DWARF=0 WERROR=0 " + " ".join(BART_LIBS),
            cwd=bart, env="conanbuild")
        for lib in BART_LIBS:
            if not os.path.exists(os.path.join(bart, lib)):
                raise ConanInvalidConfiguration(f"BART {lib} was not built")

    def _patch_bart_view_sources(self):
        # cfl2png.c 用 rindex()（BSD 遗留，musl 未在 strings.h 声明）→ 等价
        # 的 strrchr()（C 标准库，string.h 已包含）。
        cfl2png = os.path.join(self.source_folder, "src", "cfl2png.c")
        with open(cfl2png, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "rindex(out_prefix" in content:
            content = content.replace(
                "rindex(out_prefix", "strrchr(out_prefix")
            with open(cfl2png, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info("patched bart-view src/cfl2png.c: rindex -> strrchr")

    def _blocks_stub(self, cc):
        # 宏 blocks：BART misc/nested.h 用 clang blocks 实现嵌套函数，编译器
        # 需 -fblocks，链接需 libBlocksRuntime 符号；鸿蒙无该库 → 提供最小
        # stub（blocks 均为栈上立即调用，不跨作用域复制）。
        stub_src = os.path.join(self.source_folder, "compat", "blocks_runtime_stub.c")
        stub_obj = os.path.join(self.build_folder, "blocks_runtime_stub.o")
        self.run(f"{cc} -c {stub_src} -o {stub_obj}", cwd=self.source_folder)
        return stub_obj

    def _build_bart_view(self, cc):
        fftw = self.dependencies["fftw3f"].package_folder
        blas = self.dependencies["openblas"].package_folder
        png = self.dependencies["libpng"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        stub = self._blocks_stub(cc)
        # 命令行变量覆盖 Makefile：避免其追加 -lBlocksRuntime（鸿蒙无）与
        # 硬编码 -lpng（conan libpng 提供 libpng16）；GTK 的 cflags/libs 仍由
        # Makefile 内的 `pkg-config gtk+-3.0` 提供（PKG_CONFIG_PATH 见 generate）。
        cflags = "-O2 -std=c11 -fopenmp -fblocks -Wall"
        cppflags = (
            f"-I{os.path.join(fftw, 'include')} "
            f"-I{os.path.join(blas, 'include')} "
            f"-I{os.path.join(png, 'include')} "
            f"-I{os.path.join(zlib, 'include')}")
        ldflags = (
            f"-L{os.path.join(fftw, 'lib')} -Wl,-rpath,{os.path.join(fftw, 'lib')} "
            f"-L{os.path.join(blas, 'lib')} -Wl,-rpath,{os.path.join(blas, 'lib')} "
            f"-L{os.path.join(png, 'lib')} -Wl,-rpath,{os.path.join(png, 'lib')} "
            f"-L{os.path.join(zlib, 'lib')} -Wl,-rpath,{os.path.join(zlib, 'lib')} "
            f"-lm -lpng16 -lz -lrt -lopenblas -lfftw3f -lomp -lpthread {stub}")
        self.run(
            f"make -j1 SHELL=/bin/sh CC={cc} "
            f"BART_TOOLBOX_PATH={self._bart_dir()} "
            f"CFLAGS='{cflags}' CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}'",
            cwd=self.source_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # CI 沙箱中 lld（clang 链接器）加载 libxml2.so.16 失败（CI 注入的
        # LD_LIBRARY_PATH 空壳库优先级高于 lld 的 RUNPATH）→ 将 clang 所在
        # SDK 的 llvm/lib 前置注入 LD_LIBRARY_PATH（同 bart/1.0.00 方案）。
        clang_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(clang_real)), "lib")
        if os.path.isdir(llvm_lib):
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                llvm_lib + (os.pathsep + old_ld if old_ld else ""))
        bart = self._bart_dir()
        self._patch_shebang(bart)
        self._patch_bart_build_files(bart)
        self._patch_bart_unused_macro(bart)
        self._patch_bart_sources(bart)
        self._build_bart_toolbox(cc)
        self._patch_bart_view_sources()
        self._build_bart_view(cc)
        for exe in ("view", "cfl2png"):
            if not os.path.exists(os.path.join(self.source_folder, exe)):
                raise ConanInvalidConfiguration(f"bart-view {exe} was not built")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for exe in ("view", "cfl2png"):
            copy(self, exe, self.source_folder, bindir)
        # 鸿蒙可执行需 ELF 签名才能运行
        self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _sign_installed_elfs(self):
        import shutil
        import stat
        import tempfile
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}")
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    f"sign {binary}")
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}")
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}")
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}")
        return any(".codesign" in line.split() for line in section_table.splitlines())

    @staticmethod
    def _run_tool(command, action):
        import subprocess
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}")
        return result.stdout

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}") from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}")
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        import shutil
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate):
            resolved = candidate
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool '{executable}' not found in PATH")
        return resolved
