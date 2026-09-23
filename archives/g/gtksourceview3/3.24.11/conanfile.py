#!/usr/bin/env python3
"""Conan recipe — gtksourceview3 3.24.11 (autotools).

GtkSourceView 3 — syntax highlighting widget for GTK+ 3 (GNOME).
Source of the gedit editor's code view.

OHOS 适配要点：
  - 构建系统: autotools (tarball 自带 configure，无需 autoreconf)
  - config.guess 2018 版不识别 HarmonyOS → 运行时 sed 补丁 (E160)
  - 依赖 gtk/3.24.43 (broadway 后端) + libxml2/2.15.3，均已发布 OHOS binary
  - glib 构建工具: glib-mkenums (python 脚本可直接跑)、
    glib-compile-resources (OHOS ELF 需重签后拷入构建目录, E046/E051 变体)
  - SDK lld 需要 ABI 匹配的 libxml2.so.16 → SDK llvm/lib 注入
    LD_LIBRARY_PATH (abx 同款)
  - 上游 testsuite (22 程序 102 用例) 在 build() 中全量运行：
    broadwayd 以 :tcpN 模式提供无头显示服务，客户端 BROADWAY_DISPLAY=:tcpN
    (GTK3 broadway 客户端忽略 DISPLAY 环境变量，见 gdkbroadway-server.c)
  - shared-mime-info 数据库在 build() 现场生成 (XDG_DATA_DIRS 注入)，
    供 test-languagemanager 的 g_content_type_is_a 判定
"""
import glob
import os
import shutil
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GtkSourceView3Conan(ConanFile):
    name = "gtksourceview3"
    version = "3.24.11"
    description = "GtkSourceView 3 — syntax highlighting source widget for GTK+ 3"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/GtkSourceView"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        # mime 数据（freedesktop shared-mime-info 2.5.1 数据集）：
        # test-languagemanager 的 guess-language 用例依赖
        # g_content_type_is_a，OHOS 无 /usr/share/mime，测试时通过
        # XDG_DATA_DIRS 注入。递归拷贝（含 packages/ 子目录）。
        test_data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "test-data")
        if os.path.isdir(test_data):
            import shutil as _shutil
            dst = os.path.join(self.export_sources_folder, "test-data")
            if os.path.isdir(dst):
                _shutil.rmtree(dst)
            _shutil.copytree(test_data, dst)

    def requirements(self):
        # gtk/3.24.43 只发布 shared=True OHOS binary；gtk 传递 pango/cairo 等
        # (R36: 依赖必须已发布，PF4 依赖闸会逐个探测)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        # R32: platform check uses in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gtksourceview3 requires Linux or OHOS, got {self.settings.os}")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # 系统同名库策略：libgtksourceview-3.0 无系统同名冲突，默认动态由
        # Conan 管理依赖链 (R26 仅适用于系统同名库)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 无 glade-catalog / gtk-doc / introspection / installed-tests
        tc.configure_args.append("--disable-Werror")
        tc.configure_args.append("--enable-glade-catalog=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_guess()
        self._patch_config_status_tmpdir()
        self._prepare_glib_tools()
        env = self._build_environment()
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            # E074: HMDFS jobserver fifo → -j1
            # make 命令行变量覆盖 configure 固化进 Makefile 的工具路径
            # （系统 /data/service/hnp/bin 的 glib 工具缺 libffi/坏
            # shebang，不能用）
            tools = self._tools_folder()
            make_overrides = [
                "GLIB_COMPILE_RESOURCES=" + os.path.join(tools, "glib-compile-resources"),
                "GLIB_MKENUMS=" + os.path.join(tools, "glib-mkenums"),
            ]
            self.run("make -j1 " + " ".join(make_overrides),
                     cwd=self.build_folder, env="conanbuild")
            self._run_upstream_testsuite()
        self._strip_glib_tools()  # 构建产物不包含临时工具

    def _export_glib_tool_env(self):
        """AC_PATH_PROG 尊重预导出的环境变量；把 staged 工具的绝对
        路径写入 buildenv_info，configure 探测结果即指向重签副本，
        而不是系统 /data/service/hnp/bin 里的旧版/坏 shebang 工具。
        """
        tools = self._tools_folder()
        self.buildenv_info.define("GLIB_MKENUMS",
                                  os.path.join(tools, "glib-mkenums"))
        self.buildenv_info.define("GLIB_COMPILE_RESOURCES",
                                  os.path.join(tools, "glib-compile-resources"))
        self.buildenv_info.prepend_path("PATH", tools)

    def _patch_config_status_tmpdir(self):
        """E011 (babeltrace DRAFT-6048 / abx 同款): config.status 由
        `umask 077 && mktemp -d ./confXXXXXX` 创建 0700 临时目录，
        HMDFS 的 SGID 语义把目录映射成 drwx--S---，构建进程不可写 →
        `./confXXXXXX/subs1.awk: Permission denied`。
        修复：把 configure 脚本内嵌模板中的 umask 建目录替换为普通
        mktemp -d（目录权限继承当前 umask，组可写）。
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        if patched == content:
            # tarball 的 configure 模板可能已被上游调整；找不到模式时
            # 记录而不阻塞（错误会在 config.status 阶段明确暴露）
            self.output.warning(
                "config.status tmpdir template pattern not found in configure")
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info("configure: config.status tmpdir umask patched (E011)")

    def package(self):
        env = self._build_environment()
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.install()
        # LGPL license copy
        from conan.tools.files import copy
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gtksourceview-3.0"]
        incs = [d for d in ("include/gtksourceview-3.0", "include")
                if os.path.isdir(os.path.join(self.package_folder, d))]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GtkSourceView")
        self.cpp_info.set_property("cmake_target_name", "GtkSourceView::GtkSourceView")
        self.cpp_info.set_property("pkg_config_name", "gtksourceview-3.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        # resdir: language-specs/styles 数据由 meson/autotools 装到
        # share/gtksourceview-3.0；下游通过
        # gtk_source_language_manager_set_search_path 自行指定

    # ------------------------------------------------------------------
    # OHOS helpers
    # ------------------------------------------------------------------

    def _tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_tools(self):
        """Stage glib build-time tools where make can execute them.

        glib-mkenums 是 python 脚本可直接执行；glib-compile-resources 是
        OHOS aarch64 ELF，conan 缓存目录里的副本无法直接 exec（HMDFS 上
        已签名二进制从缓存路径执行报 Operation not permitted），拷贝到
        构建目录后重签即可运行。configure 在 PATH 中发现这些工具。
        """
        glib_bin = os.path.join(self.dependencies["gtk"].package_folder, "bin")
        # glib 是 gtk 的传递依赖，通过 host 依赖图找到 glib 包
        glib_pkg = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                glib_pkg = dep
                break
        if glib_pkg is None:
            raise ConanInvalidConfiguration("glib (transitive via gtk) not found in graph")
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")

        tools = self._tools_folder()
        os.makedirs(tools, exist_ok=True)
        # python 脚本工具：shebang 解释器路径在本机有效，直接拷贝
        for tool in ("glib-mkenums",):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            shutil.copyfile(src, os.path.join(tools, tool))
            os.chmod(os.path.join(tools, tool), 0o755)
        # ELF 工具：拷贝 + OHOS 重签
        for tool in ("glib-compile-resources",):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            dst = os.path.join(tools, tool)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(dst)
        # 库依赖：ELF 工具运行时需要 glib/libglib 等 conan 库
        # （由 _build_environment 的 LD_LIBRARY_PATH 提供）

    def _strip_glib_tools(self):
        # 构建目录里的临时工具不进入打包产物（package() 只 install 上游
        # 定义的文件；这里仅清理，防止后续步骤误用）
        tools = self._tools_folder()
        if os.path.isdir(tools) and os.path.isdir(self.build_folder):
            pass  # 保留在 build 目录供 testsuite 复用，package() 不复制

    def _build_environment(self):
        env = Environment()
        # E002: /tmp 只读 → 构建目录内 tmp
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        # glib 构建工具优先（含重签的 glib-compile-resources）
        env.prepend_path("PATH", self._tools_folder())
        # 全部 host 依赖的 bin（glib-mkenums 依赖图内自动带上）
        for dep in self.dependencies.host.values():
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        # SDK lld 需要 ABI 匹配 libxml2.so.16（abx 同款；c 调 clang 链接时
        # lld 运行库从 SDK 自带目录解析）
        if self.settings.os == "OHOS":
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            if sdk_llvm_libs:
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
            # libc++_shared.so（harfbuzz 等 NEEDED）在 SDK aarch64-linux-ohos
            libcxx = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"))
            if libcxx:
                env.prepend_path("LD_LIBRARY_PATH", libcxx[-1])
        return env

    def _patch_config_guess(self):
        """E160: config.guess (2018) 不识别 HarmonyOS → 按 E007/E160 补丁。

        运行时 sed（与 cgl/clp/coin-or 配方一致），不生成 .patch 文件。
        """
        guess = os.path.join(self.source_folder, "config.guess")
        if not os.path.isfile(guess):
            return
        with open(guess, encoding="utf-8") as f:
            content = f.read()
        if "HarmonyOS|HongMeng)" in content:
            return
        old = 'case "$UNAME_SYSTEM" in'
        if old not in content:
            raise RuntimeError("config.guess: UNAME_SYSTEM case not found")
        patched = content.replace(
            old, old + '\n    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;', 1)
        with open(guess, "w", encoding="utf-8", newline="\n") as f:
            f.write(patched)
        self.output.info("config.guess patched for HarmonyOS (E160)")

    def _mime_db_dir(self):
        return os.path.join(self.build_folder, "mime-db", "share")

    def _ensure_mime_database(self):
        """准备 shared-mime-info 缓存（test-languagemanager 需要）。

        OHOS 无 /usr/share/mime；g_content_type_is_a 判定
        application/xslt+xml ⊂ text/xml 需要 mime 数据库。配方自带
        freedesktop shared-mime-info 2.5.1 的数据（test-data/mime/：
        纯文本缓存 globs/globs2/subclasses/aliases/types 等 +
        packages/freedesktop.org.xml），测试时通过 XDG_DATA_DIRS 注入。
        GIO 读不到二进制 mime.cache 时自动回退文本缓存（已实测验证：
        guess-language 用例在纯文本数据集下通过）；magic/treemagic
        为二进制格式且本测试不依赖，不入仓（gitcode .diff 接口对
        binary patch 数据不完整会导致 CI git apply 失败）。
        """
        db = os.path.join(self._mime_db_dir(), "mime")
        if os.path.isfile(os.path.join(db, "globs2")):
            return  # already staged
        src = os.path.join(self.source_folder, "test-data", "mime")
        if not os.path.isdir(src):
            src = os.path.join(self.build_folder, "test-data", "mime")
        if not os.path.isdir(src):
            self.output.warning(
                "test-data/mime not found; guess-language test may mis-detect")
            return
        os.makedirs(db, exist_ok=True)
        # 递归拷贝（含 packages/ 子目录 —— GIO 读 packages/*.xml 的
        # <sub-class-of> 判定 content type 继承）
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst_root = db if rel == "." else os.path.join(db, rel)
            os.makedirs(dst_root, exist_ok=True)
            for fn in files:
                shutil.copyfile(os.path.join(root, fn),
                                os.path.join(dst_root, fn))
        self.output.info(f"staged mime cache from {src}")

    def _ensure_broadway_display(self):
        """启动 broadwayd 无头显示服务（:tcpN 模式）供上游测试使用。

        gtk/3.24.43 的 broadwayd 监听 TCP 9090+N（display 名 :tcpN）；
        GTK3 broadway 客户端读 BROADWAY_DISPLAY（DISPLAY 被忽略，
        参见 gdkbroadway-server.c _gdk_broadway_server_new）。
        返回 display 环境变量值（如 ":tcp41"），失败时返回 None。
        """
        import socket
        import subprocess
        import time

        display_port = 9131  # :tcp41
        display = ":tcp41"

        def _port_open():
            s = socket.socket()
            s.settimeout(1)
            try:
                s.connect(("127.0.0.1", display_port))
                return True
            except OSError:
                return False
            finally:
                s.close()

        if _port_open():
            return display  # 已有服务（上一次构建残留）

        gtk_pkg = self.dependencies["gtk"]
        broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
        if not os.path.isfile(broadwayd):
            self.output.warning("broadwayd not found in gtk package; "
                                "display-dependent tests will be skipped")
            return None
        tools = self._tools_folder()
        bd_local = os.path.join(tools, "broadwayd")
        if not os.path.isfile(bd_local):
            shutil.copyfile(broadwayd, bd_local)
            os.chmod(bd_local, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(bd_local)

        env = self._build_environment()
        with env.vars(self).apply():
            log = open(os.path.join(self.build_folder, "broadwayd.log"), "w")
            subprocess.Popen(
                [bd_local, display], cwd=self.build_folder,
                stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(20):
            if _port_open():
                self.output.info(f"broadwayd ready on port {display_port}")
                return display
            time.sleep(1)
        self.output.warning("broadwayd did not become ready; display tests may fail")
        return display

    _TESTS = [
        "test-buffer", "test-buffer-input-stream", "test-buffer-output-stream",
        "test-completion-model", "test-completion-words", "test-encoding",
        "test-file-loader", "test-file-saver", "test-iter", "test-language",
        "test-languagemanager", "test-mark", "test-printcompositor",
        "test-regex", "test-region", "test-search-context",
        "test-space-drawer", "test-stylescheme", "test-styleschememanager",
        "test-undo-manager", "test-utils", "test-view",
    ]

    def _run_upstream_testsuite(self):
        """跑上游 testsuite/（22 程序，TAP 输出）并校验全绿。

        make check 在 libtool wrapper 下执行测试会因 OHOS 无法 exec
        libtool shell wrapper 的 .libs 二进制路径语义而失败，改为
        直接执行 testsuite/ 下已构建的 ELF（与 abiword 插件测试同思路）。
        """
        suite_dir = os.path.join(self.build_folder, "testsuite")
        if not os.path.isdir(suite_dir):
            self.output.warning("testsuite not built; skip upstream tests")
            return
        self._ensure_mime_database()
        display = self._ensure_broadway_display()
        env = self._build_environment()
        if display:
            env.define("GDK_BACKEND", "broadway")
            env.define("BROADWAY_DISPLAY", display)
        # test-file-saver 的 permissions 断言依赖 POSIX chmod 语义：
        # HMDFS（~/.conan2）上 chmod(0600) 后 stat 返回 0660（组写位
        # 被文件系统强制，E011/E046 同族平台语义），断言物理上不可能
        # 满足。g_get_tmp_dir() 尊重 TMPDIR —— 测试期把 TMPDIR 指向
        # el2 分区（真实 POSIX 语义，chmod 600 → 600 已实测验证）。
        posix_tmp = "/data/storage/el2/base/temp/gsv-testsuite-tmp"
        os.makedirs(posix_tmp, exist_ok=True)
        env.define_path("TMPDIR", posix_tmp)
        env.define_path("TMP", posix_tmp)
        env.define_path("TEMP", posix_tmp)
        env.define("G_TEST_SRCDIR",
                   os.path.join(self.source_folder, "testsuite"))
        if os.path.isdir(self._mime_db_dir()):
            env.prepend_path("XDG_DATA_DIRS", self._mime_db_dir())
        total = ok = fail = 0
        failed_names = []
        with env.vars(self).apply():
            for t in self._TESTS:
                binpath = os.path.join(suite_dir, t)
                if not os.path.isfile(binpath):
                    self.output.warning(f"test binary missing: {t}")
                    fail += 1
                    failed_names.append(t)
                    continue
                from conan.tools.build import build_jobs
                self.output.info(f"Running upstream test: {t}")
                result = self.run(
                    shlex.quote(binpath), cwd=suite_dir,
                    ignore_errors=True, env="conanbuild")
                if result != 0:
                    fail += 1
                    failed_names.append(t)
        # 解析每个测试的 TAP 统计（重跑一遍 -k --tap? TAP 已在 stdout）
        # 这里以进程退出码为准（g_test_run 非零 = 有失败用例）
        if failed_names:
            raise ConanInvalidConfiguration(
                f"Upstream testsuite failures: {failed_names}")
        self.output.info(
            f"Upstream testsuite: {len(self._TESTS)} programs, "
            f"all exited 0 (102 TAP cases upstream)")

    # ------------------------------------------------------------------
    # OHOS signing
    # ------------------------------------------------------------------

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        # signer 是系统 ELF，依赖系统 libc++（/usr/lib 等）；在 conan
        # build 环境的 LD_LIBRARY_PATH（只含 conan 包/SDK）下运行会缺
        # 符号。用剥离 conan 环境的干净子进程执行。
        import subprocess
        clean_env = {
            "PATH": "/data/service/hnp/bin:/system/bin:/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/data/storage/el2/base"),
            "LD_LIBRARY_PATH": "",
            "TMPDIR": os.environ.get("TMPDIR", "/data/storage/el2/base/temp"),
        }
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", binary,
             "-selfSign", "1"],
            env=clean_env, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed for {binary}: "
                f"{result.stdout[-500:]} {result.stderr[-500:]}")

    def _sign_installed_elfs(self):
        import glob as _glob
        patterns = [os.path.join(self.package_folder, "lib", "**", "*.so"),
                    os.path.join(self.package_folder, "lib", "**", "*.so.*")]
        cands = []
        for pat in patterns:
            cands.extend(_glob.glob(pat, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            ce = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
            cc = ce.get("c") or ""
            candidates = [shutil.which("llvm-objcopy")]
            if cc and os.path.sep in cc:
                candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
            objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
            if objcopy:
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign "
                         f"{shlex.quote(binary)} 2>/dev/null || true")
            self._sign_elf(binary)
