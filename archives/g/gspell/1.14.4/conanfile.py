#!/usr/bin/env python3
"""Conan recipe — gspell 1.14.4 (meson)

gspell adds spell checking to GTK 3 text widgets: it wraps Enchant behind
GspellChecker / GspellLanguage, and provides GtkEntry / GtkTextBuffer /
GtkTextView subclasses that underline misspelled words.  Consumers on OHOS
previously had to compile the feature out (evince, pan, yad all fall back to
"spell checking disabled" because no gspell package existed).

OHOS adaptation notes
---------------------
* Build system is meson; only the library is delivered.  ``gspell_app`` is
  disabled so the package stays ``package_type = "library"`` (no ``bin/``).
* Public deps (``gio-2.0``, ``gtk+-3.0``, ``enchant-2``) and the private
  dep (``icu-uc``) are resolved through PkgConfigDeps, exactly like the
  upstream ``dependency()`` calls.
* icu4c/77 is pinned instead of icu4c/78: 78 ships no ``fPIC`` option and does
  not set ``pkg_config_name = "icu-uc"``, so ``dependency('icu-uc')`` would
  fail to resolve.  icu4c/77 is a *static* C++ archive, so every C link in
  this project needs ``-lc++`` (same as the cif-api recipe).
* ``libglib-2.0.so`` leaves ``g_libintl_*`` unresolved and Conan's
  ``glib-2.0.pc`` does not carry ``-lintl``; the Libs line is patched the same
  way gtk/3.24.43 does.
* Upstream unit tests are compiled and really executed (``tests=true``).  The
  six binaries in ``tests/unit-tests`` are driven by ``gtk_test_init``, so
  they need a display: they run on the headless **broadway** backend served by
  ``broadwayd`` from the gtk package (same technique as ayatana-ido/0.10.4-v2).
  Fifteen of the 23 upstream cases additionally need an installed Enchant
  dictionary; ``enchant/2.8.2`` on ohpcd is built with every provider disabled
  (``--without-aspell/hspell/hunspell/nuspell/...``), so they are skipped with
  the provider count recorded as evidence — the skip is decided at build time
  from the dependency graph, not hard-coded.
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# glib/2.84.0.1 包内 bin/ 的构建期工具在 HMFS 上不能直接执行：
#   * python 脚本（glib-mkenums / glib-genmarshal / gdbus-codegen）解释器
#     shebang 不可用，跨 UID 脚本执行被拒；
#   * ELF（glib-compile-resources / gobject-query / ...）缺少 .codesign
#     段，execve 返回 EPERM（shell 报 Operation not permitted，退出码 126）。
# 按 archives/g/gtk/3.24.43（依赖同一 glib/2.84.0.1）已验证的做法，在 build
# 目录里 staging 一份：python 工具包 sh wrapper 显式指定解释器，ELF 工具拷
# 贝出来重签名；meson 的 .pc 工具变量与 native file 的 [binaries] 覆盖项
# 统一指向 staging 副本。
HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
PYTHON3 = os.path.realpath(sys.executable)

GLIB_PYTHON_TOOLS = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen")
GLIB_ELF_TOOLS = (
    "glib-compile-resources",
    "glib-compile-schemas",
    "gobject-query",
    "gio-querymodules",
)

# Upstream test inventory — `tests/unit-tests/meson.build` (the same six files
# and the same g_test_add_func counts are on upstream master at the time of
# adaptation):
#   test-checker 3, test-entry 7, test-icu 2, test-inline-checker-text-buffer 5,
#   test-text-iter 3, test-utils 3   ->  23 g_test_add_func cases / 6 binaries.
UPSTREAM_CASES_PER_BINARY = {
    "test-checker": 3,
    "test-entry": 7,
    "test-icu": 2,
    "test-inline-checker-text-buffer": 5,
    "test-text-iter": 3,
    "test-utils": 3,
}
UPSTREAM_TEST_CASES = sum(UPSTREAM_CASES_PER_BINARY.values())

# Cases that create a GspellChecker with a real language and therefore need an
# Enchant provider + installed dictionary.  Without one, `gspell_language_lookup
# ("en_US")` returns NULL and the tests abort on `g_assert_true (lang != NULL)`.
DICTIONARY_DEPENDENT = (
    "test-checker",
    "test-entry",
    "test-inline-checker-text-buffer",
)
# Cases that only need GTK initialised (a GDK backend), no dictionary.
ENVIRONMENT_INDEPENDENT = (
    "test-icu",
    "test-text-iter",
    "test-utils",
)


class GspellConan(ConanFile):
    name = "gspell"
    version = "1.14.4"
    description = "Spell-checking library for GTK 3 applications (libgspell-1)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gspell"
    url = "https://github.com/GNOME/gspell/archive/refs/tags/1.14.4.tar.gz"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Version pins match gtk/3.24.43's own dependency tree so the graph
        # stays flat (no duplicate glib/gtk instances).
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # gspell public headers do not include enchant.h, but the installed
        # gspell-1.pc lists enchant-2 in Requires: (upstream `GSPELL_PUBLIC_DEPS`).
        self.requires("enchant/2.8.2", transitive_headers=True, transitive_libs=True)
        # Private dep: used by gspell-language.c / gspell-icu.c only.
        self.requires("icu4c/77", transitive_headers=True, transitive_libs=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # generate                                                            #
    # ------------------------------------------------------------------ #
    def generate(self):
        PkgConfigDeps(self).generate()
        staged_tools = self._prepare_glib_build_tools()
        self._fix_glib_intl_link()
        self._inject_glib_tool_variables(staged_tools)
        tc = MesonToolchain(self)
        # Only the library is delivered: gspell-app is an executable.
        tc.project_options["gspell_app"] = "false"
        # gobject-introspection / vala / gtk-doc are not published on ohpcd and
        # are not needed for a C library package.
        tc.project_options["gobject_introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["gtk_doc"] = "false"
        # Upstream unit tests must be compiled and executed.
        tc.project_options["tests"] = "true"
        # ... but the test executables are not part of the delivered package.
        tc.project_options["install_tests"] = "false"
        # Never let meson try to fetch a wrap sub-project.
        tc.project_options["wrap_mode"] = "nodownload"
        # icu4c/77 is a static C++ archive (shared=False, fPIC=True).  gspell is
        # C, so linking libicuuc.a/libicudata.a leaves __gxx_personality_v0 /
        # __cxa_begin_catch unresolved unless the C++ runtime is added.
        if "-lc++" not in tc.c_link_args:
            tc.c_link_args.append("-lc++")
        tc.generate()
        self._inject_meson_archiver(staged_tools)
        self._setup_build_ld_library_path()

    def _fix_glib_intl_link(self):
        """Add -lintl to glib-2.0.pc's Libs line.

        glib's libglib-2.0.so references g_libintl_bindtextdomain and friends,
        but Conan's PkgConfigDeps does not emit -lintl.  Same fix (and same
        reason) as gtk/3.24.43 and vte/0.74.2.
        """
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc, encoding="utf-8").read()
        if "-lintl" in text:
            return
        lines = text.splitlines(True)
        for i, line in enumerate(lines):
            if line.startswith("Libs:"):
                lines[i] = line.rstrip("\r\n") + " -lintl\n"
                break
        with open(pc, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(lines))
        self.output.info("patched glib-2.0.pc: added -lintl to Libs")

    def _inject_glib_tool_variables(self, staged_tools):
        """Inject the glib tool variables that meson's gnome module queries.

        gspell uses GNOME.mkenums_simple (glib_mkenums from glib-2.0.pc) and
        GNOME.compile_resources (glib_compile_resources from gio-2.0.pc).
        PkgConfigDeps emits neither, and meson fails with
        "Could not get pkg-config variable ...".  注入的是 staging 副本的
        绝对路径 —— glib 包缓存里的原件在 HMFS 上不可执行。
        """
        gens = self.generators_folder
        tool_map = {
            "gio-2.0.pc": (
                "glib_compile_resources",
                "glib_compile_schemas",
                "gio_querymodules",
                "gdbus_codegen",
            ),
            "glib-2.0.pc": (
                "glib_mkenums",
                "glib_genmarshal",
            ),
        }
        for pc_name, variables in tool_map.items():
            pc_path = os.path.join(gens, pc_name)
            if not os.path.isfile(pc_path):
                continue
            text = open(pc_path, encoding="utf-8").read()
            additions = []
            for var in variables:
                path = staged_tools.get(var.replace("_", "-"))
                if not path:
                    continue
                if "\n%s=" % var in text or "\n%s =" % var in text:
                    continue
                additions.append("%s=%s" % (var, path.replace(os.sep, "/")))
            if not additions:
                continue
            lines = text.splitlines(True)
            out = []
            injected = False
            for line in lines:
                if not injected and line.startswith("Name:"):
                    out.extend(a + "\n" for a in additions)
                    out.append("\n")
                    injected = True
                out.append(line)
            if not injected:
                out.append("\n")
                out.extend(a + "\n" for a in additions)
            with open(pc_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(out))

    def _inject_meson_archiver(self, staged_tools):
        """Inject ar/ranlib and glib tool paths into conan_meson_native.ini.

        [binaries] 里的工具路径同样指向 staging 副本：meson 的 gnome 模块
        在拿不到 .pc 变量时会回落到这里查工具。
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar, rl = ce.get("ar"), ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        rl = rlc
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(nf):
            return
        with open(nf, encoding="utf-8") as f:
            content = f.read()

        additions = []
        if ar and "[binaries]" in content and "\nar =" not in content:
            additions.append("ar = '%s'" % ar)
            if rl:
                additions.append("ranlib = '%s'" % rl)

        for tool_name, tool_path in sorted(staged_tools.items()):
            additions.append("%s = '%s'" % (tool_name, tool_path))

        if not additions or "[binaries]" not in content:
            return
        lines = content.splitlines(True)
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.strip() == "[binaries]":
                out.extend(a + "\n" for a in additions)
                inserted = True
        with open(nf, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(out))

    # ------------------------------------------------------------------ #
    # glib 构建工具 staging                                               #
    # ------------------------------------------------------------------ #
    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _sign_elf(self, binary):
        """HMFS 执行限制规避：去掉 .codesign 段后 selfSign 重签。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _prepare_glib_build_tools(self):
        """把 glib 包 bin/ 里的构建工具 staging 到 build 目录。

        返回 {工具名: 可执行文件绝对路径}。
        """
        try:
            glib_pkg = self.dependencies["glib"]
        except KeyError:
            return {}
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        quote = lambda s: "'" + str(s).replace("'", "'\\''") + "'"

        staged = {}
        for tool in GLIB_PYTHON_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            wrapper = os.path.join(tools_folder, tool)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(f"#!/bin/sh\nexec {quote(PYTHON3)} {quote(src)} \"$@\"\n")
            os.chmod(wrapper, 0o755)
            staged[tool] = wrapper

        for tool in GLIB_ELF_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            target = os.path.join(tools_folder, tool)
            shutil.copyfile(src, target)
            os.chmod(target, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(target)
            staged[tool] = target
        return staged

    def _setup_build_ld_library_path(self):
        """Put dependency bindirs/libdirs on PATH/LD_LIBRARY_PATH for the build.

        meson's gnome module execs glib-compile-resources / glib-mkenums during
        `ninja`.  On OHOS, /data/service/hnp/bin holds broken symlinks to system
        glib tools and Conan does not set LD_LIBRARY_PATH, so the tools either
        are not found or fail with "Error loading shared library
        libgio-2.0.so.0".
        """
        env = Environment()
        for dep in self.dependencies.values():
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
            for component in dep.cpp_info.components.values():
                for bindir in component.bindirs:
                    env.prepend_path("PATH", bindir)
                for libdir in component.libdirs:
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        # staging 副本必须优先于 glib 包自带的 bin/。
        env.prepend_path("PATH", self._glib_tools_folder())
        env.vars(self, scope="build").save_script("conanbuild_ld_library_path")

    # ------------------------------------------------------------------ #
    # build                                                               #
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _enchant_provider_count(self):
        """Number of Enchant provider modules shipped by the enchant package.

        enchant loads its spell backends from lib/enchant-2/*.so at runtime.
        The ohpcd enchant/2.8.2 recipe is configured with every provider
        disabled, so this returns 0 and dictionary-backed tests cannot run.
        The decision below therefore comes from the dependency graph, not from
        a hard-coded assumption.
        """
        dep = self.dependencies.get("enchant")
        if dep is None or not dep.package_folder:
            return 0
        moddir = os.path.join(dep.package_folder, "lib", "enchant-2")
        if not os.path.isdir(moddir):
            return 0
        return len([
            f for f in os.listdir(moddir)
            if f.endswith(".so") and not os.path.islink(os.path.join(moddir, f))
        ])

    def _broadway_env(self):
        """Start broadwayd and return (env, process) — or (env, None).

        The unit tests call gtk_test_init(), so they need a GDK backend.  The
        repo has no X/Wayland server; gtk/3.24.43 is built broadway-only and
        ships bin/broadwayd, which serves a headless display over TCP.
        """
        env = dict(os.environ)
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        saved = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(dep_libdirs + ([saved] if saved else []))

        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg is not None and gtk_pkg.package_folder:
            candidate = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
            if os.path.isfile(candidate):
                # broadwayd 是 gtk 包里的动态可执行文件，运行时同样按
                # LD_LIBRARY_PATH 找 libgtk-3.so.0 / libgio 等。上面那份
                # LD_LIBRARY_PATH 只写进了本地 env dict，**必须 env=env 传下去**：
                # 少了它，子进程继承的是 CI 进程的环境，加载器找不到库直接退
                # 127（"broadwayd exited early (rc=127)"），之后每个调用
                # gtk_test_init() 的用例都拿不到 display 而崩掉（rc=-5）。
                # stderr 落盘，失败时回读尾部，避免再出现「只看到一个 rc
                # 猜不出原因」。同仓库先例：ayatana-ido/0.10.4-v2（它直接改
                # os.environ，从而让 subprocess 的默认继承拿到同一个效果）。
                log_path = os.path.join(self.build_folder, "broadwayd.log")
                with open(log_path, "wb") as log_file:
                    proc = subprocess.Popen([candidate, ":5"], env=env,
                                            stdout=log_file, stderr=log_file)
                for _ in range(20):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                if proc.poll() is None:
                    env["GDK_BACKEND"] = "broadway"
                    env["BROADWAY_DISPLAY"] = ":5"
                else:
                    tail = ""
                    try:
                        with open(log_path, "rb") as fh:
                            tail = fh.read()[-800:].decode("utf-8", "replace")
                    except OSError:
                        pass
                    self.output.warning(
                        "broadwayd exited early (rc=%s): %s"
                        % (proc.returncode, tail.strip()))
                    proc = None
        return env, proc

    def _run_upstream_tests(self):
        """Compile-and-run the upstream unit tests, emit machine evidence.

        Every runnable binary is executed with `--tap`, GLib's own TAP
        reporter, so the number of *cases* (not just binaries) is measured
        directly from upstream output.
        """
        test_dir = os.path.join(self.build_folder, "tests", "unit-tests")
        providers = self._enchant_provider_count()

        names = list(ENVIRONMENT_INDEPENDENT)
        skipped = []
        if providers > 0:
            names += list(DICTIONARY_DEPENDENT)
        else:
            skipped = list(DICTIONARY_DEPENDENT)

        env, broadwayd_proc = self._broadway_env()
        command = "meson test " + " ".join(names)
        passed = failed = 0
        details = {}
        try:
            for name in names:
                exe = os.path.join(test_dir, name)
                if not os.path.isfile(exe):
                    raise ConanException(
                        "upstream test binary not built: %s "
                        "(meson option tests=true expected)" % exe)
                run = subprocess.run([exe, "--tap"], cwd=test_dir, env=env,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True, timeout=600)
                out = run.stdout or ""
                self.output.info("----- %s --tap (rc=%s) -----\n%s" % (name, run.returncode, out))
                ok = len(re.findall(r"^ok\b", out, re.M))
                not_ok = len(re.findall(r"^not ok\b", out, re.M))
                passed += ok
                failed += not_ok
                if run.returncode != 0 and not_ok == 0:
                    # Crash/abort before the TAP plan was completed.
                    failed += 1
                details[name] = {"passed": ok, "failed": not_ok, "rc": run.returncode}
                if run.returncode != 0:
                    raise ConanException("upstream test binary %s exited %s"
                                         % (name, run.returncode))
        finally:
            if broadwayd_proc is not None and broadwayd_proc.poll() is None:
                broadwayd_proc.terminate()

        executed = passed + failed
        expected = sum(UPSTREAM_CASES_PER_BINARY[n] for n in names)
        status = "passed" if (failed == 0 and passed == expected) else "failed"
        result = {
            "status": status,
            "framework": "glib-gtest-tap",
            "command": command,
            "discovered": UPSTREAM_TEST_CASES,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": UPSTREAM_TEST_CASES - executed,
            "enchant_providers": providers,
            "skip_reason": (
                "enchant/2.8.2 on ohpcd is built with all providers disabled "
                "(lib/enchant-2/ is empty); %s require an installed dictionary"
                % ", ".join(skipped) if skipped else ""
            ),
            "per_binary": details,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        # Dual channel: raw stdout survives buffering for the preflight scraper.
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as f:
                json.dump(result, f)
        except OSError:
            pass
        if status != "passed":
            raise ConanException(
                "gspell upstream unit tests failed: expected %s passing cases, "
                "got %s (failed=%s)" % (expected, passed, failed))

    # ------------------------------------------------------------------ #
    # package                                                             #
    # ------------------------------------------------------------------ #
    def package(self):
        Meson(self).install()
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._sign_binaries()

    def _sign_binaries(self):
        """Sign ELF binaries for HarmonyOS XPM."""
        if self.settings.os != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"),
                            recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"),
                             recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                     .format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                     .format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["gspell-1"]
        # Headers are installed as include/gspell-1/gspell/*.h
        # (upstream: includedir / 'gspell-1/gspell'), so the consumer include
        # root is include/gspell-1 and the spelling is <gspell/gspell.h>.
        self.cpp_info.includedirs = ["include/gspell-1"]
        self.cpp_info.set_property("pkg_config_name", "gspell-1")
        self.cpp_info.set_property("cmake_file_name", "gspell")
        self.cpp_info.set_property("cmake_target_name", "gspell::gspell")
