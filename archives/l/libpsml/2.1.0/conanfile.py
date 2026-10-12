#!/usr/bin/env python3
"""Conan recipe — libpsml 2.1.0 (CMake + Fortran, os=OHOS arch=armv8)

SIESTA/ESL 生态的 PSML 赝势文件处理库。上游是纯 Fortran 源码
(LANGUAGES "Fortran")，设备与 NDK 都不带 Fortran 编译器，用仓库
flang-ohos/20.1.0 作 tool_requires（同 netcdf-fortran/fortran-shlex 先例）。

依赖处理：
  - tool_requires flang-ohos/20.1.0（LLVM Flang，编译 .mod 私有接口，
    消费方 test_package 用同一工具链，见 manifest 的 knowledge_gained）。
  - xmlf90 是上游硬依赖（target_link_libraries PUBLIC xmlf90::xmlf90），
    制品仓无此包。上游自带 LibpsmlFindPackage.cmake，支持 SOURCE_DIR
    离线注入（add_subdirectory）：本 recipe 在 source() 用 conandata
    第二源下载并校验 xmlf90-1.6.3（上游 MIN_VERSION 1.5.4，1.6.3 自带
    CMake 框架且含 xml_parse stat 特性），generate() 传
    -DXMLF90_SOURCE_DIR 指过去，构建期零 git clone、零网络
    （E668 FetchContent 离线注入模式）。

上游测试（build() 内真实执行，ctest 12 项 = libpsml 6 + xmlf90 6）：
  examples/CMakeLists.txt 注册 6 项（getz/getz_die/getz_stat_non_existent/
  getz_stat_parsing/show/mgga），xmlf90 自带 testsuite 注册 6 项
  （XMLF90_SAX_Features/check/check_stat/Malformed/Malformed_stat/
  BadEntity）。计数唯一确定源为 ctest 经 -O 落盘的 stdout 日志
  （ctest_stdout.log，逐行解析 "N/M Test #K ... Passed|Failed"，
  与 netcdf-fortran 实测口径一致）；LastTest.log 仅作诊断交叉核对。

OHOS 补丁（patches/0001-xmlf90-scratch-tmpdir-fallback.patch）：
  xmlf90 的 find_eor_eof 用 STATUS="SCRATCH" 开 EOR/EOF 探测文件（运行库
  经 libc tmpfile() 在 /tmp 下建匿名临时文件），HarmonyOS 上 /tmp 缺失或
  不可写导致每次 open_xmlfile 都 STOP "Cannot open test file"、12 项全部
  未及断言即失败。补丁保留 SCRATCH 快捷路径，失败时回退到
  $TMPDIR/$TMP/$TEMP 下的显名临时文件（最后是当前目录，用完即删），
  EOR/EOF 探测语义不变，不弱化任何断言。
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibpsmlConan(ConanFile):
    name = "libpsml"
    version = "2.1.0"
    description = "Library to process PSML pseudopotential files (SIESTA/ESL)"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/siesta-project/libraries/libpsml"
    url = "https://gitlab.com/siesta-project/libraries/libpsml"

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

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libpsml is built natively on HarmonyOS PC "
                "(os=OHOS, arch=armv8); Fortran flags/sysroot paths below "
                "are OHOS-specific (same scope as netcdf-fortran)")

    def build_requirements(self):
        # .mod 文件是编译器私有二进制接口，消费方必须用同一 Flang。
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # xmlf90 第二源：解到源码树 external/ 下，供 generate() 以
        # -DXMLF90_SOURCE_DIR 离线注入（上游 source 机制，无需补丁）。
        get(self, **self.conan_data["sources"]["xmlf90-1.6.3"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "external",
                                     "xmlf90-1.6.3"))

    # ── Fortran 工具链（netcdf-fortran 实测口径，包名适配） ──────────
    def _sdk_native_or_none(self):
        """定位 OHOS SDK native 根；找不到时返回 None（由驱动反推兜底）。

        预检 runner 的 SDK 挂载点与 CI worker 可能不同，主 glob
        零命中不直接判死：先按 conf/环境变量/LD_LIBRARY_PATH 与
        驱动位置做最小回退；仍无则返回 None 让 _fortran_toolchain
        改问 C 驱动的 -print-sysroot/-print-resource-dir。
        """
        configured = self.conf.get("user.libpsml:sdk_native", default=None,
                                   check_type=str)
        if configured:
            candidates = [configured]
            searched = ["conf:user.libpsml:sdk_native=%s" % configured]
        else:
            candidates = []
            searched = []
            for pattern in (
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native",
                    "/data/service/hnp/ohos-sdk*/*/ohos/native",
                    "/data/service/hnp/*/ohos/native",
                    "/data/service/hnp/ohos-sdk*/*/native",
                    "/data/service/hnp/*/native",
                    "/opt/ohos-sdk*/native",
                    "/opt/ohos-sdk*/*/native"):
                hits = glob.glob(pattern)
                if hits:
                    candidates.extend(hits)
                searched.append(pattern)
            # harmonybrew Cellar 布局（本轮真机实证：
            # resource=/.../.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1/native/llvm/...，
            # 主 glob 全在 /data 下故空命中）。HOME 在真机为
            # /storage/Users/currentUser，必须展开后 glob。
            try:
                home = os.path.expanduser("~")
            except Exception:
                home = ""
            for pattern in (
                    os.path.join(home, ".harmonybrew", "Cellar",
                                 "ohos-sdk", "*", "native"),
                    os.path.join(home, ".harmonybrew", "Cellar",
                                 "ohos-sdk", "*", "*", "native"),
                    "/storage/*/.harmonybrew/Cellar/ohos-sdk/*/native",
                    "/storage/*/.harmonybrew/Cellar/ohos-sdk/*/*/native",
                    "/home/*/.harmonybrew/Cellar/ohos-sdk/*/native"):
                try:
                    hits = glob.glob(pattern)
                except Exception:
                    hits = []
                if hits:
                    candidates.extend(hits)
                searched.append(pattern)
            for env_key in ("OHOS_SDK_NATIVE", "OHOS_SDK", "OHOS_NDK_HOME"):
                env_val = os.environ.get(env_key, "")
                if env_val:
                    if env_key == "OHOS_SDK_NATIVE":
                        candidates.append(env_val)
                    else:
                        candidates.append(os.path.join(env_val, "native"))
                        candidates.append(env_val)
                    searched.append("env:%s=%s" % (env_key, env_val))
            for entry in os.environ.get("LD_LIBRARY_PATH", "").split(
                    os.pathsep):
                norm = entry.replace("\\", "/").rstrip("/")
                for marker in ("/ohos/native/llvm/lib",
                               "/native/llvm/lib"):
                    if marker in norm:
                        suffix = "/ohos/native" if "ohos" in marker else "/native"
                        root = norm.split(marker)[0] + suffix
                        if root not in candidates:
                            candidates.append(root)
            searched.append("LD_LIBRARY_PATH-derived")
            # 驱动位置反推：沿 realpath 逐级上走找 native 根（挂载点漂移时仍
            # 有效）。旧逻辑只按 parts.index("native") 取首个 native，对
            # harmonybrew 的 .../Cellar/ohos-sdk/26.0.0.18_1/native/llvm/bin
            # 应命中，但 sysroot 校验失败或 realpath 链异常时无诊断。本轮
            # 改为祖先目录逐级校验 + resource-dir 派生，双路互备。
            try:
                driver = self._resolve_driver_clang(quiet=True)
                real = os.path.realpath(driver)
                searched.append("driver-real=%s" % real)
                cur = os.path.dirname(real)
                for _ in range(8):
                    cand_native = None
                    base = os.path.basename(cur)
                    if base == "native":
                        cand_native = cur
                    elif os.path.isdir(os.path.join(cur, "native")):
                        # 如 .../ohos 下挂 native（旧布局 /.../ohos/native）
                        cand_native = os.path.join(cur, "native")
                    if cand_native and cand_native not in candidates:
                        candidates.append(cand_native)
                    parent = os.path.dirname(cur)
                    if parent == cur:
                        break
                    cur = parent
                # resource-dir 派生：.../native/llvm/lib/clang/X.Y.Z 上推到 native
                try:
                    env0 = os.environ.copy()
                    out = subprocess.run(
                        [real, "-print-resource-dir"], check=False, env=env0,
                        text=True, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=30).stdout.strip()
                    if out:
                        rreal = os.path.realpath(out)
                        searched.append("driver-resource=%s" % rreal)
                        c2 = rreal
                        for _ in range(8):
                            if os.path.basename(c2) == "native":
                                if c2 not in candidates:
                                    candidates.append(c2)
                                break
                            c2 = os.path.dirname(c2)
                except Exception as e_res:
                    self.output.warning(
                        "HMBS diag resource-derived native probe failed: %s"
                        % e_res)
            except Exception as e_drv:
                self.output.warning(
                    "HMBS diag driver-derived native probe failed: %s" % e_drv)
        valid = []
        rejected = []
        for candidate in candidates:
            if not candidate:
                continue
            candidate = os.path.realpath(candidate)
            required = (
                os.path.join(candidate, "sysroot"),
                os.path.join(candidate, "llvm", "bin"),
                os.path.join(candidate, "llvm", "lib"),
                os.path.join(candidate, "llvm", "lib", "aarch64-linux-ohos"),
            )
            clang = os.path.join(candidate, "llvm", "bin", "clang")
            missing = [p for p in required if not os.path.isdir(p)]
            if missing:
                rejected.append("%s缺%s" % (candidate, ";".join(missing)))
                continue
            if not (os.path.isfile(clang) and os.access(clang, os.X_OK)):
                rejected.append("%s缺可执行clang" % candidate)
                continue
            valid.append(candidate)
        valid = sorted(set(valid))
        if not valid:
            self.output.warning(
                "未找到完整 OHOS SDK native 根；已搜索 %s；候选拒绝明细 %s；"
                "LD=%s"
                % ("; ".join(searched), "; ".join(rejected[:10]),
                   os.environ.get("LD_LIBRARY_PATH", "")))
            return None
        if len(valid) > 1:
            self.output.warning(
                "发现 %d 个完整 OHOS SDK native 根，取最新：%s"
                % (len(valid), "; ".join(valid)))
            return valid[-1]
        return valid[0]

    def _sdk_native(self):
        found = self._sdk_native_or_none()
        if found is None:
            raise ConanInvalidConfiguration(
                "未找到完整的 OHOS SDK native 根；请在 conf 中设置 "
                "user.libpsml:sdk_native 明确指定")
        return found

    def _resolve_driver_clang(self, quiet=False):
        """按聚合经验#1：conf 存在即用，缺失时经 PATH 发现 C 驱动。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={},
            check_type=dict) or {}
        raw = compilers.get("c", "")
        ordered = []
        if raw:
            ordered.append(raw.split()[0] if isinstance(raw, str) else raw)
        which_hit = shutil.which("clang")
        if which_hit:
            ordered.append(which_hit)
        ordered.append("/data/service/hnp/bin/clang")
        for cand in ordered:
            if not cand:
                continue
            resolved = shutil.which(cand)
            if not resolved and os.path.isfile(cand) and os.access(
                    cand, os.X_OK):
                resolved = os.path.abspath(cand)
            if resolved:
                if not quiet:
                    self.output.info(
                        "HMBS diag C driver=%s (raw=%s)" % (resolved, raw))
                return resolved
        raise ConanInvalidConfiguration(
            "C 驱动均不可用（conf=%s，PATH clang=%s）；属环境故障"
            % (raw, which_hit))

    def _probe_driver(self, driver, extra_libpath):
        """问 C 驱动要 sysroot/resource-dir；失败返回 (None, None)。"""
        env = os.environ.copy()
        if extra_libpath:
            env["LD_LIBRARY_PATH"] = extra_libpath + os.pathsep + env.get(
                "LD_LIBRARY_PATH", "") if env.get(
                    "LD_LIBRARY_PATH") else extra_libpath
        sysroot = None
        resource_dir = None
        for flag in ("-print-sysroot", "-print-resource-dir"):
            try:
                out = subprocess.run(
                    [driver, flag], check=True, env=env, text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE).stdout.strip()
            except (OSError, subprocess.CalledProcessError) as error:
                self.output.warning(
                    "HMBS diag driver probe %s failed: %s" % (flag, error))
                continue
            if flag == "-print-sysroot" and out:
                cand = os.path.realpath(out)
                if os.path.isdir(cand):
                    sysroot = cand
            elif flag == "-print-resource-dir" and out:
                cand = os.path.realpath(out)
                if os.path.isdir(cand):
                    resource_dir = cand
        self.output.info(
            "HMBS diag driver probe sysroot=%s resource=%s"
            % (sysroot, resource_dir))
        return sysroot, resource_dir

    def _find_unwind_dir(self, driver, sysroot, resource_dir, sdk_native):
        """定位含 libunwind.a 的 -L 目录；找不到返回 None（让驱动默认）。"""
        tried = []
        cands = []
        if sdk_native:
            cands.append(os.path.join(sdk_native, "llvm", "lib",
                                      "aarch64-linux-ohos"))
        if resource_dir:
            cands.append(os.path.join(resource_dir, "..", "..", "..",
                                      "aarch64-linux-ohos"))
            cands.append(resource_dir)
        if sysroot:
            cands.append(os.path.join(sysroot, "usr", "lib",
                                      "aarch64-linux-ohos"))
        try:
            env = os.environ.copy()
            out = subprocess.run(
                [driver, "-print-search-dirs"], check=True, env=env,
                text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE).stdout
            for line in out.splitlines():
                if "libraries:" in line:
                    payload = line.split("=", 1)[1] if "=" in line else line
                    for sep in (":", ";"):
                        if sep in payload:
                            for piece in payload.split(sep):
                                piece = piece.strip().strip("=")
                                if piece:
                                    cands.append(piece)
                            break
                    break
        except (OSError, subprocess.CalledProcessError):
            pass
        for cand in cands:
            cand = os.path.normpath(cand)
            tried.append(cand)
            if os.path.isfile(os.path.join(cand, "libunwind.a")):
                self.output.info("HMBS diag unwind dir=%s" % cand)
                return cand
        self.output.warning(
            "HMBS diag libunwind.a not found; tried %s" % "; ".join(tried))
        return None

    def _derive_sysroot_from_known(self, resource_dir, unwind, driver_real):
        """从 resource/unwind/驱动祖先后推 sysroot；找不到返回 None。"""
        anchors = []
        for p in (resource_dir, unwind, driver_real):
            if p:
                anchors.append(p)
        for anchor in anchors:
            cur = anchor if os.path.isdir(anchor) else os.path.dirname(anchor)
            for _ in range(10):
                for cand in (os.path.join(cur, "sysroot"),
                             os.path.join(cur, "native", "sysroot")):
                    if os.path.isdir(cand):
                        return os.path.realpath(cand)
                if os.path.basename(cur) == "native":
                    cand = os.path.join(cur, "sysroot")
                    if os.path.isdir(cand):
                        return os.path.realpath(cand)
                parent = os.path.dirname(cur)
                if parent == cur:
                    break
                cur = parent
        return None

    def _fortran_toolchain(self):
        """返回 (flang 可执行文件, Fortran 编译 flags, 链接 flags, 运行期库目录)。"""
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        if not os.path.isfile(flang) or not os.path.isdir(flang_lib):
            raise ConanInvalidConfiguration("flang-ohos 工具包不完整")
        sdk_native = self._sdk_native_or_none()
        driver = self._resolve_driver_clang()
        if sdk_native:
            sdk_clang = os.path.join(sdk_native, "llvm", "bin", "clang")
            runtime_dirs = (os.path.join(sdk_native, "llvm", "lib"), flang_lib)
            probe_env = os.environ.copy()
            probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
            try:
                resource_dir = subprocess.run(
                    [sdk_clang, "-print-resource-dir"], check=True,
                    env=probe_env,
                    text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE).stdout.strip()
            except (OSError, subprocess.CalledProcessError) as error:
                raise ConanInvalidConfiguration(
                    "无法探测 OHOS SDK clang 的 resource-dir") from error
            resource_dir = os.path.realpath(resource_dir)
            if (not os.path.isdir(resource_dir)
                    or os.path.commonpath((sdk_native, resource_dir)) != sdk_native):
                raise ConanInvalidConfiguration("SDK clang 返回了 SDK 之外的 resource-dir")
            compile_flags = [
                "--target=aarch64-unknown-linux-ohos",
                "--sysroot={}".format(os.path.join(sdk_native, "sysroot")),
                "-resource-dir={}".format(resource_dir),
            ]
            link_flags = [
                "-L{}".format(os.path.join(sdk_native, "llvm", "lib",
                                           "aarch64-linux-ohos")),
            ]
        else:
            # SDK 挂载点漂移兜底：直接问 C 驱动要 sysroot/resource，
            # unwind 目录按搜索式定位。本轮真机实证 OHOS 包装 clang 的
            # `-print-sysroot` 直接 exit 1（故 sysroot=None），但
            # `-print-resource-dir` 成功返回
            # .../Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib/clang/15.0.4。
            # 无 sysroot 即无 Scrt1.o/crti.o/-lc（本轮 ld.lld 原样报错），
            # 不得再“留空让驱动默认”进破碎构建：必须从 resource/unwind/
            # 驱动祖先反推 native/sysroot，找不到才如实抛环境错。
            self.output.warning(
                "HMBS diag SDK glob 空命中，走 C 驱动反推：%s" % driver)
            drv_real = os.path.realpath(driver)
            drv_lib = os.path.dirname(drv_real)
            sysroot, resource_dir = self._probe_driver(driver, flang_lib)
            unwind = self._find_unwind_dir(driver, sysroot, resource_dir,
                                           None)
            if not sysroot:
                sysroot = self._derive_sysroot_from_known(
                    resource_dir, unwind, drv_real)
                if sysroot:
                    self.output.info(
                        "HMBS diag sysroot derived from known paths: %s"
                        % sysroot)
            runtime_dirs = tuple(dict.fromkeys(
                [d for d in (os.path.join(drv_lib, "..", "lib")
                             if os.path.isdir(os.path.join(drv_lib, "..",
                                                           "lib")) else None,
                             flang_lib) if d]))
            compile_flags = ["--target=aarch64-unknown-linux-ohos"]
            if sysroot:
                compile_flags.append("--sysroot={}".format(sysroot))
            if resource_dir:
                compile_flags.append(
                    "-resource-dir={}".format(resource_dir))
            link_flags = []
            if unwind:
                link_flags.append("-L{}".format(unwind))
            if not sysroot or not resource_dir:
                self.output.warning(
                    "HMBS diag 驱动反推不完整 sysroot=%s resource=%s "
                    "unwind=%s；继续真实构建，失败即如实报错"
                    % (sysroot, resource_dir, unwind))
            if not sysroot:
                raise ConanInvalidConfiguration(
                    "无法确定 OHOS sysroot（driver=%s resource=%s unwind=%s）；"
                    "属环境故障，已搜索驱动祖先/resource/unwind 派生"
                    % (drv_real, resource_dir, unwind))

        def _join(flags):
            return " ".join(flags).replace("\\", "/")

        return (flang.replace("\\", "/"), _join(compile_flags),
                _join(link_flags), runtime_dirs)

    def _apply_runtime_env(self):
        """构建期与测试运行期的加载路径，返回原值以便复原。"""
        dirs = []
        _flang, _flags, _link_flags, runtime_dirs = self._fortran_toolchain()
        dirs.extend(runtime_dirs)
        previous = os.environ.get("LD_LIBRARY_PATH")
        if previous:
            dirs.append(previous)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(dirs))
        return previous

    def generate(self):
        flang, fortran_flags, fortran_link_flags, _runtime_dirs = \
            self._fortran_toolchain()
        xmlf90_dir = os.path.join(self.source_folder, "external",
                                  "xmlf90-1.6.3")
        if not os.path.isfile(os.path.join(xmlf90_dir, "CMakeLists.txt")):
            raise ConanInvalidConfiguration(
                "xmlf90 第二源缺失：%s 下找不到 CMakeLists.txt" % xmlf90_dir)

        tc = CMakeToolchain(self)
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而
        # cmake 自带的平台文件叫 Platform/OHOS.cmake；名字对不上时平台变量
        # 留空（首当其冲 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空 → 产物无
        # DT_SONAME 并传染下游）。必须带 os 守卫，同 netcdf-fortran 先例。
        if self.settings.os in ("Linux", "OHOS") and str(self.settings.os) == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 跟随 options.shared，写死会让消费方的 -o shared=False 静默失效。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Signal 9 (SIGKILL，多为真机 OOM) 加固：强制串行构建。
        # HMBS 已注入 tools.build:jobs=1，本处在配方层再钉死一次，
        # 即使 runner 忽略 conf，峰值内存仍最低；不改测试语义。
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

        tc.variables["CMAKE_Fortran_COMPILER"] = flang
        tc.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = fortran_link_flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = fortran_link_flags

        # 上游 LibpsmlFindPackage 的 source 机制：有该目录即允许 source 路，
        # 但默认查找顺序 cmake→pkgconf→source→fetch，而 pkgconf 分支首行即
        # find_package(PkgConfig QUIET REQUIRED)，真机无 pkg-config 可执行
        # 文件时直接 FATAL，永远到不了 source（本轮预检实证）。按上游支持的
        # <name>_FIND_METHOD 变量强制只走 source，直达 add_subdirectory，
        # 大小写两路都传（函数内同时查 xmlf90/XMLF90）。
        tc.variables["XMLF90_SOURCE_DIR"] = xmlf90_dir.replace("\\", "/")
        tc.variables["xmlf90_FIND_METHOD"] = "source"
        tc.variables["XMLF90_FIND_METHOD"] = "source"
        tc.generate()

    def _apply_scratch_fallback(self):
        """python 回退：.patch 上下文漂移时同语义注入（幂等）。

        内联 BLOCK 回退（不新增任何子程序/符号）：flang 曾把后加的模块级
        open_probe_file 当外部符号处理，导致 xmlf90 示例链接时报
        undefined symbol，内联 BLOCK 可彻底避开该类链接问题。
        """
        target = os.path.join(self.source_folder, "external",
                              "xmlf90-1.6.3", "src", "sax",
                              "m_sax_reader.f90")
        try:
            with open(target, "r", encoding="utf-8",
                      errors="replace") as f:
                text = f.read()
        except OSError as e:
            raise ConanException(
                "scratch fallback: cannot read %s: %s" % (target, e))
        if "probe_fname" in text:
            self.output.info("HMBS diag scratch fallback already applied")
            return
        if "open_probe_file" in text:
            raise ConanException(
                "scratch fallback: stale open_probe_file helper present; "
                "refusing to mix with inline fallback")
        old = ('open(unit=lun,status="scratch",form="formatted", &\n'
               '     action="readwrite",position="rewind",iostat=iostat)')
        if old not in text:
            raise ConanException(
                "scratch fallback: anchor open() not found; refusing to guess")
        fallback = (
            old + '\n'
            'if (iostat /= 0) then\n'
            '! HarmonyOS has no writable /tmp for the libc tmpfile() behind\n'
            '! STATUS="SCRATCH": fall back to an explicitly-named file under\n'
            '! $TMPDIR/$TMP/$TEMP, else the current directory (deleted on close).\n'
            '! Only the constant EOR/EOF iostat codes are probed, so semantics hold.\n'
            '! BLOCK keeps the helper variables local: no new procedure, no new symbol.\n'
            '   block\n'
            '     character(len=256) :: probe_dir\n'
            '     character(len=300) :: probe_fname\n'
            '     character(len=16) :: probe_lun_str\n'
            '     integer :: probe_k\n'
            "     write(probe_lun_str,'(I0)') lun\n"
            '     do probe_k = 1, 4\n'
            '        probe_dir = ""\n'
            '        if (probe_k == 1) call get_environment_variable("TMPDIR",probe_dir)\n'
            '        if (probe_k == 2) call get_environment_variable("TMP",probe_dir)\n'
            '        if (probe_k == 3) call get_environment_variable("TEMP",probe_dir)\n'
            '        if (probe_k < 4 .and. len_trim(probe_dir) == 0) cycle\n'
            '        if (probe_k < 4) then\n'
            '           probe_fname = trim(probe_dir) // "/__xmlf90_eor_eof_probe_" // &\n'
            '                   trim(adjustl(probe_lun_str)) // ".tmp"\n'
            '        else\n'
            '           probe_fname = "__xmlf90_eor_eof_probe_" // &\n'
            '                   trim(adjustl(probe_lun_str)) // ".tmp"\n'
            '        endif\n'
            '        open(unit=lun,file=trim(probe_fname),form="formatted", &\n'
            '             action="readwrite",position="rewind",iostat=iostat)\n'
            '        if (iostat == 0) exit\n'
            '     enddo\n'
            '   end block\n'
            'endif')
        text = text.replace(old, fallback, 1)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        self.output.info("HMBS diag scratch fallback injected via python")

    def build(self):
        try:
            apply_conandata_patches(self)
        except ConanException as e:
            self.output.warning(
                "conandata patch missed context (%s); using python fallback"
                % e)
            self._apply_scratch_fallback()
        previous_ld_path = self._apply_runtime_env()
        try:
            cmake = CMake(self)
            cmake.configure()
            # Signal 9 加固：显式 -j1 串行构建，降低 OOM 被 kill 概率；
            # 与上方 CMAKE_BUILD_PARALLEL_LEVEL 双保险，不跳过任何测试。
            cmake.build(cli_args=["-j1"])
            # 真实执行上游全部注册用例（libpsml 6 + xmlf90 6 = 12 项）。
            self._run_upstream_tests(cmake)
        finally:
            if previous_ld_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous_ld_path

    # ── 上游 ctest 运行与计数（laz-perf 实测口径） ──────────────────
    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        # 双通道：conan 输出 + 原始 stdout，预检两边都能抓到。
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning("HMBS diag persist upstream failed: %s" % e)
        return line

    def _count_registered_ctest(self):
        count = 0
        try:
            bf = getattr(self, "build_folder", None) or ""
            for path in glob.glob(os.path.join(bf, "**", "CTestTestfile.cmake"),
                                  recursive=True):
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        for line in f:
                            if "add_test(" in line:
                                count += 1
                except OSError:
                    continue
        except Exception as e:
            self.output.warning("HMBS diag count ctest failed: %s" % e)
        return count

    def _find_last_test_logs(self):
        # cmake_layout 可能把真实 CTest 树放在 self.build_folder 下一级
        # （build/Release），单一固定路径必然 fail-open。主路径优先，
        # 全树 walk 深度封顶 6。
        bf = getattr(self, "build_folder", None) or ""
        candidates = [os.path.join(bf, "Testing", "Temporary",
                                   "LastTest.log")]
        try:
            if os.path.isdir(bf):
                base_depth = bf.count(os.sep)
                for cur, _dirs, files in os.walk(bf):
                    if "LastTest.log" in files:
                        full = os.path.join(cur, "LastTest.log")
                        if full not in candidates:
                            candidates.append(full)
                    if cur.count(os.sep) - base_depth > 6:
                        try:
                            _dirs[:] = []
                        except Exception:
                            pass
        except Exception:
            pass
        return candidates

    def _parse_ctest_lasttest(self):
        # 诊断交叉核对源（非标记计数源）：Testing/Temporary/LastTest.log。注意 ctest 只在
        # stdout 打印 "N/M Test #K:" 行；LastTest.log 里是每用例
        # "N/M Testing:" 头 + "Test Passed." / "***Failed" 等 verdict
        # 尾行，永远没有 "Test #K" 行——stdout 风格的正则在这里一个都
        # 匹配不上。禁止 stdout 数数、禁止算术修补：
        #   discovered： "N/M Testing:" / "N/M Test:" 头的分母 M（各条目
        #     必须一致，否则如实失败）
        #   passed/failed/skipped：verdict 短语单遍计数
        # 日志缺失时如实失败并列出搜过路径，宁缺毋假。
        candidates = self._find_last_test_logs()
        existing = [p for p in candidates if os.path.isfile(p)]
        non_empty = []
        for path in existing:
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            if content.strip():
                non_empty.append((path, content))
        if not non_empty:
            return (0, 0, 0, 0, [], candidates)

        def _entries(item):
            _p, _c = item
            return len(re.findall(r"(?m)^\s*\d+/\d+\s+Test(?:ing)?:", _c))

        # 真实构建树胜出（条目最多的日志）。
        non_empty.sort(key=_entries)
        log_path, text = non_empty[-1]
        try:
            text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
        except Exception:
            pass
        sizes = set(
            int(m.group(1))
            for m in re.finditer(r"(?m)^\s*\d+/(\d+)\s+Test(?:ing)?:", text)
        )
        if len(sizes) != 1:
            self.output.warning(
                "HMBS diag LastTest denominators disagree %s in %s"
                % (sorted(sizes), log_path))
            return (0, 0, 0, 0, [], candidates)
        discovered = sizes.pop()
        passed = len(re.findall(r"Test Passed", text))
        failed = len(re.findall(r"Test Failed", text))
        failed += len(re.findall(r"Test Timeout", text))
        failed += len(re.findall(r"\*\*\*Failed", text))
        failed += len(re.findall(r"\*\*\*Timeout", text))
        skipped = len(re.findall(r"Test Skipped", text))
        skipped += len(re.findall(r"\*\*\*Skipped", text))
        executed = passed + failed
        self.output.info(
            "HMBS diag LastTest.log=%s discovered=%d executed=%d "
            "passed=%d failed=%d skipped=%d"
            % (log_path, discovered, executed, passed, failed, skipped))
        return (passed, failed, skipped, discovered, [log_path], candidates)

    def _parse_ctest_stdout_log(self, path):
        # 单一确定源（本轮主用）：ctest 经 -O 落盘的 stdout 全量日志。
        # 逐行解析 "N/M Test #K: <name> ... <verdict>"（每用例恰一行，
        # 与 netcdf-fortran 实测口径一致），禁止 findall 数数后算术修补：
        #   discovered：各 "N/M Test #" 行分母 M（必须唯一，否则如实失败）
        #   passed/failed/skipped：同一行尾 verdict 词逐行单判（if/elif，
        #     一行只计一类，不存在双计；无已知 verdict 的行计 failed 并
        #     原样转储，宁严勿假绿）
        #   executed = passed + failed（定义，不做猜测修正）
        # 为何不用 LastTest.log 作主源：本轮预检 LastTest.log 分母为 12 但
        # verdict 短语零命中（discovered=12 executed=0），而 stdout 明确
        # 打印 "1/12 Test #1 ... Passed" 行；stdout 行是守则明示允许的
        # ctest 确定性来源之一。LastTest.log 保留作诊断交叉核对。
        try:
            with open(path, "r", encoding="utf-8",
                      errors="replace") as handle:
                raw = handle.read()
        except OSError as e:
            self.output.warning(
                "HMBS diag ctest stdout log unreadable %s: %s" % (path, e))
            return (0, 0, 0, 0, [], [path])
        if not raw.strip():
            return (0, 0, 0, 0, [], [path])
        try:
            text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", raw)
        except Exception:
            text = raw
        test_lines = []
        for line in text.splitlines():
            if re.match(r"^\s*\d+/\d+\s+Test\s+#\d+\s*:", line):
                test_lines.append(line)
        if not test_lines:
            self.output.warning(
                "HMBS diag ctest stdout log has no Test # lines: %s "
                "(size=%d)" % (path, len(raw)))
            return (0, 0, 0, 0, [], [path])
        sizes = set()
        for line in test_lines:
            m = re.match(r"^\s*\d+/(\d+)\s+Test\s+#\d+\s*:", line)
            if m:
                sizes.add(int(m.group(1)))
        if len(sizes) != 1:
            self.output.warning(
                "HMBS diag ctest stdout denominators disagree %s in %s"
                % (sorted(sizes), path))
            return (0, 0, 0, 0, [], [path])
        discovered = sizes.pop()
        passed = 0
        failed = 0
        skipped = 0
        unknown = []
        for line in test_lines:
            if re.search(r"\bPassed\b", line):
                passed += 1
            elif re.search(r"\bTimeout\b", line):
                failed += 1
            elif re.search(r"\bFailed\b", line):
                failed += 1
            elif (re.search(r"\bSkipped\b", line)
                    or re.search(r"\bNot Run\b", line)):
                skipped += 1
            else:
                unknown.append(line)
                failed += 1
        if unknown:
            self.output.warning(
                "HMBS diag ctest stdout %d Test # lines with unknown "
                "verdict (counted as failed):" % len(unknown))
            for line in unknown[:10]:
                self.output.warning("HMBS diag unknown verdict: %s" % line)
        executed = passed + failed
        self.output.info(
            "HMBS diag ctest-stdout.log=%s discovered=%d executed=%d "
            "passed=%d failed=%d skipped=%d testlines=%d"
            % (path, discovered, executed, passed, failed, skipped,
               len(test_lines)))
        return (passed, failed, skipped, discovered, [path], [path])

    def _run_upstream_tests(self, cmake):
        """运行上游 ctest 全量套件（L1），scratch 目录可写（E002 家族）。"""
        # 可写临时目录：Fortran 探测文件回退（$TMPDIR/$TMP/$TEMP/当前目录）
        # 与 CTest 工作树都需要它。os.environ 直接继承给 ctest 子进程；
        # env 脚本排在最后，确保本值覆盖注入的 conanbuild TMPDIR。
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir

        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self, scope="build").save_script("libpsml_ctest_env")

        # ctest stdout 全量落盘：-O 只做输出复制，不改变测试选择与语义；
        # 落盘文件是标记计数的唯一确定源（守则允许的 Test #N 逐行解析）。
        ctest_stdout_log = os.path.join(self.build_folder,
                                        "ctest_stdout.log")
        test_error = None
        try:
            cmake.ctest(cli_args=["--output-on-failure", "-O",
                                  ctest_stdout_log.replace("\\", "/")],
                        env=["conanbuild", "conanrun", "libpsml_ctest_env"])
        except Exception as e:
            test_error = e
            self.output.warning(
                "ctest failed (will emit upstream marker before re-raise): %s"
                % e)
        registered = self._count_registered_ctest()
        passed, failed, skipped, discovered, found, searched = \
            self._parse_ctest_stdout_log(ctest_stdout_log)
        # 诊断交叉核对：LastTest.log 只用于诊断回显，不参与标记计数。
        try:
            (lt_passed, lt_failed, lt_skipped, lt_discovered, lt_found,
             _lt_searched) = self._parse_ctest_lasttest()
            if lt_found:
                self.output.info(
                    "HMBS diag LastTest xcheck discovered=%d executed=%d "
                    "passed=%d failed=%d skipped=%d in %s"
                    % (lt_discovered, lt_passed + lt_failed, lt_passed,
                       lt_failed, lt_skipped, "; ".join(lt_found)))
                if (lt_discovered != discovered or lt_passed != passed
                        or lt_failed != failed):
                    self.output.warning(
                        "HMBS diag count drift: stdout-log "
                        "(d=%d p=%d f=%d) vs LastTest "
                        "(d=%d p=%d f=%d)" % (
                            discovered, passed, failed, lt_discovered,
                            lt_passed, lt_failed))
        except Exception as e_x:
            self.output.warning("HMBS diag LastTest xcheck failed: %s" % e_x)
        self.output.info(
            "HMBS diag registered ctest entries=%d stdout-log discovered=%d"
            % (registered, discovered))
        if not found:
            # 主源缺失时如实失败：转储 LastTest 搜过路径与 stdout 文件状态，
            # 宁缺毋假，不回退猜数。
            try:
                _lt, _lf, _ls, _ld, _lfd, lt_searched = \
                    self._parse_ctest_lasttest()
            except Exception:
                lt_searched = []
            try:
                stdout_state = ("missing" if not os.path.isfile(
                    ctest_stdout_log) else "size=%d" % os.path.getsize(
                        ctest_stdout_log))
            except Exception:
                stdout_state = "unknown"
            payload = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": registered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "ctest stdout log not found or unparseable "
                          "(%s: %s); LastTest searched: %s"
                          % (ctest_stdout_log, stdout_state,
                             "; ".join(lt_searched or searched)),
            }
            self._hmbs_emit_upstream(payload)
            if test_error is not None:
                raise test_error
            raise RuntimeError(
                "upstream tests left no parseable ctest stdout log: %s"
                % "; ".join(searched))
        # 自检恒等式（只诊断，不改数字）：passed+failed==executed；
        # executed+skipped<=discovered；executed<=discovered。
        executed = passed + failed
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered):
            payload = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": "count identities violated "
                          "(discovered=%d executed=%d passed=%d failed=%d "
                          "skipped=%d) in %s"
                          % (discovered, executed, passed, failed,
                             skipped, "; ".join(found)),
            }
            self._hmbs_emit_upstream(payload)
            if test_error is not None:
                raise test_error
            raise RuntimeError("upstream test counts inconsistent: %s"
                               % payload)
        if registered > 0 and discovered != registered:
            self.output.warning(
                "HMBS diag ctest count drift: LastTest discovered(%d) != "
                "registered(%d)" % (discovered, registered))
        status = "passed" if (test_error is None and failed == 0
                              and skipped == 0 and discovered > 0
                              and executed == discovered) else "failed"
        payload = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            payload["reason"] = (
                "upstream ctest not fully green (discovered=%d executed=%d "
                "passed=%d failed=%d skipped=%d) in %s"
                % (discovered, executed, passed, failed, skipped,
                   "; ".join(found)))
        self._hmbs_emit_upstream(payload)
        if test_error is not None:
            raise test_error
        if status != "passed":
            raise RuntimeError("upstream tests failed: %s" % payload)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # 真实上游结果随包携带，cache-hit 的 test_package 也能 re-emit。
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir,
                                                  "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s"
                                % e)
        if self.options.shared:
            self._sign_so()

    def _sign_so(self):
        # 鸿蒙 XPM：dlopen 的 .so 必须代码签名，否则 loader 拒绝加载。
        # 必须在 cmake.install() 之后：install 期 CMake 的 RPATH 改写会
        # 原位改字节、令链接器内置签名失效（netcdf-fortran 实测）。
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException(
                "os=OHOS 下 shared 产物必须重新签名，但 %s 不存在" % signer)
        # 签名器靠 loader 默认路径找 libc++，构建期 LD_LIBRARY_PATH
        #（含依赖 libdir）会遮蔽正确版本，必须清空（netcdf-fortran 实测）。
        env = "env -u LD_LIBRARY_PATH "
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets += glob.glob(os.path.join(self.package_folder, "lib",
                                               pattern))
        for path in targets:
            if os.path.islink(path):
                continue
            self.run('{env}{oc} --remove-section .codesign "{p}" '
                     '2>/dev/null || true'.format(env=env, oc=objcopy,
                                                  p=path))
            self.run('{env}{sg} sign -inFile "{p}" -outFile "{p}" -selfSign 1'
                     .format(env=env, sg=signer, p=path))

    def _mod_include_dirs(self):
        """包内含 .mod 文件的 include 子目录（相对路径，含顶层 include）。"""
        found = ["include"]
        try:
            inc = os.path.join(str(self.package_folder), "include")
            for cur, _dirs, files in os.walk(inc):
                if any(n.endswith(".mod") for n in files):
                    rel = os.path.relpath(cur, str(self.package_folder))
                    if rel not in found:
                        found.append(rel.replace("\\", "/"))
        except Exception:
            pass
        return found

    def package_info(self):
        # libpsml.a（OUTPUT_NAME psml）+ 随构建的 xmlf90（OUTPUT_NAME
        # xmlf90，静态链必备；上游 PUBLIC 链接，消费者同样需要它）。
        self.cpp_info.libs = ["psml", "xmlf90"]
        self.cpp_info.includedirs = self._mod_include_dirs()
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libpsml")
        self.cpp_info.set_property("cmake_target_name", "libpsml::libpsml")
        self.cpp_info.set_property("pkg_config_name", "libpsml")
