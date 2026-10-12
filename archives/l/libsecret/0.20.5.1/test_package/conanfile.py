#!/usr/bin/env python3
"""Consumer test for libsecret 0.20.5.1 — meson + pkg-config consumer (R34).

Two probes are built and executed against the produced artifact:

  * ``link_probe``   — linked via the exported ``secret-1`` pkg-config module
                       (proves the downstream link contract: headers + ``-lsecret-1``).
  * ``dlopen_probe`` — NOT linked against libsecret; it ``dlopen()``s the produced
                       ``libsecret-1.so.0`` with ``RTLD_NOW`` and resolves/calls real
                       ``secret_*`` API symbols. This is the acceptance test for the
                       published-0.20.5 defect: that artifact carried a stale
                       ``.codesign`` section and the OHOS loader rejected it with
                       EACCES ("Permission denied"). A linked probe would hide the
                       defect because the loader maps the library at process start
                       and ``dlopen()`` would just return the existing handle.

The glib package ships pkg-config metadata only (CMakeDeps include dirs come out
empty for it), so the consumer builds with Meson + PkgConfigDeps, matching the
main recipe's proven dependency resolution path.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibsecretTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib-2.0.pc Requires: proxy-libintl + libpcre2-8; making them direct
        # here lets PkgConfigDeps emit .pc for each (upstream ships none).
        self.requires("proxy-libintl/0.5")
        self.requires("pcre2/10.47")
        self.requires("libffi/3.5.2")
        self.requires("zlib/1.3.2")
        self.requires("libgpg-error/1.55")

    def build_requirements(self):
        # Same rationale as the main recipe: meson is not on PATH by default.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        # Dependency .pc files ship "prefix=/" — rewrite to the real package
        # folder so pkg-config resolves includes/libs inside the Conan cache.
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            src_pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(src_pc):
                real_prefix = dep.package_folder.replace(os.sep, "/")
                for pc_name in os.listdir(src_pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    with open(os.path.join(src_pc, pc_name), encoding="utf-8") as handle:
                        content = handle.read()
                    rewritten = re.sub(
                        r"^prefix=.*$", "prefix={}".format(real_prefix),
                        content, flags=re.MULTILINE,
                    )
                    with open(
                        os.path.join(self.generators_folder, pc_name),
                        "w", encoding="utf-8", newline="\n",
                    ) as handle:
                        handle.write(rewritten)
        # proxy-libintl has no .pc but glib-2.0.pc Requires it. It is a
        # transitive dep here, so locate it by its libintl.h artifact.
        for dep in self.dependencies.values():
            if dep.package_folder and os.path.isfile(
                os.path.join(dep.package_folder, "include", "libintl.h")
            ):
                with open(
                    os.path.join(self.generators_folder, "proxy-libintl.pc"),
                    "w", encoding="utf-8", newline="\n",
                ) as handle:
                    handle.write(
                        "prefix={}\n".format(dep.package_folder.replace(os.sep, "/"))
                        + "libdir=${prefix}/lib\nincludedir=${prefix}/include\n\n"
                        + "Name: proxy-libintl\nDescription: intl proxy\nVersion: 0.5\n"
                        + "Libs: -L${libdir} -lintl\nCflags: -I${includedir}\n"
                    )
                break
        # Point meson at the host pkg-config for OHOS cross builds.
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if pkg_config and os.path.isfile(str(pkg_config)):
            replacement = "pkg-config = '{}'".format(os.path.abspath(str(pkg_config)))
            for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
                machine_file = os.path.join(self.generators_folder, filename)
                if not os.path.isfile(machine_file):
                    continue
                with open(machine_file, encoding="utf-8") as handle:
                    content = handle.read()
                if "pkg-config =" not in content:
                    content = content.replace(
                        "[binaries]\n", "[binaries]\n{}\n".format(replacement), 1
                    )
                    with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(content)
        VirtualRunEnv(self).generate()
        # R33: see the main recipe. This matters here even when the tested
        # package is served from the Conan cache (main generate() then never
        # runs), which is exactly when a bare inherited "AR=llvm-ar" reaches
        # meson and kills project() with `Unknown linker(s): [['llvm-ar']]`.
        ar_path = self._resolve_archiver()
        toolchain = MesonToolchain(self)
        if ar_path:
            os.environ["AR"] = ar_path
            toolchain.binaries["ar"] = ar_path
        else:
            os.environ.pop("AR", None)
        toolchain.generate()

    def _resolve_archiver(self):
        """Absolute archiver for meson, or "" (drop $AR instead — R33)."""
        candidates = []
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or ""
        if compiler:
            candidates.append(
                os.path.join(os.path.dirname(os.path.normpath(compiler)), "llvm-ar")
            )
        candidates += ["/data/service/hnp/bin/llvm-ar", "/data/service/hnp/bin/ar"]
        candidates += [shutil.which("llvm-ar") or "", shutil.which("ar") or ""]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return os.path.abspath(candidate)
        return ""

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Deliberately NOT meson.install()'ing the probes: `meson install`
        # rewrites their RPATH with patchelf, which invalidates the OHOS
        # linker signature and makes the probes themselves un-runnable
        # (E077). The probes are harness code, not the artifact under test,
        # so we simply execute the build-tree binaries — those keep the
        # signature the linker gave them.

    # ------------------------------------------------------------------ test
    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer binary is run on OHOS device")
            return

        link_probe = os.path.join(self.build_folder, "link_probe")
        dlopen_probe = os.path.join(self.build_folder, "dlopen_probe")

        runtime_dir = self._assemble_runtime()
        lib_artifact = os.path.join(runtime_dir, "libsecret-1.so.0")

        env = Environment()
        env.define("LD_LIBRARY_PATH", runtime_dir)

        with env.vars(self).apply():
            self.output.info("== link probe (downstream link/load contract) ==")
            self.run('"{}"'.format(link_probe))
            self.output.info("== dlopen acceptance probe (RTLD_NOW on the produced artifact) ==")
            self.run('"{}" "{}"'.format(dlopen_probe, lib_artifact))

    def _assemble_runtime(self):
        """Copy the produced library and every dependency .so as REAL files.

        The OHOS loader cannot resolve shared objects through the symlinks that
        the Conan cache uses (libsecret-1.so -> .so.0 -> .so.0.0.0), so each
        NEEDED object is materialised byte-for-byte next to the probes. Nothing
        is re-signed: the acceptance test must exercise the *produced artifact*
        exactly as it will be shipped (E077 — a stale `.codesign` stays stale
        and the dlopen probe then fails, which is the point).
        """
        runtime_dir = os.path.join(self.build_folder, "runtime")
        os.makedirs(runtime_dir, exist_ok=True)

        copied = []

        def real_copy(src, name):
            dst = os.path.join(runtime_dir, name)
            if os.path.exists(dst):
                return dst
            with open(os.path.realpath(src), "rb") as handle:
                data = handle.read()
            with open(dst, "wb") as handle:
                handle.write(data)
            os.chmod(dst, 0o755)
            copied.append(name)
            return dst

        tested = self.dependencies[self.tested_reference_str]
        tested_lib = os.path.join(tested.package_folder, "lib")
        # Ship the produced library under its SONAME — that is what consumers
        # (and dlopen("libsecret-1.so.0")) actually look up.
        for candidate in ("libsecret-1.so.0.0.0", "libsecret-1.so.0"):
            src = os.path.join(tested_lib, candidate)
            if os.path.isfile(os.path.realpath(src)):
                real_copy(src, "libsecret-1.so.0")
                break
        else:
            raise ConanException("produced libsecret-1.so.0 not found in %s" % tested_lib)

        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for name in sorted(os.listdir(lib_dir)):
                if ".so" not in name:
                    continue
                src = os.path.join(lib_dir, name)
                if os.path.isfile(os.path.realpath(src)):
                    real_copy(src, name)

        self.output.info("runtime dir: {} -> {}".format(runtime_dir, sorted(copied)))
        return runtime_dir
