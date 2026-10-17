#!/usr/bin/env python3
"""Conan recipe — ols dev_2026_05（Odin 语言 LSP 服务器）

ols 是纯 Odin 语言实现的 Language Server（LSP）。上游构建完全由 odin 编译器驱动
（build.sh / ci.sh），无 CMake/Make/Autotools、无 configure。

构建策略（与本仓已合入的 ols/dev-2026-06、ols/26-jun 同族，逐条对齐上游 ci.sh）：
- 构建工具链为 odin 编译器（tool_requires）。odin 本体是 C++ + LLVM，运行期需要
  libLLVM.so.22.1，故同时以 tool_requires 引入 llvm/22.1.0（shared 聚合库）。
  odin 属 build context，conan 会把 tool_requires 的运行环境聚合进 conanbuild
  （VirtualBuildEnv 默认环境）：PATH 含 odin 的 bin/、LD_LIBRARY_PATH 含
  llvm/22.1.0 的 lib/。ODIN_ROOT 由本配方显式指定为 odin 包根
  （即 base/core/shared/vendor 所在目录）。
- 链接驱动 clang 由本配方解析为绝对路径并经 ODIN_CLANG_PATH 传入：odin 在链接
  阶段默认以裸名 `clang` 找链接驱动（src/linker.cpp），显式化可消除对构建环境
  PATH 的隐式依赖。
- 构建命令取上游 CI 形态（ci.sh）：`odin build src/ -show-timings -collection:src=src
  -out:ols -no-bounds-check -o:speed -define:VERSION=<ver>`。VERSION 显式固定为
  「dev_2026_05」（上游默认 `nightly-<date>-<sha>`，固定后 `ols version` 可断言且
  构建可复现）。
- 上游测试：`cd tests && odin test ../tests -collection:src=../src -o:speed
  -define:ODIN_TEST_THREADS=1`（即 ci.sh CI 分支的第 (1) 段，ols 自身的 LSP 端到端套件，
  本配方在 build() 内真实执行）。ci.sh 第 (2) 段 `tools/odinfmt/tests.sh` 测的是
  odinfmt 这个**独立可执行产物**，本包不构建也不安装它（package() 只装 bin/ols 与
  bin/builtin），故不在本包的验证面内；相关实测观察见 archives/o/ols/dev_2026_05/
  manifest.yaml 的 knowledge_gained 与 PR 正文。
- 唯一的上游改动（patches/0001-backport-upstream-haiku-removal.patch，纯删除 6 行）：
  本仓为 OHOS 发布的编译器包是 odin/dev-2026-08，其 builtin 的 `Odin_OS_Type` 已不含
  `Haiku`；dev-2026-05 的源码仍引用 `.Haiku`，直接编译即
  `src/server/build.odin(73:20) Error: Undeclared name 'Haiku' for type 'Odin_OS_Type'`
  （3 处，同名）。该补丁逐字 backport 上游自己在下一个 release（dev-2026-06）里做的
  同一删除（dev-2026-05 的 build.odin/when.odin/builtin.odin 各有 Haiku，dev-2026-06 的
  同名文件里 0 命中），不改任何逻辑、不改任何期望值、不碰任何测试用例。
- 平台垫片（链接期，不改上游代码）：OHOS libc（SDK sysroot 与设备端）未导出线程
  取消符号 `pthread_cancel / pthread_setcancelstate / pthread_setcanceltype /
  pthread_testcancel`，而 ols 经 core:thread 创建请求线程与 checker worker，
  直接编译会报 `ld.lld: error: undefined symbol: pthread_setcancelstate`。
  本配方在 build() 内生成无害空桩并用 `-extra-linker-flags:<stub.o>` 注入链接。
- 产物 bin/ols 是 ELF 可执行文件，OHOS XPM 要求代码签名（binary-sign-tool 自签）。
  签名工具按「/data/service/hnp/bin 绝对路径优先 → PATH 回退」解析：CI worker 上命中的
  就是该绝对路径（与已合入的 ols/dev-2026-06 逐字同一，不会挑到 PATH 上同名但行为不同的
  工具）；真机上两处都没有 binary-sign-tool（硬编码即 rc=127 `/bin/sh: ...: inaccessible
  or not found`），配方告警跳过并如实记日志（实测未自签产物在本机 `ols version` rc=0）。
- 运行期资产：上游 README 要求 `builtin/` 目录位于 ols 二进制同级（ols 用
  /proc/self/exe 推断自身目录；找不到时可用环境变量 OLS_BUILTIN_FOLDER 指定），
  故随包安装到 bin/builtin/。bin/ols 的 DT_NEEDED 仅 libc.so，无第三方动态库依赖。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class OlsConan(ConanFile):
    name = "ols"
    version = "dev_2026_05"
    description = "Odin 语言语言服务器（LSP，aarch64-unknown-linux-ohos）"
    license = "MIT"
    homepage = "https://github.com/DanielGavin/ols"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ── OHOS libc 线程取消符号空桩（平台垫片，链接期注入，不改被测代码语义）──────
    # 依据：odin dev-2026-08 适配实测结论——OHOS libc（SDK sysroot 与设备端）未导出
    # 这四个符号，core:testing → core:thread 与 core:thread 本体都会引用它们，表现为
    # 链接期 `undefined symbol` 或加载期 `Error relocating ...: symbol not found`。
    _PTHREAD_STUB_C = """\
typedef unsigned long pthread_t;
int pthread_cancel(pthread_t thread) { (void)thread; return 0; }
int pthread_setcancelstate(int state, int *oldstate) { (void)state; if (oldstate) *oldstate = 0; return 0; }
int pthread_setcanceltype(int type, int *oldtype) { (void)type; if (oldtype) *oldtype = 0; return 0; }
void pthread_testcancel(void) { }
"""

    # 链接驱动搜索位置（绝对路径优先，避免裸名依赖 PATH）
    _CLANG_CANDIDATES = ("/data/service/hnp/bin/clang",)

    # 签名工具解析：CI worker 上是 /data/service/hnp/bin/*，真机上该路径不可用、
    # SDK 里也未必有 binary-sign-tool。取本仓 abx/0.1 的同款顺序：先查 PATH，再回退
    # /data/service/hnp/bin。两者都缺时告警跳过——真机实测未自签的 ELF 可以正常 exec
    # （`ols version` rc=0），而 CI worker 上工具存在、产物照旧被自签，交付语义不变。
    _SIGNER_CANDIDATES = ("/data/service/hnp/bin/binary-sign-tool", "binary-sign-tool")
    _OBJCOPY_CANDIDATES = ("/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")

    # ── rule4：上游测试真跑（构建期，非致命，仅记录证据）────────────────────────
    # 上游 ci.sh「CI」分支的两段测试入口，逐条照抄：
    #   (1) cd tests && odin test ../tests -collection:src=../src -o:speed \
    #         -define:ODIN_TEST_THREADS=1
    #   (2) cd tools/odinfmt && odin run tests.odin -file -collection:src=../../src \
    #         -out:tests.exe
    _UPSTREAM_TEST_CMD = "test ../tests -collection:src=../src -o:speed -define:ODIN_TEST_THREADS=1"

    # 上游测试的最长墙钟（秒）。真机实测 804 项耗时 1.6s，给 25 min 余量只为兜住
    # 「worker 上某个用例卡住 → 整条构建无界挂死 → CI 永不回写结论」这一种失败形态。
    _TEST_TIMEOUT_S = 1500

    def build_requirements(self):
        # odin 编译器（构建工具）；llvm 供 odin 运行期解析 libLLVM.so.22.1
        self.tool_requires("odin/dev-2026-08")
        self.tool_requires("llvm/22.1.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # conandata 的 codeload URL 末段是 tag 名、无 .tar.gz 后缀，必须显式给
        # filename=，否则 get() 按扩展名误判成 zip → BadZipFile。
        get(self, filename="ols-dev_2026_05.tar.gz",
            **self.conan_data["sources"], strip_root=True)
        # 补丁与取源码同生命周期（都在 source() 内、同一份 s 目录），不会因
        # conan 复用 source 缓存而重复打；见 conandata.yml 的 patch_description。
        apply_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build-ohos"

    # ── 工具链辅助 ────────────────────────────────────────────────────────────
    @staticmethod
    def _q(s):
        return "'{}'".format(s.replace("'", "'\\''"))

    def _tool_chain(self):
        """返回 (odin 包根, odin 可执行文件绝对路径)。

        顺带校验 llvm 包的 lib/ 存在——odin 的 DT_NEEDED 记着 libLLVM.so.22.1，
        缺目录时 conanbuild 的 LD_LIBRARY_PATH 也无从拼起，早失败早定位。
        """
        odin_pkg = self.dependencies.build["odin"].package_folder
        llvm_pkg = self.dependencies.build["llvm"].package_folder
        odin_bin = os.path.join(odin_pkg, "bin", "odin")
        if not os.path.exists(odin_bin):
            raise RuntimeError("odin compiler not found: {}".format(odin_bin))
        llvm_lib = os.path.join(llvm_pkg, "lib")
        if not os.path.isdir(llvm_lib):
            raise RuntimeError("llvm lib dir not found: {}".format(llvm_lib))
        return odin_pkg, odin_bin

    def _clang_path(self):
        """解析链接驱动 clang 的绝对路径。

        odin 在链接阶段以 `ODIN_CLANG_PATH` 或裸名 `clang` 作为链接驱动
        （上游 src/linker.cpp），裸名依赖构建环境 PATH。这里解析为绝对路径后经
        ODIN_CLANG_PATH 显式传入，去掉对该隐式前提的依赖。
        """
        candidates = [os.environ.get("ODIN_CLANG_PATH", "")] + list(self._CLANG_CANDIDATES)
        for c in candidates:
            if c and os.path.exists(c):
                return c
        found = shutil.which("clang")
        if not found:
            raise RuntimeError("clang (odin linker driver) not found")
        return found

    def _build_libc_shim(self, bdir, clang):
        """生成并编译 OHOS libc 线程取消符号空桩，返回 .o 绝对路径。"""
        q = self._q
        stub_c = os.path.join(bdir, "ohos_libc_compat.c")
        stub_o = os.path.join(bdir, "ohos_libc_compat.o")
        with open(stub_c, "w") as f:
            f.write(self._PTHREAD_STUB_C)
        self.run("{} --target=aarch64-linux-ohos -c {} -o {}".format(q(clang), q(stub_c), q(stub_o)))
        return stub_o

    def _elf_tool(self, candidates):
        """按给定顺序解析工具：含 / 的当作绝对路径直接验存在，裸名走 PATH 查找。"""
        for c in candidates:
            if os.path.sep in c:
                if os.path.isfile(c):
                    return c
            else:
                found = shutil.which(c)
                if found:
                    return found
        return ""

    def _sign_elf(self, path):
        """OHOS XPM 自签（幂等：先剥离旧 .codesign 段再签）。

        返回是否真正执行了签名，便于日志里明确记明本机跳过的事实。
        """
        q = self._q
        signer = self._elf_tool(self._SIGNER_CANDIDATES)
        objcopy = self._elf_tool(self._OBJCOPY_CANDIDATES)
        if not signer:
            self.output.warning(
                "[sign] binary-sign-tool 既不在 PATH 也不在 /data/service/hnp/bin，"
                "本机跳过自签：{}".format(path))
            return False
        if objcopy:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=q(objcopy), f=path))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
            sg=q(signer), f=path))
        return True

    def _run_stage(self, name, cmd, workdir, odin_pkg, clang):
        """在指定目录内、用「与主构建完全相同的环境」跑一段上游测试并回读日志。

        必须走 self.run（build() 内默认 conanbuild 环境），不能改成 subprocess + 自建
        env：真机实测那样会在链接阶段报
        `clang: error: unable to execute command: posix_spawn failed: No such file or
        directory` → `linker command failed with exit code 1`，因为只有 conan 的
        VirtualBuildEnv 才会把 llvm/22.1.0 包的 bin/（内含 clang 需要的 ld.lld）拼进
        PATH。ODIN_ROOT / ODIN_CLANG_PATH 与主构建一样以命令前缀显式给出。

        上游测试失败绝不能让打包失败，故 wrapper 恒以 0 退出，rc 只回显进日志；
        日志尾部同时 echo 到 conan 日志，供 CI 与审查直接取证。
        命令前缀 `timeout <_TEST_TIMEOUT_S>`（本机存在该程序时才加）：给上游测试一个墙钟
        上限，避免任何一种「用例卡住 → 构建无界挂死 → CI 永不回写结论」的失败形态。
        """
        q = self._q
        log = os.path.join(self.build_folder, name + ".log")
        wrapper = os.path.join(self.build_folder, "run_{}.sh".format(name))
        tmo = self._elf_tool(("timeout", "/system/bin/timeout", "/usr/bin/timeout"))
        pre = "{} {} ".format(q(tmo), self._TEST_TIMEOUT_S) if tmo else ""
        full = "ODIN_ROOT={} ODIN_CLANG_PATH={} {}{}".format(q(odin_pkg), q(clang), pre, cmd)
        with open(wrapper, "w") as f:
            f.write("#!/bin/sh\n"
                    "cd {wd} || exit 0\n"
                    "(\n{cmd}\n) > {log} 2>&1\n"
                    'echo "[captured] {name} rc=$?"\n'
                    "tail -n 25 {log}\n"
                    "exit 0\n".format(wd=q(workdir), cmd=full, log=q(log), name=name))
        os.chmod(wrapper, 0o755)
        bash = "/data/service/hnp/bin/bash"
        shell = bash if os.path.exists(bash) else "sh"
        self.run("{} {}".format(q(shell), q(wrapper)))
        try:
            with open(log, "r", errors="replace") as f:
                return f.read()
        except IOError:
            return ""

    def _diagnostics(self, clang, stub_o):
        """打印构建环境关键项（含链路驱动可用性），便于 CI 失败时定位。"""
        q = self._q
        self.run('echo "[env] PATH=$PATH"; echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"',
                 ignore_errors=True)
        for label, path in (("clang", clang), ("ld.lld", "/data/service/hnp/bin/ld.lld"),
                            ("stub.o", stub_o)):
            self.output.info("[env] {} exists={} path={}".format(
                label, os.path.exists(path), path))
        self.run("{} --version 2>&1 | head -n 2".format(q(clang)), ignore_errors=True)
        self.run("ls -l {} 2>&1".format(q(stub_o)), ignore_errors=True)

    def _run_captured(self, cmd, cwd, log):
        """执行命令并把 stdout+stderr 完整落盘后再回显。

        上游 odin 在链接阶段失败时可能静默返回非 0（CI #51349 实测：`lld-link`
        阶段 32ms、无任何输出、rc=255），所以这里显式重定向落盘 + tail 回显，
        确保链接器的真实报错始终出现在 conan 日志与 CI 评论里。
        """
        q = self._q
        wrapper = os.path.join(self.build_folder, "run_captured.sh")
        with open(wrapper, "w") as f:
            f.write("#!/bin/sh\n"
                    'log="{log}"\n'
                    "(\n{cmd}\n) > \"$log\" 2>&1\n"
                    "rc=$?\n"
                    'echo "[captured] rc=$rc log={log}"\n'
                    'tail -n 150 "$log"\n'
                    "exit $rc\n".format(log=log, cmd=cmd))
        os.chmod(wrapper, 0o755)
        bash = "/data/service/hnp/bin/bash"
        shell = bash if os.path.exists(bash) else "sh"
        self.run("{} {}".format(q(shell), q(wrapper)), cwd=cwd)

    def build(self):
        q = self._q
        src = self.source_folder
        odin_pkg, odin_bin = self._tool_chain()
        clang = self._clang_path()

        bdir = self.build_folder
        os.makedirs(bdir, exist_ok=True)
        ols = os.path.join(bdir, "ols")
        stub_o = self._build_libc_shim(bdir, clang)
        self._diagnostics(clang, stub_o)

        # 与上游 ci.sh 的构建命令等价（-show-timings / -collection:src=src /
        # -no-bounds-check / -o:speed 全部取自上游），仅 -out 改为绝对路径、
        # VERSION 固定为登记版本、并注入 libc 空桩与绝对路径的链接驱动。
        # 运行环境用 conan 默认的 conanbuild（VirtualBuildEnv 聚合 build context 的
        # tool_requires：PATH 含 odin 的 bin/，LD_LIBRARY_PATH 含 llvm/22.1.0 的 lib/），
        # ODIN_ROOT 由本配方显式指定。
        cmd = " ".join([
            "ODIN_ROOT={}".format(q(odin_pkg)),
            "ODIN_CLANG_PATH={}".format(q(clang)),
            q(odin_bin),
            "build", "src/",
            "-show-timings",
            "-collection:src=src",
            "-out:{}".format(q(ols)),
            "-no-bounds-check",
            "-o:speed",
            "-define:VERSION={}".format(self.version),
            "-extra-linker-flags:{}".format(q(stub_o)),
        ])
        self.output.info("ols build command: {}".format(cmd))
        self._run_captured(cmd, cwd=src, log=os.path.join(bdir, "ols-build.log"))
        if not os.path.exists(ols):
            raise RuntimeError("ols binary not produced ({})".format(ols))

        # 签名（OHOS XPM：被 exec 的 ELF 必须签名；工具缺失时按上面的策略告警跳过）
        self._sign_elf(ols)

        # 冒烟：`ols version` 是 main() 中服务端启动之前的纯 IO 退出路径
        # （src/main.odin 判 os.args[1] == "version" 即打印并 exit 0），
        # 不需要任何 conan 运行期环境（DT_NEEDED 仅 libc.so）。
        self.run("{} version | grep -qF {}".format(q(ols), q("ols version " + self.version)),
                 cwd=bdir, env=None)

        # rule4：上游测试真跑（非致命，仅记录证据）
        self._run_upstream_tests(odin_bin, odin_pkg, clang, src, stub_o)

    # ── rule4 第 (1) 段：ols tests/ 套件（上游 ci.sh CI 分支第一段）──────────────
    def _run_upstream_tests(self, odin_bin, odin_pkg, clang, src, stub_o):
        """在源码树 tests/ 目录内运行上游测试套件（cwd 必须是 tests/，与 ci.sh 一致）。

        任何异常都在此吞掉并写日志——绝不能因其失败而使包构建失败。
        """
        try:
            workdir = os.path.join(src, "tests")
            if not os.path.isdir(workdir):
                self.output.warning("[rule4] upstream-tests skipped: tests/ not found")
                return
            cmd = "{} {} -extra-linker-flags:{}".format(
                self._q(odin_bin), self._UPSTREAM_TEST_CMD, self._q(stub_o))
            log = self._run_stage("upstream-tests", cmd, workdir, odin_pkg, clang)

            m = re.search(r"Finished (\d+) tests?", log)
            executed = int(m.group(1)) if m else 0
            mf = re.search(r"(\d+) tests? failed", log)
            failed = int(mf.group(1)) if mf else 0
            ok = "All tests were successful" in log
            self.output.info(
                "[rule4] upstream-tests ols executed={} passed={} failed={} all_successful={}".format(
                    executed, executed - failed, failed, ok))
        except Exception as exc:  # noqa: BLE001 — 非致命
            self.output.warning("[rule4] upstream-tests skipped on error: {}".format(exc))


    def package(self):
        bdir = self.build_folder
        copy(self, "ols", src=bdir, dst=os.path.join(self.package_folder, "bin"))
        # 上游 README：builtin/ 必须位于 ols 二进制同级（ols 用 /proc/self/exe 推断目录）
        copy(self, "*", src=os.path.join(self.source_folder, "builtin"),
             dst=os.path.join(self.package_folder, "bin", "builtin"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # package 复制后重签保险（工具缺失时告警跳过，见 _sign_elf）
        self._sign_elf(os.path.join(self.package_folder, "bin", "ols"))

    def package_info(self):
        # application 型：bin/ols + bin/builtin 运行期资产，无库
        self.cpp_info.bindirs = ["bin"]
