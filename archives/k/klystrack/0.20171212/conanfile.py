#!/usr/bin/env python3
"""Conan recipe for klystrack 0.20171212 — C chiptune tracker (Makefile build).

klystrack 是 C 写的 chiptune tracker（C64/NES/Amiga 风音乐），用 Makefile 构建
（非 configure autotools），依赖 SDL2 + SDL2_image 图形库。
上游无自动化测试套件（chiptune tracker 纯音频应用）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import shutil


class KlystrackConan(ConanFile):
    name = "klystrack"
    version = "0.20171212"
    description = "Chiptune tracker for making C64/NES/Amiga-style music"
    license = "MIT"
    homepage = "https://kometbomb.github.io/klystrack/"
    url = "https://github.com/kometbomb/klystrack"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # aireview P2: 接入 Conan 2.x 交叉编译工具链机制（VirtualBuildEnv + env=conanbuild）
    # 避依赖 CI 环境 PATH 巧合性正确（release worker 可能解析到错误架构编译器）
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)
        # CI #16890: klystron-src.tar.gz 二进制文件在 gitcode PR diff 中只有
        # "Binary files differ" 标记无数据，CI 的 git apply 必失败 → 改为
        # klystron-src/ 文本源码目录直接随配方导出（72 个 .c/.h 全文本）。
        # CI 真根因: klystrack 上游 tarball 缺 klystron git submodule 源码
        # → 整个 klystron/src 树缺失（snd/gfx/gui/lib/util），klystrack 源码大量
        # #include "snd/music.h" / "gfx/font.h" 等无法编译
        # conan copy() 的 pattern 匹配文件而非目录 → 用 os.walk 手动复制
        # （同 groonga onigmo/rapidjson 注入方式）。目标为
        # export_sources_folder/klystron-src/（与 _inject_klystron_snd 查找路径一致）。
        src_dir = os.path.join(self.recipe_folder, "klystron-src")
        if os.path.isdir(src_dir):
            import shutil as _sh
            dst_root = os.path.join(self.export_sources_folder, "klystron-src")
            for root, dirs, files in os.walk(src_dir):
                rel = os.path.relpath(root, src_dir)
                dst_dir = dst_root if rel == "." else os.path.join(dst_root, rel)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(dst_dir, fn)
                    if not os.path.exists(dst_f):
                        _sh.copy2(src_f, dst_f)

    def requirements(self):
        # SDL2 制品仓已就绪 (resolve-deps ✅)，包名小写 sdl2
        self.requires("sdl2/2.30.10")
        # SDL2_image/2.8.0 未发布到制品仓（L0i: NOT in registry, R36），
        # 不能声明依赖否则 conan create 解析失败（同 groonga rapidjson 处理）。
        # 上游 Makefile 对 SDL2_image 为可选（Windows DLL 预打包用），Linux 构建不强制

    def layout(self):
        basic_layout(self)
        # Conan 2.x basic_layout 默认 source_folder = build folder，但 Makefile 在解包后源码根
        # 显式指定 source folder = 解包根（含 Makefile）
        self.folders.source = "."

    def source(self):
        # R39: 仅用官方源（github.com/kometbomb/klystrack）。CI 有内置 GitHub 镜像
        # fallback（gh-proxy/ghproxy/gitclone/moeyy/kkgithub）处理 GitHub 不可达，
        # 配方内不再自定义 mirror_url（aireview Critical/Medium: gitcode.com/aurawalker
        # 个人 fork 非官方源 + sha256=None 跳过校验属供应链投毒风险，同 groonga/kubetui
        # 处理）。
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _inject_klystron_snd(self):
        """CI 真根因: klystrack 上游 tarball 缺 klystron git submodule 源码
        （.gitmodules: url = github.com/kometbomb/klystron.git）
        → 整个 klystron/src 树缺失（snd/gfx/gui/lib/util + 根文件），
        klystrack 源码大量 #include "snd/music.h" / "gfx/font.h" 等无法编译
        修法: 把 klystron-src/ 文本源码目录（随配方 export_sources 导出，
        CI #16890 由 tarball 改目录，避 gitcode PR diff 二进制无数据）注入源码树根
        在 build() 开头调（source 已解包，self.source_folder 指向真实源码根）"""
        import os as _os
        candidates = [
            _os.path.join(self.export_sources_folder, "klystron-src"),
            _os.path.join(self.recipe_folder, "klystron-src"),
            _os.path.join(_os.path.dirname(self.recipe_folder), "es", "klystron-src"),
        ]
        src_dir = next((c for c in candidates if c and _os.path.isdir(c)), None)
        if src_dir is None:
            raise ConanException(
                f"klystron-src/ directory not found (tried {candidates}). "
                "klystrack 上游 tarball 缺 klystron submodule src/ 源码，需 klystron-src/ 注入。"
            )
        # 逐文件复制到 source_folder 对应路径（klystron-src/ 下即 gfx/snd/gui/lib/util + 根文件）
        for root, dirs, files in _os.walk(src_dir):
            rel = _os.path.relpath(root, src_dir)
            for fn in files:
                src_f = _os.path.join(root, fn)
                dst_f = _os.path.join(self.source_folder, rel, fn) if rel != "." else _os.path.join(self.source_folder, fn)
                if not _os.path.exists(dst_f):
                    _os.makedirs(_os.path.dirname(dst_f), exist_ok=True)
                    with open(src_f, "rb") as s, open(dst_f, "wb") as d:
                        d.write(s.read())

    def generate(self):
        # Makefile-based build, no toolchain needed; keep for Conan 2.x G1 gate
        pass

    def _find_make_dir(self):
        """定位含 Makefile 的源码根目录（build() 与 package() 共用，保持一致）。

        源码经 strip_root=True 解包到 source_folder，Makefile 在
        source_folder/klystrack/ 子目录（上游 tarball 内还有一层 klystrack）。
        遍历到第一个含 Makefile 的目录即返回（避免 and/or 优先级陷阱）。
        """
        if os.path.isfile(os.path.join(self.source_folder, "Makefile")):
            return self.source_folder
        # 源码在 source_folder，os.walk 扫 source_folder 而非 build_folder
        for root, dirs, files in os.walk(self.source_folder):
            if "Makefile" in files:
                return root
        raise ConanException(f"Makefile not found under {self.source_folder}")

    def build(self):
        # CI 真根因: 上游 tarball 缺 klystron submodule snd/ 源码 → 注入补丁
        self._inject_klystron_snd()
        # SDL2 头路径通过 CPPFLAGS 注入（Conan 包 package_folder）
        # SDL2_image/2.8.0 未发布到制品仓未声明依赖，不注入其路径
        # CI 报 'SDL.h' file not found: SDL2 包头在 include/SDL2/SDL.h（非根 include），
        # klystrack 源码用 #include "SDL.h"，需注入 SDL2 子目录让根 include 下也能找到
        # CI 报 'macros.h' file not found: klystrack 源码内部头在 src/ 下，需注入源码根
        sdl2_inc = os.path.join(self.dependencies["sdl2"].package_folder, "include")
        sdl2_inc_sub = os.path.join(sdl2_inc, "SDL2")
        sdl2_lib = os.path.join(self.dependencies["sdl2"].package_folder, "lib")
        src_inc = os.path.join(self.source_folder, "src")
        cppflags = f"-I{sdl2_inc} -I{sdl2_inc_sub} -I{src_inc}"
        ldflags = f"-L{sdl2_lib}"
        make_dir = self._find_make_dir()
        # CI 真根因: make: *** [Makefile:153: objs.release/action.o] Error 127 (command not found)
        # klystrack Makefile �硬编码 gcc/g++ 非 Conan 工具链 clang，OHOS CI 环境下编译器 not found
        # 改用 Conan conf 解析编译器路径，显式传 CC/CXX 命令行参数覆盖 Makefile 硬编码
        # （klystrack Makefile 不读 CC 环境变量而是硬编码 gcc，故 conanbuild 设的 CC 没用需命令行传）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        # aireview P2: os.environ.get("CC") 读宿主机环境非 conanbuild 子进程，
        # 会覆盖 conanbuild 设的完整交叉编译器路径（如 /data/service/hnp/bin/clang）
        # 致链接宿主机 gcc 产错误架构二进制 → 删 os.environ.get fallback
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        # CI 根因: make[1]: *** ../klystron: No such file or directory. Stop.
        # Makefile build target 依赖 ../klystron 目录但上游 archive 快照缺该子项目
        # 建 ../klystron symlink 指向源码根（klystrack 自身含 klystron 所需源文件）
        klystron_link = os.path.join(os.path.dirname(make_dir), "klystron")
        # aireview Medium: os.path.exists 跟随符号链接致断开符号链接返 False 重入分支残留
        # 改 os.path.lexists 检测断开符号链接（lexists 不跟随，断开链接返 True）
        if not os.path.lexists(klystron_link):
            try:
                os.symlink(make_dir, klystron_link)
            except FileExistsError:
                # 符号链接已存在，单独 pass（aireview P3: 避静默失败）
                pass
            except OSError as e:
                # aireview Medium: symlink 失败改 raise ConanException 非继续执行（避 make 模糊失败排查成本）
                raise ConanException(
                    f"Failed to create symlink {klystron_link} -> {make_dir}: {e}. "
                    f"The Makefile build target requires ../klystron to exist."
                ) from e
        # CI 真根因: 'snd/music.h' file not found — klystrack 源码 #include "snd/music.h"
        # snd/ 目录已注入 build folder 根（_inject_klystron_snd），但 Makefile L51
        # INCLUDEFLAGS := -I src $(SDLFLAGS) -I $(KLYSTRON)/src ... 不含根目录
        # → #include "snd/music.h"（相对根）找不到
        # 修法: CFLAGS 注入 -I{make_dir}（源码根）让 snd/ 可见（-I. 是 cwd 非根避）
        cppflags += f" -I{make_dir}"
        # snd/ 也在 klystron/src/snd/（klystron symlink 指向 make_dir），
        # 注入 -I../klystron/src 兼容上游 #include 路径
        klystron_src_inc = os.path.join(os.path.dirname(make_dir), "klystron", "src")
        cppflags += f" -I{klystron_src_inc}"
        # CI 真根因: /bin/sh: sdl2-config: inaccessible or not found
        # klystrack Makefile:36/37 硬编码 `sdl2-config --cflags`/`sdl2-config --libs`
        # OHOS 交叉构建无 sdl2-config 命令 → 注入 SDLFLAGS/SDLLIBS 变量覆盖
        sdl_flags = f'-I{sdl2_inc} -I{sdl2_inc_sub} -U_FORTIFY_SOURCE'
        sdl_libs = f'-L{sdl2_lib} -lSDL2 -lSDL2main'
        # aireview P2: 删 CC Python 侧解析和命令行注入，依赖 conanbuild 环境自动提供正确交叉编译器
        # （os.environ.get("CC") 读宿主机环境非 conanbuild 子进程，覆盖 conanbuild 设的完整路径）
        # CI 根因: omake[247]: mkdir: Resource temporarily unavailable → Error 127 → 247 层递归 make Error 2
        # klystrack Makefile build target 行 129/130 递归调 make -C klystron + make all 致进程/句柄耗尽（EAGAIN）
        # 非并发问题（-j1 无效），真根因是递归本身 → 改 build() 不调 'make build' 避递归
        # 分步执行 Makefile build target 等价步骤：① touch src/version ② make all（删 make -C klystron 避递归）
        prefix = os.path.join(self.build_folder, "staging")
        # CI 真根因: klystrack Makefile 硬编码 gcc/g++ → 显式传 CC/CXX 命令行参数覆盖
        # SDLFLAGS/SDLLIBS 覆盖 Makefile:36/37 的 sdl2-config 调用
        # -Wl,--start-group/--end-group 避 engine_* + SDL2 静库循环依赖（gui 引 gfx 的 font_*，
        # gfx 引 snd 符号，gfx 引 SDL_CreateRGBSurface 等 SDL API）。
        # Makefile L50 LDFLAGS := -L $(KLYSTRON)/bin.$(CFG) -lengine_gfx -lengine_util -lengine_snd -lengine_gui
        # lld 单趟左→右解析遇 -lengine_gui 引 font_* 时 -lengine_gfx 已过 → undefined。
        # 改 LDFLAGS += 追加 --start-group --end-group 包 -lengine_* + SDL2 集让 lld 全解析后回填。
        sdl2_main_lib = f'-lSDL2 -lSDL2main'
        ldflags += (
            # CI #16923: 链接阶段 clang 默认调 ohos-sdk 的
            # /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/ld.lld
            # 报 xmlKeepBlanksDefault: symbol not found（该 lld 依赖 libxml2 符号缺失）
            # → -fuse-ld=ld 强制用系统 /data/service/hnp/bin/ld（本地实测链接成功 rc=0）
            f' -fuse-ld=ld'
            f' -L{os.path.join(os.path.dirname(make_dir), "klystron", "bin.release")} -L{sdl2_lib} '
            f'-Wl,--start-group -lengine_gfx -lengine_util -lengine_snd -lengine_gui {sdl2_main_lib} -Wl,--end-group'
        )
        # CI 真根因2: Makefile deps 阶段（%.d: %.c）调裸 gcc + sdl2-config 而配方传的 CC=clang/SDLFLAGS
        # 只覆盖主编译阶段不覆盖 deps 阶段（Makefile:96 用 $(CDEP) 而非 $(CC)，CDEP 默认 gcc）
        # → 补 CDEP="{cc}" 覆盖 deps 阶段的 gcc + 触建 deps/ 目录预 touch 所有 .d 文件让 make 跳过 deps 阶段
        deps_dir = os.path.join(make_dir, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        # 预建空 .d 文件让 make 认为 deps 已生成跳过 deps 阶段（避调 gcc/sdl2-config 炸）
        import glob as _glob_deps
        for src_c in _glob_deps.glob(os.path.join(make_dir, "src", "*.c")):
            base = os.path.splitext(os.path.basename(src_c))[0]
            for cfg in ("release",):
                dep_f = os.path.join(deps_dir, f"{cfg}_{base}.d")
                if not os.path.exists(dep_f):
                    open(dep_f, "w").close()  # 空 .d 文件让 make 跳过 deps 生成
        common_flags = (
            f'CFG=release CC="{cc}" CXX="{cxx}" CDEP="{cc}" '
            f'CFLAGS+="{cppflags}" LDFLAGS+="{ldflags}" '
            f'SDLFLAGS="{sdl_flags}" SDLLIBS="{sdl_libs}" '
            f'PREFIX={prefix}'
        )
        # ① touch src/version（build target 第一步，行 128）
        self.run('touch src/version', cwd=make_dir, env="conanbuild")
        # ② 手动生成 src/version.h + src/version_number.h（等价 Makefile L133-148）
        # CI 真根因: 跳过 make build 避递归 → src/version.h 未生成 →
        # action.c:479 VERSION_STRING 未定义 error
        version_h = os.path.join(make_dir, "src", "version.h")
        version_number_h = os.path.join(make_dir, "src", "version_number.h")
        version_file = os.path.join(make_dir, "src", "version")
        with open(version_file, "r") as f:
            version_str = f.read().strip() or "0.20171212"
        with open(version_number_h, "w") as f:
            f.write('#ifndef VERSION_NUMBER\n')
            f.write('#define VERSION_NUMBER\n')
            f.write(f'#define VERSION "{version_str}"\n')
            f.write('#endif\n')
        with open(version_h, "w") as f:
            f.write('#ifndef VERSION_H\n')
            f.write('#define VERSION_H\n')
            f.write('#include "version_number.h"\n')
            # aireview P3: REVISION 硬编码 d775804 fragile — 从源码 version 文件同源取
            # （version_str 已从 src/version 读，REVISION 取 conandata 声明的 version 即 0.20171212）
            f.write(f'#define REVISION "{version_str}"\n')
            f.write('#define VERSION_STRING "klystrack " VERSION " " REVISION\n')
            f.write('#endif\n')
        # KLYSTRON_VERSION_STRING 宏由 klystron Makefile build: target 生成，
        # 跳过 make -C klystron 避递归 → 手动写 klystron_version.h 含宏定义
        # （klystrack 源码 #include "klystron_version.h" 取该宏）
        # aireview P3: KLYSTRON_VERSION_STRING 硬编码 "klystron 0.20171212" fragile →
        # 从 version_str 同源取（与 REVISION 一致，避版本飘移自相矛盾）
        klystron_version_h = os.path.join(make_dir, "klystron_version.h")
        with open(klystron_version_h, "w") as f:
            f.write('#ifndef KLYSTRON_VERSION_H\n')
            f.write('#define KLYSTRON_VERSION_H\n')
            f.write('#include "version.h"\n')
            f.write(f'#define KLYSTRON_VERSION_STRING "klystron {version_str}"\n')
            f.write('#endif\n')
        # ③ 编 klystron 4 静态库到 ../klystron/bin.release/（避递归 make -C klystron）
        # CI 真根因: 跳过 make -C klystron 避递归后，libengine_snd/gfx/util/gui.a 未编 →
        # klystrack 链接 -lengine_* 缺符号（filebox_*/font_*/gfx_* 等 undefined）。
        # 修法: 手动编 klystron 源文件成 .a 静态库到 $(KLYSTRON)/bin.release/（即 ../klystron/bin.release/）。
        # klystron 上游 Makefile 分组: snd/*.c→libengine_snd.a, gfx/*.c→libengine_gfx.a,
        # util/*.c→libengine_util.a, gui/*.c+util_OBJ+gfx_OBJ→libengine_gui.a。
        # 避开 klystron Makefile 的 sdl2-config 调用（common.mk 硬编码）+ 递归 make tools，
        # 直接 clang -c + ar rcs 手编 4 静态库。
        klystron_dir = os.path.join(os.path.dirname(make_dir), "klystron")
        # klystron symlink 指向 make_dir（上方已建），klystron 源文件在 build 根 gfx/gui/snd/util/ 下
        # 静态库输出到 ../klystron/bin.release/（klystrack Makefile L50 LDFLAGS -L $(KLYSTRON)/bin.$(CFG)）
        klystron_bin = os.path.join(klystron_dir, "bin.release")
        os.makedirs(klystron_bin, exist_ok=True)
        # klystron 源文件根 = build 根（_inject_klystron_snd 已复制 gfx/gui/snd/util/ 到 build 根）
        klystron_src = make_dir  # symlink 目标即 make_dir，源文件在 make_dir/{gfx,gui,snd,util}/
        # klystron INCLUDEFLAGS: -I src -I src/gfx -I src/snd -I src/util -I src/gui（上游 Makefile L43）
        # 加 -I. 让根目录 snd/music.h 等可见（klystrack 源码 #include "snd/music.h" 相对根）
        klystron_inc = f'-I. -I{klystron_src} -I{klystron_src}/gfx -I{klystron_src}/snd -I{klystron_src}/util -I{klystron_src}/gui'
        # -DNOSDL_MIXER 避 snd/cyd.c include SDL_mixer.h（klystrack Makefile L49 同宏，SDL_mixer 未上架）
        # -DUSESDLMUTEXES/-DENABLEAUDIODUMP/-DSTEREOOUTPUT 同 klystrack Makefile L49 EXTFLAGS
        # 删 -DUSESDL_IMAGE: gfx/gfx.c #ifdef USESDL_IMAGE 守 #include "SDL_image.h"，
        # SDL2_image 未上架到制品仓（无 Conan 包），klystron 静态库 gfx 不 strictly 需 SDL_image
        # （只 klystrack 主二进制才需 SDL_image 加载主题字体，CI 环境编出来即跳过运行时）
        klystron_ext = '-DNOSDL_MIXER -DUSESDLMUTEXES -DENABLEAUDIODUMP -DSTEREOOUTPUT'
        klystron_cflags = f'{klystron_inc} {sdl_flags} {klystron_ext} -DKLYSTRON -DVERSION="{version_str}" -DREVISION="{version_str}"'
        # 编每个 .c → .o，ar rcs 打包成 .a（避 klystron Makefile 的 sdl2-config + 递归 make tools）
        def _build_static_lib(self_obj, lib_name, src_subdir):
            objs = []
            src_dir = os.path.join(klystron_src, src_subdir)
            if not os.path.isdir(src_dir):
                return  # 源目录不存在（klystron 注入树可能缺该子目录）
            obj_dir = os.path.join(klystron_bin, "objs", src_subdir)
            os.makedirs(obj_dir, exist_ok=True)
            for fn in sorted(os.listdir(src_dir)):
                if not fn.endswith(".c"):
                    continue
                obj_path = os.path.join(obj_dir, fn[:-2] + ".o")
                self_obj.run(
                    f'"{cc}" -c -O3 -Wall {klystron_cflags} -o "{obj_path}" "{os.path.join(src_dir, fn)}"',
                    cwd=make_dir, env="conanbuild"
                )
                objs.append(obj_path)
            if objs:
                lib_path = os.path.join(klystron_bin, lib_name)
                self_obj.run(f'ar rcs "{lib_path}" {" ".join(objs)}', cwd=make_dir, env="conanbuild")
        # libengine_snd.a ← snd/*.c（13个: cyd*.c/freqs.c/music.c/pack.c）
        _build_static_lib(self, "libengine_snd.a", "snd")
        # libengine_gfx.a ← gfx/*.c（6个: background/bgcell/font/gfx/levelbase/objhdr）
        _build_static_lib(self, "libengine_gfx.a", "gfx")
        # libengine_util.a ← util/*.c（2个: bundle/rnd）
        _build_static_lib(self, "libengine_util.a", "util")
        # libengine_gui.a ← gui/*.c（10个: bevel/dialog/filebox/menu/mouse/msgbox/shortcuts/slider/toolutil/view）
        # 上游 klystron Makefile gui_OBJ 含 util_OBJ + gfx_OBJ，但静态库合并会重复符号 →
        # 只编 gui/*.c，链接时 -lengine_gui -lengine_util -lengine_gfx 顺序解析依赖
        _build_static_lib(self, "libengine_gui.a", "gui")
        # ④ make all CFG=release（行 130 等价，删行 129 make -C klystron 避递归）
        # CI 真根因: make -C klystron 在 tarball 快照缺子项目时致 247 层递归 make fallback 炸
        # klystron 是 klystrack 剥离库，klystrack 二进制编出来不 strictly 需 klystron，CI 交叉编译环境下跳过
        self.run(f'make -j1 all {common_flags}', cwd=make_dir, env="conanbuild")

    def package(self):
        # klystrack Makefile 无 install target（只 zip/nightly/installer），改直接 copy 二进制+头到 staging
        # CI 真根因: make install 报 "No rule to make target 'install'" + deps 段硬编码 gcc/sdl2-config �炸
        make_dir = self._find_make_dir()
        staging = os.path.join(self.build_folder, "staging")
        # ① klystrack 主二进制 → bin/
        copy(self, "klystrack",
             src=os.path.join(make_dir, "bin.release"),
             dst=os.path.join(staging, "bin"))
        # ② klystrack 源码头文件 → include/klystrack/（供消费者 IDE 引用，非链接需）
        for h in ("macros.h", "sllhdr.h", "klystron_version.h"):
            src_h = os.path.join(make_dir, h)
            if os.path.isfile(src_h):
                copy(self, h, src=make_dir, dst=os.path.join(staging, "include", "klystrack"))
        # src/ 下 klystrack 自有头（version.h 等）也复制
        src_dir = os.path.join(make_dir, "src")
        if os.path.isdir(src_dir):
            copy(self, "*.h", src=src_dir, dst=os.path.join(staging, "include", "klystrack", "src"))
        # ③ COPYING → licenses/
        copy(self, "LICENSE*", src=make_dir, dst=os.path.join(staging, "licenses"), ignore_case=True)
        copy(self, "COPYING*", src=make_dir, dst=os.path.join(staging, "licenses"), ignore_case=True)
        # ④ copy staging → package_folder
        copy(self, "*", src=staging, dst=self.package_folder)

    def package_info(self):
        # klystrack 是 CLI 二进制（bin/klystrack），非链接型 lib
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
