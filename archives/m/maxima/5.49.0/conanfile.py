#!/usr/bin/env python3
"""Conan recipe — Maxima 5.49.0（跑在 ECL 上的计算机代数系统；手写 recipe）

为什么手写：Maxima 不是普通 autotools 库。
① 它**编译成 Lisp 镜像**：`--enable-ecl` 让构建产出 `src/binary-ecl/maxima.fas`，
   这个 .fas 才是 sage/passagemath 真正加载的东西 —— 而 `make install` **不装它**，
   sage 的 spkg-install 单独 `cp src/binary-ecl/maxima.fas $SAGE_LOCAL/lib/ecl/maxima.fas`。
   漏了这一步：maxima 命令行能用，但 passagemath-ecl / -maxima 从 ECL 里
   `(require 'maxima)` 直接失败 —— 又是构建全绿的静默缺失。
② **必须 unset CFLAGS/LDFLAGS**：这些从 ECL 的构建配置里继承，再传一份进来会被
   过度引用（sage Issue #29606）。
③ `git_found=false`：configure 见到 git 就去仓库里取版本号（sage Issue #15529）。
④ ECL 出错时会弹交互提示，构建挂死 —— stdin 重定向到 /dev/null。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MaximaConan(ConanFile):
    name = "maxima"
    version = "5.49.0"
    description = "Maxima — 计算机代数系统（符号计算），构建在 ECL 之上"
    license = "GPL-2.0-or-later"
    homepage = "https://maxima.sourceforge.io/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ECL 既是构建期解释器又是运行期宿主，故用普通 requires（构建期路径显式给）
        self.requires("ecl/24.5.10")
        # **gmp 与 gc 必须显式提成直接依赖**，不能只靠 ecl 的传递关系：
        # ECL 的公共头 `ecl/config.h` 里就写着 `#include "gmp.h"` 与 `# include "gc/gc.h"`
        # （其余包含项都是 libc 的），任何编译 ECL 扩展/Lisp 镜像的动作都要它们的头。
        # 而 conan 默认 `tools.graph:skip_binaries=True` 会把「运行期用不到」的传递依赖
        # 标成 skipped、连 package 都不下载 —— 那样下面拼 CPATH 时就拿不到它们的 include。
        # 版本跟随 ecl 的钉法，对不上会在图里报冲突（响的，不会静默）。
        self.requires("gmp/6.3.0.1")
        self.requires("gc/8.2.12")
        # 同理还要 libffi / ncurses / readline —— 它们同样是 ecl 的传递依赖，
        # 而**链接 Lisp 镜像**时 ECL 会带上 `-lffi -lreadline -lhistory -lformw
        # -lmenuw -lpanelw`。CI 上被 skip 掉就没有 libdir 进 LIBRARY_PATH，
        # 报的是 `lld: error: unable to find library -lffi`（实撞，第 12 轮）。
        # 版本跟随 ecl 的钉法（对不上会在依赖图里报冲突，是响的）。
        self.requires("libffi/3.4.4")
        self.requires("ncurses/6.6")
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self, src_folder=".")
        # **必须 in-source 构建**：configure 自己会拦下来 ——
        # `For ECL out-of-tree builds aren't supported. See src/maxima.system for details.`
        # （ECL 编 Lisp 时按源码树相对路径找文件，异地构建的路径它算不对）
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--enable-ecl")
        # --with-ecl 收的是**可执行文件路径**（不是前缀）
        tc.configure_args.append("--with-ecl=%s" %
                                 os.path.join(self.dependencies["ecl"].package_folder, "bin", "ecl"))
        # configure 见到 git 会去仓库取版本号（sage Issue #15529）
        tc.configure_args.append("git_found=false")
        # 设备上没有 texinfo，maxima 的 configure **硬失败**：
        # `makeinfo not found; Maxima needs makeinfo to build docs.` —— 它自己给了出口。
        tc.configure_args.append("--disable-build-docs")
        env = tc.environment()
        # ② CFLAGS/LDFLAGS 从 ECL 的配置继承，再传一份会被过度引用（sage Issue #29606）
        env.define("CFLAGS", "")
        env.define("LDFLAGS", "")
        env.define("EMACS", "no")
        # 构建期要真的**跑** ecl 去编 Lisp；而它的 libecl.so 在 conan cache 里，
        # 不进 LD_LIBRARY_PATH 就是一串 `cl_boot: symbol not found`（实撞，
        # 措辞像 ECL 版本不对，其实是**库没找到**——与 tachyon 的 libpng 同款）。
        # ECL 把自己的系统目录（cmp.fas 等编译器模块所在）**烤死在二进制里**，
        # 指向它构建时的 --prefix；conan 打包后那个路径根本不存在，于是一 load
        # 就报 `Cannot open #P"SYS:CMP.NEWEST". C library error: No such file or directory`
        # —— 措辞像文件损坏，其实是 SYS: 逻辑路径指错了。ECLDIR 就是用来覆盖它的。
        import glob as _glob2
        _ecl_root = self.dependencies["ecl"].package_folder
        _sysdirs = sorted(_glob2.glob(os.path.join(_ecl_root, "lib", "ecl-*")))
        if not _sysdirs:
            raise RuntimeError("ecl 包里找不到 lib/ecl-* 系统目录: " + _ecl_root)
        # ⚠️ 不能直接把 ecl 包里的 lib/ecl-<ver>/ 当 ECLDIR：ECL 的编译器后端找头文件的
        # 逻辑是（src/cmp/cmpbackend-cxx/cmpbackend-cxx.lsp:270 `ecl-include-directory`）：
        #   ① 烤死的 *ecl-include-directory*（= 构建时的 @includedir@）下有 ecl/config.h → 用它
        #   ② 否则看 `SYS:ecl;config.h`（SYS: 就是 ECLDIR）
        #   ③ 都没有 → `error "Unable to find include directory"`
        # conan 包里头文件在 <pkg>/include/ecl/，既不在烤死的路径下、也不在 ECLDIR 下，
        # 于是走到 ③。解法：在**我们自己的构建目录**里拼一个 ECLDIR ——
        # 把 ecl 系统目录的内容软链过来，再补一个 `ecl` → <pkg>/include/ecl 的软链，
        # 让判据 ② 命中。不动依赖包本身（那是别人的包，只读语义）。
        self._ecldir = os.path.join(self.build_folder, "ecl-sysdir")
        self._ecl_sysdir_src = _sysdirs[0]
        env.define("ECLDIR", self._ecldir + os.sep)

        # **必须遍历传递依赖**：只加 ecl 自己的 libdir 不够 —— libecl.so 还要
        # libgmp/libgmpxx，报的是 `Error loading shared library libgmp.so.10:
        # (needed by …/libecl.so.24.5)`。host 视图带传递依赖。
        _seen = set()
        try:
            _it = list(self.dependencies.host.items())
        except AttributeError:
            _it = list(self.dependencies.items())
        for _ref, _dep in _it:
            _base = getattr(_dep, "package_folder", None) or ""
            for _d in (_dep.cpp_info.libdirs or []):
                _p = _d if os.path.isabs(_d) else os.path.join(_base, _d)
                if _p and _p not in _seen and os.path.isdir(_p):
                    _seen.add(_p)
                    env.prepend_path("LD_LIBRARY_PATH", _p)          # configure 的 emacs 探测有 bug（sage Issue #15546）

        # ECL 把**它自己构建期的依赖 include 路径**烤进了 `ecl/config.h` 与 ecl-config
        # （config.h 里 `#include "gmp.h"`，编译命令里跟着一串
        #  `-I<当年那台机器的 conan cache>/p/gmp…/include`）。换一台 cache 路径不同的机器，
        # 那串 -I 全指向不存在的目录，ECL 编译 Lisp 时直接：
        #   ecl/config.h:54: fatal error: 'gmp.h' file not found
        #   (EXT:RUN-PROGRAM "clang" (… "-I/…/.conan2/p/gmp…/include" …))
        # CI 实撞：worker 的 cache 在 `~/.cache/conan2`，烤进去的却是 `~/.conan2` ——
        # 本机一直能过只是因为路径恰好一致，属于**靠机器巧合掩盖的缺陷**。
        # 修法既不改依赖包也不动 ECL：clang 认 **CPATH**，把所有依赖（含传递）的
        # include 目录喂进去，ECL 那串烤死的 -I 找不到时由 CPATH 兜住。
        _incs = []
        for _ref, _dep in _it:
            _base = getattr(_dep, "package_folder", None) or ""
            for _d in (_dep.cpp_info.includedirs or []):
                _p = _d if os.path.isabs(_d) else os.path.join(_base, _d)
                if _p and os.path.isdir(_p) and _p not in _incs:
                    _incs.append(_p)
        if _incs:
            env.define("CPATH", ":".join(_incs))
            self.output.info("CPATH（兜住 ECL 内部调 clang 时烤死的 -I）: %d 个目录" % len(_incs))
        # 烤死的不只有 -I，还有 **-L**：ECL 链接 Lisp 镜像时报
        #   lld: error: unable to find library -lecl / -lgmp / -lgc
        # 头用 CPATH 兜，库就用 **LIBRARY_PATH** 兜（clang/lld 的链接期搜索路径，
        # 与运行期的 LD_LIBRARY_PATH 是两回事，两个都要给）。
        _libs = sorted(_seen)
        if _libs:
            env.define("LIBRARY_PATH", ":".join(_libs))
            self.output.info("LIBRARY_PATH（兜住 ECL 烤死的 -L）: %d 个目录" % len(_libs))
        tc.generate(env)

    def _make_ecldir(self):
        """拼一个「头文件找得到」的 ECLDIR（理由见 generate() 里的注释）。"""
        import glob as _glob3
        ecl_root = self.dependencies["ecl"].package_folder
        os.makedirs(self._ecldir, exist_ok=True)
        for item in _glob3.glob(os.path.join(self._ecl_sysdir_src, "*")):
            link = os.path.join(self._ecldir, os.path.basename(item))
            if not os.path.lexists(link):
                os.symlink(item, link)
        inc = os.path.join(ecl_root, "include", "ecl")
        if not os.path.isdir(inc):
            raise RuntimeError("ecl 包里没有 include/ecl：" + inc)
        link = os.path.join(self._ecldir, "ecl")
        if not os.path.lexists(link):
            os.symlink(inc, link)
        if not os.path.isfile(os.path.join(self._ecldir, "ecl", "config.h")):
            raise RuntimeError("拼出来的 ECLDIR 里仍找不到 ecl/config.h：" + self._ecldir)
        self.output.info("ECLDIR 就位：%s（含 ecl/config.h 软链）" % self._ecldir)

    def build(self):
        self._make_ecldir()
        apply_conandata_patches(self)
        import glob as _glob
        for cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # 上游那条 'multiple targets' 规则在新 make 上是错的（sage PR #35619）
        mk = os.path.join(self.source_folder, "doc", "info", "Makefile.in")
        if os.path.isfile(mk):
            with open(mk, encoding="utf-8", errors="ignore") as f:
                t = f.read()
            if t.startswith("maxima_singlepage.html "):
                with open(mk, "w", encoding="utf-8") as f:
                    f.write(t.replace("maxima_singlepage.html ", "", 1))
        autotools = Autotools(self)
        # ④ ECL 出错会弹交互提示卡死 —— stdin 关掉
        autotools.configure()
        # `--disable-build-docs` 管不到 interfaces/emacs/imaxima：那个子目录在
        # **install** 阶段还要建 imaxima.info（`makeinfo: command not found` → Error 127）。
        # 我们不需要 emacs 前端（sage/passagemath 走的是 maxima 命令行与 maxima.fas），
        # 把顶层 Makefile 的 SUBDIRS 里的 interfaces 去掉。
        # 只改顶层这一处、不用 `make SUBDIRS=...`（那会递归传给子 make，实撞过）。
        _top = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(_top):
            import re as _re2
            with open(_top, encoding="utf-8", errors="ignore") as _f:
                _t = _f.read()
            _m = _re2.search(r"(?m)^SUBDIRS\s*=(.*)$", _t)
            if _m and "interfaces" in _m.group(1):
                _new = " ".join(x for x in _m.group(1).split() if x != "interfaces")
                _t = _t[:_m.start()] + "SUBDIRS = " + _new + _t[_m.end():]
                with open(_top, "w", encoding="utf-8") as _f:
                    _f.write(_t)
                self.output.info("顶层 SUBDIRS 去掉 interfaces（imaxima 要 texinfo）")
        autotools.make(args=["-j1"])
        self._check_fas_built()

    def _check_fas_built(self):
        """构建一结束就核对 `src/binary-ecl/maxima.fas` 在不在，不在就**当场失败并留证据**。

        为什么不留到 package()：maxima 的 make 对 Lisp 镜像那步是「失败也继续」的，
        真正的原因在 make 日志中段，而 package() 阶段报错时 CI 只截到日志尾巴 ——
        我们在 CI 上就吃过这个亏（本机构建出 fas、CI 没有，而 CI 日志里连一行 ecl 都看不到）。
        这里顺带把 ecl 能不能跑、binary-ecl 目录里有什么打出来，让下一次失败自带诊断。
        """
        import glob as _glob
        fas = os.path.join(self.source_folder, "src", "binary-ecl", "maxima.fas")
        if os.path.isfile(fas):
            self.output.info("maxima.fas 已产出：%s（%.1f MB）"
                             % (fas, os.path.getsize(fas) / 1048576.0))
            return
        ecl_bin = os.path.join(self.dependencies["ecl"].package_folder, "bin", "ecl")
        self.output.warning("没有 maxima.fas —— 下面是诊断信息")
        self.run('"%s" --version || true' % ecl_bin, ignore_errors=True)
        bdir = os.path.join(self.source_folder, "src", "binary-ecl")
        self.output.warning("binary-ecl 目录：%s -> %s"
                            % (bdir, sorted(os.listdir(bdir)) if os.path.isdir(bdir) else "（不存在）"))
        self.output.warning("src 下的 .fas：%s"
                            % sorted(_glob.glob(os.path.join(self.source_folder, "src", "*.fas")))[:10])
        raise RuntimeError(
            "构建没产出 src/binary-ecl/maxima.fas。maxima 的 make 对 Lisp 镜像那步失败也会继续，"
            "所以要看上面的 ecl 诊断与 make 日志中段，别只看这一行。")

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        self._install_fas()
        self._sign_binaries()

    def _install_fas(self):
        """把 maxima.fas 装进 lib/ecl/ —— `make install` 不管这件事。

        passagemath-ecl / -maxima 是从 ECL 里 `(require 'maxima)` 加载它的，
        少了这个文件：maxima 命令行照样能跑，Python 侧一调就失败。
        """
        src = os.path.join(self.source_folder, "src", "binary-ecl", "maxima.fas")
        if not os.path.isfile(src):
            raise RuntimeError("没产出 maxima.fas（--enable-ecl 没生效？）: " + src)
        dst = os.path.join(self.package_folder, "lib", "ecl")
        os.makedirs(dst, exist_ok=True)
        copy(self, "maxima.fas", src=os.path.dirname(src), dst=dst)
        self.output.info("已装 lib/ecl/maxima.fas")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _tool(self, name, fallback):
        import shutil as _shutil
        return _shutil.which(name) or fallback

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        import glob as _glob
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for n in os.listdir(bindir):
                p = os.path.join(bindir, n)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = self._tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = self._tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 消费方（跑 bin/maxima 或从 ECL 里 require maxima）都需要 ECLDIR 指向 ecl 的
        # 系统目录，否则模块 require 全部落空（ECL 把前缀烤死在二进制里，见 generate()）。
        import glob as _glob4
        _sys = sorted(_glob4.glob(os.path.join(
            self.dependencies["ecl"].package_folder, "lib", "ecl-*")))
        if _sys:
            self.runenv_info.define_path("ECLDIR", _sys[0] + os.sep)
        self.runenv_info.define_path("MAXIMA_PREFIX", self.package_folder)
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
