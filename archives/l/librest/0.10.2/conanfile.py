#!/usr/bin/env python3
"""Conan recipe for librest 0.10.2 (Meson)."""

import filecmp
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibrestConan(ConanFile):
    name = "librest"
    version = "0.10.2"
    description = "RESTful web services access library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/librest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": True,
        "fPIC": True,
        "libsoup3/*:shared": True,
        "json-glib/*:shared": True,
    }
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("librest OHOS builds require armv8")

    def requirements(self):
        self.requires(
            "glib/2.84.0.1.1",
            options={"shared": True},
            headers=True,
            libs=True,
            run=True,
            transitive_headers=True,
            transitive_libs=True,
            force=True,
        )
        # Bind the released r3 recipe revision so stale local cache entries
        # cannot silently resolve the superseded glib2-based candidate.
        self.requires(
            "libsoup3/3.6.5-r3#3bbc75da3c320deddf009771ec0406f9"
        )
        self.requires("json-glib/1.10.6")
        self.requires("libxml2/2.15.3")
        # GLib's gobject-2.0.pc requires libffi.pc. Keep the published
        # transitive provider materialized so the Meson pkg-config probe can
        # resolve that public metadata in a closed Conan graph.
        self.requires("libffi/3.4.4", transitive_headers=True, transitive_libs=True)
        # glib's glib-2.0.pc requires pcre2; keep its generator metadata direct
        # when the graph-level override hides transitive pkg-config nodes.
        self.requires("pcre2/10.45", transitive_headers=True, transitive_libs=True)
        # gio-2.0.pc declares zlib privately, but Conan does not expose that
        # private node to this recipe's generator context. Keep the target
        # provider explicit so its pkg-config metadata and link closure remain
        # available to the OHOS worker.
        self.requires(
            "zlib/1.3.1.1",
            headers=True,
            libs=True,
            run=True,
            transitive_headers=True,
            transitive_libs=True,
        )
    def layout(self):
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._materialize_dependency_shared_aliases()
        for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not in PATH: " + ", ".join(missing)
            )

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if pkg_config is not None:
            pkg_config = str(pkg_config)
        else:
            pkg_config = shutil.which("pkg-config")
        if pkg_config is None:
            raise ConanInvalidConfiguration("pkg-config is required for Meson dependency discovery")
        # Conan writes the current `pkg-config` key from tools.gnu:pkg_config.
        # Keep Meson's historical alias byte-identical when both keys exist.
        tc.binaries["pkgconfig"] = pkg_config
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["soup2"] = "false"
        tc.project_options["tests"] = "true"

        extra_pc = []
        # Conan's override graph can alias name lookups to the forced provider;
        # select the resolved glib2 recipe so its pkg-config metadata matches.
        glib_dep = next(
            (dep for dep in self.dependencies.values()
             if getattr(getattr(dep, "ref", None), "name", None) == "glib2"),
            None,
        )
        if glib_dep is None:
            glib_dep = self.dependencies.get("glib")
        if glib_dep and glib_dep.package_folder:
            glib_pkg = glib_dep.package_folder
            glib_pc = os.path.join(glib_pkg, "lib", "pkgconfig")
            if os.path.isdir(glib_pc):
                pc_fix = os.path.join(self.build_folder, "glib2-pc-fix")
                os.makedirs(pc_fix, exist_ok=True)
                for filename in os.listdir(glib_pc):
                    if not filename.endswith(".pc"):
                        continue
                    with open(os.path.join(glib_pc, filename), "r", encoding="utf-8") as fh:
                        content = fh.read()
                    # A Windows package path contains backslashes; use a callable
                    # replacement so regex treats it as literal text.
                    content = re.sub(
                        r"^prefix=.*$",
                        lambda _match: f"prefix={glib_pkg}",
                        content,
                        count=1,
                        flags=re.M,
                    )
                    if filename in {
                        "glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
                        "gmodule-2.0.pc", "gmodule-no-export-2.0.pc",
                        "gmodule-export-2.0.pc", "gthread-2.0.pc",
                    }:
                        content = re.sub(r"^Libs:.*$", "Libs: ", content, flags=re.M)
                        content = re.sub(r"^Libs\.private:.*$", "Libs.private: ", content, flags=re.M)
                    with open(os.path.join(pc_fix, filename), "w", encoding="utf-8") as fh:
                        fh.write(content)
                extra_pc.append(pc_fix)
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in (
                    "glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                    "glib-compile-resources", "glib-compile-schemas",
                ):
                    path = os.path.join(glib_bin, tool)
                    if os.path.isfile(path):
                        tc.binaries[tool] = path
            glib_libdir = os.path.join(glib_pkg, "lib")
            if os.path.isdir(glib_libdir):
                link_flag = f"-L{glib_libdir}"
                if link_flag not in tc.c_link_args:
                    tc.c_link_args.append(link_flag)
                if link_flag not in tc.cpp_link_args:
                    tc.cpp_link_args.append(link_flag)
        # GLib's official glib-2.0.pc names PCRE2's module
        # ``libpcre2-8``. PkgConfigDeps emits the Conan target as
        # ``pcre2.pc`` instead, so expose the package's real module files
        # through a task-local directory with an absolute prefix.
        pcre2_dep = self.dependencies.get("pcre2")
        if pcre2_dep and pcre2_dep.package_folder:
            pcre2_pc_dir = os.path.join(pcre2_dep.package_folder, "lib", "pkgconfig")
            pcre2_pc_fix = os.path.join(self.build_folder, "pcre2-pc-fix")
            os.makedirs(pcre2_pc_fix, exist_ok=True)
            for filename in ("libpcre2-8.pc", "libpcre2-posix.pc"):
                source_pc = os.path.join(pcre2_pc_dir, filename)
                if not os.path.isfile(source_pc):
                    continue
                with open(source_pc, "r", encoding="utf-8") as fh:
                    content = fh.read()
                content = re.sub(
                    r"^prefix=.*$",
                    lambda _match: f"prefix={pcre2_dep.package_folder}",
                    content,
                    count=1,
                    flags=re.M,
                )
                with open(os.path.join(pcre2_pc_fix, filename), "w", encoding="utf-8") as fh:
                    fh.write(content)
            extra_pc.append(pcre2_pc_fix)

        # GLib's gobject-2.0.pc likewise refers to libffi by its upstream
        # module name, while the transitive Conan package is not emitted by
        # PkgConfigDeps for this recipe. Copy the real module metadata with a
        # task-local absolute prefix.
        libffi_dep = self.dependencies.get("libffi")
        if libffi_dep and libffi_dep.package_folder:
            libffi_pc_dir = os.path.join(libffi_dep.package_folder, "lib", "pkgconfig")
            libffi_pc_fix = os.path.join(self.build_folder, "libffi-pc-fix")
            os.makedirs(libffi_pc_fix, exist_ok=True)
            source_pc = os.path.join(libffi_pc_dir, "libffi.pc")
            if os.path.isfile(source_pc):
                with open(source_pc, "r", encoding="utf-8") as fh:
                    content = fh.read()
                content = re.sub(
                    r"^prefix=.*$",
                    lambda _match: f"prefix={libffi_dep.package_folder}",
                    content,
                    count=1,
                    flags=re.M,
                )
                with open(os.path.join(libffi_pc_fix, "libffi.pc"), "w", encoding="utf-8") as fh:
                    fh.write(content)
            extra_pc.append(libffi_pc_fix)

        # zlib ships zlib.pc but does not expose a Conan pkg-config property,
        # so PkgConfigDeps cannot materialize it. GLib's gio-2.0.pc keeps zlib
        # as a private requirement; bind the real metadata into this task's
        # pkg-config search path with an absolute package prefix.
        zlib_dep = self.dependencies.get("zlib")
        if zlib_dep is None:
            zlib_dep = next(
                (dep for dep in self.dependencies.values()
                 if getattr(getattr(dep, "ref", None), "name", None) == "zlib"),
                None,
            )
        if zlib_dep and zlib_dep.package_folder:
            zlib_pc_dir = os.path.join(zlib_dep.package_folder, "lib", "pkgconfig")
            zlib_pc_fix = os.path.join(self.build_folder, "zlib-pc-fix")
            os.makedirs(zlib_pc_fix, exist_ok=True)
            source_pc = os.path.join(zlib_pc_dir, "zlib.pc")
            if os.path.isfile(source_pc):
                with open(source_pc, "r", encoding="utf-8") as fh:
                    content = fh.read()
                content = re.sub(
                    r"^prefix=.*$",
                    lambda _match: f"prefix={zlib_dep.package_folder}",
                    content,
                    count=1,
                    flags=re.M,
                )
                with open(os.path.join(zlib_pc_fix, "zlib.pc"), "w", encoding="utf-8") as fh:
                    fh.write(content)
            extra_pc.append(zlib_pc_fix)
        # MesonToolchain carries this into the native file, but the worker's
        # pkg-config subprocess may be invoked outside Meson's native-file
        # lookup path. Bind the same task-local directories to Conan's build
        # environment so both entry points resolve identical metadata.
        if extra_pc:
            for pc_dir in extra_pc:
                self.buildenv_info.prepend_path("PKG_CONFIG_PATH", pc_dir)
            self.output.info(
                "Task-local pkg-config dirs: " + os.pathsep.join(extra_pc)
            )
        tc.pkg_config_path = os.pathsep.join(extra_pc + [tc.pkg_config_path])

        # Meson runs the upstream tests from the build tree on the OHOS worker.
        # Bind the host dependency library closure into each test executable so
        # the target loader can resolve indirect SONAMEs such as json-glib
        # without relying on a worker-specific shell environment.
        runtime_libdirs = self._dependency_runtime_libdirs()
        runtime_stage = self._stage_runtime_library_closure(runtime_libdirs)
        runtime_search_dirs = [runtime_stage]
        for libdir in runtime_search_dirs:
            rpath_flag = f"-Wl,--disable-new-dtags,-rpath,{libdir}"
            if rpath_flag not in tc.c_link_args:
                tc.c_link_args.append(rpath_flag)
            if rpath_flag not in tc.cpp_link_args:
                tc.cpp_link_args.append(rpath_flag)
            # The OHOS worker invokes Meson tests with a fresh loader
            # environment; bind the same dependency closure explicitly so
            # indirect SONAMEs (for example json-glib behind librest) resolve
            # even when the worker linker drops target RPATH flags.
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        self._bind_runtime_library_path(runtime_search_dirs)
        self.output.info("Target test runtime RPATH dirs: " + os.pathsep.join(runtime_search_dirs))
        tc.generate()

        generated_glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(generated_glib_pc):
            with open(generated_glib_pc, "r", encoding="utf-8") as fh:
                content = fh.read()
            content = re.sub(r"^Libs:.*$", "Libs: ", content, flags=re.M)
            with open(generated_glib_pc, "w", encoding="utf-8") as fh:
                fh.write(content)

    def _materialize_dependency_shared_aliases(self):
        """Make task-private Conan .so aliases readable by Windows clang.

        Conan packages downloaded from POSIX archives retain aliases such as
        ``libfoo.so -> libfoo.so.0 -> libfoo.so.0.1``.  On a Windows-hosted
        OHOS cross build those reparse points are not usable by the compiler
        wrapper.  Validate the complete in-package chain first, then replace
        only the explicit aliases with byte-identical regular files.
        """
        for dep_name, dep in self.dependencies.items():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            libdir = os.path.abspath(os.path.join(package_folder, "lib"))
            if not os.path.isdir(libdir):
                continue
            for filename in os.listdir(libdir):
                if not (filename.endswith(".so") or ".so." in filename):
                    continue
                alias = os.path.join(libdir, filename)
                if not os.path.islink(alias):
                    continue

                target = alias
                seen = set()
                while os.path.islink(target):
                    target_key = os.path.normcase(os.path.abspath(target))
                    if target_key in seen:
                        raise ConanInvalidConfiguration(
                            f"cyclic shared-library alias in {dep_name}: {filename}"
                        )
                    seen.add(target_key)
                    link_target = os.readlink(target)
                    target = (
                        link_target
                        if os.path.isabs(link_target)
                        else os.path.join(os.path.dirname(target), link_target)
                    )
                    target = os.path.abspath(os.path.normpath(target))

                try:
                    inside = os.path.commonpath([libdir, target]) == libdir
                except ValueError:
                    inside = False
                if not inside or not os.path.isfile(target):
                    raise ConanInvalidConfiguration(
                        f"invalid shared-library alias in {dep_name}: {filename}"
                    )

                os.unlink(alias)
                shutil.copy2(target, alias)
                self.output.info(
                    f"Materialized dependency shared alias {dep_name}/{filename}"
                )

    def _dependency_runtime_libdirs(self):
        """Return unique host dependency library directories in graph order."""
        runtime_libdirs = []
        host_deps = getattr(self.dependencies, "host", self.dependencies)
        for dep in host_deps.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for libdir in getattr(dep.cpp_info, "libdirs", []) or ["lib"]:
                path = libdir if os.path.isabs(libdir) else os.path.join(package_folder, libdir)
                path = os.path.abspath(path)
                if os.path.isdir(path) and path not in runtime_libdirs:
                    runtime_libdirs.append(path)
        return runtime_libdirs

    def _stage_runtime_library_closure(self, runtime_libdirs):
        """Copy the verified dependency SONAME closure into one short directory.

        Some OHOS workers expose every dependency directory in
        ``LD_LIBRARY_PATH`` but still stop resolving entries late in that long
        list.  Meson tests only need the dependency shared objects, so stage
        their already-materialized regular files into a build-local directory.
        A conflicting duplicate SONAME is rejected instead of being silently
        overwritten.
        """
        runtime_stage = os.path.join(self.build_folder, "runtime-libs")
        os.makedirs(runtime_stage, exist_ok=True)
        staged = 0
        for libdir in runtime_libdirs:
            for filename in sorted(os.listdir(libdir)):
                if not (filename.endswith(".so") or ".so." in filename):
                    continue
                source = os.path.join(libdir, filename)
                if os.path.islink(source) or not os.path.isfile(source):
                    raise ConanInvalidConfiguration(
                        f"runtime shared library is not a regular file: {source}"
                    )
                destination = os.path.join(runtime_stage, filename)
                if os.path.exists(destination):
                    if not os.path.isfile(destination) or not filecmp.cmp(
                        source, destination, shallow=False
                    ):
                        raise ConanInvalidConfiguration(
                            f"conflicting runtime shared library: {filename}"
                        )
                    continue
                shutil.copy2(source, destination)
                staged += 1
        if staged == 0:
            raise ConanInvalidConfiguration("dependency runtime closure is empty")
        self.output.info(
            f"Staged dependency runtime closure: {runtime_stage} ({staged} files)"
        )
        return runtime_stage

    def _inject_project_runtime_roots(self, runtime_stage):
        """Keep critical OHOS runtime roots in project targets only.

        The OHOS worker loader can resolve direct dependencies from a test
        executable while failing to apply that executable's search path to an
        indirect dependency behind a just-built shared library.  Meson puts
        the complete dependency graph on the link line, but its default
        ``--as-needed`` drops libraries that are only needed transitively.
        The roots cannot be placed in MesonToolchain.c_link_args because those
        arguments also reach Meson's unsigned compiler-runnability probe on a
        native OHOS worker.  Insert project link arguments after ``project()``
        but before any targets are declared, so only real project outputs carry
        the direct DT_NEEDED entries.
        """
        root_names = ("libintl.so.8", "libjson-glib-1.0.so.0")
        root_paths = []
        for filename in root_names:
            path = os.path.join(runtime_stage, filename)
            if not os.path.isfile(path) or os.path.islink(path):
                raise ConanInvalidConfiguration(
                    f"direct target runtime root is not a regular file: {path}"
                )
            root_paths.append(os.path.abspath(path))

        meson_file = os.path.join(self.source_folder, "meson.build")
        with open(meson_file, "r", encoding="utf-8") as handle:
            content = handle.read()
        marker = "glib_dep = dependency('glib-2.0', version: '>= 2.44')"
        if content.count(marker) != 1:
            raise ConanInvalidConfiguration(
                "librest Meson dependency marker is missing or ambiguous"
            )
        block_lines = [
            "# Conan OHOS target-test runtime roots: keep as separate driver arguments.",
            "add_project_link_arguments(",
            "  '-Wl,--no-as-needed',",
        ]
        for path in root_paths:
            normalized = path.replace("\\", "/")
            if "'" in normalized:
                raise ConanInvalidConfiguration(
                    f"unsupported quote in target runtime root: {normalized}"
                )
            block_lines.append(f"  '{normalized}',")
        block_lines.extend([
            "  '-Wl,--as-needed',",
            "  language: 'c',",
            ")",
            "",
        ])
        content = content.replace(marker, "\n".join(block_lines) + marker)
        with open(meson_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("Forced target runtime DT_NEEDED roots: " + ":".join(root_paths))

    def _sign_native_ohos_runtime_roots(self, runtime_dir):
        """Self-sign task-private direct roots at their final native path.

        A release signature remains present in copied Conan libraries, but an
        OHOS native worker may reject that copied identity even when the file is
        reached through exec-time DT_NEEDED. Re-sign only the two observed
        direct roots, never the shared Conan cache, and make signing the final
        mutation at each loader-visible task-private location.
        """
        if str(self.settings.os) != "OHOS" or not can_run(self):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        for tool in (objcopy, sign_tool, readelf):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    f"native OHOS runtime signing tool is missing: {tool}"
                )

        for filename in ("libintl.so.8", "libjson-glib-1.0.so.0"):
            path = os.path.join(runtime_dir, filename)
            if not os.path.isfile(path) or os.path.islink(path):
                raise ConanInvalidConfiguration(
                    f"native OHOS runtime root is not a regular file: {path}"
                )
            cleanup = subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if cleanup.returncode != 0:
                raise ConanInvalidConfiguration(
                    f"failed to remove stale codesign from {path}: "
                    f"{(cleanup.stdout + cleanup.stderr).strip()}"
                )
            signed = path + ".signed.tmp"
            last_error = ""
            for _attempt in range(3):
                if os.path.exists(signed):
                    os.unlink(signed)
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", path, "-outFile", signed,
                     "-selfSign", "1"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0 and os.path.isfile(signed):
                    os.replace(signed, path)
                    os.chmod(path, 0o755)
                    break
                last_error = (result.stdout + result.stderr).strip()
            else:
                raise ConanInvalidConfiguration(
                    f"failed to self-sign native OHOS runtime root {path}: {last_error}"
                )
            verify = subprocess.run(
                [readelf, "-S", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if verify.returncode != 0 or ".codesign" not in verify.stdout:
                raise ConanInvalidConfiguration(
                    f"self-signed runtime root lacks .codesign: {path}"
                )
            self.output.info(f"Self-signed native OHOS runtime root: {path}")

    def _materialize_meson_first_runtime_dir(self, runtime_stage):
        """Put the dependency closure in Meson's first loader directory.

        ``meson test`` prepends the directory containing the just-built
        ``librest`` shared object to ``LD_LIBRARY_PATH``.  Some OHOS workers do
        not reliably continue to later entries, so keeping the dependency
        closure only in ``runtime-libs`` is insufficient even though Meson
        prints that directory in the test environment.
        """
        test_runtime_dir = os.path.join(self.build_folder, "rest")
        if not os.path.isdir(test_runtime_dir):
            raise ConanInvalidConfiguration(
                "Meson primary test runtime directory is missing"
            )
        materialized = 0
        for filename in sorted(os.listdir(runtime_stage)):
            source = os.path.join(runtime_stage, filename)
            if not os.path.isfile(source) or os.path.islink(source):
                raise ConanInvalidConfiguration(
                    f"staged runtime library is not a regular file: {source}"
                )
            destination = os.path.join(test_runtime_dir, filename)
            if os.path.exists(destination):
                if not os.path.isfile(destination) or not filecmp.cmp(
                    source, destination, shallow=False
                ):
                    raise ConanInvalidConfiguration(
                        f"conflicting Meson runtime library: {filename}"
                    )
                continue
            shutil.copy2(source, destination)
            materialized += 1
        required_json = os.path.join(test_runtime_dir, "libjson-glib-1.0.so.0")
        if materialized == 0 or not os.path.isfile(required_json):
            raise ConanInvalidConfiguration(
                "Meson primary runtime closure is empty or missing json-glib"
            )
        self.output.info(
            "Materialized Meson-first runtime closure: "
            f"{test_runtime_dir} ({materialized} files)"
        )
        return test_runtime_dir

    def _bind_runtime_library_path(self, runtime_libdirs=None):
        """Bind dependency loader directories to the current Conan process."""
        if runtime_libdirs is None:
            runtime_libdirs = self._dependency_runtime_libdirs()
        if not runtime_libdirs:
            return
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        merged = []
        for path in list(runtime_libdirs) + [part for part in existing.split(os.pathsep) if part]:
            path = os.path.abspath(path)
            if path not in merged:
                merged.append(path)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(merged)
        self.output.info("Current-process LD_LIBRARY_PATH: " + os.environ["LD_LIBRARY_PATH"])

    def build(self):
        apply_conandata_patches(self)
        runtime_stage = os.path.join(self.build_folder, "runtime-libs")
        if not os.path.isdir(runtime_stage):
            raise ConanInvalidConfiguration("generated runtime closure is missing")
        self._sign_native_ohos_runtime_roots(runtime_stage)
        self._inject_project_runtime_roots(runtime_stage)
        self._bind_runtime_library_path([runtime_stage])
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson_runtime_dir = self._materialize_meson_first_runtime_dir(runtime_stage)
        self._sign_native_ohos_runtime_roots(meson_runtime_dir)
        if can_run(self):
            # Meson.test() forces env="conanbuild", which replaces the
            # task's loader closure with dependency build directories. Run the
            # helper-equivalent command without an env file so the current
            # process LD_LIBRARY_PATH reaches every upstream test.
            self._bind_runtime_library_path([runtime_stage])
            self.run(
                f'meson test -v -C "{self.build_folder}"',
                env=None,
            )

    def package(self):
        Meson(self).install()
        license_src = os.path.join(self.source_folder, "COPYING")
        if os.path.isfile(license_src):
            license_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(license_dir, exist_ok=True)
            shutil.copy2(license_src, os.path.join(license_dir, "COPYING"))
        if self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            os.makedirs(libdir, exist_ok=True)
            for root, _dirs, files in os.walk(self.build_folder):
                for filename in files:
                    if filename.startswith(("librest-1.0.so.", "librest-extras-1.0.so.")):
                        shutil.copy2(os.path.join(root, filename), os.path.join(libdir, filename))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rest-1.0")
        rest = self.cpp_info.components["rest-1.0"]
        rest.libs = ["rest-1.0"]
        rest.includedirs = ["include/rest-1.0"]
        rest.requires = [
            "glib::glib",
            "libsoup3::libsoup3",
            "json-glib::json-glib-1.0",
            "libxml2::libxml2",
            "pcre2::pcre2",
            "libffi::libffi",
            "zlib::zlib",
        ]
        for depname in ("glib", "libsoup3", "json-glib", "libxml2"):
            dep = self.dependencies.get(depname)
            if not dep or not dep.package_folder:
                continue
            base = dep.package_folder
            for inc in dep.cpp_info.includedirs or ["include"]:
                path = inc if os.path.isabs(inc) else os.path.join(base, inc)
                if os.path.isdir(path) and path not in rest.includedirs:
                    rest.includedirs.append(path)
            for libdir in dep.cpp_info.libdirs or ["lib"]:
                path = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(path) and path not in rest.libdirs:
                    rest.libdirs.append(path)
        rest.set_property("cmake_target_name", "rest-1.0::rest-1.0")
        rest.set_property("pkg_config_name", "rest-1.0")
        rest.system_libs = ["m", "pthread", "dl"]

        extras = self.cpp_info.components["rest-extras-1.0"]
        extras.libs = ["rest-extras-1.0"]
        extras.includedirs = ["include/rest-1.0"]
        extras.requires = ["rest-1.0"]
        extras.set_property("cmake_target_name", "rest-1.0::rest-extras-1.0")
        extras.set_property("pkg_config_name", "rest-extras-1.0")
        extras.system_libs = ["m", "pthread", "dl"]
