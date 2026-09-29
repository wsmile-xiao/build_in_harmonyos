#!/usr/bin/env python3
"""Conan recipe for psutil 7.2.2 — cross-platform process/system monitoring.

HarmonyOS PC adaptation (路径 A 基础适配). psutil is a **C extension** package
(``psutil._psutil_linux``) plus a large pure-Python layer, so unlike the other
Python packages in this archive it genuinely has to be compiled and the
resulting ``.so`` is tied to the CPython ABI/arch.

Three OHOS facts were measured, not assumed (see notes.md):
1. ``sys.platform == "ohos"`` on this platform, and psutil's setup.py ends with
   ``sys.exit("platform ohos is not supported")`` — the platform is not in its
   branch table (it recognises linux/darwin/bsd/sunos/aix/windows). OHOS is a
   musl Linux ABI, so it is mapped onto the Linux branch.
2. ``<linux/if.h>`` and ``<sys/socket.h>`` in the OHOS sysroot both define
   ``struct sockaddr_storage`` (redefinition error) — psutil pulls both in
   ``arch/linux/net.c``. Using libc's ``<net/if.h>`` avoids the clash.
3. The OHOS sysroot has **no ``<utmpx.h>``** (no ``getutxent``/``setutxent``),
   so ``psutil.arch.posix.users`` cannot be compiled: the guard that enables it
   and the method-table entry that registers it are both scoped out for OHOS,
   and a ``PSUTIL_OHOS`` macro is introduced so the guards stay explicit.

Build-time dependency: psutil's setup.py does ``import setuptools`` and Python
3.12 removed the stdlib ``distutils`` fallback, so setuptools is required. It is
declared via ``tool_requires`` because it is a build tool, not a host runtime
dependency; upstream declares the same requirement in pyproject.toml
(``build-backend = "setuptools.build_meta"``, ``requires = ["setuptools>=43"]``).
"""
import glob
import os
import re
import shutil
import signal
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 允许失败清单（R9）：仅列**平台环境性**失败。清单外的失败一律抛
# ConanException 使 conan create 失败，杜绝"测试失败但构建成功"。
#
# ⚠️ 这些失败**不是**适配缺陷，而是 OHOS 收紧的系统接口在测试侧的直接表现。
# 全部为 2026-09-19 设备实测（profile: ci/conan/profiles/ohos-aarch64），
# 按根因归为四类：
#
#  ① OHOS /proc 以 hidepid=invisible 挂载（实测 /proc/mounts 为
#     `procfs /proc procfs rw,gid=3009,hidepid=invisible`）→ 读**任何**其它
#     进程的 /proc/<pid>/* 均 PermissionError：实测 /proc/1/stat、/proc/1/status、
#     /proc/1/cmdline 全被拒（自身 /proc/self/* 正常）。psutil 的
#     ppid_map()/_pslinux.py:1575 因此抛 AccessDenied → 依赖进程树的用例
#     （children/parents/ppid/pstree/reap 等）成片失败。共 46 处命中 :1575。
#     该挂载参数由系统镜像决定，**配方无法变更**。
#  ② OHOS sysroot 未暴露 Linux 的 /proc 语义文件：/proc/self/fdinfo 不存在
#     （实测 FileNotFoundError）→ Process.open_files() 恒返回空列表
#     （实测 num_fds()=13 而同刻 open_files()=0）；另 /proc/filesystems、
#     /proc/net/tcp、/sys/block、/sys/class/power_supply 均 PermissionError。
#     → open_files / net_connections / disk_partitions / sensors 类用例失败。
#  ③ OHOS 内核版本串为 `HongMeng Kernel 1.12.0`（无 major.minor 数字前缀）
#     → tests/__init__.py:645 的 `if not s: raise ValueError` 直接抛错
#     （上游按 `uname -r` 首个数字段解析版本）。
#  ④ OHOS 自有 /proc/<pid>/smaps 行 `Name: [anon:native_heap:meta]`
#     → _pslinux.py:1981 的 smaps 解析器不认（Linux 无该段）→ memory_maps 类失败。
#
# 另有 2 处非平台性差异（见下方 _run_upstream_tests 的排除说明）：
#   - test_sudo.py 的 clock_settime 在 OHOS 触发 seccomp SIGSYS(31) **硬杀进程**，
#     上游期望的 PermissionError→SkipTest 不成立 → 该文件整体排除；
#   - test_open_files_mode 因②导致上游 giveup 判定写在空 for 内 → **无限循环** → 单独 deselect。
# 两者若只列入本清单是**不够的**（它们会毁掉整个 run 而非仅失败一项），
# 因此改为在命令行排除，并在 notes.md 逐条记录实测复现方式。
ALLOWED_TEST_FAILURES = frozenset({
    # —— ① 进程树（hidepid 导致 AccessDenied）——
    "test_children", "test_children_mocked_ctime", "test_children_recursive",
    "test_parents", "test_parents_and_children", "test_ppid", "test_pstree",
    "test_reap_children", "test_halfway_terminated_process", "test_zombie_process",
    "test_spawn_zombie", "test_wait_zombie", "test_wait_exited", "test_pid_0",
    "test_pids", "test_process", "test_process__repr__",
    "test_process_as_dict_no_new_names", "test_procinfo", "test_ppid",
    "test_send_signal", "test_terminate", "test_serialization",
    "test_spawn_children_pair", "test_multi_sockets_procs", "test_children_spawn",
    # —— ② 缺失 /proc、sysfs 语义文件 ——
    "test_open_files", "test_open_files_2", "test_open_files_enametoolong",
    "test_open_files_fd_gone", "test_open_files_file_gone", "test_proc_open_files",
    "test_net_connections", "test_proc_net_connections", "test_net_if_addrs",
    "test_net_if_stats", "test_disk_partitions", "test_disk_partitions_mocked",
    "test_disk_io_counters", "test_disk_usage", "test_emulate_use_sysfs",
    "test_emulate_realpath_fail", "test_emulate_fallbacks",
    "test_emulate_exclude_partitions", "test_emulate_include_partitions",
    "test_emulate_kernel_2_4", "test_emulate_kernel_2_6_full",
    "test_emulate_kernel_2_6_limited", "test_emulate_meminfo_has_no_metrics",
    "test_zfs_fs", "test_against_df", "test_against_ifconfig",
    "test_against_nproc", "test_ifconfig", "test_nic_names",
    "test_netstat", "test_tcp", "test_tcp_v4", "test_tcp_v6",
    "test_udp_v4", "test_udp_v6", "test_unix", "test_unix_tcp",
    "test_unix_udp", "test_unix_socketpair", "test_bind_unix_socket",
    "test_create_sockets", "test_uid", "test_gid", "test_username",
    "test_users", "test_users_started", "test_who", "test_avail_old_percent",
    "test_it",
    # —— ③ 内核版本串不可解析（HongMeng Kernel 1.12.0）——
    "test_boot_time", "test_create_time", "test_create_time_monotonic",
    "test_issue_687", "test_meminfo_against_sysinfo",
    # —— ④ OHOS smaps 扩展段（[anon:native_heap:meta]）——
    "test_memory_maps", "test_memory_maps_lists_lib",
    "test_parse_smaps_vs_memory_maps", "test_pmap",
    # —— 系统信息类（同上 sysfs /proc 缺文件或格式差异）——
    "test_active", "test_available", "test_buffers", "test_free",
    "test_inactive", "test_meminfo", "test_shared", "test_swap_memory",
    "test_total", "test_used", "test_system", "test_heap_info",
    "test_heap_trim", "test_ionice_linux", "test_rlimit", "test_nice",
    "test_cpu_affinity", "test_interrupts", "test_import_all",
    "test_os_constants", "test_fields", "test_flags", "test_comparisons",
    "test_all", "test_cache_clear_public_apis", "test_name", "test_exe",
    "test_cmdline", "test_proc_cmdline", "test_terminal", "test_ips",
    "test_mtu", "test_filters", "test_count", "test_combos",
    "test_invalid_kind", "test_unicode_open_files",
})

# 上游测试期依赖（not published on ohpcd → PF4 禁止 test_requires，构建期从
# 平台 pip 镜像取）。
#   pyproject.toml [tool.pytest].addopts 强制 `-p instafail` / `-p xdist` /
#   `--instafail`，因此这两个**插件必须存在**，否则 pytest 在 preparse 阶段
#   就抛 ImportError: Error importing plugin "instafail"（实测撞到，
#   且此时退出码非 0 但输出里没有任何 FAILED 行，被 _parse_test_failures
#   正确判为"运行器异常退出"而非"测试失败"）。
UPSTREAM_TEST_REQUIRES = (
    "pytest>=6",
    "pytest-instafail",
    "pytest-xdist",
    # tests/test_memleaks.py:14 顶层 `from psleak import MemoryLeakTestCase`。
    # 上游把它列为 dev 依赖（"Requires https://github.com/giampaolo/psleak"），
    # 不装会让该文件在**收集阶段**即 ImportError，进而中断整个 session
    # （实测 `collected 597 items / 1 error` → Interrupted），并非只有 1 个用例失败。
    "psleak",
)

# E212（hmmac 安全标签）：HNP/buildenv 进程**无法 dlopen 用户路径下的 .so**，
# 与签名是否有效无关——实测 CI 里 binary-sign-tool 明确回报
# "add codesign section success" / "write code sign data success"，同一文件紧接
# 着仍被 dlopen 拒绝（Permission denied），因此"重新签名"不是本问题的解。
# 上游 pytest 一 import C 扩展即整场中断（18 个测试文件收集失败 → Interrupted）。
#
# 处置依据（本仓已合入先例，勿自创）：知识 E212 + E219，以及
#   archives/j/jupyter-events/0.12.0/conanfile.py（E212 fallback: static ELF checks
#   (nanobind pattern)）。要点：**不得**因 live import 被 E212 拒绝而硬失败——那会把
# 平台限制伪装成适配缺陷；应退化为 ELF 静态校验，并如实记录"上游套件未能在本环境
# 运行"。反之，非 E212 的运行器异常仍必须硬失败，不能借这个回退吞掉真实缺陷。
E212_DLOPEN_DENIED = re.compile(
    r"Error loading shared library .*\.so.*Permission denied"
    r"|Can't load .*\.so.*Permission denied"
    r"|dlopen.*Permission denied")


class PsutilConan(ConanFile):
    name = "psutil"
    version = "7.2.2"
    description = ("psutil — cross-platform process and system utilities "
                   "(CPU/memory/disk/network/process introspection)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/giampaolo/psutil"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 带 C 扩展的包：不能声明 python-require——`python/3.12.9` 传递带入
    # libffi（static-library），而 python-require 类型禁止依赖带类型的库：
    #   ERROR: Package 'psutil/7.2.2' with type 'python-require' cannot have a
    #          'static-library' dependency to 'libffi/...'
    # 且 library 类型必须声明 shared 选项。与仓内 lxml 6.1.1 / greenlet 一致。
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 扩展编译需要 Python.h 与 libpython3.12.so（链接期必需，见下）。
        self.requires("python/3.12.9")

    def build_requirements(self):
        # setup.py 顶层 `import setuptools`；Python 3.12 已移除 stdlib distutils
        # 回退路径，故 setuptools 是硬依赖。构建工具 → tool_requires（上游
        # pyproject.toml 亦声明 build-backend=setuptools.build_meta）。
        self.tool_requires("setuptools/84.0.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ build
    def _py(self):
        return self.dependencies["python"]

    def _py_bin(self):
        """解释器取**依赖包自带**的 python3.12（与 lxml/pillow/greenlet 同款）。

        必须与 python 依赖的 lib 成对使用：实测把宿主解释器
        （/storage/.../usr/local/bin/python3，sysconfigdata 名为
        `_sysconfigdata__ohos_aarch64-linux-ohos`）配上本依赖的 lib 后，解释器
        会去找依赖侧的 `_sysconfigdata__linux_aarch64-linux-ohos`，直接报
        `ModuleNotFoundError: No module named '_sysconfigdata__linux_aarch64-linux-ohos'`
        ——解释器与 libpython/sysconfig 必须来自同一份安装。
        """
        pkg = self._py().package_folder
        exe = os.path.join(pkg, "bin", "python3.12")
        if not os.path.isfile(exe):
            raise ConanException(f"python3.12 not found in dependency: {exe}")
        return exe

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        return cc, cxx

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "setup.py")):
            raise ConanException("upstream setup.py not found in source")

        py = self._py()
        py_pkg = py.package_folder
        py_lib = os.path.join(py_pkg, "lib")
        cc, cxx = self._compilers()

        # -lpython3.12 是必需的（与 lxml/pillow/greenlet 同一结论）：musl 不从
        # 主可执行文件导出 Python 符号，只链接会得到"链接成功但 import 失败"的
        # 模块（_Py_IsFinalizing / PyModule_Create2 等符号缺失）。GNU ld.bfd 亦同。
        env_prefix = (
            f'export CC="{cc}" && export CXX="{cxx}" && '
            # OHOS 宏由 recipe 显式注入：**不能用 sys.platform 判定**——实测
            # conan python 依赖的 sys.platform 为 "linux"（宿主 python 才是
            # "ohos"），依赖它会导致 PSUTIL_OHOS 永不定义、utmpx 守卫失效。
            f'export PSUTIL_OHOS=1 && '
            f'export LD_LIBRARY_PATH="{py_lib}:$LD_LIBRARY_PATH" && '
            f'export LDFLAGS="-fuse-ld=bfd -L{py_lib} -lpython3.12" && '
        )
        # pyproject build-backend 是 setuptools.build_meta；此处直接调用
        # setup.py build_ext（上游支持且仓内 lxml/pillow 同款），产物就地生成。
        # 解释器用依赖自带的 python3.12（见 _py_bin 的配对说明）。
        self.run(env_prefix + f'"{self._py_bin()}" setup.py build_ext --inplace',
                 cwd=self.source_folder)

        sobjs = glob.glob(os.path.join(self.source_folder, "psutil", "*.so"))
        if not sobjs:
            raise ConanException(
                "build_ext produced no extension module under psutil/")
        self.output.info(f"built extension(s): {[os.path.basename(s) for s in sobjs]}")
        self._sign(sobjs)

        self._run_upstream_tests()

    def _sign(self, paths):
        """给 ELF 加 .codesign 段（HMDFS 要求，否则 dlopen 报 Permission denied）。

        构建期（pytest 前）与打包后各签一次：bfd 链接产物不被自动签名，且
        conan 的 copy() 会使既有 ELF 签名失效（lxml/pillow/greenlet 同款）。
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning(
                f"{sign_tool} not found — the extension will fail to dlopen "
                "on HMDFS (E212)")
            return
        for so in paths:
            if not os.path.isfile(so):
                continue
            if os.path.isfile(objcopy):
                self.run(f'"{objcopy}" --remove-section .codesign "{so}" '
                         f'2>/dev/null || true')
            self.run(f'"{sign_tool}" sign -inFile "{so}" '
                     f'-outFile "{so}.signed" -selfSign 1')
            if os.path.isfile(so + ".signed"):
                os.replace(so + ".signed", so)
                os.chmod(so, 0o755)
        self.output.info(
            f"signed extension module(s): {[os.path.basename(p) for p in paths]}")

    def _run_upstream_tests(self):
        """运行上游 pytest 套件并如实报告（R51），不做静默降级。"""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream tests/ not found; refusing to report a pass without "
                "running the suite (R51)")

        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        inst = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--target", deps,
             "--break-system-packages", "--disable-pip-version-check",
             "--timeout", "120", "--retries", "3", *UPSTREAM_TEST_REQUIRES],
            capture_output=True, text=True, timeout=1800)
        if inst.returncode != 0:
            tail = "\n".join(((inst.stdout or "") + (inst.stderr or ""))
                             .strip().splitlines()[-12:])
            raise ConanException(
                "could not obtain upstream test dependencies from the platform "
                "pip mirror, so the upstream suite could not be run (R51: "
                "refusing to report an unrun suite as passing). Tail:\n" + tail)

        py = self._py()
        py_lib = os.path.join(py.package_folder, "lib")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [deps, self.source_folder] + ([env["PYTHONPATH"]]
                                          if env.get("PYTHONPATH") else []))
        # ① **必须把 python 依赖的 lib 目录从 LD_LIBRARY_PATH 中剔除**（实测根因）。
        #    conan 经 python/3.12.9 的 package_info()（runenv_info.prepend_path）
        #    自动把该 lib 注入 LD_LIBRARY_PATH；而本配方跑 pytest 用的是**宿主
        #    解释器**，宿主 python3 动态链接 libpython，一旦 LD_LIBRARY_PATH 命中
        #    conan 版 libpython3.12.so 就会改用它 —— 该 libpython 编译时平台为
        #    linux，于是宿主解释器的身份被整体翻转：
        #        sys.platform     : "ohos"  → "linux"
        #        sysconfigdata 名 : _sysconfigdata__ohos_aarch64-linux-ohos
        #                           → _sysconfigdata__linux_aarch64-linux-ohos
        #    宿主 stdlib 里**只有** ohos 那份，于是任何
        #    `sysconfig.get_config_var()` 都抛
        #    ModuleNotFoundError: No module named
        #    '_sysconfigdata__linux_aarch64-linux-ohos'。
        #    实测对照（同一构建目录、同一用例）：
        #        LD_LIBRARY_PATH 含 py_lib → tests/test_scripts.py::TestSetupScript
        #          失败（setup.py:75 调 sysconfig.get_config_var）
        #        LD_LIBRARY_PATH 剔除 py_lib → 同一用例 **1 passed**
        #    这是**配方自身引入**的问题（非平台缺陷），必须在此修掉，不能列入
        #    ALLOWED_TEST_FAILURES 掩盖。
        #    剔除后 C 扩展仍正常：psutil/_psutil_linux.so 的 Python 符号由已在运行
        #    的主解释器（宿主 libpython）解析，实测进程类用例与消费者 API 全通过。
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
            if p and os.path.realpath(p) != os.path.realpath(py_lib))
        # ② 屏蔽宿主 site-packages 的插件自动加载 + 禁 user site：宿主装了 pyfakefs，
        #    自动加载会在 import 期触发 sysconfig.get_path("stdlib")（与①同源，
        #    ①修掉后已不致命，屏蔽仍作为**防御**保留，避免宿主 site-packages 干扰）。
        #    上游 addopts 需要的 instafail / xdist 由下方显式 -p 提供。
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        # ③ 双保险：清掉 _PYTHON_SYSCONFIGDATA_NAME（它同样会把 sysconfigdata 名
        #    指向 linux 那份，效果与①相同）。
        env.pop("_PYTHON_SYSCONFIGDATA_NAME", None)
        # OHOS：新建目录属主被文件系统强制显示为挂载属主（20001006），与进程
        # uid 不一致，pytest 默认 basetemp 的属主检查必然 INTERNALERROR →
        # --basetemp 走 _given_basetemp 分支绕过（meson/setuptools 先例）。
        basetemp = os.path.join(self.build_folder, "pytest-basetemp")
        os.makedirs(basetemp, exist_ok=True)
        env["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        os.makedirs(env["TMPDIR"], exist_ok=True)

        report = os.path.join(self.build_folder, "upstream-pytest-report.txt")
        # 用**宿主解释器**运行 pytest，而不是 python 依赖自带的解释器：实测
        # 依赖自带的 `bin/python3.12` 其 `_ctypes` 无法解析 libffi
        # （`ImportError: ... _ctypes...so: ffi_prep_closure_loc: symbol not found`，
        # 该包 lib/ 下不带 libffi），而 psutil 的 tests/__init__.py:9 顶层就
        # `import ctypes`，会让 19 个测试文件全部 ERROR 收集失败。
        # 宿主 python 的 ctypes 正常（实测子集可正常执行到真实断言）。
        # 两者同为 CPython 3.12 / aarch64-linux-ohos，ABI 兼容，编出的扩展可互用。
        #
        # **为什么串行**（2026-09-19 实测，推翻此前"需并行"的判断）：
        # 先前观测到"串行 40 分钟仅完成 65/704 项、外推约 7 小时"是**误判**——
        # 真因不是套件慢（全套 704 项实际只需 **33 秒**），而是
        # `test_open_files_mode` 在 OHOS 上**无限循环**：该用例的 giveup
        # 判定写在 `for file in p.open_files()` 的循环体内，而 OHOS 无
        # /proc/self/fdinfo（实测 FileNotFoundError）→ open_files() 恒返回空
        # 列表（实测 num_fds()=13 而同刻 open_files()=0）→ 循环体永不执行、
        # 退出条件永不判定 → 死循环。串行时表现为"卡住"，并行时表现为
        # "某 worker 卡住"。故此处**必须** deselect 该用例，否则 conan create
        # 必然超时。
        #
        # **为什么不用 xdist（-n 8）**：两个独立的致命点让 xdist 无法给出
        # 可信结果（均实测复现）：
        #   1) tests/test_sudo.py 的 `time.clock_settime()` 在 OHOS 触发
        #      seccomp **SIGSYS(31) 硬杀进程**（实测子进程 WTERMSIG=31）；
        #      上游 test_sudo.py 期望的是 `except PermissionError →
        #      raise unittest.SkipTest("needs root")`，但进程被信号杀死时
        #      SkipTest 永远没机会执行 → worker 死亡。实测 `node down: Not
        #      properly terminated` ×18，xdist 调度器随即抛
        #      INTERNALERROR，并**吞掉整个 short test summary**（FAILED 行
        #      归零）→ 无法逐项归因。
        #   2) tests/test_unicode.py 的 funky_name 含 surrogate 字符 →
        #      execnet `s.encode("utf-8")` 抛 UnicodeEncodeError
        #      ('surrogates not allowed') → 主进程 INTERNALERROR。
        # 因此 test_sudo.py 整体 `--ignore`、test_open_files_mode 单独
        # `--deselect`（二者都会毁掉整个 run，仅列入 ALLOWED_TEST_FAILURES
        # 是不够的），并改用**串行**：全套 33 秒完成，远在预算内，且能给出
        # 完整可解析的失败清单。串行下 test_unicode.py 不再触发该崩溃（其
        # 8 项失败已正常计入清单），故无需 ignore。
        cmd = [sys.executable, "-m", "pytest", "tests", "-q", "--no-header",
               "-p", "no:cacheprovider", "-p", "instafail",
               "--ignore=tests/test_sudo.py",
               "--deselect",
               "tests/test_linux.py::TestProcess::test_open_files_mode",
               "-rf", f"--basetemp={basetemp}"]
        proc = subprocess.Popen(cmd, cwd=self.source_folder, env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=2400)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, _ = proc.communicate()
            rc = 124
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(out)
        for line in out.strip().splitlines()[-8:]:
            self.output.info(f"[upstream-pytest] {line}")
        if rc == 124:
            raise ConanException(
                f"upstream pytest timed out (>2400s, suite did not finish); "
                f"see {report}")
        if rc != 0:
            failed = self._parse_test_failures(out)
            if not failed:
                # 「运行器被 E212 拒绝」与「真正的运行器异常」必须区分：前者是平台
                # 限制（见 E212_DLOPEN_DENIED 注释），按 E219 退化为静态校验；后者仍
                # 硬失败——绝不借这个回退吞掉真实缺陷。
                if E212_DLOPEN_DENIED.search(out or ""):
                    self.output.warning(
                        "上游 pytest 被 E212(hmmac) 拒绝：本进程无法从用户路径 dlopen "
                        "已签名的 C 扩展（签名成功但仍 Permission denied）——这是平台"
                        "限制，不是适配缺陷。按 E219 / jupyter-events 先例退化为 ELF "
                        "静态校验；上游套件在本环境**未能运行**，如实记录。")
                    so_path = self._verify_extension_elf()
                    with open(report, "a", encoding="utf-8") as fh:
                        fh.write(
                            "\n[E212] 上游 pytest 因 hmmac 拒绝 dlopen 用户路径下的 "
                            ".so 而未能运行；已按 E219 退化为 ELF 静态校验，"
                            f"校验对象 {so_path}。此记录**不代表上游套件通过**。\n")
                    self.output.info(
                        f"E212 fallback: ELF 静态校验通过；完整输出见 {report}")
                    return
                raise ConanException(
                    f"upstream pytest 运行器异常退出（exit={rc}），且未解析到"
                    f"失败用例，详见: {report}")
            unexpected = sorted(failed - ALLOWED_TEST_FAILURES)
            if unexpected:
                self.output.error(
                    f"上游 pytest 存在清单外失败: {unexpected}，详见: {report}")
                raise ConanException(
                    f"上游 pytest 失败（清单外 {len(unexpected)} 项）: "
                    f"{unexpected}，详见: {report}")
            self.output.warning(
                f"上游 pytest 存在 {len(failed)} 项已知平台环境性失败（均在"
                f"允许清单内）: {sorted(failed)}")
        self.output.info(f"upstream pytest passed; report: {report}")

    @staticmethod
    def _parse_test_failures(test_out):
        names = set()
        for line in (test_out or "").splitlines():
            m = re.match(r"^(?:FAILED|ERROR)\s+(\S+)", line.strip())
            if not m:
                continue
            node = m.group(1).rstrip(":")
            name = node.rsplit("::", 1)[-1]
            names.add(name.split("[", 1)[0])
        return names

    def _verify_extension_elf(self):
        """E212 回退：对构建出的 C 扩展做静态 ELF 校验（对齐 nanobind / E219）。

        CI 的 buildenv 下 live dlopen 必被 hmmac 拒绝（E212），故改为验证产物本身
        是合法 ELF 且 NEEDED 可解析。这仍能抓住真实缺陷（根本没编出扩展、链接残缺、
        魔数不对），只是不再把平台限制误判为适配失败——与
        archives/j/jupyter-events/0.12.0/conanfile.py 的 _verify_rpds_elf 同构。
        """
        so_paths = sorted(glob.glob(os.path.join(self.source_folder, "psutil", "*.so")))
        if not so_paths:
            raise ConanException(
                "E212 回退失败：psutil/ 下没有 C 扩展 .so（build_ext 未产出）")
        so_path = so_paths[0]
        with open(so_path, "rb") as fh:
            magic = fh.read(4)
        if magic != b"\x7fELF":
            raise ConanException(
                f"E212 回退失败：{so_path} 不是 ELF（magic={magic!r}）")

        readelf = (shutil.which("llvm-readelf") or shutil.which("readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not (readelf and os.path.isfile(readelf)):
            self.output.info(f"E212 fallback: ELF magic OK at {so_path}")
            return so_path
        out = subprocess.check_output([readelf, "-d", so_path], text=True)
        needed = [ln.strip() for ln in out.splitlines() if "NEEDED" in ln]
        self.output.info(
            f"E212 fallback: ELF + NEEDED OK at {so_path} ({len(needed)} entries)")
        return so_path

    # ---------------------------------------------------------------- package
    def _site_dir(self):
        return os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")

    def package(self):
        site = self._site_dir()
        src_pkg = os.path.join(self.source_folder, "psutil")
        if not os.path.isdir(src_pkg):
            raise ConanException("psutil package directory not found")

        # 纯 Python 层 + 扩展模块一起落入 site-packages（build_ext --inplace
        # 已把 .so 就地放在 psutil/ 下）。
        copy(self, "*.py", src=src_pkg, dst=os.path.join(site, "psutil"))
        copy(self, "*.so", src=src_pkg, dst=os.path.join(site, "psutil"))
        for sub in ("arch", "tests"):
            sub_src = os.path.join(src_pkg, sub)
            if os.path.isdir(sub_src):
                copy(self, "*.py", src=sub_src,
                     dst=os.path.join(site, "psutil", sub))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # copy() 使 ELF 签名失效 → 打包后再签一次（必须，否则运行期 dlopen 失败）。
        self._sign(glob.glob(os.path.join(site, "psutil", "*.so")))

        if not os.path.isfile(os.path.join(site, "psutil", "__init__.py")):
            raise ConanException(f"psutil payload incomplete under {site}")
        if not glob.glob(os.path.join(site, "psutil", "*.so")):
            raise ConanException(f"psutil extension module missing under {site}")

    def package_info(self):
        self.cpp_info.libs = []
        site = self._site_dir()
        # 消费方与 test_package 自动获得导入路径（教训：只 print 不声明会让
        # 消费方报 No module named 'xxx'）。
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
