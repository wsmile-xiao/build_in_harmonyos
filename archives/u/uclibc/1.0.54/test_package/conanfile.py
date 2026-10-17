import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get

# 上游测试源码（uClibc-ng-test，固定 commit 996f404，与 uClibc-ng 1.0.54 配套）
# 部分 CI worker 无法直连 github.com，用 gh-proxy 镜像优先、github 直连兜底（conan get 支持 URL 列表依次尝试）。
_UPSTREAM_TEST_URLS = [
    "https://gh-proxy.com/https://github.com/wbx-github/uclibc-ng-test/archive/996f40439263860340114f5bf2d160eb6e738cfc.tar.gz",
    "https://github.com/wbx-github/uclibc-ng-test/archive/996f40439263860340114f5bf2d160eb6e738cfc.tar.gz",
]
_UPSTREAM_TEST_SHA = "5335d8f246816f1153eabc506835cea68e9ad30d56da4139a224872095d03527"

# 上游测试子集：基础 libc 功能，确定性、无外部依赖，返回 0 表示通过。
# 完整套件含 30+ 子目录（nptl/tls/locale 等需额外配置），此处取可静态链接运行的确定性子集。
_UPSTREAM_TESTS = [
    ("test/string/tst-strlen.c", "tst-strlen"),
    ("test/string/tst-memmove.c", "tst-memmove"),
    ("test/string/tst-strtok.c", "tst-strtok"),
    ("test/stdlib/teststrtol.c", "teststrtol"),
    ("test/stdlib/testatexit.c", "testatexit"),
]


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["uclibc"].cpp_info

        # R34/L1e：显式校验包内产物路径真实存在，避免 CI 破坏性负测试
        # （移走包产物后）fallback 到系统 musl 头文件而误判为假测试。
        header_dirs = [p for p in dep.includedirs if os.path.isdir(p)]
        if not header_dirs:
            raise ConanException(f"uclibc package include dir missing: {dep.includedirs}")
        lib_dirs = [p for p in dep.libdirs if os.path.isdir(p)]
        if not lib_dirs:
            raise ConanException(f"uclibc package lib dir missing: {dep.libdirs}")

        # 定位 crt1.o 与 libc.a（静态链接必需，位于 usr/lib）
        crt = None
        libc = None
        for d in lib_dirs:
            if crt is None and os.path.exists(os.path.join(d, "crt1.o")):
                crt = os.path.join(d, "crt1.o")
            if libc is None and os.path.exists(os.path.join(d, "libc.a")):
                libc = os.path.join(d, "libc.a")
        if crt is None or libc is None:
            raise ConanException(f"uclibc package missing crt1.o/libc.a in {lib_dirs}")

        # R33: 编译器从 Conan conf 获取
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # clang 内置头文件（stddef.h/stdarg.h 等），-nostdinc 会禁掉系统路径
        res_dir = subprocess.run(
            [cc, "-print-resource-dir"], capture_output=True, text=True, timeout=30
        ).stdout.strip()

        # /tmp 只读，编译器临时文件写到可写目录
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # 消费者测试：-c 编译探针，验证 uClibc 头文件 + __UCLIBC__ 宏（R34）
        self.run(f'{cc} -c test.c -o test_probe.o {" ".join("-I" + p for p in dep.includedirs)}')

        # 下载上游测试源码
        get(self, url=_UPSTREAM_TEST_URLS, sha256=_UPSTREAM_TEST_SHA, strip_root=True)

        # 编译上游测试子集：静态链接 uclibc 的 crt1.o + libc.a（-nostdinc/-nostdlib）
        env = dict(os.environ)
        env["TMPDIR"] = tmpdir
        # OHOS SDK 的 lld 依赖 llvm/lib 下的 libxml2.so（二进制无 RUNPATH，靠加载器路径
        # 搜索），部分 CI worker 的 buildenv LD_LIBRARY_PATH 未传递到 test_package 的
        # subprocess，导致 lld 报 "xmlFreeDoc: symbol not found"。从 resource-dir 上溯到
        # llvm/lib 显式前置到 LD_LIBRARY_PATH，确保链接器可执行。
        llvm_lib = os.path.normpath(os.path.join(res_dir, "..", ".."))
        ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = llvm_lib + (":" + ld_path if ld_path else "")
        self._test_bins = []
        stubs_c = os.path.join(self.build_folder, "stubs.c")
        for src, name in _UPSTREAM_TESTS:
            src_path = os.path.join(self.build_folder, src)
            out = os.path.join(self.build_folder, name)
            cmd = (
                [cc, "--target=aarch64-linux-ohos", "-std=gnu99", "-nostdinc",
                 "-isystem", os.path.join(res_dir, "include")]
                + ["-I" + p for p in dep.includedirs]
                + ["-nostdlib", crt, src_path, stubs_c, libc,
                   "-Wl,--defsym=_init=0", "-Wl,--defsym=_fini=0",
                   os.path.join(res_dir, "lib", "aarch64-linux-ohos", "libclang_rt.builtins.a"),
                   "-o", out]
            )
            r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
            if r.returncode != 0:
                raise ConanException(f"compile upstream test failed: {name}\n{r.stderr}")
            self._test_bins.append(out)
        self.output.info(f"compiled {len(self._test_bins)} upstream uClibc-ng tests")

    def test(self):
        # 运行上游测试（静态链接 uclibc 的可执行文件，真机 native 直接运行）
        passed = 0
        failed = []
        for b in self._test_bins:
            r = subprocess.run([b], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                passed += 1
            else:
                failed.append((os.path.basename(b), r.returncode, r.stdout, r.stderr))
        self.output.info(f"uclibc upstream tests: {passed}/{len(self._test_bins)} passed")
        if failed:
            for name, rc, out, err in failed:
                self.output.error(f"FAIL {name} rc={rc}\n{out}{err}")
            raise ConanException(f"{len(failed)} upstream tests failed")
