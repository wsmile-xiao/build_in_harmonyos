#!/usr/bin/env python3
"""Conan recipe — RHVoice 1.14.0 (free TTS speech synthesizer, SCons build).

Upstream 1.14.0 drives its build with SCons (the CMake files in the tree only
carry sanitizer helpers).  The release tarball leaves the external/ git
submodules empty, so the boost headers the build needs come from the Conan
package of boost instead of the vendored copy.

SCons is not published to the ohpcd registry, so generate() installs it into a
private prefix inside the build folder and exposes it through PYTHONPATH (same
strategy as archives/d/dxx-rebirth/0.6).  The audio backends (pulse/libao/
portaudio) and the speech-dispatcher module are left disabled: RHVoice's C API
hands samples to the caller through the RHVoice_callbacks it is given, which is
what a HarmonyOS application uses.

Upstream keeps language and voice data in separate repositories and the engine
refuses to start without at least one voice, so source() also unpacks the
language/voice archives pinned in conandata.yml ("data_sources"): the English
language pack and the CC BY-SA 4.0 Dasha-Eng voice.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import build_jobs, can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# The community PyPI mirror is the one configured for ohpcd workers; passing it
# explicitly keeps the SCons bootstrap reproducible on a clean CI machine.
_PIP_INDEX_URL = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
_PIP_TRUSTED_HOST = "pypi.cnb.cool"
_SCONS_VERSION = "4.10.0"


class RhvoiceConan(ConanFile):
    name = "rhvoice"
    version = "1.14.0"
    description = "A free and open source speech synthesizer (TTS engine)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/RHVoice/RHVoice"
    url = "https://github.com/RHVoice/RHVoice"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream vendors boost as git submodules, which source tarballs do
        # not carry, so the headers come from the Conan package instead.
        self.requires("boost/1.91.0.1.3")

    def _boost_include_dir(self):
        dep = self.dependencies["boost"]
        candidates = []
        for rel in dep.cpp_info.includedirs or ["include"]:
            candidates.append(
                rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
            )
        for path in candidates:
            if os.path.isdir(os.path.join(path, "boost")):
                return path
        return candidates[0] if candidates else None

    def _stub_boost_submodules(self):
        """Give the vendored boost SConscript the directories it walks.

        Without the submodules it fails while listing
        external/libs/boost/libs/*/include/boost, and the boost_headers alias
        that src/core/SConscript depends on would never be exported.
        """
        libs = os.path.join(self.build_folder, "external", "libs", "boost", "libs")
        if not os.path.isdir(libs):
            return
        for name in os.listdir(libs):
            os.makedirs(
                os.path.join(libs, name, "include", "boost"), exist_ok=True
            )

    def _unpack_data_source(self, kind, name, source):
        """Fetch one language/voice data repository into data/<kind>/<name>.

        The archives carry a single top directory, and voice repositories ship
        model data only: the voice metadata file the engine expects is written
        from the fields declared next to the URL in conandata.yml.
        """
        staging = "data-source-" + name
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            filename=name + ".tar.gz",
            destination=os.path.join(self.source_folder, staging),
            strip_root=False,
        )
        unpacked = os.path.join(self.source_folder, staging)
        entries = os.listdir(unpacked)
        if len(entries) != 1:
            raise ConanException(f"{name}: unexpected archive layout {entries}")
        target = os.path.join(self.source_folder, "data", kind, name)
        if os.path.isdir(target):
            shutil.rmtree(target)  # the empty submodule placeholder
        shutil.move(os.path.join(unpacked, entries[0]), target)
        shutil.rmtree(unpacked)
        fields = source.get("fields")
        if fields:
            with open(os.path.join(target, kind[:-1] + ".info"), "w") as handle:
                for key in sorted(fields):
                    handle.write(f"{key}={fields[key]}\n")

    def _fetch_data_sources(self):
        for kind, entries in (self.conan_data.get("data_sources") or {}).items():
            for name, source in entries.items():
                self._unpack_data_source(kind, name, source)

    def _drop_empty_data_placeholders(self):
        """Remove the language/voice submodule placeholders left empty.

        The source archive carries data/languages and data/voices as empty
        directories, because upstream keeps that content in separate git
        repositories and distributes it as data packages (Debian splits
        rhvoice-voice-* off the engine in the same way).  data/SConscript
        aborts on an empty placeholder, so drop the ones that no data source
        filled in.
        """
        for kind in ("languages", "voices"):
            root = os.path.join(self.source_folder, "data", kind)
            if not os.path.isdir(root):
                continue
            for entry in sorted(os.listdir(root)):
                path = os.path.join(root, entry)
                if os.path.isdir(path) and not os.listdir(path):
                    os.rmdir(path)

    def source(self):
        # The codeload URL of a tag carries no file suffix, so name the
        # downloaded file explicitly and let conan extract it as a tarball.
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename="rhvoice-1.14.0.tar.gz",
            strip_root=True,
        )
        apply_conandata_patches(self)
        self._fetch_data_sources()
        self._drop_empty_data_placeholders()

    def generate(self):
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)
        self.run(
            f'"{sys.executable}" -m pip install --quiet --no-input '
            f"--disable-pip-version-check --no-warn-script-location "
            f'--target="{scons_prefix}" --index-url {_PIP_INDEX_URL} '
            f"--trusted-host {_PIP_TRUSTED_HOST} scons=={_SCONS_VERSION}"
        )
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _command_shell():
        """Absolute path of a POSIX shell, or None to keep the SCons default."""
        for candidate in ("/system/bin/sh", "/usr/bin/sh", "/bin/sh"):
            if os.path.exists(candidate):
                return candidate
        return None

    def _scons_env(self):
        """Variables the SCons process needs on top of the toolchain buildenv."""
        env = Environment()
        env.define_path("PYTHONPATH", os.path.join(self.build_folder, "_scons_env"))
        # R33: tool paths come from the Conan toolchain, never from the ambient
        # shell environment (which is empty on a release worker).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++")
        toolbin = os.path.dirname(cxx)
        cc = compilers.get("c", "clang")
        # RHVOICE_SCONS_<name> construction variables (patches/0001-*): SCons
        # cannot discover a cross toolchain, and the bare "sh" it spawns
        # commands with is not searched in PATH by posix_spawn.
        scons_vars = {"CC": cc, "CXX": cxx}
        for name in ("AR", "RANLIB"):
            candidate = os.path.join(toolbin, "llvm-" + name.lower())
            if os.path.exists(candidate):
                scons_vars[name] = candidate
        # GNU make's jobserver talks through a FIFO in the temp directory, and
        # the platform default is not writable inside the build sandbox.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            env.define_path(name, tmpdir)
        shell = self._command_shell()
        if shell:
            scons_vars["SHELL"] = shell
        for name, value in scons_vars.items():
            env.define(name, value)
            env.define_path("RHVOICE_SCONS_" + name, value)
        return env.vars(self)

    def _scons_settings(self):
        """RHVoice SConstruct variables that select what gets built."""
        settings = [
            # Synthesized samples are returned through RHVoice_callbacks, so no
            # audio backend is needed; leaving the list empty also keeps
            # sd_module (speech-dispatcher) and sonic out of the build.
            'audio_libs=""',
            "enable_shared=%d" % (1 if self.options.shared else 0),
            "dev=0",
        ]
        boost_include = self._boost_include_dir()
        if boost_include:
            settings.append(f'CPPPATH="{boost_include}"')
        return settings

    def _scons(self, target, jobs):
        command = f"python3 -m SCons -j{jobs} {target} {' '.join(self._scons_settings())}"
        # The toolchain buildenv (CC/CXX come from it on cross builds) and the
        # private SCons prefix are applied in sequence, the inner one winning.
        with VirtualBuildEnv(self).vars().apply():
            with self._scons_env().apply():
                self.run(command)

    def build(self):
        self._stub_boost_submodules()
        self._scons("", build_jobs(self))
        if not can_run(self):
            self.output.info("Cross-compiling: upstream tests are not executed here.")

    def package(self):
        self._scons(f"install DESTDIR={self.package_folder} prefix=/usr", 1)

    def package_info(self):
        self.cpp_info.libs = ["RHVoice"]
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.includedirs = ["usr/include"]
        self.cpp_info.libdirs = ["usr/lib"]
        self.cpp_info.resdirs = ["usr/share"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "usr", "bin")
        )
