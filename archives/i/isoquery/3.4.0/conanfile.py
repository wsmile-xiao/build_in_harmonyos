#!/usr/bin/env python3
"""Conan recipe for isoquery 3.4.0.

isoquery prints ISO codes from the JSON files shipped by iso-codes.
The program links glib and json-glib. iso-codes itself is data: upstream
documents it as useful but not required to compile. The integration suite
still calls dgettext() on the iso_* domains, so the recipe exports that
data directory into the binary when the dependency is present.
"""

import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class IsoqueryConan(ConanFile):
    name = "isoquery"
    version = "3.4.0"
    description = "Search and display ISO codes for countries, languages, currencies and scripts"
    license = "GPL-3.0-or-later"
    homepage = "https://codeberg.org/toddy/isoquery"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("iso-codes", "iso-3166", "iso-639")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)
        # The published OHOS shared json-glib is mapped with EACCES
        # (Permission denied) even after the .codesign section is removed.
        # glib from the same cache loads. Linking the static library keeps
        # json-glib out of the dynamic loader.
        json_shared = str(self.settings.os) != "OHOS"
        self.requires(
            "json-glib/1.10.8",
            transitive_headers=True,
            transitive_libs=True,
            options={"shared": json_shared},
        )
        self.requires("proxy-libintl/0.5", transitive_headers=True, transitive_libs=True)
        self.requires("iso-codes/4.20.1")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.6")
        # msgfmt for the optional nls feature, and libintl.so for dgettext().
        # Kept as a build tool so its libintl is not pulled onto the host link
        # line ahead of the static proxy-libintl that glib already uses.
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        self._fetch_and_extract()

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["man"] = "auto"
        toolchain.project_options["nls"] = "auto"
        localedir = self._iso_localedir()
        if localedir and os.path.isdir(localedir):
            # The integration executable replaces the environment before it
            # execs isoquery, so an LD_LIBRARY_PATH or ISO_CODES_LOCALEDIR
            # inherited from the parent is not visible. Bake the directory
            # the same way a distro bakes /usr/share/locale, and give the
            # binary an RPATH so the wiped environment can still load the
            # shared libraries and dlopen gettext.
            toolchain.extra_cflags.append(
                '-DISOQUERY_ISO_CODES_LOCALEDIR="%s"' % localedir
            )
        libintl = self._libintl_path()
        if libintl:
            # glib's g_libintl_dgettext() dlopens "libintl.so" and, on this
            # loader, does not see the RPATH copy. The integration child
            # also wipes the environment, so the path has to be compiled in.
            toolchain.extra_cflags.append('-DISOQUERY_LIBINTL="%s"' % libintl)
        toolchain.extra_ldflags.append("-Wl,--disable-new-dtags")
        for libdir in self._runtime_libdirs():
            toolchain.extra_ldflags.append("-Wl,-rpath,%s" % libdir)
        toolchain.generate()
        self._inject_meson_tools()

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "meson.build")):
            self._fetch_and_extract()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def package(self):
        copy(
            self,
            "GPL-3.0-or-later.txt",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Meson(self).install()
        binary = os.path.join(self.package_folder, "bin", "isoquery")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        json_dir = self._iso_jsondir()
        localedir = self._iso_localedir()
        if json_dir:
            self.runenv_info.define_path("ISOQUERY_DATA", json_dir)
        if localedir:
            self.runenv_info.define_path("ISO_CODES_LOCALEDIR", localedir)
        bin_dir = os.path.join(self.package_folder, "bin")
        self.runenv_info.append_path("PATH", bin_dir)
        self.buildenv_info.append_path("PATH", bin_dir)

    def _source_spec(self):
        data = self.conan_data["sources"][self.version]
        urls = data["url"]
        if isinstance(urls, str):
            urls = [urls]
        return urls, data["sha256"]

    def _fetch_and_extract(self):
        urls, sha256 = self._source_spec()
        archive = os.path.join(self.source_folder, "isoquery-src.tar.gz")
        os.makedirs(self.source_folder, exist_ok=True)
        errors = []
        for url in urls:
            try:
                if os.path.exists(archive):
                    os.remove(archive)
                download(self, url, archive, sha256=sha256)
                errors = []
                break
            except ConanException as exc:
                errors.append("%s: %s" % (url, exc))
        if errors or not os.path.isfile(archive):
            raise ConanInvalidConfiguration(
                "source download failed: %s" % " | ".join(errors)
            )
        extract_root = os.path.join(self.source_folder, "_extract")
        if os.path.isdir(extract_root):
            shutil.rmtree(extract_root)
        os.makedirs(extract_root)
        with tarfile.open(archive, "r:gz") as tar:
            kwargs = {}
            if hasattr(tarfile, "data_filter"):
                kwargs["filter"] = "data"
            tar.extractall(extract_root, **kwargs)
        roots = [
            name
            for name in os.listdir(extract_root)
            if os.path.isdir(os.path.join(extract_root, name))
        ]
        tree = extract_root
        if len(roots) == 1:
            tree = os.path.join(extract_root, roots[0])
        for name in os.listdir(tree):
            dest = os.path.join(self.source_folder, name)
            if os.path.exists(dest):
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
            os.replace(os.path.join(tree, name), dest)
        shutil.rmtree(extract_root)
        os.remove(archive)
        if not os.path.isfile(os.path.join(self.source_folder, "meson.build")):
            raise ConanInvalidConfiguration("extracted source has no meson.build")

    def _runtime_libdirs(self):
        found = []
        groups = []
        host = getattr(self.dependencies, "host", None)
        build = getattr(self.dependencies, "build", None)
        if host is not None:
            groups.append(host.values())
        if build is not None:
            groups.append(build.values())
        for group in groups:
            for dep in group:
                folder = getattr(dep, "package_folder", None)
                if not folder:
                    continue
                libdir = os.path.join(folder, "lib")
                if os.path.isdir(libdir) and libdir not in found:
                    found.append(libdir)
        return found

    def _dependency_root(self, name):
        dep = self.dependencies[name]
        return dep.package_folder

    def _iso_jsondir(self):
        root = self._dependency_root("iso-codes")
        if not root:
            return None
        candidates = [
            os.path.join(root, "share", "iso-codes", "json"),
            os.path.join(root, "share", "iso-codes"),
        ]
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "iso_3166-1.json")):
                return cand
        return None

    def _libintl_path(self):
        dep = None
        build = getattr(self.dependencies, "build", None)
        if build is not None:
            dep = build.get("gettext")
        if dep is None or not dep.package_folder:
            return None
        libdir = os.path.join(dep.package_folder, "lib")
        for name in ("libintl.so.8", "libintl.so"):
            path = os.path.join(libdir, name)
            if os.path.exists(path):
                return path
        return None

    def _iso_localedir(self):
        root = self._dependency_root("iso-codes")
        if not root:
            return None
        share = os.path.join(root, "share")
        direct = os.path.join(share, "locale")
        marker = os.path.join(direct, "fr", "LC_MESSAGES", "iso_3166-1.mo")
        if os.path.isfile(marker):
            return direct
        if not os.path.isdir(share):
            return None
        for dirpath, _dirnames, filenames in os.walk(share):
            if "iso_3166-1.mo" in filenames and os.path.basename(dirpath) == "LC_MESSAGES":
                return os.path.dirname(os.path.dirname(dirpath))
        return None

    def _inject_meson_tools(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or ""
        tool_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        ar = compilers.get("ar") or ""
        ranlib = compilers.get("ranlib") or ""
        if tool_dir:
            if not ar:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(tool_dir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
            if not ranlib:
                for name in ("llvm-ranlib", "ranlib"):
                    cand = os.path.join(tool_dir, name)
                    if os.path.isfile(cand):
                        ranlib = cand
                        break
        pkg_config = ""
        pkgconf = self.dependencies.build.get("pkgconf")
        if pkgconf is not None and pkgconf.package_folder:
            for name in ("pkgconf", "pkg-config"):
                cand = os.path.join(pkgconf.package_folder, "bin", name)
                if os.path.isfile(cand):
                    pkg_config = cand
                    break
        if not pkg_config:
            pkg_config = shutil.which("pkgconf") or shutil.which("pkg-config") or ""
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]\n" not in content:
                continue
            extra = ""
            if ar and "\nar =" not in content:
                extra += "ar = '%s'\n" % ar.replace("\\", "/")
            if ranlib and "\nranlib =" not in content:
                extra += "ranlib = '%s'\n" % ranlib.replace("\\", "/")
            if pkg_config and "\npkg-config =" not in content:
                extra += "pkg-config = '%s'\n" % pkg_config.replace("\\", "/")
            if not extra:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + extra, 1)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        if cross_building(self):
            self.output.info("meson machine file: cross")
        else:
            self.output.info("meson machine file: native")

    def _run_upstream_tests(self):
        # Parent g_test processes need the shared libraries. The integration
        # child wipes its environment and relies on the RPATH baked above.
        libdirs = self._runtime_libdirs()
        localedir = self._iso_localedir()
        # Prefix assignments survive conanbuild's virtualenv, which may
        # replace LD_LIBRARY_PATH when it is sourced.
        prefix = ""
        if libdirs:
            prefix += 'LD_LIBRARY_PATH="%s" ' % ":".join(libdirs)
        if localedir:
            prefix += 'ISO_CODES_LOCALEDIR="%s" ' % localedir
        command = prefix + 'meson test -C "%s" --print-errorlogs --no-rebuild -v' % self.build_folder
        self.run(command, env="conanbuild")
