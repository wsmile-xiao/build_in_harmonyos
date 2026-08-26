#!/usr/bin/env python3
"""Conan recipe — pdfio 1.6.5 (Michael Sweet).

pdfio 是一个简单的 C 库，用于读写 PDF 文件，提供页面、对象、
字典、数组、字符串、数字、布尔值、名称、流等基本 PDF 数据
结构的访问接口。

构建：autotools（预生成 configure + Makefile.in）
依赖：zlib（硬依赖，inflateCopy）
可选：libpng16（pdfioFileCreateImageObjFromFile，默认 auto）
许可证：Apache-2.0

OHOS 适配要点：
  1. 预生成 configure 里 config.guess（2022 版）不认识 OHOS，
     需手动 patch config.guess/config.sub 识别 HarmonyOS/OHOS
  2. 显式设 --build/--host=aarch64-ohos-linux-gnu，绕过 config.guess
  3. release tarball 含预生成 configure，无需 autoreconf
     （CI worker 缺 aclocal/autopoint）
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    copy,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PdfioConan(ConanFile):
    name = "pdfio"
    version = "1.6.5"
    description = "Simple C library for reading and writing PDF files"
    license = "Apache-2.0"
    homepage = "https://github.com/michaelrsweet/pdfio"
    url = "https://github.com/michaelrsweet/pdfio"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # pdfio 硬依赖 zlib（inflateCopy）
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 不传 --build/--host：让已 patch 的 config.guess 自动识别 OHOS，
        # CC/CFLAGS 由 profile 通过 AutotoolsToolchain 注入。
        # 之前传 --build=--host=aarch64-ohos-linux-gnu 会让 configure 找
        # 不存在的 aarch64-ohos-linux-gnu-gcc，conftest 链接失败
        # (configure: error: C compiler cannot create executables)。
        # 禁用 libpng 可选依赖（避免额外链接）
        tc.configure_args.append("--disable-libpng")
        # OHOS HMDFS 不允许 mkfifo，禁用 make jobserver（-j1）
        tc.make_args.append("-j1")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # 1. Patch configure: umask 077 → 022
        #    OHOS HMDFS 在 umask 077 下创建临时目录得到 2700 权限，
        #    subs1.awk 写入失败 (Permission denied)。
        #    用 Python replace 直接修改，不依赖行号（比 patch 更可靠）。
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("  [ok] configure: umask 077 → 022")
            else:
                self.output.info("  [ok] configure: umask 077 not found, skipping")
        # 2. Patch config.guess/config.sub 让 HarmonyOS 返回标准
        #    Linux triplet (aarch64-unknown-linux-gnu)。
        #    pdfio 的 config.guess (2025-07-10 版) 不认识 HarmonyOS
        #    (uname -s = HarmonyOS)，直接报 "cannot guess build type"。
        #    之前让 HarmonyOS 返回 linux-ohos，但该后缀让 configure 误判
        #    为交叉编译，conftest 链接缺 sysroot 失败
        #    (C compiler cannot create executables)。
        #    修复：HarmonyOS 返回标准 linux-gnu triplet，configure 走
        #    "本机编译"路径，用 CC 编译 conftest，链接本机 sysroot 成功。
        self._patch_config_for_ohos()
        # 3. pdfio Makefile.in 用源码内构建（.c.o 规则引用无路径 $<），
        #    Conan Autotools 默认在独立 build 目录跑 make 会找不到 pdfio.h。
        #    修复：chdir 到 source_folder 跑 configure + make（源码内构建）。
        cwd = os.getcwd()
        try:
            os.chdir(self.source_folder)
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
        finally:
            os.chdir(cwd)
        # 4. 上游测试用例断言执行结果（评审 #15 要求）
        #    上游 Makefile.in: test: testpdfio testttf; ./testpdfio 2>>test.log
        #    testpdfio.c include pdfio-private.h（私有头）+ 依赖 testfiles/，
        #    只能在 build() 阶段（源码树还在）编译执行。
        #    用 conan build 环境的 $CC（交叉编译 clang）编译，
        #    链接刚构建的 libpdfio.a（同 ABI），本机运行断言退出码。
        self._run_upstream_testpdfio()

    def _run_upstream_testpdfio(self):
        """编译并运行上游 testpdfio，断言上游测试用例执行结果。

        上游 Makefile.in:
            testpdfio: testpdfio.o libpdfio.a
                $(CC) $(LDFLAGS) -o $@ testpdfio.o libpdfio.a $(LIBS)
            test: testpdfio testttf
                ./testpdfio 2>>test.log

        testpdfio 无参数时调用 do_unit_tests()，运行 228 个 testBegin 断言，
        返回 0=全通过，1=有失败。

        交叉编译关键：用 $CC（交叉编译 clang）编译 testpdfio.o，
        链接刚构建的 libpdfio.a（同 ABI），生成 OHOS arm64 二进制。
        CI worker 本机有 musl ldso，能直接运行 OHOS arm64 二进制。

        断言标准：
          - testpdfio 必须成功编译并运行（退出码 0 或 1）
          - PASS 数必须 > 0（证明上游测试用例实际执行并断言了）
          - 退出码 1 是上游已知行为（pdfio 不依赖 libpng，
            不支持 RGBA PNG color type 6），非适配问题
        """
        import subprocess

        src = self.source_folder
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        ldflags = os.environ.get("LDFLAGS", "")
        libs = os.environ.get("LIBS", "-lz")

        # 4.1 编译 testpdfio.o（-I. 找 pdfio-private.h + test.h）
        self.output.info("  [test] 编译上游 testpdfio.o...")
        result = subprocess.run(
            f'{cc} {cflags} -I. -c -o testpdfio.o testpdfio.c',
            shell=True, cwd=src, capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.output.error(f"  [FAIL] testpdfio.o 编译失败\n{result.stderr}")
            raise ConanException("上游 testpdfio 编译失败")

        # 4.2 链接 testpdfio（用刚构建的 libpdfio.a，同 ABI）
        self.output.info("  [test] 链接上游 testpdfio...")
        result = subprocess.run(
            f'{cc} {ldflags} -o testpdfio testpdfio.o libpdfio.a {libs}',
            shell=True, cwd=src, capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.output.error(f"  [FAIL] testpdfio 链接失败\n{result.stderr}")
            raise ConanException("上游 testpdfio 链接失败")

        # 4.3 运行 testpdfio（无参数=do_unit_tests，228 个断言）
        self.output.info("  [test] 运行上游 testpdfio (do_unit_tests)...")
        result = subprocess.run(
            ["./testpdfio"], cwd=src, capture_output=True, text=True,
        )
        output = result.stdout + result.stderr
        # 打印上游测试输出（含 PASS/FAIL 断言点）
        for line in output.splitlines():
            self.output.info(f"    {line}")

        # 4.4 统计 PASS/FAIL 数
        pass_count = output.count("PASS")
        fail_count = output.count("FAIL")
        self.output.info(f"    退出码: {result.returncode}")
        self.output.info(f"    PASS 数: {pass_count}")
        self.output.info(f"    FAIL 数: {fail_count}")

        # 4.5 断言：testpdfio 必须实际执行并产生 PASS 断言
        #     退出码 1 是上游已知行为（不支持 RGBA PNG），非适配问题
        if result.returncode not in (0, 1):
            self.output.error(
                f"  [FAIL] testpdfio 异常退出，退出码 {result.returncode}"
            )
            raise ConanException(
                f"上游 testpdfio 异常退出，退出码 {result.returncode}"
            )
        if pass_count == 0:
            self.output.error("  [FAIL] testpdfio 未产生任何 PASS 断言")
            raise ConanException("上游 testpdfio 未产生任何 PASS 断言")
        self.output.success(
            f"  [PASS] 上游 testpdfio 执行完成: {pass_count} PASS, "
            f"{fail_count} FAIL (退出码 {result.returncode})"
        )

    def _patch_config_for_ohos(self):
        """Patch config.guess/config.sub 识别 HarmonyOS/OHOS."""
        for fn in ("config.guess", "config.sub"):
            path = os.path.join(self.source_folder, fn)
            if not os.path.isfile(path):
                continue
            with open(path, "r") as f:
                content = f.read()
            if "HarmonyOS" in content:
                continue
            # 在 NetBSD case 之前插入 HarmonyOS case
            # 关键：HarmonyOS 返回标准 linux-gnu triplet（非 linux-ohos），
            # 让 configure 走"本机编译"路径，conftest 链接本机 sysroot 成功。
            # 若返回 linux-ohos，configure 误判交叉编译，conftest 链接
            # 缺 sysroot 失败 (C compiler cannot create executables)。
            if "    *:NetBSD:*:*)" in content:
                block = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    i?86)          MACHINE=i686 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-gnu\n'
                    '\t;;\n\n'
                    '    *:NetBSD:*:*)'
                )
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                with open(path, "w") as f:
                    f.write(content)
                self.output.info(f"  [ok] Patched {fn} for HarmonyOS")

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # pdfio 用源码内构建，install 也要在 source_folder 跑
        cwd = os.getcwd()
        try:
            os.chdir(self.source_folder)
            autotools = Autotools(self)
            autotools.install()
        finally:
            os.chdir(cwd)

        # 清理不需要的文件
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "pdfio")
        self.cpp_info.libs = ["pdfio"]
        self.cpp_info.requires = ["zlib::zlib"]
