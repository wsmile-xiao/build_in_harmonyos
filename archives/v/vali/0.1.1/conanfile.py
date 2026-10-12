#!/usr/bin/env python3
"""Conan recipe — vali 0.1.1（Varlink 协议的纯 C 实现 + 代码生成器）

上游事实（对 v0.1.1 官方 release tarball 实测审计，30493 bytes，
sha256 791785eca66392f91f28ca371ba9cfa2dc11915df0bff9f590a33453f67e5756）：

  * Meson 项目（`project(..., meson_version: '>=1.0')`），install 两类产物：
      - 库 `libvali`：client.c / service.c / registry.c / conn.c / util.c
        + 构建期生成的 org.varlink.service.c；
      - 可执行文件 `bin/vali`：Varlink 接口定义（.varlink）→ C 代码生成器。
  * 公共头只有 `include/vali.h`，并且**自包含**（只 include <stdbool.h>）。
    另外 3 个头 conn.h / def.h / util.h 是内部结构，不 install。
  * 两个外部依赖，都是纯 C：json-c（报文编解码）+ aml（事件循环）。
    上游用 `dependency('aml', 'aml1')` 做双名回退，aml 包的 pkg-config 名是 aml1。
  * **构建期自举**：meson.build 里的 `custom_target` 直接用刚编译出来的
    `tool`（bin/vali）生成 org.varlink.service.{h,c}；test/ 与 example/ 同理。
    也就是说"被构建的产物本身就是构建过程的工具"，交叉编译时必须能运行它。
  * 上游测试：test/meson.build 注册 2 条 `test()`：
      basic          —— fork + socketpair，客户端/服务端往返（echo、more 多回复、stop）
      certification  —— 以 `self-test` 运行，Varlink 官方认证套件 Test1..Test11
  * **test/basic.c 硬要求 NDEBUG 关闭**（`#ifdef NDEBUG` 则打印提示并 return 1），
    而上游自己的 CI（.builds/alpine.yml）用默认 `buildtype=debug`，从不跑 Release，
    所以这个约束在上游不会暴露。

OHOS 适配要点（逐项实测记录见 notes.md）：

  * 零补丁：上游源码一行不改，两个障碍都在配方层解决（见下）。
  * 构建工具 meson 缺失：基础镜像与 CI 环境**都没有 meson**
    （真机实测 `command -v meson` 为空，python3 也无 mesonbuild 模块），
    必须 `tool_requires("meson/1.11.0")`。
  * `<json_object.h>` 找不到：json-c 官方 CMakeLists 只把 16 个头装进
    `include/json-c/`，顶层 `json_object.h` 是 Debian/Alpine 打包补出来的兼容
    符号链接；制品仓的 json-c/0.18 同样只有 `include/json-c/`。配方补一个
    `-I<json-c>/include/json-c` 即可编译上游原样源码。
  * `b_ndebug`：CI profile 是 Release，MesonToolchain 会写 `b_ndebug='true'`
    ⇒ NDEBUG 打开 ⇒ 上游 basic 测试自杀式失败。配方显式改成 `'false'`。
  * `ar`/`ranlib`：conan 不把 `tools.build:compiler_executables` 的 ar/ranlib
    写进 native file，meson 会按裸名探测 `ar`/`ranlib`，而 OHOS 的 clang 工具链在
    /data/service/hnp/bin、那里的名字是 `llvm-ar`/`llvm-ranlib` ⇒ 从 c 编译器同
    目录推导全路径写进 `[binaries]`（官方 API `tc.binaries`）。
  * CI 会 export `AR`/`RANLIB` 等为 `llvm-*` 名字，构建前先清掉，避免它们被
    原样写进 native file 后 meson 报 `Program 'llvm-ar' not found`。
  * tool_requires 的 meson/1.11.0 在真机镜像里预置的 `bin/meson` 是**带 shebang 的
    /bin/sh 包装脚本**，而 OHOS 上 conan 的 `run()`（Python subprocess）**无法
    execve 这个沙箱内文件**（内核 EACCES）⇒
    `/bin/sh: .../bin/meson: Permission denied` + `Error 126`。generate() 里把它
    改写成**不带 shebang** 的等价脚本，让 shell 走 ENOEXEC 回退解释执行。
    实测矩阵与判据见 notes.md §3.5。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rmdir)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ValiConan(ConanFile):
    name = "vali"
    version = "0.1.1"
    description = ("vali — Varlink C implementation and code generator: client, "
                   "service and interface registry speaking Varlink over Unix sockets")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/vali"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("varlink", "ipc", "unix-socket", "code-generator", "rpc")

    # 上游 install 目标既有库也有代码生成器（bin/vali），但消费语义是"链接库 +
    # 可用生成器"，包类型取 library（L0k 只在检测到 application 或 bin 安装动作时
    # 才索要 commands.json，本包按 library 处理，bin/ 仍随包分发）。
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 制品仓的包是裸 ref（无 @user/channel），带 @ohpcd/stable 会在依赖
        # 解析阶段直接报 Unable to find——同仓库先例 archives/r/ruy、
        # archives/c/cairo/1.18.4。
        self.requires("json-c/0.18")
        self.requires("aml/1.0.0")

    def build_requirements(self):
        # 基础镜像里没有 meson：实测 `command -v meson` 为空、python3 无
        # mesonbuild 模块，CI profile 的 [buildenv] PATH 也只补了
        # usr/local/bin 与 /data/service/hnp/bin，两者都没有 meson。
        # meson 只能由制品仓的 meson/1.11.0 提供。
        # 同款先例：archives/c/cairo/1.18.4.2、archives/c/c-stdaux/1.6.0、
        # archives/a/account-utils/1.4.0。
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI/worker 会把 AR/AS/STRIP/NM/RANLIB export 成 llvm-* 名字（见
        # ci/conan/build_and_test.sh 的 conf_map：tools.gnu:gcc:ar → env AR=llvm-ar）。
        # 这些名字由 /data/service/hnp/bin 提供、**不在普通 PATH 上**，若被
        # MesonToolchain 原样写进 conan_meson_native.ini 的 [binaries]，meson 会报
        #   ERROR: Program 'llvm-ar' not found
        # 直接清掉，随后由下面显式写绝对路径。
        # 同款先例：archives/g/gtksourceview5/5.22.0（"CI/worker exports
        # AR/AS/STRIP/NM/RANLIB as llvm-* names not on PATH; pin the real tools
        # by ABSOLUTE PATH"）。
        for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(var, None)

        # tool_requires 的 meson 包装脚本可执行位修复（必须在任何 meson 调用之前）。
        self._fix_meson_launcher()

        # 依赖全部经 conan pkg-config 提供（json-c.pc / aml1.pc）。
        # MesonToolchain 的 pkg_config_path 固定指向 generators 目录
        # （conan/tools/meson/toolchain.py：self.pkg_config_path = generators_folder），
        # 因此 meson 只会看到 conan 生成的 .pc —— 包内自带的 .pc 不会被误用
        # （aml1.pc 的 prefix 是 '/'、json-c.pc 的 prefix 还指向构建机路径，
        #  若被采用会解析出错误路径）。
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        # R26：系统名库默认静态。MesonToolchain 自身也会按 shared 选项推导
        # default_library，这里显式写一遍，语义更明确（官方 meson 模板同款）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 子项目回退必须关闭：上游 subprojects/aml.wrap 是 [wrap-git] revision=HEAD，
        # 一旦 meson 走 subproject 就会 clone 上游 HEAD（不可复现，且 CI 无网络）。
        # 上游 project() 的 default_options 里已写 wrap_mode=nodownload，这里再显式
        # 声明一遍，保证永远只用 conan 提供的 aml1.pc。
        tc.project_options["wrap_mode"] = "nodownload"
        # ★ NDEBUG 必须关掉：上游 test/basic.c 里
        #     #ifdef NDEBUG  →  fprintf("NDEBUG must be disabled for tests"); return 1;
        # 而 CI profile 是 build_type=Release，MesonToolchain 会写 b_ndebug='true'
        # ⇒ 上游 basic 测试必然以退出码 1 失败。b_ndebug 是 meson 的 combo 选项
        # （true / false / if-release），conan 自己也是按字符串写入 native file，
        # 所以这里覆写为 'false'（永不定义 NDEBUG）。
        # 上游从不跑 Release（.builds/alpine.yml 用默认 buildtype=debug），
        # 这个约束只在我们这边才暴露。
        tc.b_ndebug = "false"
        # ★ 补 json-c 的头目录：上游源码写的是顶层兼容头
        #     #include <json_object.h> / <json_tokener.h>
        # 而 json-c 官方 CMakeLists 只 install 到 include/json-c/（已核对
        # json-c-0.18 源码：`install(FILES ${JSON_C_PUBLIC_HEADERS}
        # DESTINATION ${CMAKE_INSTALL_FULL_INCLUDEDIR}/json-c)`）——顶层那批头是
        # Debian/Alpine 的 json-c-dev 打包时补的兼容符号链接。真机制品仓的
        # json-c/0.18 包实测同样只有 include/json-c/（16 个头），且 conan 的
        # PkgConfigDeps 按 cpp_info.includedirs=["include"] 生成的 json-c.pc
        # 只有 -I<prefix>/include ⇒ <json_object.h> 必然找不到。
        # 解法：把 json-c 自己的头目录补进 c_args，上游源码零改动。
        jsonc = self.dependencies["json-c"]
        tc.extra_cflags = [
            "-I{}".format(os.path.join(jsonc.package_folder, "include", "json-c")),
        ]
        # ★ ar / ranlib：conan MesonToolchain 只从 buildenv 的 AR/RANLIB 取值，而
        # CI profile 的 tools.build:compiler_executables 只给了 c/cpp ⇒ 它写不出
        # ar/ranlib，meson 便按裸名探测。OHOS 的 clang 工具链在 /data/service/hnp/bin，
        # 那里的归档器叫 llvm-ar / llvm-ranlib，裸名 `ar`/`ranlib` 在 PATH 上找不到
        # ⇒ configure 阶段就失败。这里用 conan 的官方 API（tc.binaries 会并入
        # native file 的 [binaries] 段，且自动过滤 None）写绝对路径。
        # 同款先例：archives/a/aml/1.0.0、archives/c/cairo/1.18.4、archives/p/pixman/0.46.4
        # （它们用的是"事后改写 conan_meson_native.ini"的等价做法）。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        # meson 的 [binaries] 键名 → 候选可执行文件名（OHOS 上是 llvm-* 前缀）
        for meson_name, candidates in (("ar", ("llvm-ar", "ar")),
                                       ("ranlib", ("llvm-ranlib", "ranlib"))):
            found = None
            for name in candidates:
                if bindir:
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        found = cand
                        break
            if not found:
                for name in candidates:
                    found = shutil.which(name)
                    if found:
                        break
            if found:
                tc.binaries[meson_name] = found
        tc.generate()

    def _fix_meson_launcher(self):
        """把 tool_requires meson 的 shebang 包装脚本改写成**不带 shebang** 的等价脚本。

        ★ 真机实测（vali-15/16/17 三支只读探针，矩阵见 notes.md §3.5）：OHOS 上
        conan 的 `run()` 走 Python `subprocess`，而**沙箱内的 `#!` 脚本一律
        execve 失败**（`#!/bin/sh`、`#!/system/bin/sh`、`#!/data/service/hnp/bin/bash`
        全部 EACCES，报 `bad interpreter: Permission denied`）。同目录下用
        `sh <脚本>` 却能跑通，说明不是权限位、不是属主、不是路径——
        **是内核处理 shebang 这一步被拒**。

        meson/1.11.0 的 `bin/meson` 恰好就是这种 shebang 脚本 ⇒ `conan create` 在
        `meson.configure()` 直接 `Error 126`。

        解法：**去掉 shebang**。无 shebang 时 execve 返回 ENOEXEC，POSIX shell 会
        回退成"按脚本解释执行"——实测 `shell=True` 下 `rc=0`，而 conan 的 `run()`
        正是 `/bin/sh -c`。脚本体一字不改（`$0` 仍是自身路径，`dirname "$0"` 照常）。

        ⚠️ 不要试图用 chmod 修：真机上 `chmod` 返回 0 但 mode 纹丝不动
        （知识库 E046 的"静默失效"），`os.chmod` 同样无效。
        幂等：首行已不是 `#!` 时一个字节都不动。
        """
        launcher = self._locate_meson_launcher()
        if not launcher:
            self.output.warning("meson launcher not found; skipping shebang fix")
            return
        try:
            with open(launcher, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            self.output.warning("meson launcher unreadable: %s (%s)" % (launcher, exc))
            return
        if not raw.startswith(b"#!"):
            self.output.info("meson launcher already shebang-free: %s" % launcher)
            self._verify_launcher(launcher)
            return

        body = raw.split(b"\n", 1)[1] if b"\n" in raw else b""
        if not body.strip():
            self.output.warning("meson launcher has an empty body, not touching it")
            return
        # 留下原件，便于排查（也不会被执行：没有 .sh 之类的后缀也无妨）。
        backup = launcher + ".conan-orig"
        if not os.path.exists(backup):
            try:
                with open(backup, "wb") as handle:
                    handle.write(raw)
            except OSError as exc:
                self.output.warning("meson launcher backup failed: %s" % exc)
        tmp = launcher + ".conan-tmp"
        try:
            with open(tmp, "wb") as handle:
                handle.write(body)
            os.chmod(tmp, 0o775)
            os.replace(tmp, launcher)          # 目录写权限即可，不需要属主
        except OSError as exc:
            self.output.warning("meson launcher rewrite failed: %s (%s)" % (launcher, exc))
            try:
                os.remove(tmp)
            except OSError:
                pass
            return
        self._verify_launcher(launcher)

    def _locate_meson_launcher(self):
        """定位 tool_requires meson 的 bin/meson（依赖容器优先，缓存兜底）。"""
        try:
            dep = self.dependencies.build.get("meson")
        except Exception:  # noqa: BLE001 —— 依赖容器形态随 conan 小版本变动，不致命
            dep = None
        if dep is not None and getattr(dep, "package_folder", None):
            candidate = os.path.join(dep.package_folder, "bin", "meson")
            if os.path.isfile(candidate):
                return candidate
        which = shutil.which("meson")
        if which:
            return which
        # 兜底：直接扫本地缓存（本机镜像预置包的形态异常就发生在这里）。
        import glob
        pattern = os.path.join(os.environ.get("CONAN_HOME") or
                               os.path.join(os.path.expanduser("~"), ".conan2"),
                               "p", "*", "p", "bin", "meson")
        hits = sorted(glob.glob(pattern))
        return hits[0] if hits else None

    def _verify_launcher(self, launcher):
        """改写后立刻按 conan 的方式（`/bin/sh -c`）实跑一次，把 rc 写进日志。"""
        import subprocess
        try:
            proc = subprocess.run(["'%s' --version" % launcher],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  shell=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning("meson launcher probe errored: %s" % exc)
            return
        text = (proc.stdout or b"").decode("utf-8", "replace").strip()
        if proc.returncode == 0:
            # 措辞刻意区分"改了什么"与"现在能不能跑"：本方法在两条路径上都会被调用
            # （刚改写完 / 上一轮已改写过），所以这里只断言"现在可用"，不宣称刚做了修复。
            self.output.info("meson launcher usable via /bin/sh (shebang-free): %s -> %s"
                             % (launcher, text))
        else:
            self.output.warning("meson launcher probe still failing rc=%d: %s | %s"
                                % (proc.returncode, launcher, text))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试真实执行（test/meson.build 注册 basic / certification 两条）。
        # 输出进入 conan create 日志 —— CI 的 L1c 判据是日志里出现 "meson test"，
        # 所以除 meson.test() 自身打印的命令行外，这里再显式记一行。
        self.output.info("Meson upstream test: meson test -v -C {}".format(self.build_folder))
        meson.test()

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # meson install 出的 vali.pc 有两个问题：① prefix 是构建期根目录
        # （conan 用 `--prefix=/` + `install --destdir` 的方式安装，.pc 里落的是
        #  / 而不是包目录）；② Requires 只写了 json-c，漏掉静态链接真正需要的 aml。
        # 下游若拿它取链接参数会缺 aml，conan 侧本来就会由 CMakeDeps/PkgConfigDeps
        # 另生成完整描述，包内这份只会误导，故删除。
        # 同款先例：archives/r/reliable/1.3.5（删除 lib/pkgconfig）。
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["vali"]
        self.cpp_info.set_property("cmake_file_name", "vali")
        self.cpp_info.set_property("cmake_target_name", "vali::vali")
        self.cpp_info.set_property("pkg_config_name", "vali")
