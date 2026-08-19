#!/usr/bin/env python3
"""Conan recipe for criterion 2.4.3 — Meson-based C/C++ unit testing framework.

Criterion is a cross-platform C and C++ unit testing framework.
Build system: Meson (since v2.4.0, previously CMake).

Uses Meson wrap fallback mechanism for all dependencies since most are not
yet available as separate Conan packages in the OHOS artifact repository.

R32: settings.os judgment uses `in ("Linux", "OHOS")` not `== "Linux"`.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CriterionConan(ConanFile):
    name = "criterion"
    version = "2.4.3"
    description = "A cross-platform C and C++ unit testing framework for the 21st century"
    license = "MIT"
    homepage = "https://github.com/Snaipe/Criterion"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        # retry/retry_wait 增强下载可靠性：真机首连 gh-proxy.com 出现过
        # Read timed out（get() 默认 retry=2/retry_wait=5，这里放宽）。
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=3, retry_wait=10)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 上游测试套件在 build() 末尾通过 meson.test() 执行（真机 aarch64 OHOS
        # 可直接运行，与 libsigc 等 meson 包的做法一致）。
        tc.project_options["tests"] = True
        tc.project_options["samples"] = False
        tc.project_options["dev"] = False
        tc.project_options["i18n"] = "disabled"
        # diffs 需要 libgit2 子项目，但 libgit2 v0.25.1 的 http_parser.c
        # 在 OHOS clang 26 上编译失败（错误信息缺失，疑似编译器崩溃或 OOM）。
        # diffs 仅用于测试失败时显示差异，非核心功能，禁用以跳过 libgit2。
        tc.project_options["diffs"] = "disabled"
        tc.project_options["theories"] = "enabled"
        tc.project_options["cxx-support"] = "enabled"
        # wrap_mode=default: 仅对系统未安装的依赖使用 wrap fallback。
        # force_fallback_for 显式指定 nanomsg 和 nanopb 必须从源码编译
        # (这两个 CMake 子项目需要 OHOS→Linux 平台映射补丁)。
        # boxfort/libffi 使用 fallback: 关键字，wrap_mode=default 时自动回退。
        # debugbreak/klib 是 header-only，系统找不到时自动使用 wrap。
        tc.project_options["wrap_mode"] = "default"
        tc.project_options["force_fallback_for"] = "nanomsg,nanopb"
        tc.generate()

        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar")
        _rl = _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
            if _bindir:
                _cand = _os.path.join(_bindir, "llvm-ar")
                if _os.path.isfile(_cand):
                    _ar = _cand
                    if not _rl:
                        _rlc = _os.path.join(_bindir, "llvm-ranlib")
                        if _os.path.isfile(_rlc):
                            _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f:
                _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = f"[binaries]\nar = '{_ar}'\n"
                if _rl and "\nranlib =" not in _c:
                    _ins += f"ranlib = '{_rl}'\n"
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f:
                    _f.write(_c)

        # Fix libffi aarch64 compilation on OHOS (issue #4):
        # libffi 3.2.9999 (meson wrap subproject) uses 'asm' keyword
        # (GNU extension, invalid in -std=c11 strict mode).
        # Only -Dasm=__asm__ is safe for global c_args: it applies to both
        # C and .S assembly sources. -include sys/types.h must NOT be global
        # because it breaks aarch64/sysv.S (C typedefs parsed as asm tokens).
        # Instead, build() patches the specific libffi C/H files that need
        # ssize_t to #include <sys/types.h> directly.
        if self.settings.os == "OHOS":
            if _os.path.isfile(_nf):
                with open(_nf) as _f:
                    _c = _f.read()
                if "-Dasm=__asm__" not in _c:
                    if "c_args = []" in _c:
                        _c = _c.replace(
                            "c_args = []",
                            "c_args = ['-Dasm=__asm__']",
                            1)
                    elif "c_args = [" in _c:
                        _c = _c.replace(
                            "c_args = [",
                            "c_args = ['-Dasm=__asm__', ",
                            1)
                    elif "[built-in options]" in _c:
                        _c = _c.replace(
                            "[built-in options]\n",
                            "[built-in options]\n"
                            "c_args = ['-Dasm=__asm__']\n",
                            1)
                    else:
                        _c += ("\n[built-in options]\n"
                               "c_args = ['-Dasm=__asm__']\n")
                    with open(_nf, "w") as _f:
                        _f.write(_c)

    def _ensure_meson(self):
        """HMBS 真机无全局 meson，自举一个可执行 meson 并前置到 PATH。

        官方 CI worker 已全局提供 meson，此函数直接跳过；HMBS 真机只注入
        cmake/make/ninja/python3（HMBS_PYTHON3），build() 的 meson.configure()
        报 'meson: inaccessible or not found' (Error 127)。自举顺序：
        1) 设备 python3 已装 mesonbuild 模块 → 包装为 python3 -m 调用；
        2) 否则下载 meson 1.5.1 源码 tarball（镜像优先、官方 GitHub 兜底，
           与 ci/conan/build_and_test.sh 维护的镜像映射一致），用 HMBS
           提供的 python3 执行 meson.py。
        wrapper 用 os.open(0o755) 直接生成可执行文件（HMFS 不支持 chmod），
        前置到 PATH 后 Conan 的 Meson 工具按裸名 meson 即可找到。
        """
        import os
        import shutil
        import subprocess

        if shutil.which("meson"):
            return
        _bin = os.path.join(self.build_folder, "meson-bin")
        _script = os.path.join(_bin, "meson")
        if os.path.isfile(_script):
            os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
            return
        python = os.environ.get("HMBS_PYTHON3") or "python3"
        entry = None
        try:
            _r = subprocess.run([python, "-c", "import mesonbuild"],
                                capture_output=True)
            if _r.returncode == 0:
                # -u 强制 Python 行级无缓冲输出：Conan 经管道捕获子进程
                # stdout，meson.py 默认块缓冲（约 8KB）会让 SSH 网关在
                # meson setup 长时间无足量输出时误判"静默"，触发 60s 熔断
                # 断开连接（本轮日志 'Connection ... closed by remote host'）。
                entry = 'exec "%s" -u -m mesonbuild.mesonmain "$@"' % python
        except OSError:
            entry = None
        if entry is None:
            _src = os.path.join(self.build_folder, "meson-src")
            if not os.path.isfile(os.path.join(_src, "meson.py")):
                # 真机无法直连 github.com（ConnectTimeout），按
                # ci/conan/build_and_test.sh 的 GitHub 镜像映射把可用镜像放前面、
                # 官方 URL 放最后兜底；get() 对 url 列表逐个尝试直到成功，
                # 镜像必须提供与官方完全相同的归档，sha256 保持不变。
                # gh-proxy.com 置于首位——本轮真机 criterion/meson 两处下载
                # 均经其兜底成功；ghfast.top 本轮真机 ConnectTimeout（无法建立
                # 连接），后移作候选；官方 github.com URL 仍最后兜底。
                _m_url = ("https://github.com/mesonbuild/meson/releases/download/"
                          "1.5.1/meson-1.5.1.tar.gz")
                get(self,
                    url=[
                        "https://gh-proxy.com/" + _m_url,
                        "https://mirror.ghproxy.com/" + _m_url,
                        "https://ghproxy.com/" + _m_url,
                        "https://gitclone.com/" + _m_url[len("https://"):],
                        "https://moeyy.cn/gh-proxy/" + _m_url,
                        _m_url.replace("https://github.com", "https://kkgithub.com"),
                        "https://ghfast.top/" + _m_url,
                        _m_url,
                    ],
                    retry=3, retry_wait=10,
                    sha256="567e533adf255de73a2de35049b99923caf872a455af9ce03e01077e0d384bed",
                    destination=_src, strip_root=True)
            # -u 同上：meson.py 块缓冲输出会在 SSH 网关 60s 无输出窗口内
            # 被误判为挂起并整体断开连接，行级无缓冲让网关实时看到进度。
            entry = 'exec "%s" -u "%s" "$@"' % (python, os.path.join(_src, "meson.py"))
        os.makedirs(_bin, exist_ok=True)
        _fd = os.open(_script, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o755)
        with os.fdopen(_fd, "w") as _f:
            _f.write("#!/bin/sh\n" + entry + "\n")
        os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
        self.output.info("[criterion] meson bootstrap: %s" % entry)

    def _meson_configure(self, meson):
        """真机上 meson setup 偶发以退出码 5 失败：Conan 报 'Exiting with
        code: 5'，且同轮日志出现 Signal 15/SIGTERM（SSH 网关熔断）。按
        meson 1.5.1 mesonmain.errorhandler，退出码 5 = 未捕获 OSError 的
        e.errno（errno 5 = EIO），meson 自述 'not a Meson bug, but an issue
        with your build environment'——真机 pty/会话通道被网关短暂切断时，
        meson 写 stdout 得到 EIO。Conan 的 Meson.configure() 不做重试，
        这里包一层：
        1) 失败时转储 build 目录 meson-logs/meson-log.txt 尾部（含真实
           traceback，供下一轮 hmbs 日志定位根因）；
        2) 清理 meson-private（meson 判断 build 目录已配置的标志）使重试
           走全新 meson setup，避免 'Directory already configured'；
        3) 等待 65s（> 网关 60s 熔断窗口）后重试一次；仍失败则原样抛出，
           不吞错误、不影响 HMBS 门禁判定。
        另一变体（本轮）：日志停在 'RUN: meson setup ...' 后出现
        'Connection to 113.25.148.239 closed by remote host'——网关把整个
        SSH 会话断开而非只给 meson 发 SIGTERM，配方内重试无从触发。根因
        是 meson.py 经 Conan 管道捕获 stdout 时默认块缓冲（约 8KB），
        meson setup 早期输出积压在缓冲区，网关在 60s 无输出窗口内误判
        挂起而断连。_ensure_meson() 生成的 wrapper 已加 '-u' 强制行级
        无缓冲，让网关实时看到 meson setup 进度，从源头消除该静默窗口。
        """
        import os as _os
        import shutil
        import time
        from conan.errors import ConanException

        _attempts = 2
        for _i in range(1, _attempts + 1):
            try:
                meson.configure()
                return
            except ConanException as _e:
                self.output.info("[criterion] meson setup failed (attempt %d/%d): %s"
                                 % (_i, _attempts, _e))
                _log = _os.path.join(self.build_folder, "meson-logs", "meson-log.txt")
                if _os.path.isfile(_log):
                    try:
                        with open(_log, encoding="utf-8", errors="replace") as _f:
                            _lines = _f.readlines()
                        _tail = "".join(_lines[-40:])
                        self.output.info("[criterion] meson-log.txt tail:\n%s" % _tail)
                    except OSError:
                        pass
                if _i == _attempts:
                    raise
                _mp = _os.path.join(self.build_folder, "meson-private")
                if _os.path.isdir(_mp):
                    shutil.rmtree(_mp, ignore_errors=True)
                self.output.info("[criterion] waiting 65s for SSH gateway circuit breaker, retrying meson setup...")
                time.sleep(65)

    def build(self):
        self._ensure_meson()
        meson = Meson(self)
        self._meson_configure(meson)
        if self.settings.os == "OHOS":
            # libffi wrap subproject 的 C/H 源文件引用 ssize_t 但未包含
            # <sys/types.h>。之前通过全局 c_args 的 -include sys/types.h
            # 解决，但该标志也会污染 aarch64/sysv.S 汇编源（-include 在
            # 源文件之前处理，#define _SYS_TYPES_H 守卫无效），导致
            # musl bits/alltypes.h 的 C typedef 被当作汇编指令解析。
            # 改为直接在需要 ssize_t 的 C/H 文件中补 #include <sys/types.h>。
            # 注意：meson 的 wrap 子项目源码克隆在 meson 的 source 目录下
            # （即 self.source_folder/subprojects/，对应 meson setup 的源目录），
            # 而不是 self.build_folder（basic_layout 下 build_folder 是
            # "build-<build_type>"，即 meson 的构建目录，只有产物无原始 .c/.h 源）。
            # 之前误用 self.build_folder 导致补丁作用在构建产物目录上，
            # aarch64/ffi.c 从未被补丁，引发 ssize_t 未定义编译失败。
            import os as _os
            _libffi = _os.path.join(self.source_folder, "subprojects", "libffi")
            if _os.path.isdir(_libffi):
                for _root, _dirs, _files in _os.walk(_libffi):
                    for _fn in _files:
                        if not _fn.endswith((".c", ".h")):
                            continue
                        _fp = _os.path.join(_root, _fn)
                        try:
                            with open(_fp, encoding="utf-8") as _f:
                                _src = _f.read()
                        except (OSError, UnicodeDecodeError):
                            continue
                        if "ssize_t" not in _src:
                            continue
                        if "sys/types.h" in _src:
                            continue
                        with open(_fp, "w", encoding="utf-8") as _f:
                            _f.write("#include <sys/types.h>\n" + _src)
            # boxfort wrap 子项目 (criterion 测试运行器依赖) 在 OHOS 上有
            # 三类不兼容，逐个在源码级就地补丁（boxfort 由 meson wrap-git
            # 克隆，只能在此处 build() 阶段、meson.configure() 之后修改）：
            #  1) POSIX 共享内存 shm_open → /dev/shm：OHOS 无 /dev/shm，
            #     改为 CWD 相对路径普通文件 (open/unlink)；meson test 的
            #     CWD 是构建目录（可写），父进程 fork/exec worker 时 CWD
            #     不变，父子按相对名互相找得到。
            #  2) arena 64 位固定映射基址 0x200000000000 (2^41) 超出 OHOS
            #     aarch64 用户地址空间上限（实测 < 2^41），mmap 报 EINVAL
            #     → cri_alloc_init cr_panic "Could not initialize inheritable
            #     arena: Invalid argument" → 全部 criterion 与 boxfort
            #     context.c 测试 SIGABRT。把 64 位基址区间降到 4GB~20GB
            #     （对任意 aarch64 VA 配置都合法），页探测/重试逻辑不变。
            #  3) worker trampoline 重入时 bxfi_exe_patch_main 要把 trampoline
            #     写入可执行文件文本页：在 OHOS 上把文本页改可写（mprotect RW）
            #     可能被内核/安全策略拒绝，且上游忽略 mprotect 返回值 →
            #     memcpy 写只读页 SIGSEGV → spawn 子进程提前死亡。改为优先经
            #     /proc/self/mem 写入（调试器标准手法，对 self 访问无需
            #     ptrace 权限），失败再回退 mprotect(RW) 窗口并检查返回值。
            _boxfort = _os.path.join(self.source_folder, "subprojects", "boxfort")
            if _os.path.isdir(_boxfort):
                def _bxfi_apply(_src, _repls, _what):
                    _out = _src
                    for _old, _new in _repls:
                        if _old not in _out:
                            self.output.warning(
                                "[criterion] boxfort patch miss (%s): %s"
                                % (_what, _old[:64]))
                            continue
                        # 全量替换：shm_open/shm_unlink/"/bxfi_%d" 在文件内
                        # 出现多次（sandbox-posix.c 3 处 bxfi 名、2 处
                        # shm_open、5 处 shm_unlink），只替换首处会残留
                        # shm 调用导致子进程打不开 ctx（ENOENT/ENOSYS）。
                        _out = _out.replace(_old, _new)
                    return _out

                # 1) shm → file：arena.c 与 sandbox-posix.c 各自替换，
                #    避免跨文件共用列表导致必然 miss（"/bxf_arena_%d"
                #    只在 arena.c、"/bxfi_%d" 只在 sandbox-posix.c）。
                _shm_repls = {
                    "src/arena.c": [
                        ('"/bxf_arena_%d"', '"bxf_arena_%d"'),
                        ("shm_open(", "open("),
                        ("shm_unlink(", "unlink("),
                    ],
                    "src/sandbox-posix.c": [
                        ('"/bxfi_%d"', '"bxfi_%d"'),
                        ("shm_open(", "open("),
                        ("shm_unlink(", "unlink("),
                    ],
                }
                for _rel, _repls in _shm_repls.items():
                    _fp = _os.path.join(_boxfort, _rel)
                    if not _os.path.isfile(_fp):
                        continue
                    with open(_fp, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, _repls, _rel)
                    if _new != _src:
                        with open(_fp, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] boxfort shm→file patch: %s" % _rel)

                # 2) arena 64 位固定基址下调（仅 BXF_BITS==64 分支常量行）
                _afp = _os.path.join(_boxfort, "src", "arena.c")
                with open(_afp, encoding="utf-8") as _f:
                    _src = _f.read()
                _new = _bxfi_apply(_src, [
                    ("static void *mmap_base = (void *) 0x200000000000;",
                     "static void *mmap_base = (void *) 0x100000000;"),
                    ("static void *mmap_max  = (void *) 0x7f0000000000;",
                     "static void *mmap_max  = (void *) 0x4000000000;"),
                    ("static intptr_t mmap_off_mask = 0x3fffff;",
                     "static intptr_t mmap_off_mask = 0x3ff;"),
                ], "arena constants")
                if _new != _src:
                    with open(_afp, "w", encoding="utf-8") as _f:
                        _f.write(_new)
                    self.output.info("[criterion] boxfort arena base → 4GB~20GB")

                # 3) worker trampoline 重入：把 trampoline 写入文本页。
                #    真机实测证据链：① /proc/self/mem write → EACCES（第 19 轮）；
                #    ② mprotect(RW) 成功但 mprotect(RX) 恢复被拒（EACCES，第 20
                #    轮）→ 页面停在 RW 不可执行，执行 trampoline SIGSEGV（sig=11）；
                #    ③ mprotect(RWX) 一次过渡同样被拒（EACCES，第 21 轮）——本机
                #    内核拒绝一切"改写文本页且保持/恢复可执行"的组合。因此本节的
                #    exe-elf.c 改写已不是主路径（worker 启动见下方第 5 节 no-exec
                #    方案，完全不触碰文本页），仅作为任何残余 exec 路径的兜底保留：
                #    首选 mprotect(RWX)（成功则 memcpy + mprotect(RX) 去 W；即便
                #    RX 恢复失败页面停在 RWX 仍可执行），/proc/self/mem 兜底；
                #    全部失败才打印并返回 -1（子进程 abort，由第 5 节诊断定位）。
                _efp = _os.path.join(_boxfort, "src", "exe-elf.c")
                with open(_efp, encoding="utf-8") as _f:
                    _src = _f.read()
                _new = _bxfi_apply(_src, [
                    ("#include <string.h>\n#include <sys/mman.h>",
                     "#include <string.h>\n#include <sys/mman.h>\n"
                     "#include <fcntl.h>\n#include <unistd.h>"),
                    ("""    mprotect(base, len, PROT_READ | PROT_WRITE | PROT_EXEC);
    size_t prelude_len = bxfi_exe_inject_prelude(addr);
    memcpy(nonstd (void *) ((uintptr_t) addr + prelude_len), opcodes, sizeof (opcodes));
    mprotect(base, len, PROT_READ | PROT_EXEC);
    bxfi_exe_clear_cache(addr, sizeof(opcodes));""",
                     """    size_t prelude_len = bxfi_exe_inject_prelude(addr);
    void *patch_at = (char *) addr + prelude_len;
    int wrote = 0;
    if (mprotect(base, len, PROT_READ | PROT_WRITE | PROT_EXEC) == 0) {
        memcpy(nonstd (void *) patch_at, opcodes, sizeof (opcodes));
        if (mprotect(base, len, PROT_READ | PROT_EXEC) < 0)
            fprintf(stderr, "boxfort: mprotect(RX) restore failed: %s\\n", strerror(errno));
        wrote = 1;
    } else {
        fprintf(stderr, "boxfort: mprotect(RWX) trampoline write failed: %s\\n", strerror(errno));
    }
    if (!wrote) {
        int memfd = open("/proc/self/mem", O_RDWR);
        if (memfd >= 0) {
            if (lseek(memfd, (off_t) (uintptr_t) patch_at, SEEK_SET) == (off_t) -1
                    || write(memfd, opcodes, sizeof (opcodes)) != (ssize_t) sizeof (opcodes)) {
                fprintf(stderr, "boxfort: /proc/self/mem trampoline write failed: %s\\n", strerror(errno));
                close(memfd);
                return -1;
            }
            close(memfd);
            wrote = 1;
        } else {
            fprintf(stderr, "boxfort: open /proc/self/mem failed: %s\\n", strerror(errno));
        }
    }
    if (!wrote) {
        fprintf(stderr, "boxfort: all trampoline write methods failed\\n");
        return -1;
    }
    bxfi_exe_clear_cache(addr, sizeof(opcodes));"""),
                ], "exe-elf trampoline write")
                if _new != _src:
                    with open(_efp, "w", encoding="utf-8") as _f:
                        _f.write(_new)
                    self.output.info("[criterion] boxfort trampoline write: mprotect(RW) first, /proc/self/mem fallback")

                # 4) spawn 舞步诊断（EPROTO 定位）：boxfort 父进程 wait_stop
                #    期望子进程在两个 SIGSTOP 点停下（exec 前 raise(SIGSTOP)
                #    与 term_sandbox_ctx 的 kill(self, SIGSTOP)），子进程提前
                #    退出/被杀（exec 失败 _exit(errno)、trampoline 内 abort）
                #    时 !WIFSTOPPED → EPROTO → runner panic "Could not spawn
                #    test instance: Protocol error"。打印 waitpid 真实状态
                #    （WIFEXITED 退出码=exec 失败 errno / WIFSIGNALED 信号=
                #    崩溃点），并在子进程各阶段打印标记，把死亡点精确到
                #    exec 前/构造函数/trampoline 三步之一。
                _sfp = _os.path.join(_boxfort, "src", "sandbox-posix.c")
                with open(_sfp, encoding="utf-8") as _f:
                    _src = _f.read()
                _new = _bxfi_apply(_src, [
                    ("""    if (!WIFSTOPPED(status)) {
        errno = EPROTO;
        return 0;
    }""",
                     """    if (!WIFSTOPPED(status)) {
        fprintf(stderr, "boxfort: wait_stop(pid=%d) not stopped: WIFEXITED=%d exit=%d WIFSIGNALED=%d sig=%d\\n",
                (int) pid,
                WIFEXITED(status) ? 1 : 0,
                WIFEXITED(status) ? WEXITSTATUS(status) : -1,
                WIFSIGNALED(status) ? 1 : 0,
                WIFSIGNALED(status) ? WTERMSIG(status) : -1);
        errno = EPROTO;
        return 0;
    }"""),
                    ("""    setsid();

    raise(SIGSTOP);""",
                     """    setsid();

    fprintf(stderr, "boxfort: child pid=%d pre-exec stop\\n", (int) getpid());
    raise(SIGSTOP);"""),
                ], "sandbox-posix spawn diagnostics")
                if _new != _src:
                    with open(_sfp, "w", encoding="utf-8") as _f:
                        _f.write(_new)
                    self.output.info("[criterion] boxfort spawn diagnostics (wait_stop + pre-exec stop)")

                _scfp = _os.path.join(_boxfort, "src", "sandbox.c")
                with open(_scfp, encoding="utf-8") as _f:
                    _src = _f.read()
                _new = _bxfi_apply(_src, [
                    ("""    if (bxfi_init_sandbox_ctx(&local_ctx) < 0)
        abort();""",
                     """    if (bxfi_init_sandbox_ctx(&local_ctx) < 0) {
        fprintf(stderr, "boxfort: worker bxfi_init_sandbox_ctx failed: %s\\n", strerror(errno));
        abort();
    }"""),
                    ("""    if (!fn)
        abort();""",
                     """    if (!fn) {
        fprintf(stderr, "boxfort: worker bxfi_denormalize_fnaddr failed\\n");
        abort();
    }"""),
                    ("""    if (bxfi_context_inherit(&local_ctx.ctx->context) < 0)
        abort();""",
                     """    if (bxfi_context_inherit(&local_ctx.ctx->context) < 0) {
        fprintf(stderr, "boxfort: worker bxfi_context_inherit failed: %s\\n", strerror(errno));
        abort();
    }"""),
                    ("""    if (bxfi_term_sandbox_ctx(&local_ctx) < 0)
        abort();""",
                     """    if (bxfi_term_sandbox_ctx(&local_ctx) < 0) {
        fprintf(stderr, "boxfort: worker bxfi_term_sandbox_ctx failed: %s\\n", strerror(errno));
        abort();
    }"""),
                    ("""    if (!bxfi_check_sandbox_ctx())
        return;

    if (bxfi_exe_patch_main((bxfi_exe_fn *) bxfi_main) < 0)
        abort();""",
                     """    if (!bxfi_check_sandbox_ctx())
        return;

    fprintf(stderr, "boxfort: worker constructor patch_main entered\\n");
    if (bxfi_exe_patch_main((bxfi_exe_fn *) bxfi_main) < 0) {
        fprintf(stderr, "boxfort: worker bxfi_exe_patch_main failed\\n");
        abort();
    }"""),
                ], "sandbox.c trampoline diagnostics")
                if _new != _src:
                    with open(_scfp, "w", encoding="utf-8") as _f:
                        _f.write(_new)
                    self.output.info("[criterion] boxfort trampoline step diagnostics")

                # 5) worker 启动恢复 exec + 源码级入口（不再触碰文本页）：
                #    第 22 轮 no-exec 方案暴露新问题——criterion 的 worker 需经
                #    nanomsg 消息通道（cri_proto_connect = nn_socket + nn_connect，
                #    URL 为 tcp://127.0.0.1，见 0003 补丁）与父进程通信，而 fork
                #    子进程继承的 nanomsg 内部工作线程已随 fork 消失，其同步对象
                #    状态被继承 → worker 首次 nn_connect/nn_send 永久挂起，父进程
                #    read_message 阻塞 → 14/19 全部 30s TIMEOUT（boxfort 样例不碰
                #    nanomsg，4/4 通过，与 0003 补丁前 EPROTO 全挂不同）。因此恢复
                #    exec（新映像 nanomsg 状态干净，与上游设计一致），trampoline
                #    不再写文本页：① 本节的 patch_main 改为 no-op（不再调用
                #    bxfi_exe_patch_main）；② 导出 bxfi_main（去 static）；③ worker
                #    舞步改由各二进制 main() 检测到 BXFI_MAP 后执行（criterion 的
                #    src/entry/entry.c 与 boxfort 样例 main 分别就地补丁，见第 7/8
                #    节）——main 在所有构造函数之后运行，C++ 静态初始化完整，无
                #    构造函数顺序风险；第 6 节的 cri_is_runner 复位保留为防御（exec
                #    流程中该值本就为 0，复位是幂等 no-op）。
                _scfp2 = _os.path.join(_boxfort, "src", "sandbox.c")
                with open(_scfp2, encoding="utf-8") as _f:
                    _src = _f.read()
                _new = _bxfi_apply(_src, [
                    ("static int bxfi_main(void)",
                     "int bxfi_main(void)"),
                    ("""    fprintf(stderr, "boxfort: worker constructor patch_main entered\\n");
    if (bxfi_exe_patch_main((bxfi_exe_fn *) bxfi_main) < 0) {
        fprintf(stderr, "boxfort: worker bxfi_exe_patch_main failed\\n");
        abort();
    }""",
                     """    /* OHOS W^X: the exec'd image's text page cannot host the main
       trampoline (mprotect RWX / RX-restore after RW and /proc/self/mem
       are all denied with EACCES), so patch_main no longer patches text.
       The worker dance runs from main() when BXFI_MAP is set (see
       conanfile.py sections 7-8). */
    fprintf(stderr, "boxfort: worker patch_main no-op (dance runs from main)\\n");
    return;"""),
                ], "sandbox.c worker entry via main")
                if _new != _src:
                    with open(_scfp2, "w", encoding="utf-8") as _f:
                        _f.write(_new)
                    self.output.info("[criterion] boxfort worker: exec + main-entry (no text patch)")

                # 6) no-exec worker 继承父进程 cri_is_runner=1 的分歧修正：
                #    criterion 的 cr_log_noformat（src/log/logging.c）以
                #    cri_is_runner 选择日志出口：1 → runner 本地 provider（父进程
                #    看不到）；0 → 经消息协议 cr_send_to_runner 发回父进程。exec
                #    流程的 worker 是新映像（cri_is_runner=0），而 no-exec 的 fork
                #    子进程继承父进程的 1，导致 worker 的 cr_log_* 消息到不了父
                #    进程（依赖消息送达的用例会失败）。在 run_test_child 入口
                #    复位为 0，与 exec worker 状态一致。cri_nb_asserts 等其余
                #    全局父进程从不自增（测试体只在 worker 里跑），无分歧。
                _rcfp = _os.path.join(self.source_folder, "src", "core", "runner_coroutine.c")
                if _os.path.isfile(_rcfp):
                    with open(_rcfp, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, [
                        ("    cri_diff_init();",
                         """    /* no-exec worker (see conanfile.py): the forked child inherits
       the runner's cri_is_runner=1; reset it so worker logs are routed
       to the message server like in the exec'd worker. */
    cri_is_runner = 0;

    cri_diff_init();"""),
                    ], "runner_coroutine cri_is_runner reset")
                    if _new != _src:
                        with open(_rcfp, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] run_test_child: reset cri_is_runner for no-exec worker")

                # 7) criterion 测试二进制的 main（libcriterion 的 src/entry/entry.c）
                #    检测到 BXFI_MAP（worker 环境变量，exec 时由 boxfort 子分支经
                #    dupenv 注入）时改走 worker 舞步：调用导出后的 bxfi_main() 并
                #    exit，不再进入 runner（原 trampoline 重定向 main 的职责移到
                #    源码级 main 检查）。main 在所有构造函数（含 C++ 静态初始化）
                #    之后运行，无顺序风险；exec 映像 nanomsg 干净，消息通道可用。
                _efp2 = _os.path.join(self.source_folder, "src", "entry", "entry.c")
                if _os.path.isfile(_efp2):
                    with open(_efp2, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, [
                        ('#include "criterion/criterion.h"',
                         '#include <stdlib.h>\n#include "criterion/criterion.h"'),
                        ("""CR_API int main(int argc, char *argv[])
{
    struct criterion_test_set *tests = criterion_initialize();""",
                         """CR_API int main(int argc, char *argv[])
{
    /* OHOS W^X boxfort worker (see conanfile.py): when exec'd as a boxfort
       worker (BXFI_MAP set), run the worker dance instead of the runner;
       this replaces the text-page main trampoline the kernel forbids. */
    if (getenv("BXFI_MAP")) {
        extern int bxfi_main(void);
        exit(bxfi_main());
    }

    struct criterion_test_set *tests = criterion_initialize();"""),
                    ], "criterion entry.c worker main")
                    if _new != _src:
                        with open(_efp2, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] entry.c: worker dance on BXFI_MAP")

                # 8) boxfort 样例二进制（nested/callback/timeout/context）的 main
                #    同样接 BXFI_MAP 舞步：样例是 C 程序（无 C++ 静态初始化顺序
                #    问题），exec 后的样例 main 若直接跑样例逻辑会无限再 spawn，
                #    故先检查 BXFI_MAP 走舞步。样例均已 include <stdlib.h>
                #    （getenv/exit 可用）。
                for _smp in ("nested.c", "callback.c", "timeout.c", "context.c"):
                    _sfp2 = _os.path.join(_boxfort, "sample", _smp)
                    if not _os.path.isfile(_sfp2):
                        continue
                    with open(_sfp2, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, [
                        ("EXPORT int main(void)\n{\n",
                         "EXPORT int main(void)\n{\n"
                         "    if (getenv(\"BXFI_MAP\")) {\n"
                         "        extern int bxfi_main(void);\n"
                         "        exit(bxfi_main());\n"
                         "    }\n"),
                    ], "sample/%s worker main" % _smp)
                    if _new != _src:
                        with open(_sfp2, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] boxfort sample %s: worker dance on BXFI_MAP" % _smp)

                # 9) 崩溃处理测试（other-crashes）的 runner 侧韧性修复（第 4 轮重写）：
                #    worker 在 init/fini 中按设计以 SIGSEGV 快速死亡，其 birth/SETUP
                #    消息可能与 runner 经自身连接发出的 death 消息乱序——nanomsg REP
                #    服务器一次只处理一个请求，runner 自身 REQ 连接（child_pump 的
                #    death_callback）与 worker 请求交错时，death 消息可能被丢弃或迟到，
                #    runner 因而在未标记 dead 的客户端上处理死 worker 的迟到消息。
                #    上一轮（仅 process_client_message_impl / handle_phase 的
                #    ctx->dead 守卫）在真机上未生效：日志仍现 "Cannot spawn a subtest
                #    outside of the 'main' test phase." + "Synthesis: Tested: 52364"
                #    （nb_tests 虚增，~18s，二进制 SIGABRT）。本轮日志新证据：spawn
                #    行仅约 2-3 个 worker（"boxfort: child pid=NNNNN pre-exec stop"
                #    极少），而 SETUP 处理达 5 万次（~0.34ms/次）——不是海量 spawn，
                #    而是同一批消息被重复处理：runner 循环复用 criterion_protocol_msg
                #    且 pb_decode 不清除新消息中缺失的字段（which_data/pid/phase 残留
                #    → 同一 SETUP 被反复处理，PRE_INIT 反复 push，state==0 恒成立）。
                #    修复四点（全部为 OHOS 韧性，不改上游语义，崩溃检测仍走 waitpid/
                #    WIFSIGNALED）：
                #    ① client.h：client_ctx 新增 pre_init_done 标记（designated
                #       initializer 自动清零，无泄漏）；
                #    ② client.c handle_pre_init：PRE_INIT 每个客户端上下文只 push 一次，
                #       重复 SETUP 不再虚增 nb_tests（handle_phase 的 state==0 判定
                #       不变，嵌套子测试 state==CS_MAIN 不受影响）；
                #    ③ runner.c run_tests_async：每轮循环前把 msg 重置为 init_zero，
                #       杜绝旧字段残留导致的消息重放；
                #    ④ runner.c run_tests_async：boxfort child_pump 在进程退出时立即
                #       清除 instance->status.alive（reap_child 写 props.status.alive，
                #       instance 内嵌于 sandbox props，同一内存，独立于 death 消息）——
                #       循环中检测到 WORKER 客户端 OS 级已死但未标记 dead 时，直接
                #       调用 handle_death 补记崩溃结果（other_crash 警告 / TEST_CRASH
                #       事件），随后走原 dead 分支 remove_client_by_pid +
                #       spawn_next_client，保证 death 消息丢失时 runner 也能推进。
                _hlfp = _os.path.join(self.source_folder, "src", "core", "client.h")
                if _os.path.isfile(_hlfp):
                    with open(_hlfp, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, [
                        ("    uint32_t state;\n    bool dead;",
                         "    uint32_t state;\n    bool dead;\n    bool pre_init_done;"),
                    ], "client.h pre_init_done field")
                    if _new != _src:
                        with open(_hlfp, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] client.h: pre_init_done field")

                _clfp = _os.path.join(self.source_folder, "src", "core", "client.c")
                if _os.path.isfile(_clfp):
                    with open(_clfp, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, [
                        ("""static void process_client_message_impl(struct server_ctx *sctx, struct client_ctx *ctx, const criterion_protocol_msg *msg)
{
    message_handler *handler = message_handlers[msg->data.which_value];""",
                         """static void process_client_message_impl(struct server_ctx *sctx, struct client_ctx *ctx, const criterion_protocol_msg *msg)
{
    /* OHOS crash-test resilience (see conanfile.py): a worker that dies
       mid-phase (SIGSEGV during setup/teardown) can leave its messages
       queued behind the runner's own death message (nanomsg REP request
       reordering / dropped concurrent requests). A dead worker cannot
       resurrect, so drop every message from it. */
    if (ctx->dead)
        return;

    message_handler *handler = message_handlers[msg->data.which_value];"""),
                        ("""    enum client_state new_state = phase_to_state[phase_msg->phase];
    enum client_state curstate = ctx->state & (CS_MAX_CLIENT_STATES - 1);""",
                         """    enum client_state new_state = phase_to_state[phase_msg->phase];
    enum client_state curstate = ctx->state & (CS_MAX_CLIENT_STATES - 1);

    /* Ignore phase messages from a dead client (see the process_client_message_impl
       guard above): late phases from a crashed worker must not touch the state
       machine, spawn new work, or produce error ACKs that make workers abort. */
    if (ctx->dead)
        return false;"""),
                        ("""    if (ctx->state == 0) { /* only pre_init if there are no nested states */
        push_event_noreport(PRE_INIT);
        report(PRE_INIT, ctx->test);
        log(pre_init, ctx->suite, ctx->test);
    }
    return false;""",
                         """    if (ctx->state == 0 && !ctx->pre_init_done) {
        /* OHOS crash-test resilience (see conanfile.py): a dead worker's
           queued SETUP can be processed more than once (reused message struct
           + nanomsg REP reordering), which would push PRE_INIT repeatedly and
           inflate nb_tests ("Tested: 52364"). Push it at most once per client
           context. */
        ctx->pre_init_done = true;
        push_event_noreport(PRE_INIT);
        report(PRE_INIT, ctx->test);
        log(pre_init, ctx->suite, ctx->test);
    }
    return false;"""),
                    ], "client.c dead guard + pre_init dedup")
                    if _new != _src:
                        with open(_clfp, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] client.c: dead guard + PRE_INIT once per client")

                _rlfp = _os.path.join(self.source_folder, "src", "core", "runner.c")
                if _os.path.isfile(_rlfp):
                    with open(_rlfp, encoding="utf-8") as _f:
                        _src = _f.read()
                    _new = _bxfi_apply(_src, [
                        ("""    criterion_protocol_msg msg = criterion_protocol_msg_init_zero;
    while ((has_msg = read_message(socket, &msg)) == 1) {
        struct client_ctx *cctx = process_client_message(&sctx, &msg);

        /* drop invalid messages */
        if (!cctx)
            continue;

        if (cctx->dead) {""",
                         """    criterion_protocol_msg msg;
    while (1) {
        /* OHOS crash-test resilience (see conanfile.py): reset the message
           before every decode. pb_decode does not clear fields absent from
           the new encoding and criterion's messages do not all share the same
           shape, so a stale which_data / pid / phase from a previous iteration
           could otherwise be re-processed (observed as ~52k replayed SETUP
           phases on the other-crashes tests: "Synthesis: Tested: 52364"). */
        /* criterion_protocol_msg_init_zero is a nanopb brace-list macro
           ({0, 0, {0}, ...}), valid only as an initializer, so wrap it in a
           compound literal to use it as an assignment expression. */
        msg = (criterion_protocol_msg) criterion_protocol_msg_init_zero;
        if ((has_msg = read_message(socket, &msg)) != 1)
            break;

        struct client_ctx *cctx = process_client_message(&sctx, &msg);

        /* drop invalid messages */
        if (!cctx)
            continue;

        /* OHOS crash-test resilience: the boxfort child_pump reaps a dead
           worker and clears instance->status.alive as soon as the process
           exits -- independently of the death message, which the nanomsg REP
           socket can drop when the runner's own client connection interleaves
           with the worker's pending request. When a WORKER client is already
           dead at the OS level but not yet marked dead, synthesize the death
           handling inline (logs the crash / pushes TEST_CRASH) so the branch
           below removes it and spawns the next test. */
        if (cctx->kind == WORKER && !cctx->dead && !cctx->instance->status.alive) {
            bool handle_death(struct server_ctx *, struct client_ctx *, const criterion_protocol_msg *);
            criterion_protocol_msg dmsg = criterion_message(death,
                    .result = cctx->instance->status.signal
                            ? criterion_protocol_death_result_type_CRASH
                            : criterion_protocol_death_result_type_NORMAL,
                    .has_status = true,
                    .status = cctx->instance->status.signal
                            ? cctx->instance->status.signal
                            : cctx->instance->status.exit);
            dmsg.id.pid = cctx->instance->pid;
            handle_death(&sctx, cctx, &dmsg);
            pb_release(criterion_protocol_msg_fields, &dmsg);
        }

        if (cctx->dead) {"""),
                    ], "runner.c message reset + OS-death fallback")
                    if _new != _src:
                        with open(_rlfp, "w", encoding="utf-8") as _f:
                            _f.write(_new)
                        self.output.info("[criterion] runner.c: msg reset + OS-death fallback")
        meson.build()
        # 上游测试套件在 build() 末尾真机执行（meson test），并输出
        # HMBS_UPSTREAM_TEST_RESULT 标记（HMBS 硬门禁要求的机器证据）。
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """在 build() 末尾执行 criterion 上游测试套件（meson test）并输出
        HMBS_UPSTREAM_TEST_RESULT 标记。

        此前 build() 只调 meson.test()：测试真实运行但从未打印标记行，
        HMBS 因此上报"上游测试：发现 0，执行 0"（evidence 阶段 incomplete）。
        本方法改为 Popen 逐行回显 meson test 输出（真机 SSH 网关有 60s
        静默熔断，逐行 flush 避免长测试被误判挂起断连），同时收集输出：
        ① 解析 meson 汇总行（Ok/Fail/Skipped/Timeout/Expected Fail/
        Unexpected Pass）得到真实计数；② 结果 dict 持久化到
        build_folder/upstream_test_result.json（package() 复制进包内 res/，
        test_package 每轮复发同一标记——包缓存命中时 build() 不重跑，
        仅 test_package 每轮必跑）；③ 立即 print 标记行作为首轮证据。
        status 非 passed（有失败/跳过/执行数为 0/解析不到汇总）时抛
        ConanException 显式失败，不伪造通过。
        """
        import json
        import os as _os
        import re as _re
        import shutil as _shutil
        import subprocess as _subprocess
        from conan.errors import ConanException

        _meson = _shutil.which("meson")
        if not _meson:
            raise ConanException("[criterion] meson not found; cannot run upstream tests")
        _cmd = [_meson, "test", "-C", self.build_folder]
        _proc = _subprocess.Popen(_cmd, stdout=_subprocess.PIPE,
                                  stderr=_subprocess.STDOUT, text=True,
                                  env=_os.environ, bufsize=1)
        _lines = []
        for _line in _proc.stdout:
            _lines.append(_line)
            print(_line, end="", flush=True)
        _proc.wait()
        _out = "".join(_lines)

        _sums = {}
        for _m in _re.finditer(
                r"^\s*(Ok|Expected Fail|Fail|Unexpected Pass|Skipped|Timeout):\s+(\d+)",
                _out, _re.M):
            _sums[_m.group(1)] = _sums.get(_m.group(1), 0) + int(_m.group(2))
        if not _sums:
            raise ConanException(
                "[criterion] meson test summary not found (exit=%d); cannot "
                "produce HMBS_UPSTREAM_TEST_RESULT" % _proc.returncode)
        _ok = _sums.get("Ok", 0)
        _fail = _sums.get("Fail", 0) + _sums.get("Timeout", 0)
        _skip = _sums.get("Skipped", 0)
        _exp = _sums.get("Expected Fail", 0)
        _unexp = _sums.get("Unexpected Pass", 0)
        _discovered = _ok + _fail + _skip + _exp + _unexp
        _executed = _discovered
        _passed = _ok
        _status = ("passed" if (_proc.returncode == 0 and _fail == 0
                                and _skip == 0 and _executed > 0
                                and _executed == _discovered)
                   else "failed")
        _result = {
            "status": _status,
            "framework": "meson",
            "command": " ".join(_cmd),
            "discovered": _discovered,
            "executed": _executed,
            "passed": _passed,
            "failed": _fail,
            "skipped": _skip,
        }
        _jf = _os.path.join(self.build_folder, "upstream_test_result.json")
        with open(_jf, "w", encoding="utf-8") as _f:
            json.dump(_result, _f)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_result), flush=True)
        if _status != "passed":
            raise ConanException(
                "[criterion] upstream tests not passed: %s" % json.dumps(_result))

    def package(self):
        self._ensure_meson()
        meson = Meson(self)
        meson.install()
        # 上游测试结果 JSON 复制进包内 res/，供 test_package 每轮复发
        # HMBS_UPSTREAM_TEST_RESULT 标记（包缓存命中时 build() 不重跑）。
        import os as _os
        import shutil as _shutil
        _jf = _os.path.join(self.build_folder, "upstream_test_result.json")
        if _os.path.isfile(_jf):
            _res = _os.path.join(self.package_folder, "res")
            _os.makedirs(_res, exist_ok=True)
            _shutil.copy2(_jf, _os.path.join(_res, "upstream_test_result.json"))

    def package_info(self):
        self.cpp_info.libs = ["criterion"]
        if self.settings.os in ("Linux", "OHOS"):
            # OHOS (musl libc) merges rt/dl into libc; only list what exists
            self.cpp_info.system_libs = ["pthread", "m"]
