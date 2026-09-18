#!/usr/bin/env python3
"""Conan recipe — libdogleg 0.18 (Makefile + vendored mrbuild, HarmonyOS PC / os=OHOS arch=armv8)

libdogleg: Powell's dogleg trust-region solver for nonlinear least squares
(sparse path via CHOLMOD, dense path via LAPACK dpptrf_/dpotrf_).

上游构建是裸 Makefile，由 mrbuild 框架（dkogan/mrbuild）提供全部编包规则；
choose_mrbuild.mk 在没有本地 mrbuild/ 时要求 apt 安装或现场 wget。
现场下载不可靠，本配方在 source() 把官方 mrbuild v1.13 tarball 取到源码树，
make 自动使用本地 mrbuild/，构建完全离线 hermetic。
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get


class LibdoglegConan(ConanFile):
    name = "libdogleg"
    version = "0.18"
    package_type = "shared-library"
    description = "Powell's dogleg trust-region solver for sparse and dense nonlinear least squares problems"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/dkogan/libdogleg"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "patches/*"

    def requirements(self):
        # 稀疏路径要 CHOLMOD（含 suitesparseconfig）；dense-products/dense 路径
        # 要 LAPACK（dogleg.c 直调 dpptrf_/dpotrf_）。openblas 同时提供 BLAS 与
        # LAPACK，与 suitesparse/7.8.3 所用的提供方一致，避免双 BLAS 混链。
        self.requires("suitesparse/7.8.3")
        self.requires("openblas/0.3.34")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生；cholmod 依赖只在此发布）")

    def source(self):
        # E002 / HMBS [readonly_tmp]: get() 的下载/解包临时文件走进程内
        # python tempfile，默认落只读 /tmp。复用与 generate()/build() 相同的
        # 可写目录探测；tempfile.tempdir 在进程内只解析一次（conan install
        # 阶段下载依赖时即已缓存），仅设环境变量不够，必须显式赋值。
        import tempfile
        _tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        os.environ["TEMP"] = _tmpdir
        tempfile.tempdir = _tmpdir
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # 见模块 docstring：vendored mrbuild，make 自动使用源码树内 mrbuild/。
        get(self, **self.conan_data["mrbuild"], strip_root=True,
            destination=os.path.join(self.source_folder, "mrbuild"))
        # OHOS ld.lld 不认 GNU ld 专有 -Wl,--default-symver（mrbuild
        # Makefile.common.footer 给非 Darwin 全加，真机报
        # ld.lld: unknown argument '--default-symver'）。库无版本脚本，
        # 去旗不影响符号；本地 vendored 框架去旗后构建。
        try:
            _footer = os.path.join(
                self.source_folder, "mrbuild", "Makefile.common.footer")
            _footers = [_footer]
            if not os.path.isfile(_footer):
                _footers = glob.glob(os.path.join(
                    self.source_folder, "mrbuild", "**",
                    "Makefile.common.footer"), recursive=True)
            for _fp in _footers:
                try:
                    with open(_fp, "r", encoding="utf-8",
                              errors="surrogateescape") as _f:
                        _txt = _f.read()
                except OSError:
                    continue
                if "--default-symver" in _txt:
                    _txt = _txt.replace("-Wl,--default-symver", "")
                    with open(_fp, "w", encoding="utf-8",
                              errors="surrogateescape") as _f:
                        _f.write(_txt)
                    self.output.info(
                        "patched mrbuild for ld.lld: dropped "
                        "--default-symver in {}".format(_fp))
        except OSError as _e:
            self.output.warning("mrbuild lld patch skipped: {}".format(_e))

    def _writable_tmpdir(self):
        # E002 / HMBS [readonly_tmp]: OHOS /tmp 为只读挂载，clang/make/sh 的
        # 临时文件必须落到可写目录。优先复用 hmbs 注入的任务级临时目录
        # (HMBS_TMPDIR/TMPDIR/TMP/TEMP)，用真实写入探测验证可写性（HMDFS
        # 忽略 chmod，禁止用 os.access(X_OK) 探测）；全部不可写才回退到
        # build_folder 下的 .hmbs-tmp（conan 已保证其可写）。
        for _var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            _cand = os.environ.get(_var)
            if not _cand:
                continue
            try:
                os.makedirs(_cand, exist_ok=True)
                _probe = os.path.join(_cand, ".hmbs-write-probe")
                with open(_probe, "w") as _f:
                    _f.write("ok")
                os.unlink(_probe)
                return _cand
            except OSError:
                continue
        _fb = os.path.join(self.build_folder or os.getcwd(), ".hmbs-tmp")
        try:
            os.makedirs(_fb, exist_ok=True)
        except OSError:
            pass
        return _fb

    def generate(self):
        # E2BIG 禁区（libmspub-tools/0.1.4 先例）：绝不在此调用
        # env.vars(self).save_script("conanbuild") / ("conanrun")——文件名与
        # conan 聚合脚本同名，聚合脚本按通配符 source 会把自己套自己，
        # PATH 等变量指数膨胀直至 "printenv: Argument list too long" + SIGKILL
        # （exit 137）。自定义变量改在 build() 内以 apply() 运行时注入。
        buildenv = VirtualBuildEnv(self)
        buildenv.generate()
        runenv = VirtualRunEnv(self)
        runenv.generate()

    def _is_runnable_cc(self, cand):
        # 画像 clang 路径在部分真机沙箱不存在（本轮预检
        # make: /data/service/hnp/bin/clang: No such file）。isfile 不可信，
        # 一律以真实 --version 执行验证（xmlsec/1.3.12 先例）。
        if not cand:
            return False
        try:
            proc = subprocess.run(
                [cand, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=30, check=False)
        except Exception:
            return False
        return proc.returncode == 0 and bool((proc.stdout or "").strip())

    def _resolve_cc(self, kind):
        # 画像编译器先做版本命令可运行校验，不可用时按注入变量与系统
        # 路径顺序回退（经验 1 路线）。不改变测试口径，只换可用编译器。
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        if kind == "cpp":
            profile = compilers.get("cpp")
            ordered = [profile,
                       os.environ.get("HMBS_CXX"), os.environ.get("CXX"),
                       shutil.which("clang++"), shutil.which("c++"),
                       "clang++", "c++",
                       "/storage/Users/currentUser/usr/local/bin/clang++",
                       "/data/service/hnp/bin/clang++"]
        else:
            profile = compilers.get("c")
            ordered = [profile,
                       os.environ.get("HMBS_CC"), os.environ.get("CC"),
                       shutil.which("clang"), shutil.which("cc"),
                       "clang", "cc",
                       "/storage/Users/currentUser/usr/local/bin/clang",
                       "/data/service/hnp/bin/clang"]
        seen = set()
        for cand in ordered:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if self._is_runnable_cc(cand):
                if cand != profile:
                    self.output.info(
                        "profile CC '{}' unusable, fallback to '{}'".format(profile, cand))
                else:
                    self.output.info("validated CC: {}".format(cand))
                return cand
            self.output.info("cc candidate unusable: {}".format(cand))
        # 无可用候选时保留画像值，让 make 报出原始错误而非静默换工具。
        return profile or ordered[-1]

    def _custom_env(self):
        cc = self._resolve_cc("c")
        cxx = self._resolve_cc("cpp")

        incs, libdirs = [], []
        for _ref in ("suitesparse", "openblas"):
            _dep = self.dependencies[_ref].cpp_info
            incs += list(_dep.includedirs)
            libdirs += [p for p in _dep.libdirs if os.path.isdir(p)]

        env = Environment()
        # R33：编译器与标志全部来自 Conan conf 与依赖包；mrbuild 只接受
        # 环境变量形式的 *FLAGS（命令行写 CFLAGS=... 会直接报错，见
        # mrbuild/Makefile.common.footer 开头的 *FLAGS 门禁）。
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CC_LINKER", cxx)
        env.define("SHELL", "/bin/sh")
        env.define("CPPFLAGS", " ".join("-I" + p for p in incs))
        env.define("LDFLAGS", " ".join("-L" + p for p in libdirs))
        # E002 / HMBS [readonly_tmp]：可写临时目录同样经运行时注入，
        # 使 make/clang/mktemp 及 shell 临时文件避开只读 /tmp。
        _tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", _tmpdir)
        env.define("TMP", _tmpdir)
        env.define("TEMP", _tmpdir)
        return env

    def build(self):
        # E002 / HMBS [readonly_tmp]: 进程级可写 TMPDIR（与 generate() 一致），
        # 覆盖 conan 聚合环境未透传宿主 TMPDIR 的情况。必须放在
        # apply_conandata_patches 之前：补丁流程走进程内 python tempfile，
        # 且 tempfile.tempdir 在 conan install 阶段即已缓存，事后设环境无效。
        import tempfile
        _tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        os.environ["TEMP"] = _tmpdir
        tempfile.tempdir = _tmpdir
        apply_conandata_patches(self)
        # VERSION 必须走命令行：Makefile 内 VERSION := $(VERSION_FROM_PROJECT)
        # 会覆盖环境变量；conan export 无 .git，无命令行则退化成 VERSION_UNKNOWN，
        # 产出 libdogleg.so.2.VERSION_UNKNOWN。VERSION 不是 *FLAGS，不触发门禁。
        # 自定义环境经 apply() 运行时注入（见 generate() 的 E2BIG 注释）；
        # env="conanbuild"/"conanrun" 只引用框架生成的聚合脚本（已无自引用）。
        checks = ["./sample --check sparse",
                  "./sample --check dense",
                  "./sample --check dense-products-packed-upper",
                  "./sample --check dense-products-unpacked",
                  "./test-misc"]
        _env = self._custom_env()
        with _env.vars(self).apply():
            self.run("VERSION=0.18 make -j1", cwd=self.source_folder, env="conanbuild")
            # ── 上游官方测试 ──
            # 上游 make check = 构建 sample/test-misc + 执行 check.sh。check.sh 是 zsh
            # 脚本（#!/bin/zsh，OHOS 无此解释器），但其内容就是下面 4 条
            # ./sample --check（见上游 check.sh 的 CMDS 数组），逐条直调完全等价；
            # test-misc 是第 5 个上游测试程序（校验 DOGLEG_DEBUG_VNLOG 位对齐，
            # 防止 dogleg_parameters2_t ABI 回退）。任一条非零即构建失败。
            # 测试执行同样在 apply() 上下文内：LD_LIBRARY_PATH 由 conanrun 聚合
            # 脚本提供，CC/TMPDIR 等由运行时注入提供。
            for _cmd in checks:
                self.run(_cmd, cwd=self.source_folder, env="conanrun")
        marker = {
            "status": "passed",
            "framework": "sample --check + test-misc (upstream check.sh)",
            "command": " && ".join(checks),
            "discovered": 5,
            "executed": 5,
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "reason": ("5 upstream test commands all exit 0 (each ./sample --check "
                       "mode internally asserts convergence plus recovery of all 6 "
                       "reference parameters within 5e-2; test-misc asserts the "
                       "DOGLEG_DEBUG_VNLOG bit alignment). check.sh itself is a zsh "
                       "script unavailable on OHOS; the 4 sample invocations are "
                       "exactly its CMDS array, invoked directly."),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(marker)), flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(marker)))

    def _find_built_file(self, filename):
        # 上轮真机证据：package() 时 self.source_folder 解析为
        # .../p/b/<id>/b，但该目录下无 libdogleg.so.2.0.18，而首个
        # copy() 因按 pattern 无匹配静默跳过（不抛错），导致 libdir
        # 未创建、后续 symlink 因父目录缺失进回退、回退又因同源缺失
        # 而 FileNotFoundError。根因是假定了“构建产物一定在
        # self.source_folder”，但 mrbuild/make 的实际落盘目录在
        # source/build/base 系目录间可能漂移。改为多目录定位。
        cands = []
        for _d in (getattr(self, "source_folder", None),
                   getattr(self, "build_folder", None),
                   getattr(self, "base_source_folder", None),
                   getattr(self, "base_build_folder", None)):
            if _d and _d not in cands:
                cands.append(_d)
        for _d in cands:
            _p = os.path.join(_d, filename)
            if os.path.isfile(_p) and not os.path.isdir(_p):
                return _p
        # 宽松兜底：同名版本变体（如 VERSION_UNKNOWN 产物）
        for _d in cands:
            try:
                _hits = glob.glob(os.path.join(_d, "libdogleg.so*"))
            except OSError:
                continue
            _hits = [h for h in _hits if os.path.isfile(h) and not os.path.islink(h)]
            if _hits:
                return sorted(_hits)[0]
        return ""

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        full = "libdogleg.so.2.0.18"
        os.makedirs(libdir, exist_ok=True)
        _src_lib = self._find_built_file(full)
        if not _src_lib:
            try:
                _listing = {}
                for _d in (getattr(self, "source_folder", None),
                           getattr(self, "build_folder", None)):
                    try:
                        _listing[str(_d)] = sorted(os.listdir(_d))[:30] if _d and os.path.isdir(_d) else "<missing>"
                    except OSError as _e:
                        _listing[str(_d)] = "listdir failed: {}".format(_e)
            except Exception:
                _listing = {}
            raise ConanException(
                "built {} not found (searched source/build/base dirs); listing={}".format(full, _listing))
        # 若宽松匹配拿到非标准版本名，仍按标准名安装，保持下游 -ldogleg 稳定。
        shutil.copyfile(_src_lib, os.path.join(libdir, full))
        # 版本软链：上游 make 建的软链不随文件拷贝保留，逐个重建
        #（openblas 配方已实证鸿蒙可建符号链接；失败则退化为实体拷贝）。
        for _link in ("libdogleg.so.2", "libdogleg.so"):
            _p = os.path.join(libdir, _link)
            try:
                if os.path.islink(_p) or os.path.exists(_p):
                    os.remove(_p)
                os.symlink(full, _p)
            except OSError:
                # conan copy() 的 dst 是目录语义，不能用作“改名拷贝”；
                # 此前用 copy(dst=<file>.tmp)+os.replace 在真机上因 .tmp
                # 是目录而报 FileNotFoundError。回退直接用 shutil 点对点拷贝。
                try:
                    if os.path.isdir(_p) and not os.path.islink(_p):
                        shutil.rmtree(_p)
                    elif os.path.islink(_p) or os.path.exists(_p):
                        os.remove(_p)
                except OSError:
                    pass
                shutil.copyfile(_src_lib, _p)
        copy(self, "dogleg.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as _f:
                return _f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _first_executable(self, cands):
        for cand in cands:
            if not cand:
                continue
            resolved = cand if os.path.isabs(cand) else shutil.which(cand)
            if not resolved or not os.path.isfile(resolved):
                continue
            real = resolved + ".real"
            if not resolved.endswith(".real") and os.path.isfile(real):
                resolved = real
            return resolved
        return ""

    def _sign_binaries(self):
        # 与 suitesparse/7.8.3 同法：鸿蒙 PC XPM 要求被 dlopen 的 .so 有代码签名，
        # 链接器自签在 install 拷贝后失效，逐个重签（只签真实 ELF，跳过软链）。
        # 真机沙箱的 hnp 绝对路径可能不存在，按 PATH 与常用位置回退；
        # 工具缺失时仅告警跳过，不让 package 硬失败（由后续 dlopen 实测判定）。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
        objcopy = self._first_executable([
            shutil.which("llvm-objcopy"),
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
            "/data/service/hnp/bin/llvm-objcopy"])
        signer = self._first_executable([
            shutil.which("binary-sign-tool"),
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            "/data/service/hnp/bin/binary-sign-tool"])
        if not objcopy or not signer:
            self.output.warning(
                "sign tools missing (objcopy='{}' signer='{}'), skip signing".format(objcopy, signer))
            return
        for _f in targets:
            if os.path.islink(_f) or not self._is_elf(_f):
                continue
            self.run("{oc} --remove-section .codesign \"{f}\" 2>/dev/null || true".format(oc=objcopy, f=_f))
            self.run("{sg} sign -inFile \"{f}\" -outFile \"{f}\" -selfSign 1".format(sg=signer, f=_f))

    def package_info(self):
        self.cpp_info.libs = ["dogleg"]
        self.cpp_info.set_property("cmake_file_name", "dogleg")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
