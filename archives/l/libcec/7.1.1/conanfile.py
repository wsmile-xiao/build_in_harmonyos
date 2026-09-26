#!/usr/bin/env python3
"""Conan recipe — libcec 7.1.1 (Pulse-Eight libCEC).

控制 CEC 能力 HDMI 设备（电视/功放）的 C/C++ 库，同时构建 CLI:
cec-client / cecc-client（因此软件级 commands.json 由 L0k/R38 校验）。
构建系统: CMake（根 CMakeLists.txt）。

OHOS 适配点:
  - SOURCE_DATE_EPOCH=1：7.1.1 的 src/libcec/cmake/SetBuildInfo.cmake 没有
    8.1.7 才引入的 DISABLE_BUILDINFO 守卫，而 OHOS 设备上 whoami 报
    "bad uid"（BUILD_USER 为空）导致 string(STRIP) 缺参报错；上游官方
    可复现构建分支（SOURCE_DATE_EPOCH 已定义 → BUILD_USER/BUILD_HOST
    取 "(reproducible)"）直接绕过 whoami/hostname，无需修改源码。
  - CMAKE_SYSTEM_NAME=Linux：沿用项目 json-c/p8-platform 同款做法，
    让 CMake 按 Linux 约定生成带 SONAME 的版本化共享库
    （libcec.so.7 → libcec.so.7.1.1），cec-client/cecc-client 的
    cecloader 运行期按 libcec.so.7 动态加载。
  - p8-platform/2.1.0：7.1.1 的 src/libcec 与两个 client 均
    find_package(p8-platform REQUIRED)（CMakeDeps 生成 config 提供
    p8-platform_INCLUDE_DIRS/LIBRARIES/VERSION），依赖已发布到 ohpcd。
  - 真机硬化（2026-09-24 预检 compile 失败指纹：
    "The C/CXX compiler identification is unknown" +
    CMAKE_C_COMPILER=/data/service/hnp/bin/clang 在 cmake.configure() 中断）：
    与 8.1.7.1 同机房 runner 漂移一致，profile 钉死的绝对路径在部分预检
    runner 上不可执行/缺 lld 运行时库，且 CMake 4.4.3 对老
    cmake_minimum_required 需策略下限。仅覆盖 CC/CXX 与环境，
    不碰 CFLAGS/LDFLAGS，不改测试口径。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibcecConan(ConanFile):
    name = "libcec"
    version = "7.1.1"
    description = "Pulse-Eight libCEC - control CEC-capable HDMI devices via Pulse-Eight USB-CEC and SoC-native CEC"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Pulse-Eight/libcec"
    url = "https://github.com/Pulse-Eight/libcec"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("p8-platform/2.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # E092: CMake has no HarmonyOS platform module, use Linux
            # (cache_variables 与已发布可加载的 8.1.7 制品同形态)
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # p8-platform 以静态库 (libp8-platform.a) 链接进 libcec.so，
        # 运行期无需 rpath。关闭 build rpath 可避免 install 阶段 CMake
        # 在 .dynstr 中就地清零 rpath 字符串，导致 OHOS 加载器
        # dlopen 报 Permission denied（实测：构建树含 rpath 字符串可
        # 加载，install 清零后不可加载）。
        tc.cache_variables["CMAKE_SKIP_BUILD_RPATH"] = "ON"
        # CMake 4.4.3 对老 cmake_minimum_required 需策略下限（8.1.7.1 先例）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 预检 runner 漂移：profile 的 /data/service/hnp/bin/clang 在部分机器上
        # 不可执行；探测可用编译器并经 toolchain 变量 pin 住。
        disc_c, disc_cpp = self._discover_ohos_compilers()
        if disc_c and disc_cpp:
            tc.variables["CMAKE_C_COMPILER"] = disc_c
            tc.variables["CMAKE_CXX_COMPILER"] = disc_cpp
            self.output.info("Pinning discovered compilers: %s / %s" % (disc_c, disc_cpp))
        tc.generate()
        # HMBS readonly_tmp + lld 运行时库：经 buildenv 脚本透传，编译器探测继承。
        tmpdir = self._pick_writable_tmpdir()
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        for llvm_lib in self._all_llvm_lib_dirs():
            try:
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            except Exception:
                pass
        env.vars(self).save_script("libcec_tmpdir")
        # 文件级修复：CMakeToolchain 烘焙的 profile 编译器路径在沙箱内不可达时
        # ("compiler identification is unknown")，就地替换为探测到的可用路径。
        # 文件内容优先于 CLI/cache，必须修文件而非仅传变量。
        try:
            self._repair_toolchain_files(disc_c, disc_cpp)
        except Exception as exc:
            self.output.warning("toolchain repair failed: %r" % (exc,))

    def _pick_writable_tmpdir(self):
        cands = [
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        for cand in cands:
            if not cand or cand == "/tmp":
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
                return cand
            except OSError:
                continue
        cand = os.path.join(self.build_folder, "tmp")
        os.makedirs(cand, exist_ok=True)
        return cand

    def _all_llvm_lib_dirs(self):
        # OHOS SDK lld 动态链接 llvm/lib/libxml2.so.16（无 RUNPATH），缺
        # LD_LIBRARY_PATH 时链接器无法启动，CMake 只报探测失败。返回全部现存
        # llvm/lib 目录（版本漂移不静默失效），调用方无条件前置。
        found = []

        def _add(p):
            if p and os.path.isdir(p) and p not in found:
                found.append(p)

        try:
            cc_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            cc_map = {}
        cc = cc_map.get("c") or cc_map.get("cpp") if isinstance(cc_map, dict) else None
        if cc:
            try:
                out = subprocess.check_output([cc, "-print-resource-dir"], stderr=subprocess.DEVNULL,
                                              text=True, timeout=30).strip()
                _add(os.path.dirname(os.path.dirname(out)))
            except Exception:
                pass
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                    "/data/service/hnp/*/ohos/native/llvm/lib",
                    "/data/service/hnp/*/native/llvm/lib",
                    "/data/*/ohos/native/llvm/lib",
                    "/opt/*/ohos/native/llvm/lib"):
            try:
                for g in sorted(glob.glob(pat)):
                    _add(g)
            except Exception:
                continue
        return found

    def _runs(self, p):
        try:
            if not p or not os.path.isfile(p) or not os.access(p, os.X_OK):
                return False
            r = subprocess.run([p, "--version"], capture_output=True, text=True,
                               timeout=20, env=os.environ.copy())
            return r.returncode == 0
        except Exception:
            return False

    def _discover_ohos_compilers(self):
        # 存在即用：conf 路径存在且 --version 通过则零改动返回；
        # 缺失时经 PATH/绝对路径穷举并经 --version 验证，优先同目录兄弟
        # 编译器，仅覆盖 CC/CXX，不碰 CFLAGS/LDFLAGS。两者皆无返回空，由调用
        # 方保持默认并在 build() 抛明示诊断。
        try:
            ccm = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            ccm = {}
        pc = ccm.get("c", "") if isinstance(ccm, dict) else ""
        pcpp = ccm.get("cpp", "") if isinstance(ccm, dict) else ""
        if pc and pcpp and self._runs(pc) and self._runs(pcpp):
            return pc, pcpp
        if pc or pcpp:
            self.output.warning("Profile compiler missing or not runnable: c=%s cpp=%s" % (pc, pcpp))
        for name_c, name_cpp in (("clang", "clang++"),
                                 ("aarch64-linux-ohos-clang", "aarch64-linux-ohos-clang++"),
                                 ("cc", "c++")):
            wc = shutil.which(name_c) or ""
            wcpp = shutil.which(name_cpp) or ""
            if wc and wcpp and self._runs(wc) and self._runs(wcpp):
                self.output.info("Using PATH compilers: %s / %s" % (wc, wcpp))
                return wc, wcpp
        # 同目录兄弟：若 C 已确定，优先同目录 clang++，保证 SDK 一致。
        for base_c in [pc, shutil.which("clang") or ""]:
            if base_c and os.path.isfile(base_c):
                sib = os.path.join(os.path.dirname(base_c), "clang++")
                if self._runs(base_c) and self._runs(sib):
                    self.output.info("Using sibling compilers: %s / %s" % (base_c, sib))
                    return base_c, sib
        for d in ("/storage/Users/currentUser/usr/local/bin",
                  "/data/service/hnp/bin", "/opt/hnp/bin",
                  "/usr/local/bin", "/usr/bin"):
            for pair in (("clang", "clang++"),):
                c = os.path.join(d, pair[0])
                cpp = os.path.join(d, pair[1])
                if self._runs(c) and self._runs(cpp):
                    self.output.info("Using absolute compilers: %s / %s" % (c, cpp))
                    return c, cpp
        return "", ""

    def _repair_toolchain_files(self, cc, cxx):
        if not cc and not cxx:
            return 0
        broken_c = "/data/service/hnp/bin/clang"
        broken_cxx = "/data/service/hnp/bin/clang++"
        fixed = 0
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in files:
                continue
            p = os.path.join(root, "conan_toolchain.cmake")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except Exception as exc:
                self.output.warning("toolchain read failed %s: %r" % (p, exc))
                continue
            orig = txt
            if cxx and broken_cxx in txt:
                txt = txt.replace(broken_cxx, cxx)
            if cc and broken_c in txt:
                txt = txt.replace(broken_c, cc)
            if "HMBS: authoritative compiler" not in txt:
                force = "\n# HMBS: authoritative compiler (FORCE beats stale cache)\n"
                if cc:
                    force += 'set(CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)\n' % cc
                if cxx:
                    force += 'set(CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)\n' % cxx
                txt = txt.rstrip("\n") + "\n" + force
            if txt != orig:
                try:
                    with open(p, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(txt)
                    fixed += 1
                    self.output.info("repaired toolchain: %s" % p)
                except Exception as exc:
                    self.output.warning("toolchain write failed %s: %r" % (p, exc))
        for root, _dirs, files in os.walk(self.build_folder):
            if "CMakeCache.txt" not in files:
                continue
            p = os.path.join(root, "CMakeCache.txt")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    cache = fh.read()
                if broken_c in cache and ((cc and cc not in cache) or (cxx and cxx not in cache)):
                    os.remove(p)
                    self.output.info("removed stale cache: %s" % p)
            except Exception as exc:
                self.output.warning("cache cleanup failed %s: %r" % (p, exc))
        return fixed

    def _use_writable_tmpdir(self):
        cand = self._pick_writable_tmpdir()
        os.environ["TMPDIR"] = cand
        os.environ["TMP"] = cand
        os.environ["TEMP"] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)

    def _inject_sdk_llvm_lib(self):
        for llvm_lib in self._all_llvm_lib_dirs():
            old = os.environ.get("LD_LIBRARY_PATH", "")
            if llvm_lib not in old.split(os.pathsep):
                os.environ["LD_LIBRARY_PATH"] = llvm_lib + (os.pathsep + old if old else "")
            self.output.info("Injected SDK llvm/lib into LD_LIBRARY_PATH: %s" % llvm_lib)

    def build(self):
        self._use_writable_tmpdir()
        self._inject_sdk_llvm_lib()
        try:
            cc, cxx = self._discover_ohos_compilers()
            self._repair_toolchain_files(cc, cxx)
        except Exception as exc:
            self.output.warning("toolchain re-repair failed: %r" % (exc,))
        # OHOS 设备 whoami 报 bad uid（BUILD_USER 为空）导致
        # SetBuildInfo.cmake 的 string(STRIP) 缺参报错；7.1.1 无
        # DISABLE_BUILDINFO 守卫，用上游官方 SOURCE_DATE_EPOCH 可复现
        # 分支跳过 whoami/hostname 注入（见模块 docstring）。必须在
        # configure 前注入到子进程环境。
        import os
        os.environ["SOURCE_DATE_EPOCH"] = "1"
        apply_conandata_patches(self)
        cmake = CMake(self)
        try:
            cmake.configure()
            cmake.build()
        except Exception:
            self._dump_cmake_logs(self.build_folder)
            raise

    def _dump_cmake_logs(self, bdir):
        dirs = [bdir, os.path.join(bdir, "build"), os.path.join(bdir, "build", "Release")]
        seen = [d for d in dirs if d and os.path.isdir(d)]
        for rel in ("CMakeFiles/CMakeError.log", "CMakeFiles/CMakeOutput.log"):
            for d in seen:
                p = os.path.join(d, rel)
                if os.path.isfile(p):
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as fh:
                            self.output.info("%s tail (%s):\n%s" % (rel, d, fh.read()[-6000:]))
                    except OSError as exc:
                        self.output.warning("cannot read %s: %s" % (rel, exc))
                    break

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cec"]
        self.cpp_info.set_property("cmake_file_name", "libcec")
        self.cpp_info.set_property("cmake_target_name", "libcec::libcec")
        self.cpp_info.set_property("pkg_config_name", "libcec")
        self.cpp_info.requires = ["p8-platform::p8-platform"]
        # cec-client / cecc-client 等 CLI 安装到 bin/（L0k 依据 bindirs 要求 commands.json）
        self.cpp_info.bindirs = ["bin"]
