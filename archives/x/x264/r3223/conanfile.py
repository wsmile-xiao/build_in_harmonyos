#!/usr/bin/env python3
"""Conan recipe — x264 r3223 (H.264/MPEG-4 AVC 编码库 + x264 CLI).

x264 自带**手写 configure**（不是 autoconf 产物），构建流程为
`bash ./configure ... && make && make install`。

OHOS 相关要点（逐条实测得来）：
  - configure 首行是 `#!/bin/bash`，而 OHOS 的 /bin/bash 不存在，
    必须以 hnp 的 bash 显式执行（直接 ./configure 报 "No such file or directory"）。
  - configure 用自带 config.guess 判定 host，它不认识 OHOS
    （传 aarch64-unknown-linux-ohos 报 "machine ... not recognized"）。
    OHOS 内核接口与 linux 一致、libc 为 musl，故显式给 --host=aarch64-unknown-linux-gnu
    （同 ffmpeg 配方 --target-os=linux 的先例）。
  - aarch64 分支的汇编器是 `AS="${AS-${CC}}"`（即 clang），**不需要 nasm/yasm**
    （nasm 只出现在 x86/x86_64 分支）——设备上没有 nasm/yasm，asm 仍为 yes。
  - OHOS 无 coreutils `install`，但 /bin/install 是 toybox 实现，实测支持
    `-d` 与 `-m`，因此可沿用上游 install 规则，只需显式 INSTALL=/bin/install。
  - HMDFS 的默认 TMPDIR 不可写，统一指到构建目录下 _tmp。
  - 设备 shell 的 .zshrc 会全局导出 CFLAGS/LDFLAGS/LD_LIBRARY_PATH 等，
    必须清掉，否则 configure 会静默链上 ~/usr/local 的同名库，包不自包含。
  - 鸿蒙 PC 要求 dlopen 的 .so 与被 exec 的可执行文件都带代码签名，
    故 package() 末尾统一用 binary-sign-tool 重签（先 objcopy 去旧签名）。
  - 归档不含 .git，上游 version.sh 会退化为 ver="x"，使
    X264_VERSION 为空、X264_POINTVER 变成 "0.165.x"。见 _pin_version()。
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class X264Conan(ConanFile):
    name = "x264"
    version = "r3223"
    package_type = "library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.videolan.org/developers/x264.html"
    url = "https://code.videolan.org/videolan/x264"
    description = ("x264 — H.264/MPEG-4 AVC 编码库（libx264）与 x264 命令行工具，"
                   "面向体积与速度优化的开源实现")
    topics = ("h264", "avc", "video", "encoder", "codec")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    # 设备 hnp 工具链目录（R33：不依赖未定义的 shell 环境变量）
    _HNP_BIN = "/data/service/hnp/bin"
    # 本包源码固定的提交与推导出的 revision（见 conandata.yml 注释）
    _PINNED_REV = "3223"
    _PINNED_SHA7 = "0480cb0"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # 构建
    # ------------------------------------------------------------------

    def generate(self):
        # 不生成 AutotoolsToolchain：x264 的 configure 是手写脚本，
        # 只认自有选项（--extra-cflags/--enable-shared/...），
        # autoconf 标准选项会被 die_unknown 拒绝。参数在 build() 里显式拼装。
        pass

    def _x264_build(self):
        return str(self.settings.build_type).lower()

    def _configure_args(self):
        pkg = self.package_folder
        return [
            "--prefix=" + pkg,
            "--bindir=" + os.path.join(pkg, "bin"),
            "--libdir=" + os.path.join(pkg, "lib"),
            "--includedir=" + os.path.join(pkg, "include"),
            # config.guess 不识别 OHOS；内核接口与 linux 一致、libc 为 musl
            "--host=aarch64-unknown-linux-gnu",
            "--enable-shared",
            "--enable-static",
            "--enable-pic",
            # 关闭依赖外部库/驱动/平台工具的可选特性，保持自包含
            # （lavf/ffms/swscale 会引入 ffmpeg；opencl 需要 GPU 驱动；
            #   avs/gpac/lsmash 是 Windows/macOS 输入后端）
            "--disable-opencl",
            "--disable-avs",
            "--disable-lavf",
            "--disable-ffms",
            "--disable-swscale",
            "--disable-gpac",
            "--disable-lsmash",
            "--disable-bashcompletion",
        ]

    def _tool(self, key, fallback):
        """工具链可执行文件：优先 conf（R33），缺省回退设备 hnp 绝对路径。"""
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={})
        return executables.get(key) or os.path.join(self._HNP_BIN, fallback)

    def _toolchain_env(self):
        """显式固定全部工具链变量的绝对路径。

        x264 的 configure 对 AS/AR/STRIP 用的是 `${VAR-default}`（**只认未设置**），
        因此若调用方把 VAR 导出成**空串**，取到的就是空值。CI worker 实测如此：
        AS 为空 → 汇编检查命令退化成「执行 conftest.S 文件」→ 汇编自检失败 →
        configure 报 "no NEON support, try adding -mfpu=neon to CFLAGS" 并退出 1
        （已在本机用空 AS 精确复现，且 stdout 只剩那两行，与 CI 日志一致）。
        故这里一律给绝对路径，不依赖任何继承来的环境变量。
        """
        return {
            "CC": self._tool("c", "clang"),
            "AS": self._tool("c", "clang"),
            "AR": self._tool("ar", "llvm-ar"),
            "RANLIB": self._tool("ranlib", "llvm-ranlib"),
            "NM": self._tool("nm", "llvm-nm"),
            "STRIP": self._tool("strip", "llvm-strip"),
        }

    def build(self):
        # 清掉设备 shell 全局导出的编译/链接环境，保证包自包含
        for _var in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                     "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR",
                     "LD_LIBRARY_PATH", "CMAKE_PREFIX_PATH"):
            os.environ.pop(_var, None)

        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        _bash = os.path.join(self._HNP_BIN, "bash")
        _configure = os.path.join(self.source_folder, "configure")
        _args = " ".join('"{}"'.format(a) for a in self._configure_args())
        _tools = " ".join('{}="{}"'.format(k, v)
                          for k, v in self._toolchain_env().items())
        # out-of-tree 构建：cwd 为 build_folder，configure 用绝对路径
        # 必须显式 bash（configure 的 shebang #!/bin/bash 在 OHOS 不存在）
        _cmd = '{} INSTALL=/bin/install TMPDIR="{}" "{}" "{}" {}'.format(
            _tools, _tmp, _bash, _configure, _args)
        try:
            self.run(_cmd)
        except ConanException:
            # configure 把失败命令的原始报错写进 config.log；不打出来则 CI
            # 只剩一句 "no NEON support..."，无法定位（本次实测吃过这个亏）。
            self._dump_config_log()
            raise

        self._pin_version()

        self.run("make -j{}".format(max(1, os.cpu_count() or 1)))

        self._run_upstream_tests()

    def _dump_config_log(self):
        log = os.path.join(self.build_folder, "config.log")
        if not os.path.isfile(log):
            self.output.warning("configure failed and no config.log was found")
            return
        with open(log, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        self.output.error("---- config.log (last 60 lines) ----")
        for line in lines[-60:]:
            self.output.error(line)
        self.output.error("---- end config.log ----")

    def _run_upstream_tests(self):
        """上游自带测试：tools/checkasm.c（`make checkasm` 产出 checkasm8 /
        checkasm10），逐项自检汇编内核。在可原生运行的目标上实跑，
        交叉构建时跳过（只保证编译链接）。"""
        if not can_run(self):
            self.output.info("cross-building: upstream checkasm skipped")
            return
        self.run("make checkasm INSTALL=/bin/install")
        for name in ("checkasm8", "checkasm10"):
            binary = os.path.join(self.build_folder, name)
            if not os.path.isfile(binary):
                raise ConanException(
                    "upstream {} was not built by `make checkasm`".format(name))
            # 未签名的可执行文件在鸿蒙 PC 上会被拒绝执行
            self._sign_one(binary)
            self.run('"{}"'.format(binary))

    def _pin_version(self):
        """归档没有 .git，上游 version.sh 走 fallback（ver="x"），
        导致 X264_VERSION 为空、X264_POINTVER 变成 "0.165.x"。

        这里按 conandata.yml 固定的提交回填 revision——其值等于用完整
        git clone 构建时 version.sh 的计算结果（rev-list 计数 r3223 +
        短 sha），使 x264 --version 与 x264.pc 的 Version 报告真实版本。
        """
        cfg = os.path.join(self.build_folder, "x264_config.h")
        with open(cfg, encoding="utf-8") as handle:
            text = handle.read()

        api = "0"
        with open(os.path.join(self.source_folder, "x264.h"),
                  encoding="utf-8") as handle:
            for line in handle:
                match = re.match(r"#define X264_BUILD (\d+)", line)
                if match:
                    api = match.group(1)
                    break

        text = text.replace(
            '#define X264_VERSION ""',
            '#define X264_VERSION " r{} {}"'.format(self._PINNED_REV,
                                                   self._PINNED_SHA7),
        )
        text = text.replace(
            '#define X264_POINTVER "0.{}.x"'.format(api),
            '#define X264_POINTVER "0.{}.{}"'.format(api, self._PINNED_REV),
        )
        with open(cfg, "w", encoding="utf-8") as handle:
            handle.write(text)

    # ------------------------------------------------------------------
    # 打包
    # ------------------------------------------------------------------

    def package(self):
        # 上游 install 规则用 $(INSTALL)；OHOS 无 coreutils install，
        # 但 /bin/install 是 toybox 实现且实测支持 -d/-m
        self.run("make install INSTALL=/bin/install")
        for _lic in ("COPYING",):
            copy(self, _lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        self._relocate_pc()
        self._sign_binaries()

    def _relocate_pc(self):
        """x264.pc 里 libdir/includedir 及 Libs/Cflags 写的是 configure 时的
        绝对路径字面量。改写成 ${exec_prefix}/${prefix} 相对形式，
        使 usr_local deployer 重写 prefix= 后路径自动跟随（ffmpeg 先例）。"""
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "x264.pc")
        if not os.path.isfile(pc):
            return
        lib = os.path.join(self.package_folder, "lib")
        inc = os.path.join(self.package_folder, "include")
        with open(pc, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("libdir=" + lib, "libdir=${exec_prefix}/lib")
        text = text.replace("includedir=" + inc, "includedir=${prefix}/include")
        text = text.replace("-L" + lib, "-L${libdir}")
        text = text.replace("-I" + inc, "-I${includedir}")
        # 版本串同样按固定提交回填（configure 生成时为 0.<api>.x）
        text = re.sub(r"^Version: 0\.(\d+)\.x$",
                      r"Version: 0.\1." + self._PINNED_REV,
                      text, flags=re.M)
        with open(pc, "w", encoding="utf-8") as handle:
            handle.write(text)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_one(self, target):
        """按鸿蒙 PC 要求重签单个 ELF：先去掉旧 .codesign 节再自签。"""
        objcopy = os.path.join(self._HNP_BIN, "llvm-objcopy")
        signer = os.path.join(self._HNP_BIN, "binary-sign-tool")
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                 .format(oc=objcopy, f=target))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                 .format(sg=signer, f=target))

    def _sign_binaries(self):
        """鸿蒙 PC XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都带代码签名，
        否则报 Permission denied / Operation not permitted。
        install 期的复制与 strip 会破坏链接器自签，故打包末尾统一重签。"""
        targets = []
        libdir = os.path.join(self.package_folder, "lib")
        for pattern in ("*.so", "*.so.*"):
            targets += [p for p in glob.glob(os.path.join(libdir, pattern))
                        if not os.path.islink(p)]
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path) \
                        and self._is_elf(path):
                    targets.append(path)

        for target in targets:
            self._sign_one(target)

    def package_info(self):
        self.cpp_info.libs = ["x264"]
        self.cpp_info.includedirs = ["include"]
        # 本包同时提供 x264 命令行工具，显式声明 bindirs
        # （否则 L0k 会判定「commands.json 存在但包像纯库」并告警）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "x264")
        self.cpp_info.set_property("cmake_target_name", "x264::x264")
        self.cpp_info.set_property("pkg_config_name", "x264")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
