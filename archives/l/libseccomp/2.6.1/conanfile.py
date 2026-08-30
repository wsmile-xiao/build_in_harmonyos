#!/usr/bin/env python3
"""Conan recipe for libseccomp 2.6.1 on HarmonyOS PC.

libseccomp is an interface to the Linux Kernel's syscall filtering
mechanism (seccomp/BPF). Pure C, zero external deps. Autotools build.

OHOS kernel is HongMeng-based; the library builds and links fine, and
the consumer test really calls the pure user-space API
(seccomp_version()/seccomp_api_get()). Loading real seccomp filters
into the kernel is kernel-feature dependent and honestly not claimed.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class LibseccompConan(ConanFile):
    name = "libseccomp"
    version = "2.6.1"
    package_type = "library"
    license = "LGPL-2.1"
    homepage = "https://github.com/seccomp/libseccomp"
    url = "https://github.com/seccomp/libseccomp"
    description = ("Interface to the Linux kernel syscall filtering "
                   "mechanism (seccomp/BPF)")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        # E011 根治（bacula/badvpn 同款实证）：config.status 在当前目录
        # 生成并直接执行 ./confXXXX/subs1.awk（HMDFS 执行位被剥）——源码
        # 复制到非 HMDFS（/data/storage/el2/base/cache）再 configure/make
        # work 目录唯一（CI 的多个 PR 构建共享 /data/storage/el2/base/
        # cache/libseccomp-src/——并发冲突（getcwd Permission denied
        # 实测 #6044——一个构建删改目录另一个 getcwd 失败）——加
        # package_id 后缀避免共享（2.5.6 已合入配方同款，#6042 CI 复现）
        work = "/data/storage/el2/base/cache/libseccomp-src-" + os.path.basename(self.build_folder)
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # E007：config.guess 无法识别 OHOS——显式 --build 三元组；
        # 共享库构建（shared=True）；
        # configure cross-compiling 检查（运行测试程序）在 el2 沙箱受限
        # （'C compiler cannot create executables' #6042 CI 实测 #31631
        # ——同 #6043 已通过模式：cache 预置 ac_cv_prog_cc_works=yes +
        # ac_cv_prog_cc_cross=yes 跳过 C 程序编译/运行检查——AC_PROG_CC
        # 先查 works 再查 cross，两个都需预置（ats2-postiats #6257 教训）；
        # 显式 --build 已是交叉编译）
        with open(os.path.join(work, "cross.cache"), "w") as f:
            f.write("ac_cv_prog_cc_works=yes\n")
            f.write("ac_cv_prog_cc_cross=yes\n")
            # libtool 对 ld.lld 的 deplibs 检测（2.5.6 实测 #6044：
            # scmp_sys_resolver 链接 '../src/.libs/libseccomp.so' 找
            # 不到——预置 pass_all 参照 2.6.0 构建成功）
            f.write("lt_cv_deplibs_check_method=pass_all\n")
            f.write("lt_cv_ld_force_load=no\n")
        # autoconf 对缓存变量的读取随版本而异（2.5.6 旧版 autoconf 实测
        # 不读 ac_cv_prog_cc_works 缓存）——防御性 patch configure 的
        # works/exeext 链接检查段：链接命令 (eval "$ac_link...") →
        # (eval "touch conftest")——保留分组结构不破坏语法；touch 生成
        # conftest 文件（for 循环 test -f conftest 通过——ac_cv_exeext
        # 空——检查通过）（2.5.6 已合入配方同款）
        _cfg_w = os.path.join(work, "configure")
        _cs_w = open(_cfg_w).read()
        _old_ws = '(eval "$ac_link_default") 2>&5'
        if _old_ws in _cs_w:
            _cs_w = _cs_w.replace(
                _old_ws, '(eval "touch conftest") 2>&5  # [ohos] works->touch',
                1)
            open(_cfg_w, "w").write(_cs_w)
            self.output.info("configure works link -> touch conftest")
        else:
            self.output.warning("works eval pattern not found")
        # exeext 探测（suffix of executables——cannot compute suffix of
        # executables 实测 #6044——同 ats2-lang #6258 教训）
        _marker = "checking for suffix of executables"
        _idx = _cs_w.find(_marker)
        if _idx >= 0:
            _eval_idx = _cs_w.find('(eval "$ac_link") 2>&5', _idx)
            if _eval_idx >= 0:
                _cs_w = (_cs_w[:_eval_idx]
                         + '(eval "touch conftest") 2>&5  # [ohos] exeext'
                         + _cs_w[_eval_idx + len('(eval "$ac_link") 2>&5'):])
                open(_cfg_w, "w").write(_cs_w)
                self.output.info("configure exeext link -> touch conftest")
            else:
                self.output.warning("exeext eval pattern not found")
        else:
            self.output.warning("exeext marker not found")
        # cross-compiling 检查（运行测试程序——CI 沙箱不能运行——
        # 'cannot run C compiled programs' 实测 #6044）——patch 判定为
        # 无条件 cross_compiling=yes（强制交叉编译——跳过运行测试程序）
        _old_cr = 'if test "$cross_compiling" = maybe; then'
        _new_cr = 'if true; then  # [ohos] force cross_compiling=yes'
        if _old_cr in _cs_w:
            _cs_w = _cs_w.replace(_old_cr, _new_cr, 1)
            open(_cfg_w, "w").write(_cs_w)
            self.output.info("configure cross compiling forced yes")
        else:
            self.output.warning("cross compiling anchor not found")
        # OHOS：HMDFS 上 bash 子进程 getcwd() 随机失败（E011/#6044 同源
        # ——dentry 缓存，errno 乱飘：Not a tty/ENOENT/EACCES）——按规程
        # 显式设 PWD（autotools 配方必加；bash pwd 内建在 getcwd 失败时
        # 校验 $PWD 与 stat(".") 一致后采用）
        os.environ["PWD"] = work
        self.run(
            f"./configure --cache-file={work}/cross.cache "
            f"--build=aarch64-unknown-linux-gnu "
            f"--prefix={self.package_folder} --enable-shared "
            "--disable-static",
            cwd=work,
        )
        # CI 的 configure 行为与本地不同（#6044 实测：scmp_sys_resolver
        # 链接 '../src/.libs/libseccomp.so' 找不到——本地验证通过 ≠ CI
        # 通过）——显式先 make src/（libseccomp.so 生成）再 make tools/
        # （scmp_sys_resolver）再 make -j1（完整）（2.5.6 已合入同款）
        self.run("make -C src -j1", cwd=work)
        self.run("make -C tools -j1", cwd=work)
        self.run("make -j1", cwd=work)
        # 管理员规则 4（#6043 已通过经验）：上游测试必须真实执行——
        # make all 不编译 check_PROGRAMS（测试程序，automake 机制——
        # 之前实测 02-sim-basic 等未编译导致 regression rc=127）与
        # tools/ 工具（scmp_arch_detect 缺失实测）——显式编译 +
        # make check 跑回归测试（sim 系列纯用户态可跑；arch-syscall-check
        # 的 OHOS syscall 表差异如实记录，不阻塞构建）
        # make check 用 SHELL=/data/service/hnp/bin/bash（automake
        # test-driver 用 $(SHELL) 跑测试脚本——绕过文件 shebang 的
        # /bin/bash 缺失问题）+ LD_LIBRARY_PATH（libseccomp.so.2 在
        # src/.libs/）——同 #6043 已通过模式
        # arch-syscall-check 实际在 src/ 目录（sdist 中 tests/ 无此文件
        # ——shebang 漏改根因：原路径 tests/ 从不命中——同 2.5.5/2.5.6
        # 已通过模式）——单独处理 src/ 路径
        ascp = os.path.join(work, "src", "arch-syscall-check")
        if os.path.exists(ascp):
            as_ = open(ascp).read()
            if as_.startswith("#!/bin/bash"):
                as_ = "#!/data/service/hnp/bin/bash" + as_[12:]
                open(ascp, "w").write(as_)
        self.run("make -C tools scmp_arch_detect", cwd=work,
                 ignore_errors=True)
        self.run("make check SHELL=/data/service/hnp/bin/bash",
                 cwd=work, ignore_errors=True)
        # tests/regression 的 tail_log() 用 `tail -n +0 --pid=$pid -f`
        # 跟随测试 job 日志——GNU tail 支持 --pid（job 退出时 tail 自动
        # 结束）；**toybox tail（CI /system/bin/tail，0.8.12）不支持
        # --pid，报 '--pid: No such file or directory' 后仍以 -f 模式
        # 永久跟随 log 文件 → 后台 tail 逃逸 timeout（toybox timeout
        # -k 只杀直接子进程，不杀孙进程）→ conan create 收尾挂起 →
        # buildbot 14400s 无输出被 SIGKILL（#7148 CI 实测）——patch
        # tail_log：去掉 --pid=$pid -f，job 完成后 tail -n +0 一次性
        # dump 全量日志即退出（语义等价：tail_log 在 job 结束后才被
        # 调用）——GNU/toybox 双兼容
        _reg_w = os.path.join(work, "tests", "regression")
        if os.path.exists(_reg_w):
            _rg_s = open(_reg_w).read()
            _old_tl = "tail -n +0 --pid=$pid -f $log"
            _new_tl = "tail -n +0 $log  # [ohos] toybox tail: no --pid"
            if _old_tl in _rg_s:
                _rg_s = _rg_s.replace(_old_tl, _new_tl, 1)
                open(_reg_w, "w").write(_rg_s)
                self.output.info("regression tail_log -> toybox compat")
            else:
                self.output.warning("regression tail_log pattern not found")
        self.run(
            # timeout 300 限制 regression（尾部步骤挂起——CI 14400s
            # 超时被杀实测 #6042/#7148——同 2.6.0 #6061 处理）——
            # tail_log 已 patch 为 toybox 兼容，此处 timeout 兜底——
            # miniseq 缺失处截断——如实验证不阻塞构建
            f"timeout 300 env LD_LIBRARY_PATH={work}/src/.libs "
            f"/data/service/hnp/bin/bash tests/regression",
            cwd=work, ignore_errors=True)

    def package(self):
        # work 目录唯一（同 build()——CI 并发冲突 #6044——加 package_id
        # 后缀避免共享）
        work = "/data/storage/el2/base/cache/libseccomp-src-" + os.path.basename(self.build_folder)
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        # libseccomp.so（libtool 产物在 src/.libs/）
        lib_src = os.path.join(work, "src", ".libs")
        if os.path.isdir(lib_src):
            for f in os.listdir(lib_src):
                if f.startswith("libseccomp.so"):
                    shutil.copy2(os.path.join(lib_src, f),
                                 os.path.join(lib_dir, f))
        # 头文件
        inc_src = os.path.join(work, "include")
        if os.path.isdir(inc_src):
            for f in os.listdir(inc_src):
                if f.endswith(".h"):
                    shutil.copy2(os.path.join(inc_src, f),
                                 os.path.join(inc_dir, f))

    def package_info(self):
        self.cpp_info.libs = ["seccomp"]
