#!/usr/bin/env python3
"""Conan recipe — libesmtp 1.1.0 (meson)"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibesmtpConan(ConanFile):
    name = "libesmtp"
    version = "1.1.0"
    description = "SMTP client library for submitting mail via a preconfigured MTA"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libesmtp/libESMTP"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # STARTTLS support: upstream meson.build dependency('openssl', >=1.1.0).
        # openssl/3.5.6 必须固定到 ohpcd 已发布的 OHOS 兼容 recipe revision
        # （748fc4de...，OHOS/armv8 预编译包 6b129b06...，见 abuild-sudo/ppp/re
        # 先例）：未固定时 conan 先命中 conancenter 的 CCI recipe（本机预检日志实证
        # rev 13f8f30151479797ca8a7c014856f849），它无条件 requires 上游 zlib 并在
        # OHOS 下 cmake 失败（System unknown HarmonyOS + compiler check），而 ohpcd
        # 的 recipe 无 zlib 依赖（静态 no-shared/no-asm，R26）。只固定 revision，
        # 不改版本号与测试口径。
        self.requires("openssl/3.5.6#748fc4deb56588d6f8ce900b21e8eb0a")

    def build_requirements(self):
        # meson.build dependency('openssl') uses method 'pkg-config'; the
        # preflight runner has no system pkg-config (meson aborts:
        # "Pkg-config for machine host machine not found"). Provide it as a
        # build tool (cataract/gxr precedent). 3.0.4 is the published OHOS
        # revision per archives/p/pkgconf/manifest.yaml.
        self.tool_requires("pkgconf/3.0.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libesmtp only supports Linux and OHOS, got {}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def _resolve_tmpdir(self):
        """E002/readonly_tmp: OHOS /tmp is erofs read-only.

        Prefer HMBS-injected task tmpdirs (HMBS_TMPDIR/TMPDIR/TMP/TEMP plus
        HMBS_AUTOCONF_MKTEMP_FALLBACK when it carries a path), probe each
        candidate for writability, and fall back to a build-folder-local
        directory. Only replaces the temp-file root; never deletes tests.
        This recipe itself hardcodes no /tmp path; the propagation below
        keeps meson/ninja/clang/shell temp files off read-only /tmp.
        """
        candidates = []
        fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback_var and fallback_var not in ("0", "1"):
            candidates.append(fallback_var)
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(),
                                ".conan_tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _resolve_compiler(self, kind):
        """Return an existing compiler path for 'c' or 'cpp'.

        The profile hardcodes tools.build:compiler_executables to
        /data/service/hnp/bin/clang{++}, which is absent on some preflight
        runners (meson aborts: "Unknown compiler(s)" + ENOENT on --version).
        Probe order (bulletty/bubblewrap precedent): conf value if it is a
        file -> PATH via shutil.which (hmbs prepends tool dirs) ->
        OHOS_NDK_HOME/llvm/bin -> version-agnostic SDK glob. Last resort is
        the conf value (or bare tool name), so CI workers where the profile
        path exists behave exactly as before.
        """
        names = {"c": ("clang",), "cpp": ("clang++",)}[kind]
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        conf_val = compilers.get(kind) or ""
        if conf_val and os.path.isfile(conf_val):
            return conf_val
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        sdk_dirs = []
        ndk_home = os.environ.get("OHOS_NDK_HOME", "")
        if ndk_home:
            sdk_dirs.append(os.path.join(ndk_home, "llvm", "bin"))
        try:
            sdk_dirs.extend(
                sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin"))
            )
        except Exception:
            pass
        for directory in sdk_dirs:
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate
        return conf_val or names[0]

    def _resolve_pkg_config(self):
        """Return an existing pkg-config/pkgconf binary path.

        The preflight runner has no system pkg-config (meson aborts:
        "Pkg-config for machine host machine not found"). Probe order
        (harfbuzz 14.2.0.2 precedent): conf tools.gnu:pkg_config if it is a
        file -> build-require pkgconf package bin -> PATH via shutil.which.
        Returns None when nothing is found so the machine files stay
        untouched.
        """
        try:
            conf_val = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_val = None
        if conf_val and os.path.isfile(str(conf_val)):
            return str(conf_val)
        try:
            build_deps = getattr(self.dependencies, "build", {})
            pkgconf_dep = build_deps.get("pkgconf") if build_deps else None
            if pkgconf_dep is not None:
                pkg_folder = getattr(pkgconf_dep, "package_folder", "")
                if pkg_folder:
                    for name in ("pkgconf", "pkg-config"):
                        candidate = os.path.join(pkg_folder, "bin", name)
                        if os.path.isfile(candidate):
                            return candidate
        except Exception:
            pass
        for name in ("pkg-config", "pkgconf"):
            found = shutil.which(name)
            if found:
                return found
        return None

    def _patch_meson_machine_files(self):
        """Point meson native/cross files at compilers that exist.

        Rewrites only `c = '...'` / `cpp = '...'` entries whose current path
        is not a file (missing profile clang on preflight runners); existing
        paths are left untouched. Also injects ar/ranlib absolute paths
        (MesonToolchain does not write them; cairo/libass precedent) and a
        pkg-config absolute path (harfbuzz precedent; this runner has no
        system pkg-config so dependency('openssl') cannot be probed).
        Returns an SDK llvm/lib dir for LD_LIBRARY_PATH when the resolved
        compiler comes from an SDK tree (meson lld probe needs libxml2;
        bubblewrap precedent), else None.
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        if not ar and bindir:
            candidate = os.path.join(bindir, "llvm-ar")
            if os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate
        pkg_config = self._resolve_pkg_config()
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            original = content
            if "[binaries]" in content:
                for key, resolved in (("c", cc), ("cpp", cxx)):
                    match = re.search(
                        r"(?m)^%s\s*=\s*'(.*)'\s*$" % key, content
                    )
                    if match:
                        current = match.group(1)
                        if current != resolved and not os.path.isfile(current):
                            if os.path.isfile(resolved) or (
                                "/" not in resolved and "\\" not in resolved
                            ):
                                content = (
                                    content[: match.start(1)]
                                    + resolved
                                    + content[match.end(1):]
                                )
                                self.output.info(
                                    "meson %s: compiler '%s' missing, "
                                    "using '%s' in %s"
                                    % (key, current, resolved, filename)
                                )
                inserts = []
                if ar and "\nar =" not in content:
                    inserts.append("ar = '%s'" % ar)
                    if ranlib:
                        inserts.append("ranlib = '%s'" % ranlib)
                if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                    inserts.append("pkg-config = '%s'" % pkg_config)
                    self.output.info(
                        "meson pkg-config injected: '%s' in %s"
                        % (pkg_config, filename)
                    )
                if inserts:
                    content = content.replace(
                        "[binaries]\n",
                        "[binaries]\n" + "\n".join(inserts) + "\n",
                        1,
                    )
            if content != original:
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
        sdk_lib = None
        normalized = cc.replace("\\", "/")
        if "/llvm/bin/" in normalized:
            candidate = os.path.normpath(
                os.path.join(os.path.dirname(cc), "..", "lib")
            )
            if os.path.isdir(candidate):
                sdk_lib = candidate
                self.output.info(
                    "meson compiler from SDK tree, LD_LIBRARY_PATH+=%s"
                    % sdk_lib
                )
        return sdk_lib

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Skip non-installed examples/mail-file demo: it calls obsolete
        # getpass() (upstream FIXME), which modern OHOS/musl libc no longer
        # exports, so the demo fails to link with "undefined symbol: getpass"
        # while the library itself builds fine. Line-number-free string
        # replacement (replaces fragile unified-diff patch which failed to
        # apply: hunk offset drifted to the sources list on the real tarball).
        # Library, SASL plugins, headers and pkg-config install unchanged.
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                        "subdir('examples')",
                        "# subdir('examples')  # skipped: mail-file demo needs obsolete getpass()")

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # STARTTLS is a core feature (smtp-tls.c, ntlm plugin); keep enabled.
        tc.project_options["tls"] = "enabled"
        tc.project_options["pthreads"] = "enabled"
        # lwres (libbind9 getaddrinfo) is disabled upstream by default; OHOS has none.
        tc.project_options["lwres"] = "disabled"
        tc.project_options["bdat"] = "true"
        tc.project_options["etrn"] = "true"
        tc.project_options["xusr"] = "true"
        tc.project_options["xdg"] = "true"
        tc.generate()
        # E002/readonly_tmp: OHOS /tmp is erofs read-only. Propagate the
        # HMBS-injected writable tmpdir into the Conan buildenv so meson,
        # ninja, clang and shell temp files avoid /tmp. MesonToolchain has
        # no tc.environment() hook, so use a saved Environment script
        # (aggregated into conanbuild.sh) following the repo precedent.
        _tmpdir = self._resolve_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        _keep = Environment()
        _keep.define("TMPDIR", _tmpdir)
        _keep.define("TMP", _tmpdir)
        _keep.define("TEMP", _tmpdir)
        _keep.define("TMP_DIR", _tmpdir)
        # Meson native/cross files may point at a profile clang path that
        # does not exist on this runner; rewrite missing c/cpp (and inject
        # ar/ranlib) to verified paths. SDK-tree compilers additionally need
        # their llvm/lib on LD_LIBRARY_PATH for the lld probe (libxml2).
        _sdk_lib = self._patch_meson_machine_files()
        if _sdk_lib:
            _keep.prepend_path("LD_LIBRARY_PATH", _sdk_lib)
        _keep.vars(self).save_sh("hmbs_tmpdir")
        self.output.info("E002 tmpdir propagated via buildenv: %s" % _tmpdir)

    def build(self):
        # E002/readonly_tmp: process-level writable TMPDIR so mktemp and
        # shell command-substitution temp files no longer fall to read-only
        # /tmp (backuppc-rsync/cthreadpool/courier-unicode precedent).
        _tmpdir = self._resolve_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        for _key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
            os.environ[_key] = _tmpdir
        self.output.info("E002 tmpdir for build(): %s" % _tmpdir)
        # examples/mail-file demo already skipped in source() via
        # replace_in_file (no conandata patch).
        # Upstream provides no test suite (meson.build defines no test() targets
        # and the tree has no tests/ directory); see test_package/MANIFEST.yml
        # upstream_test_audit. Only the examples/mail-file demo exists, which is
        # not a test and is not installed by upstream.
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.GPL", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["esmtp"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libesmtp")
        self.cpp_info.set_property("cmake_target_name", "libesmtp::libesmtp")
        self.cpp_info.set_property("pkg_config_name", "libesmtp-1.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
