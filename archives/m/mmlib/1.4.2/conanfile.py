#!/usr/bin/env python3
"""Conan recipe — mmlib 1.4.2 (meson)

mmlib — MindMaze 跨平台 C 工具库（日志 / 线程 / IPC / 时间 / 文件 / 内存辅助），
上游 meson 工程（C11，default_options c_std=c11）。本仓首适配：官方 main 与
Conan 制品仓均无 mmlib，版本保持 1.4.2（R37 双查不动）。

OHOS aarch64 适配要点
- 依赖面：无第三方运行期依赖。threads/dl/rt 为设备系统库——真机 clang 实测
  `-ldl -lrt -lm -lpthread` 全部可链接（musl 符号并入 libc），meson
  find_library 链接探测全部通过，无需补丁；OHOS 工具链默认 as-needed，
  libmmlib.so 的 DT_NEEDED 不含这些 stub 库（spice 同款实测口径）。
- 上游测试套件（check 框架，meson 注册 5 个程序）在 build() 内真实执行
  （ADAPTATION_GUIDE Step 3 / TEST_QUALITY_SPEC §3）：check/0.15.2 经
  test_requires 提供（只在 conan create 构建本包时生效，不进入消费者依赖
  链，先例 kea-hook 家族 gtest）；native OHOS 加 --timeout-multiplier=16
  （先例 glib/spice），cross 构建跳过执行。
- hmdfs 拒绝符号链接（ln -s EPERM）：meson 探测后跳过全部 symlinking，
  versioned 共享库缺 .so 开发链接（消费者 -lmmlib / CMakeDeps 均不可
  解析）。补丁 0001 按平台规范（no-versioned-soname：单一无版本文件）
  去掉 src/meson.build 中 shared_library 的 version 参数 → 单一 libmmlib.so。
- OHOS 内核/沙箱禁止 shebang 脚本直接 execve：顶层 meson.build 经
  run_command(find_program('read_version.py')) 取版本号，真机 configure
  阶段必然失败（先例 spice 0001）。补丁 0002 改为字面版本 '1.4.2'
  （与仓库 VERSION 文件内容一致），消除构建期脚本执行依赖。
- MesonToolchain 不写 ar/ranlib，cross 侧还缺 pkg-config：
  _inject_meson_binaries() 从编译器同目录推导 llvm-ar/llvm-ranlib 并注入
  conan_meson_native.ini / conan_meson_cross.ini（先例 glib/pixman/spice）。
- OHOS python3.12 的 subprocess 走 posix_spawn、不按 PATH 解析裸名：
  meson 为 python 程序，编译器探测在进程内 Popen，c='clang' 裸名必然
  [Errno 2]（cmake 原生二进制不受影响）。官方 profile 经 compiler_
  executables 给绝对路径；_absolutize_meson_binaries() 再把残留裸名用
  shutil.which 绝对化作兜底（真机实锤：subprocess.run(['clang']) ENOENT
  而 shutil.which/sh 均正常）。
- check 0.15.2 通信临时文件目录优先级 TEMP → P_tmpdir（musl="/tmp"，
  OHOS 只读）→ TMPDIR：真机 meson test 须前缀 TEMP=<可写目录>，否则
  check 系测试（testinternals/testapi）建立 fork 通信文件失败 exit 2
  （check_msg.c:317）。run_create 环境 TMPDIR 已指向家目录，但被
  P_tmpdir 短路，故必须显式 TEMP（补丁不可行：check 是二进制制品）。
- 上游测试两处移植性修复进补丁：0003 tests-child-proc 目标漏声明
  libcheck（conan 独立 prefix 下 check.h 不可见必挂）；0004 testlog.c
  的 abort 捕获须 sigsetjmp/siglongjmp（OHOS 上普通 longjmp 不恢复
  SIGABRT 掩码，第二次 abort 直接杀进程；真机最小复现三连捕验证）。
- 平台豁免（TEST_QUALITY_SPEC §3.3 / ADAPTATION_GUIDE §8）：真机实测 29 个
  上游 check 子测试因 OHOS 平台语义差异失败（OHOS musl 无 robust mutex API、
  无 IPv6 localhost、hmdfs 符号链接/硬链接/权限位语义、posix_memalign 不设
  ENOMEM、SOCK_SEQPACKET 断管 ECONNREFUSED 等），逐条经最小探针取值取证。
  _ohos_meson_test 解析 meson-logs/testlog.txt：失败集合 ⊆ 声明豁免名单则
  记录汇总后放行；名单外任何失败硬失败（不容忍真实回归）。豁免清单与根因
  见 test_package/MANIFEST.yml（platform_exemptions）。
- package() 后对 lib/**/*.so* 做 OHOS 重签名（binary-sign-tool，先例 glib）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class MmlibConan(ConanFile):
    name = "mmlib"
    version = "1.4.2"
    description = ("mmlib — cross-platform C utility library "
                   "(logging, threads, IPC, time, files, memory helpers)")
    license = "Apache-2.0"
    homepage = "https://github.com/mmlabs-mindmaze/mmlib"
    url = "https://github.com/mmlabs-mindmaze/mmlib"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 纯 C 库：删除消费者不需要的 C++ 设置（先例 glib）。
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # 无第三方运行期依赖：threads/dl/rt 为设备系统库（见文件头）。
        pass

    def build_requirements(self):
        # 上游测试套件（check 框架）在 build() 内真实执行；test_requires 只在
        # conan create 构建本包时生效，不向消费者传播（先例 kea-hook 家族）。
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        # MesonToolchain 不写 ar/ranlib；cross 侧还缺 pkg-config，Meson 会报
        # "Found pkg-config: NO" 而看不到 PkgConfigDeps 生成的 .pc（先例 glib/spice）。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_content = self._absolutize_meson_binaries(content)
            extras = []
            if ar and "\nar =" not in new_content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in new_content and "\npkgconfig =" not in new_content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if extras:
                new_content = new_content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1
                )
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    @staticmethod
    def _absolutize_meson_binaries(content):
        # OHOS 的 python3.12 subprocess 走 posix_spawn，不能像 sh 一样按 PATH
        # 解析裸名（subprocess.run(['clang']) → [Errno 2] No such file or
        # directory，shutil.which 同 PATH 却能解析）。Meson 是 python 程序，
        # 编译器探测在进程内 Popen，裸名 c='clang' 必然配置失败（CMake 为原生
        # 二进制，走自有 PATH 解析，不受影响）。官方 profile 经
        # tools.build:compiler_executables 提供绝对路径；本兜底把仍为裸名的
        # c/cpp/ar/ranlib 用 shutil.which 绝对化（Linux 宿主同样安全）。
        for key in ("c", "cpp", "ar", "ranlib"):
            marker = "\n%s = '" % key
            i = content.find(marker)
            if i < 0:
                continue
            j = content.find("'", i + len(marker))
            if j < 0:
                continue
            val = content[i + len(marker):j]
            if not val or os.path.sep in val:
                continue
            resolved = shutil.which(val)
            if resolved and os.path.isabs(resolved):
                content = content[:i + len(marker)] + resolved + content[j:]
        return content

    def _ensure_check_pc(self):
        # 上游 tests 开关请求 dependency('check')；check 由 test_requires 提供。
        # PkgConfigDeps 正常按包名生成 check.pc；若制品配方未提供 pkg-config
        # 元数据则补一份最小 .pc（仅构建期使用，不随包发布）。
        pc_path = os.path.join(self.generators_folder, "check.pc")
        if os.path.isfile(pc_path):
            return
        try:
            dep = self.dependencies["check"]  # create 构建期 test_requires 可见
        except Exception:
            return
        cpp = dep.cpp_info
        libdir = cpp.libdirs[0] if cpp.libdirs else "lib"
        incdir = cpp.includedirs[0] if cpp.includedirs else "include"
        abs_libdir = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
        abs_incdir = incdir if os.path.isabs(incdir) else os.path.join(dep.package_folder, incdir)
        libs = " ".join("-l%s" % l for l in (cpp.libs or ["check"]))
        text = "\n".join([
            "exec_prefix=${prefix}",
            "prefix=%s" % dep.package_folder,
            "libdir=%s" % abs_libdir,
            "includedir=%s" % abs_incdir,
            "",
            "Name: check",
            "Description: Unit testing framework for C",
            "Version: 0.15.2",
            "Libs: -L${libdir} %s -lm -lpthread" % libs,
            "Libs.private: %s" % libs,
            "Cflags: -I${includedir}",
        ])
        open(pc_path, "w").write(text + "\n")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._ensure_check_pc()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["tests"] = "enabled"   # 上游套件在 build() 内真实执行
        tc.project_options["docs"] = "disabled"   # sphinx/linuxdoc 不在依赖链
        tc.project_options["nls"] = "disabled"    # gettext/msgfmt 不在依赖链
        tc.generate()
        self._inject_meson_binaries()

    # ── 平台豁免名单（suite:case；TEST_QUALITY_SPEC §3.3 已声明豁免）──────
    # 真机 OHOS aarch64 conan create 实测：testapi 69 条 not-ok 失败子测试、
    # 29 个 check 用例失败，根因全部为平台语义差异（非配方缺陷），逐条经
    # 最小探针与单用例隔离运行取证（值见 test_package/MANIFEST.yml 与
    # notes.md）。名单外的任何失败都会硬失败——不放行真实回归。
    _OHOS_TEST_EXEMPTIONS = frozenset([
        "allocation:aligned_heap_allocation_error",
        "file:check_access_mode",
        "file:copy_fail",
        "file:copy_file",
        "file:copy_symlink",
        "file:dangling_symlink",
        "file:dir_symbolic_link",
        "file:hard_link",
        "file:path_stat",
        "file:rename_empty_directory",
        "file:symbolic_link",
        "ipc:broken_pipe",
        "process:spawn_daemon_error",
        "process:spawn_error",
        "process:wait_signal",
        "socket:create_invalid_sockclient",
        "socket:create_sockclient",
        "socket:getaddrinfo_error",
        "socket:getaddrinfo_valid",
        "socket:read_on_localhost",
        "socket:recv_multimsg_on_localhost",
        "socket:recv_on_localhost",
        "socket:recvmsg_on_localhost",
        "socket:send_multimsg_on_localhost",
        "socket:send_on_localhost",
        "socket:sendmsg_on_localhost",
        "socket:test_getpeername",
        "socket:write_on_localhost",
        "thread:robust_mutex",
    ])

    def _check_ohos_test_failures(self, build_folder):
        # meson test 对 testapi 的 TAP 结果整体判 ERROR（exit != 0）：解析
        # meson-logs/testlog.txt 把失败子测试归到 suite:case，仅当全部命中
        # _OHOS_TEST_EXEMPTIONS 时放行，其余情况抛 ConanException 硬失败。
        import re
        logfile = os.path.join(build_folder, "meson-logs", "testlog.txt")
        content = ""
        if os.path.isfile(logfile):
            with open(logfile, errors="replace") as f:
                content = f.read()
        # 注意：check 子进程可能污染 TAP 行（真机实测 "not ok" 前粘连了
        # 子进程 printf 的调试输出），故按子串而非行首匹配。
        failed = {}
        for m in re.finditer(
                r"not ok \d+ - [^:\n]+:([A-Za-z_0-9]+):([A-Za-z_0-9]+):", content):
            key = "%s:%s" % (m.group(1), m.group(2))
            failed[key] = failed.get(key, 0) + 1
        unexpected = sorted(k for k in failed
                            if k not in self._OHOS_TEST_EXEMPTIONS)
        if unexpected or not failed:
            detail = (", ".join("%s (%d)" % (k, failed[k]) for k in unexpected)
                      if unexpected else
                      "no failing subtest parsed from %s" % logfile)
            raise ConanException(
                "ohos meson.test failed: failures not covered by declared "
                "platform exemptions: " + detail)
        self.output.info(
            "ohos meson.test: %d failing subtest assertion(s) across %d "
            "case(s), all covered by declared platform exemptions "
            "(test_package/MANIFEST.yml platform_exemptions)"
            % (sum(failed.values()), len(failed)))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游官方测试（ADAPTATION_GUIDE Step 3 / TEST_QUALITY_SPEC §3）──
        # cross 构建跳过执行（OHOS 二进制无法在 Linux 构建宿主运行）。
        # native OHOS：meson test 加 --timeout-multiplier=16（先例 glib/spice）。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries not runnable on build host)"
            )
        else:
            if os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    # check 0.15.2 通信临时文件目录优先级 TEMP → P_tmpdir
                    # （musl 定义为 "/tmp"，OHOS 只读）→ TMPDIR；必须显式给
                    # TEMP 指到可写目录，否则 check 系测试（testinternals/
                    # testapi）建立 fork 通信文件失败（exit 2，真机实测
                    # check_msg.c:317 "Unable to create temporary file..."）。
                    tmp_dir = (os.environ.get("TMPDIR")
                               or os.environ.get("HOME")
                               or build_folder)
                    try:
                        self.run(
                            'TEMP="{}" meson test -v -C "{}" '
                            "--timeout-multiplier=16 --no-rebuild".format(
                                tmp_dir, build_folder)
                        )
                    except ConanException:
                        # testapi 含平台语义豁免子测试：失败集合 ⊆ 已声明豁免
                        # 名单时记录汇总后放行；名单外失败在 helper 内硬失败。
                        self._check_ohos_test_failures(build_folder)

                meson.test = _ohos_meson_test
            meson.test()

    def _sign_shared_libs(self):
        # Native OHOS worker: re-sign after meson install rewrites rpath.
        # Cross Docker SDK (oh_compile): binary-sign-tool may be absent — skip.
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["mmlib"]
        self.cpp_info.set_property("cmake_file_name", "mmlib")
        self.cpp_info.set_property("cmake_target_name", "mmlib::mmlib")
        self.cpp_info.set_property("pkg_config_name", "mmlib")
        if self.settings.os in ("Linux", "OHOS"):
            # 真机 clang 实测 -ldl/-lrt/-lm/-lpthread 全部可链接（musl 符号并入 libc）
            self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
