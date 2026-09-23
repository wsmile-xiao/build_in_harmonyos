#!/usr/bin/env python3
"""Consumer test for glade 3.40.0 (application + libgladeui library).

The packaged outputs are exercised two ways:
  1. test_glade.c — links libgladeui from the glade package and runs a
     headless-safe subset of the upstream test suite logic in-process:
     library init, GladeApp singleton, gtk+ catalog with adaptors, and a
     .glade XML round-trip through glade_project_load_from_file. It runs
     under a broadway virtual display exactly like the upstream tests
     (same mechanism proven during the port).
  2. CLI contract of the packaged `glade` binary: `--version` prints
     "glade 3.40.0" and exits 0.
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


HNP_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
HNP_SIGNER = "/data/service/hnp/bin/binary-sign-tool"


class GladeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # build 产物隔离到 build/，避免污染 test_package/ 源目录
        # （git status 干净，JC5/CID 门禁友好）
        basic_layout(self)

    def _sign(self, binary):
        if os.path.isfile(HNP_OBJCOPY):
            self.run(f"{shlex.quote(HNP_OBJCOPY)} --remove-section "
                     f".codesign {shlex.quote(binary)} 2>/dev/null || true",
                     env="conanbuild")
        if os.path.isfile(HNP_SIGNER):
            self.run(shlex.join([HNP_SIGNER, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]),
                     env="conanbuild")

    def _stage_runtime_data(self):
        """hicolor icon theme（含 image-missing）+ gettext ITS + GTK
        gsettings schemas：GTK 3.24.43 无 hicolor 时 lookup_icon 走 brk
        断言（musl SIGTRAP 无消息），refcount 类用例需要 image-missing，
        GtkFileChooserButton 类路径需要 schemas。与主配方同款数据。"""
        share = os.path.join(self.build_folder, "runtime-data", "share")
        hicolor = os.path.join(share, "icons", "hicolor")
        for sub in ("24x24/actions", "24x24/apps", "24x24/status",
                    "48x48/status"):
            os.makedirs(os.path.join(hicolor, sub), exist_ok=True)
        with open(os.path.join(hicolor, "index.theme"), "w",
                  encoding="utf-8", newline="\n") as h:
            h.write("[Icon Theme]\nName=Hicolor\nComment=Fallback icon theme\n"
                    "Hidden=true\n"
                    "Directories=24x24/actions,24x24/apps,24x24/status,"
                    "48x48/status\n"
                    "\n[24x24/actions]\nSize=24\nContext=Actions\nType=Threshold\n"
                    "\n[24x24/apps]\nSize=24\nContext=Applications\nType=Threshold\n"
                    "\n[24x24/status]\nSize=24\nContext=Status\nType=Threshold\n"
                    "\n[48x48/status]\nSize=48\nContext=Status\nType=Threshold\n")
        # image-missing：glade 包 data/icons/placeholder.png 提供合法 PNG
        prefix = self.dependencies["glade"].package_folder
        for size_dir in ("24x24", "48x48"):
            dst = os.path.join(hicolor, size_dir, "status",
                               "image-missing.png")
            if not os.path.isfile(dst):
                with open(dst, "wb") as h:
                    h.write(bytes.fromhex(
                        # 1x1 透明 PNG（合法图像，无需源码树文件）
                        "89504e470d0a1a0a0000000d494844520000000100000001"
                        "08060000001f15c4890000000d4944415478da63fcffff3f03"
                        "05000200bdc46a3b0000000049454e44ae426082"))
        # gettext ITS（msgfmt --xml desktop/appdata 合并；此处仅运行期，
        # 但保持同构）+ GTK glib schemas（GSettings 用例）
        its_src = ("/data/service/hnp/gettext.org/gettext_0.26/share/"
                   "gettext-0.26/its")
        its_dst = os.path.join(share, "gettext", "its")
        if os.path.isdir(its_src) and not os.path.isdir(its_dst):
            os.makedirs(its_dst, exist_ok=True)
            for name in os.listdir(its_src):
                shutil.copyfile(os.path.join(its_src, name),
                                os.path.join(its_dst, name))
        schemas_dir = os.path.join(share, "glib-2.0", "schemas")
        os.makedirs(schemas_dir, exist_ok=True)
        for ctx in ("host", "test"):
            deps = getattr(self.dependencies, ctx, None)
            if deps is None:
                continue
            try:
                gtk = deps["gtk"]
            except (KeyError, TypeError):
                continue
            gtk_schemas = os.path.join(gtk.package_folder, "share",
                                       "glib-2.0", "schemas")
            if os.path.isdir(gtk_schemas):
                for name in os.listdir(gtk_schemas):
                    if name.endswith(".gschema.xml"):
                        shutil.copyfile(os.path.join(gtk_schemas, name),
                                        os.path.join(schemas_dir, name))
            break
        # glib-compile-schemas：用 hnp 系统 glib 2.38（仅 --version 差异，
        # compile 能力一致）+ libffi 库
        gcs = "/data/service/hnp/bin/glib-compile-schemas"
        if os.path.isfile(gcs):
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH",
                             "/data/service/hnp/libffi.org/libffi_3.4.4/lib")
            with env.vars(self).apply():
                try:
                    self.run(f"{shlex.quote(gcs)} {shlex.quote(schemas_dir)}",
                             env="conanbuild")
                except ConanException as exc:
                    self.output.warning(f"schema compile failed: {exc}")
        return share

    def build(self):
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc = ce.get("c")
        if not cc:
            raise ConanException("C compiler missing from conf")
        prefix = self.dependencies["glade"].package_folder
        include = os.path.join(prefix, "include", "libgladeui-2.0")
        libdir = os.path.join(prefix, "lib")
        src = os.path.join(self.source_folder, "test_glade.c")
        binary = os.path.join(self.build_folder, "test_glade")
        shell_cmd = (
            f"set -e\n"
            f"cflags=$(pkg-config --cflags gtk+-3.0 libxml-2.0)\n"
            f"libs=$(pkg-config --libs gtk+-3.0 libxml-2.0)\n"
            f"{shlex.quote(cc)} -Wno-deprecated-declarations "
            f"$cflags -I{shlex.quote(include)} {shlex.quote(src)} "
            f"-o {shlex.quote(binary)} -L{shlex.quote(libdir)} "
            f"-lgladeui-2 $libs\n"
        )
        script = os.path.join(self.build_folder, "build-test.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as h:
            h.write(shell_cmd)
        pc_env = Environment()
        pc_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        with pc_env.vars(self).apply():
            self.run(f"/bin/sh {shlex.quote(script)}",
                     env=["conanbuild"], cwd=self.build_folder)
        self._sign(binary)

    def test(self):
        prefix = self.dependencies["glade"].package_folder
        # broadwayd：gtk 包（传递依赖）里的 OHOS ELF，staging + 重签名
        gtk = None
        for ctx in ("host", "build", "test"):
            deps = getattr(self.dependencies, ctx, None)
            if deps is None:
                continue
            try:
                gtk = deps["gtk"]
                break
            except (KeyError, TypeError):
                continue
        if gtk is None:
            raise ConanException("gtk dependency not found for broadwayd")
        broadwayd = os.path.join(self.build_folder, "broadwayd")
        shutil.copyfile(os.path.join(gtk.package_folder, "bin", "broadwayd"),
                        broadwayd)
        os.chmod(broadwayd, 0o755)
        self._sign(broadwayd)

        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        run_env.define("BROADWAY_DISPLAY", ":tcp7")
        run_env.define("GDK_BACKEND", "broadway")
        # glade 运行时资源路径（包内 share/glade）
        prefix = self.dependencies["glade"].package_folder
        glade_share = os.path.join(prefix, "share", "glade")
        run_env.define("GLADE_PIXMAP_DIR",
                       os.path.join(glade_share, "pixmaps"))
        run_env.define("GLADE_CATALOG_SEARCH_PATH",
                       os.path.join(glade_share, "catalogs"))
        run_env.define("GLADE_MODULE_SEARCH_PATH",
                       os.path.join(prefix, "lib", "glade", "modules"))
        run_env.define("GLADE_TESTING", "1")
        # hicolor index.theme + image-missing 图标（规避 GTK 3.24.43 conan
        # 包 lookup brk 断言；见主配方 notes.md §5）
        share = self._stage_runtime_data()
        run_env.prepend_path("XDG_DATA_DIRS", share)
        run_env.vars(self).save_script("glade_test_env")

        # broadwayd 是 OHOS ELF，依赖 conan glib/cairo 等 so；用 wrapper
        # 注入完整依赖库路径后 setsid 启动（VirtualRunEnv 生成的
        # conanrun.sh 携带全部 LD_LIBRARY_PATH）
        run_sh = os.path.join(self.generators_folder, "conanrun.sh")
        bd_wrapper = os.path.join(self.build_folder, "start-broadwayd.sh")
        with open(bd_wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\n")
            if os.path.isfile(run_sh):
                h.write(f". {shlex.quote(run_sh)}\n")
            h.write(f"export LD_LIBRARY_PATH=/system/lib64:$LD_LIBRARY_PATH\n")
            h.write(f"exec {shlex.quote(broadwayd)} :tcp7\n")
        os.chmod(bd_wrapper, 0o755)

        import time
        self.run(f"setsid {shlex.quote(bd_wrapper)} "
                 f">{shlex.quote(os.path.join(self.build_folder, 'broadwayd.log'))} "
                 "2>&1 < /dev/null &", env="conanbuild")
        time.sleep(3)
        try:
            # 1. libgladeui 消费测试（11 断言）
            self.run(shlex.quote(os.path.join(self.build_folder,
                                              "test_glade")),
                     env=["conanrun", "glade_test_env"],
                     cwd=self.build_folder)
            # 2. glade --version CLI 契约
            glade_bin = os.path.join(prefix, "bin", "glade")
            if not os.path.isfile(glade_bin):
                raise ConanException(f"glade binary missing: {glade_bin}")
            version_file = os.path.join(self.build_folder, "glade-version.txt")
            with open(version_file, "w") as redirect:
                self.run(f"{shlex.quote(glade_bin)} --version",
                         env=["conanrun", "glade_test_env"],
                         cwd=self.build_folder, stdout=redirect)
            with open(version_file) as h:
                out = h.read().strip()
            if "3.40.0" not in out:
                raise ConanException(
                    f"glade --version output unexpected: {out!r}")
            result = {
                "executed": True,
                "passed": True,
                "command": "./test_glade && glade --version",
                "discovered": 2,
                "passedCount": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
        finally:
            # pkill -f 避免匹配自身命令行（[b] 技巧）；无匹配 rc=1 也成功
            self.run("pkill -f '[b]roadwayd :tcp7' || [ $? -eq 1 ]",
                     env="conanbuild")
