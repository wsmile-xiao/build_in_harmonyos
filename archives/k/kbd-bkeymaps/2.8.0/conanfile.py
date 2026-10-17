#!/usr/bin/env python3
"""Build the Kbd 2.8.0 binary keymap data package for HarmonyOS AArch64."""

import gzip
import os
import shutil
import subprocess
from collections import defaultdict

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class KbdBkeymapsConan(ConanFile):
    name = "kbd-bkeymaps"
    version = "2.8.0"
    description = "X.org-derived binary keyboard maps for BusyBox loadkmap"
    license = "GPL-2.0-or-later"
    homepage = "https://kbd-project.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "build-scripts"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                f"kbd-bkeymaps is generated for OHOS, got {self.settings.os}"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"kbd-bkeymaps requires HarmonyOS AArch64, got {self.settings.arch}"
            )

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def package_id(self):
        # The kernel keymap payload is fixed for OHOS AArch64 and does not
        # depend on the selected compiler or build type.
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-vlock",
            "--disable-libkfont",
            "--disable-compress",
            "--disable-tests",
            "--disable-nls",
        ])
        tc.generate()
        self._patch_generated_shell_scripts()

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_status_tmp()

        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.configure()
            for component in ("libcommon", "libkbdfile", "libkeymap"):
                autotools.make(args=["-C", os.path.join("src", component), "-j1"])
            autotools.make(args=["-C", "src", "loadkeys", "-j1"])
            self._generate_maps()

    def package(self):
        generated_maps = os.path.join(self.build_folder, "bkeymaps")
        copy(self, "*.bmap.gz", src=generated_maps,
             dst=os.path.join(self.package_folder, "share", "bkeymaps"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=os.path.join(self.source_folder, "data", "keymaps"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share/bkeymaps"]

    def _generate_maps(self):
        keymap_root = os.path.join(self.source_folder, "data", "keymaps")
        source_root = os.path.join(keymap_root, "i386")
        sources = sorted(
            os.path.join(directory, filename)
            for directory, _, filenames in os.walk(source_root)
            for filename in filenames
            if filename.endswith(".map")
        )
        if len(sources) < 180:
            raise ConanException(
                f"Expected the complete Kbd 2.8.0 i386 keymap set, found {len(sources)} maps"
            )

        loadkeys = os.path.join(self.build_folder, "src", "loadkeys")
        if not os.path.isfile(loadkeys):
            raise ConanException(f"Kbd loadkeys converter was not built: {loadkeys}")

        by_name = defaultdict(list)
        for path in sources:
            by_name[os.path.basename(path)[:-4]].append(path)

        output_root = os.path.join(self.build_folder, "bkeymaps")
        shutil.rmtree(output_root, ignore_errors=True)
        os.makedirs(output_root, exist_ok=True)

        env = os.environ.copy()
        env["LOADKEYS_KEYMAP_PATH"] = os.path.join(keymap_root, "**")
        generated = 0
        for keymap_name, candidates in sorted(by_name.items()):
            ordered = sorted(candidates, key=self._source_priority)
            group = keymap_name.split("-", 1)[0].lower()
            canonical = os.path.join(output_root, group, f"{keymap_name}.bmap.gz")
            source = self._conversion_source(ordered[0])
            self._write_map(loadkeys, source, canonical, env)
            generated += 1

            # Preserve same-named layouts (for example qwerty and qwertz
            # variants) under unambiguous aliases instead of silently dropping
            # one of the upstream maps.
            for duplicate in ordered[1:]:
                family = os.path.basename(os.path.dirname(duplicate)).lower()
                alias = os.path.join(
                    output_root, group, f"{keymap_name}-{family}.bmap.gz"
                )
                if os.path.exists(alias):
                    raise ConanException(f"Duplicate binary keymap output path: {alias}")
                source = self._conversion_source(duplicate)
                self._write_map(loadkeys, source, alias, env)
                generated += 1

        if generated != len(sources):
            raise ConanException(
                f"Generated {generated} binary maps from {len(sources)} upstream maps"
            )
        self.output.info(f"Generated {generated} BusyBox binary keymaps")

    @staticmethod
    def _source_priority(path):
        family = os.path.basename(os.path.dirname(path)).lower()
        priorities = {
            "qwerty": 0,
            "qwertz": 1,
            "azerty": 2,
            "fgGIod".lower(): 3,
            "dvorak": 4,
            "olpc": 20,
        }
        return priorities.get(family, 10), path

    def _conversion_source(self, source):
        if os.path.basename(source) != "3l.map":
            return source
        if os.path.basename(os.path.dirname(source)).lower() != "neo":
            return source

        with open(source, "rb") as keymap:
            contents = keymap.read()
        normalized = contents.replace(b"Meta_PageUp", b"PageUp")
        if normalized == contents:
            return source

        normalized_path = source + ".ohos-normalized"
        with open(normalized_path, "wb") as keymap:
            keymap.write(normalized)
        self.output.warning(
            "Mapping unsupported 3l.map keysym Meta_PageUp to PageUp for bkeymap output"
        )
        return normalized_path

    @staticmethod
    def _write_map(loadkeys, source, destination, env):
        result = subprocess.run(
            [loadkeys, "-u", "-b", source],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
            raise ConanException(
                f"loadkeys could not convert {source} (exit {result.returncode}): "
                f"{diagnostic}"
            )
        if not result.stdout.startswith(b"bkeymap"):
            raise ConanException(f"loadkeys emitted an invalid binary map for {source}")

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as raw:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0
            ) as compressed:
                compressed.write(result.stdout)
        os.chmod(destination, 0o644)

    def _build_environment(self):
        env = AutotoolsToolchain(self).environment()
        env.compose_env(VirtualBuildEnv(self).vars())
        env.compose_env(AutotoolsDeps(self).vars())
        if str(self.settings.os) == "OHOS":
            env.define("CONFIG_SHELL", "/system/bin/sh")
            env.define("SHELL", "/system/bin/sh")
            env.define("TMPDIR", self._ohos_tmpdir())
            env.prepend_path("PATH", "/data/service/hnp/bin")
            env.prepend_path("PATH", "/storage/Users/currentUser/usr/local/bin")
        return env.vars(self)

    def _patch_generated_shell_scripts(self):
        if str(self.settings.os) != "OHOS":
            return
        for filename in os.listdir(self.generators_folder):
            if not filename.endswith(".sh"):
                continue
            path = os.path.join(self.generators_folder, filename)
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            changed = False
            for index, line in enumerate(lines):
                if line.startswith("export CONFIG_SHELL="):
                    lines[index] = 'export CONFIG_SHELL="/system/bin/sh"\n'
                    changed = True
                elif line.startswith("export SHELL="):
                    lines[index] = 'export SHELL="/system/bin/sh"\n'
                    changed = True
            if changed:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.writelines(lines)
                os.chmod(path, 0o755)

    def _ohos_tmpdir(self):
        configured = os.environ.get("TMPDIR")
        if configured and os.path.abspath(configured) != "/tmp":
            tmpdir = configured
        else:
            tmpdir = os.path.join(self.generators_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _patch_configure_status_tmp(self):
        if str(self.settings.os) != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return

        with open(configure, "r", encoding="utf-8") as handle:
            content = handle.read()
        replacements = {
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&':
                'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&',
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")':
                'tmp="${TMPDIR:-.}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
            '"cannot create a temporary directory in ."':
                '"cannot create a temporary directory"',
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        with open(configure, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(configure, 0o755)
