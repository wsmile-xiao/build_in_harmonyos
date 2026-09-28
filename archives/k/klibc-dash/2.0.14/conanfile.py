#!/usr/bin/env python3
"""Conan recipe for klibc-dash 2.0.14 — klibc 内嵌 dash shell（HarmonyOS PC aarch64）。

klibc-dash 是 klibc 源包内 ``usr/dash`` 组件的独立打包：klibc 2.0.14 源码树内嵌一份
dash（Debian Almquist Shell）快照（``usr/dash/README.dash``：同步自 dash.git
changeset 46abc8c6d8a5e9a5712bdc1312c0b6960eec65a4），构建产物为 ``static/sh`` /
``shared/sh``，用作 initramfs 的 ``/bin/sh``。本配方打包**静态自包含**的 ``bin/sh``。

适配要点（详见 notes.md）
- 构建系统是 kernel-style kbuild（自定义 Makefile，非 autotools/cmake），且无可用
  ``make install``（HarmonyOS 无 GNU install，E098）→ 用 Conan copy 手动打包。
- dash 依赖同树 klibc libc（``usr/klibc`` → ``libc.a``）：本配方从同一 tarball 构建
  ``scripts/basic`` + ``usr/klibc`` + ``usr/dash``（patch 0004 收窄根 ``Kbuild`` 的
  ``all`` 目标），静态链接成自包含 ``sh``，无第三方库依赖。
- 构建硬依赖 Linux UAPI 头（``KLIBCKERNELSRC``）；OHOS SDK sysroot 提供 ``linux/``、
  ``asm-generic/``，但 asm 头位于 ``aarch64-linux-ohos/asm``（非标准 ``asm-arm64``）
  → patch 0001（KLIBCASMDIR + cp -rf 规避 HMDFS 符号链接）。
- OHOS 内核 UAPI 用 ``_KERNEL__NSIG`` 而非 Linux ``_NSIG`` → patch 0002。
- ``usr/dash/mktokens`` 硬编码 ``/tmp/ka$$`` 写临时文件，OHOS ``/tmp`` 只读（E002）
  → patch 0005 改为 ``${TMPDIR:-/tmp}``。
- HMDFS 不支持硬链接（E079）→ patch 0003（共享库 soname 由 ln 改 cp）。
- **架构标志必须写在 ``CC``/``LD`` 的命令行内容里，不能用 ``EXTRA_KLIBCCFLAGS`` /
  ``EXTRA_KLIBCLDFLAGS`` 命令行变量**：``usr/dash/Kbuild`` 用 ``EXTRA_KLIBCCFLAGS``
  承载 ``-include config.h`` 与 ``-DBSD -DSMALL -DJOBS=0 -DHAVE_CONFIG_H -DSHELL``
  等 dash 配置宏，GNU make 命令行变量优先级会整体覆盖它（``:=``/``+=`` 全部失效），
  导致 dash 丢失 config.h 与配置宏，``system.h`` 里 ``long sysconf(int)`` 声明被
  klibc 的 ``sysconf`` 函数式宏展开而编译失败。
- OHOS 要求可执行 ELF 带 ``.codesign`` 段（E077）→ package() 内用 ``binary-sign-tool
  -selfSign 1`` 签名，否则内核拒绝 exec。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KlibcDashConan(ConanFile):
    name = "klibc-dash"
    version = "2.0.14"
    description = "klibc 内嵌 dash shell（initramfs /bin/sh），静态链接 klibc libc"
    license = "BSD-3-Clause AND MIT AND GPL-2.0-only"
    homepage = "https://www.kernel.org/pub/linux/libs/klibc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 产物是命令行可执行文件 bin/sh（R38：软件级 commands.json 已声明）。
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # conan arch -> klibc KLIBCARCH
    _ARCH_MAP = {
        "armv8": "arm64",
        "armv7": "arm",
        "armv6": "arm",
        "x86_64": "x86_64",
        "x86": "i386",
    }
    # KLIBCARCH -> clang --target / ld.lld -m
    _TARGET_MAP = {
        "arm64": ("aarch64-linux-ohos", "aarch64linux"),
        "arm": ("arm-linux-ohos", "armelf_linux_eabi"),
        "x86_64": ("x86_64-linux-ohos", "elf_x86_64"),
        "i386": ("i686-linux-ohos", "elf_i386"),
    }
    # KLIBCARCH -> OHOS asm 头目录名（相对 sysroot/usr/include）
    _ASM_DIR_MAP = {
        "arm64": "aarch64-linux-ohos/asm",
        "arm": "arm-linux-ohos/asm",
        "x86_64": "x86_64-linux-ohos/asm",
        "i386": "i686-linux-ohos/asm",
    }

    def _klibc_arch(self):
        arch = self._ARCH_MAP.get(str(self.settings.arch))
        if not arch:
            raise ConanInvalidConfiguration(
                f"klibc-dash: unsupported arch {self.settings.arch}"
            )
        return arch

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # klibc-dash 无第三方库依赖：libc 由同一 tarball 的 usr/klibc 提供并静态链接。
        pass

    def layout(self):
        basic_layout(self)
        # klibc 是 kernel-style kbuild，在源码树内构建（产物输出到源码树）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------- 工具链 / sysroot 探测 ----------

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or shutil.which("clang") or "clang"

    def _tool(self, cc, name):
        """从 CC 同目录推导 llvm-* 工具完整路径（构建环境 PATH 可能不含 hnp/bin）。"""
        cc_dir = os.path.dirname(cc)
        if cc_dir:
            cand = os.path.join(cc_dir, name)
            if os.path.isfile(cand):
                return cand
        return shutil.which(name) or name

    def _find_sysroot(self, cc):
        """探测 OHOS sysroot。

        OHOS clang 不支持 ``--print-sysroot``，优先用 ``--print-resource-dir`` 推导：
        resource dir 形如 ``.../native/llvm/lib/clang/<ver>``，向上 4 级到 ``native``，
        再取 ``native/sysroot``。
        """
        try:
            rd = subprocess.check_output(
                [cc, "--print-resource-dir"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if rd:
                d = os.path.normpath(rd)
                for _ in range(4):
                    d = os.path.dirname(d)
                sr = os.path.join(d, "sysroot")
                if os.path.isdir(os.path.join(sr, "usr", "include")):
                    return sr
        except Exception:
            pass
        try:
            out = subprocess.check_output(
                [cc, "--print-sysroot"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if out and os.path.isdir(os.path.join(out, "usr", "include")):
                return out
        except Exception:
            pass
        cc_dir = os.path.dirname(os.path.abspath(cc))
        for rel in (("..", "sysroot"), ("..", "..", "sysroot")):
            c = os.path.normpath(os.path.join(cc_dir, *rel))
            if os.path.isdir(os.path.join(c, "usr", "include")):
                return c
        return None

    def _find_asm_dir(self, sysroot, arch):
        inc = os.path.join(sysroot, "usr", "include")
        preferred = self._ASM_DIR_MAP.get(arch)
        if preferred and os.path.isdir(os.path.join(inc, preferred)):
            return preferred
        for name in ("aarch64-linux-ohos/asm", "arm-linux-ohos/asm", "asm-arm64", "asm"):
            if os.path.isdir(os.path.join(inc, name)):
                return name
        return None

    # ---------- 构建 ----------

    def build(self):
        apply_conandata_patches(self)
        arch = self._klibc_arch()
        cc = self._compilers()
        target, ld_emu = self._TARGET_MAP[arch]
        tools = {
            "ar": self._tool(cc, "llvm-ar"),
            "ranlib": self._tool(cc, "llvm-ranlib"),
            "strip": self._tool(cc, "llvm-strip"),
            "nm": self._tool(cc, "llvm-nm"),
            "objcopy": self._tool(cc, "llvm-objcopy"),
            "objdump": self._tool(cc, "llvm-objdump"),
            "ld": self._tool(cc, "ld.lld"),
            "perl": self._tool(cc, "perl"),
        }
        sysroot = self._find_sysroot(cc)
        if not sysroot:
            raise ConanInvalidConfiguration(
                "klibc-dash: OHOS sysroot not found; cannot satisfy klibc "
                "KLIBCKERNELSRC (Linux UAPI headers) dependency"
            )
        asm_dir = self._find_asm_dir(sysroot, arch)
        if not asm_dir:
            raise ConanInvalidConfiguration(
                f"klibc-dash: OHOS asm UAPI headers not found under {sysroot}/usr/include"
            )

        # 物化干净的 UAPI 头目录：只含 linux/asm/asm-generic，排除 OHOS musl 头
        # （sysroot/usr/include 里的 stdarg.h 等依赖 bits/alltypes.h，直接 -I 会
        #  通过 #include_next 误 include musl 头）。
        kh = os.path.join(self.build_folder, "kernel-headers")
        kh_inc = os.path.join(kh, "include")
        inc_root = os.path.join(sysroot, "usr", "include")
        shutil.rmtree(kh, ignore_errors=True)
        os.makedirs(kh_inc, exist_ok=True)
        shutil.copytree(os.path.join(inc_root, "linux"), os.path.join(kh_inc, "linux"))
        shutil.copytree(
            os.path.join(inc_root, "asm-generic"), os.path.join(kh_inc, "asm-generic")
        )
        shutil.copytree(os.path.join(inc_root, asm_dir), os.path.join(kh_inc, "asm"))
        # KLIBCASMDIR 指到 sysroot 相对名；同时按该相对名物化一份供 usr/include/Kbuild
        # 的 cp -rf 使用（patch 0001）。
        shutil.copytree(
            os.path.join(kh_inc, "asm"), os.path.join(kh_inc, asm_dir)
        )
        # 源码树内物化 usr/include/{asm,asm-generic,linux}：klibc 头会 #include
        # <asm/*.h>/<asm-generic/*.h>/<linux/*.h>，且 asm 目录需为真实目录（非符号链接）。
        for name, src in (
            ("asm", os.path.join(kh_inc, "asm")),
            ("asm-generic", os.path.join(kh_inc, "asm-generic")),
            ("linux", os.path.join(kh_inc, "linux")),
        ):
            dst = os.path.join(self.source_folder, "usr", "include", name)
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)

        kernelsrc = kh
        # 架构标志放在 CC/LD 命令行内容里，绝不覆盖 EXTRA_KLIBCCFLAGS/EXTRA_KLIBCLDFLAGS
        # （见模块 docstring：usr/dash/Kbuild 靠 EXTRA_KLIBCCFLAGS 携带 dash 配置宏）。
        make_vars = (
            f'KLIBCARCH={arch} '
            f'KLIBCKERNELSRC="{kernelsrc}" '
            f'KLIBCASMDIR="{asm_dir}" '
            f'CC="{cc} --target={target}" HOSTCC="{cc}" '
            f'AR="{tools["ar"]}" RANLIB="{tools["ranlib"]}" '
            f'STRIP="{tools["strip"]}" NM="{tools["nm"]}" '
            f'OBJCOPY="{tools["objcopy"]}" OBJDUMP="{tools["objdump"]}" '
            f'LD="{tools["ld"]} -m {ld_emu}" PERL="{tools["perl"]}" '
        )
        # R9: -j1（kbuild jobserver 在多核下偶发问题，且单包错峰，见 E074）。
        # 默认目标 all = klcc + klibc（patch 0004 后：scripts/basic + usr/klibc + usr/dash）。
        self.run(f"make {make_vars} -j1", env="conanbuild")
        # 构建上游测试程序（usr/klibc/tests，static + shared），不运行。
        self.run(f"make {make_vars} -j1 test", env="conanbuild")
        self._run_upstream_tests(cc, tools)
        self._run_dash_smoke(cc, tools)

    def _sign_elf(self, prog, objcopy, signtool):
        """给 ELF 加 OHOS 代码签名（.codesign 段），使其可被内核加载执行（E077）。

        OHOS 要求用户 ELF 带有效 .codesign；kbuild 用 ld.lld 直接链接 + strip 的产物
        未签名，exec 报 Permission denied。先移除旧签名段，再 selfSign，最后恢复执行
        权限（binary-sign-tool 签名后会把权限重置为 660）。
        """
        self.run(
            f'"{objcopy}" --remove-section .codesign "{prog}" 2>/dev/null || true',
            env="conanbuild",
            ignore_errors=True,
        )
        r = self.run(
            f'"{signtool}" sign -inFile "{prog}" -outFile "{prog}" -selfSign 1',
            env="conanbuild",
            ignore_errors=True,
        )
        self.run(f'chmod +x "{prog}"', env="conanbuild", ignore_errors=True)
        return r == 0

    def _run_upstream_tests(self, cc, tools):
        """运行上游测试程序 usr/klibc/tests（dash 链接的 klibc libc 的上游测试套件）。

        上游树内唯一的自动化测试入口是顶层 ``make test`` → ``usr/klibc/tests``
        （39 个用例，见 notes.md 上游测试清单）；``usr/dash`` 组件自身无上游测试。
        逐个运行并如实记录（15s 超时），结果写入 build_folder/upstream-tests/。
        测试失败不阻塞 conan create（如实记录，不伪造通过）。
        """
        testdir = os.path.join(self.source_folder, "usr", "klibc", "tests")
        if not os.path.isdir(testdir):
            return
        names = sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(testdir)
            if f.endswith(".c")
        )
        outdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(outdir, exist_ok=True)
        # 需要命令行参数的用例（上游无 runtests 驱动，参数由调用方提供）：
        # - fnmatch：pattern/string/flags 三参数
        # - mmaptest：test_file 可写路径（默认硬编码 /tmp，OHOS /tmp 只读 EROFS）
        test_args = {
            "fnmatch": '"*.c" "foo.c" 0',
            "mmaptest": f'"{os.path.join(outdir, "mmaptest.tmp")}"',
        }
        signtool = self._tool(cc, "binary-sign-tool")
        passed, failed, sign_failed, not_built = [], [], [], []
        results = []
        for name in names:
            prog = os.path.join(testdir, name)
            if not os.path.isfile(prog):
                not_built.append(name)
                results.append((name, "NOT_BUILT", "-"))
                continue
            if not self._sign_elf(prog, tools["objcopy"], signtool):
                sign_failed.append(name)
                results.append((name, "SIGN_FAIL", "-"))
                continue
            args = test_args.get(name, "")
            # 每个用例的输出重定向到独立日志文件：inet_aton/inet_pton 会打印原始
            # 地址字节（非 UTF-8），若让输出回到上层日志会让工具链的文本解码失败。
            logf = os.path.join(outdir, f"{name}.log")
            r = self.run(
                f'timeout 20 "{prog}" {args} > "{logf}" 2>&1',
                cwd=outdir,
                env="conanbuild",
                ignore_errors=True,
            )
            (passed if r == 0 else failed).append(name)
            results.append((name, "PASS" if r == 0 else f"FAIL({r})", logf))
        total = len(names)
        with open(os.path.join(outdir, "results.tsv"), "w") as fh:
            for name, status, logf in results:
                fh.write(f"{name}\t{status}\t{logf}\n")
        self.output.info(
            f"upstream tests (usr/klibc/tests): total={total} passed={len(passed)} "
            f"failed={len(failed)} sign_failed={len(sign_failed)} "
            f"not_built={len(not_built)}"
        )
        for label, items in (
            ("failed", failed),
            ("sign-failed", sign_failed),
            ("not-built", not_built),
        ):
            if items:
                self.output.warning(f"upstream tests {label}: {' '.join(items)}")
        summary = os.path.join(self.build_folder, "upstream-tests-summary.txt")
        with open(summary, "w") as fh:
            fh.write(f"total={total}\npassed={len(passed)}\nfailed={len(failed)}\n")
            fh.write(f"sign_failed={len(sign_failed)}\nnot_built={len(not_built)}\n")
            fh.write("passed_list=" + " ".join(passed) + "\n")
            if failed:
                fh.write("failed_list=" + " ".join(failed) + "\n")
            if sign_failed:
                fh.write("sign_failed_list=" + " ".join(sign_failed) + "\n")
            if not_built:
                fh.write("not_built_list=" + " ".join(not_built) + "\n")
        self.output.info(f"upstream test summary: {summary}")

    def _run_dash_smoke(self, cc, tools):
        """dash 组件自身的上游测试入口（Debian 打包期冒烟）。

        上游 usr/dash 无自动化测试套件（无 tests/ 目录、无 make check/ctest 注册），
        Debian 侧的实际测试入口是 ``debian/rules`` 的 override_dh_auto_test：
        ``usr/dash/static/sh -c "exit"``。此处按同一入口执行并记录。
        """
        sh = os.path.join(self.source_folder, "usr", "dash", "static", "sh")
        if not os.path.isfile(sh):
            self.output.warning("dash static/sh not built; skipping upstream smoke")
            return
        signtool = self._tool(cc, "binary-sign-tool")
        self._sign_elf(sh, tools["objcopy"], signtool)
        outdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(outdir, exist_ok=True)
        r = self.run(
            f'"{sh}" -c "exit"', cwd=outdir, env="conanbuild", ignore_errors=True
        )
        self.output.info(f"dash upstream smoke (sh -c exit): rc={r}")
        with open(os.path.join(self.build_folder, "dash-smoke-summary.txt"), "w") as fh:
            fh.write('command=usr/dash/static/sh -c "exit"\n')
            fh.write(f"rc={r}\n")

    # ---------- 打包 ----------

    def _sign_ohos_elf(self, path):
        """对打包后的可执行文件做 OHOS 代码签名（E077），并校验 .codesign 段存在。"""
        signer = self._tool(self._compilers(), "binary-sign-tool")
        if not os.path.isfile(path):
            raise ConanException(f"klibc-dash: packaged executable missing: {path}")
        if not os.path.isfile(signer):
            raise ConanException(
                "klibc-dash: binary-sign-tool not found; OHOS executables must be signed"
            )
        tmp = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            check=True,
            capture_output=True,
            timeout=60,
        )
        readelf = self._tool(self._compilers(), "llvm-readelf")
        sections = subprocess.run(
            [readelf, "-S", tmp], check=True, capture_output=True, text=True, timeout=30
        ).stdout
        if ".codesign" not in sections:
            raise ConanException("klibc-dash: signed sh lacks .codesign section")
        os.chmod(tmp, 0o755)
        os.replace(tmp, path)

    def package(self):
        src = self.source_folder
        libsrc = os.path.join(src, "usr", "klibc")
        bin_dst = os.path.join(self.package_folder, "bin")
        lic_dst = os.path.join(self.package_folder, "licenses")

        # 产物：静态自包含 sh（klibc libc 静态链接，无运行时库依赖）。
        # 共享版本 usr/dash/shared/sh 需要 /lib/klibc/libc.so 才能加载，不作为本包
        # 默认交付物（消费方式见 notes.md）。
        copy(self, "sh", os.path.join(src, "usr", "dash", "static"), bin_dst)
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(bin_dst, "sh"))
        # 许可证：klibc 树内 LICENSE（BSD/MIT + Linux 派生文件 GPL-2.0）。
        copy(self, "LICENSE", libsrc, lic_dst)

    def package_info(self):
        # CLI 包（R38）：commands.json 已在软件级目录声明。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
