#!/usr/bin/env python3
"""Native GCC 9 Ada compiler and runtime for HarmonyOS PC."""

import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import zlib
from pathlib import Path, PurePosixPath

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import copy, download, get, patch
from conan.tools.layout import basic_layout


class GccAdaConan(ConanFile):
    name = "gcc-ada"
    version = "9.5.0"
    package_type = "application"

    description = "GNU Compiler Collection 9 Ada compiler (GNAT)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/gcc-9/"

    settings = "os", "compiler", "build_type", "arch"

    _target_triplet = "aarch64-linux-ohos"
    _seed_triplet = "aarch64-alpine-linux-musl"
    _seed_version = "9.3.0"
    _upstream_test_sources = (
        (
            "gnat.dg",
            "gcc/testsuite/gnat.dg",
            (
                "abstract_with_anonymous_result.adb",
                "access_discr2.adb",
                "access_test.adb",
                "access3.adb",
                "access3.ads",
                "access4.adb",
                "aggr1.adb",
                "aggr3.adb",
                "alignment1.adb",
                "alignment10.adb",
                "alignment2.adb",
                "alignment7.adb",
                "alignment8.adb",
                "alignment9.adb",
                "array_bounds_test.adb",
                "array10.adb",
                "array12.adb",
                "array21.adb",
                "array3.adb",
                "array30.adb",
                "array31.adb",
                "array33.adb",
                "array34.adb",
                "array4.adb",
                "array6.adb",
                "concat_length.adb",
                "fixedpnt.adb",
                "fixedpnt5.adb",
                "modular1.adb",
                "modular2.adb",
                "modular3_pkg.ads",
                "modular3.adb",
                "overflow_sum3.adb",
            ),
        ),
        (
            "acats/tests",
            "gcc/testsuite/ada/acats/tests",
            (
                "a/a22006b.ada",
                "a/a22006c.ada",
                "a/a22006d.ada",
                "a/a35101b.ada",
                "c2/c23006a.ada",
                "c2/c2a021b.ada",
                "c3/c38006a.ada",
                "c4/c48004a.ada",
                "c5/c54a23a.ada",
                "c5/c55c02a.ada",
                "c9/c95040a.ada",
            ),
        ),
        (
            "acats/support",
            "gcc/testsuite/ada/acats/support",
            (
                "repbody.ada",
                "repspec.ada",
            ),
        ),
    )

    def export_sources(self):
        for filename in (
            "prepare_ohos_sources.py",
            "ohos.h",
            "prepare_ohos_bootstrap.py",
            "build_ohos_loader.sh",
        ):
            copy(
                self,
                filename,
                src=os.path.join(self.recipe_folder, "files"),
                dst=os.path.join(self.export_sources_folder, "files"),
            )
        copy(
            self,
            "0001-musl-ohos-xpm-loader.patch",
            src=os.path.join(self.recipe_folder, "patches"),
            dst=os.path.join(self.export_sources_folder, "patches"),
        )
        copy(
            self,
            "0002-gcc-ada-ohos-build-rules.patch",
            src=os.path.join(self.recipe_folder, "patches"),
            dst=os.path.join(self.export_sources_folder, "patches"),
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "gcc-ada is prepared for a native OHOS build only"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS GCC Ada package supports AArch64/armv8 only"
            )

    @staticmethod
    def _full_upstream_ada_tests_enabled():
        value = os.environ.get("GCC_ADA_FULL_UPSTREAM_TESTS", "")
        return value.strip().lower() in ("1", "true", "yes", "on")

    def build_requirements(self):
        if not self._full_upstream_ada_tests_enabled():
            return

        self.tool_requires("dejagnu/1.6.3.1")
        self.tool_requires("expect/5.45.4")
        self.tool_requires("tcl/8.6.14")

    def _build_requirement_tool(self, package_name, executable_name):
        dependency = self.dependencies.build[package_name]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(
            dependency.package_folder, bindirs[0], executable_name
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The {} build requirement does not provide {}: {}".format(
                    package_name, executable_name, executable
                )
            )
        return executable

    @property
    def _source_seed_root(self):
        return Path(self.source_folder) / "_gnat_seed"

    @property
    def _bootstrap_work_root(self):
        base = Path("/data/storage/el2/base/haps/entry/files")
        root = base / "gcc-ada-bootstrap-{}".format(os.getpid())
        probe = root / ".write-probe"
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe.write_bytes(b"gcc-ada")
            probe.unlink()
        except OSError as error:
            try:
                probe.unlink()
            except OSError:
                pass
            raise ConanInvalidConfiguration(
                "XPM bootstrap directory is not writable: {} ({})".format(
                    base, error
                )
            ) from error

        self.output.info(
            "Using XPM bootstrap directory: {}".format(root)
        )
        return root

    @property
    def _build_seed_root(self):
        return self._bootstrap_work_root / "seed"

    @property
    def _source_loader_root(self):
        return Path(self.source_folder) / "_bootstrap_musl"

    @property
    def _build_loader_root(self):
        return self._bootstrap_work_root / "musl"

    @property
    def _bootstrap_root(self):
        return self._bootstrap_work_root / "runtime"

    @property
    def _bootstrap_loader(self):
        return self._bootstrap_root / "ld-musl-aarch64.so.1"

    @property
    def _built_bootstrap_loader(self):
        return self._build_loader_root / "ld-musl-aarch64.so.1"

    @property
    def _seed_gcc_dir(self):
        return (
            self._build_seed_root
            / "usr"
            / "lib"
            / "gcc"
            / self._seed_triplet
            / self._seed_version
        )

    @property
    def _seed_libexec_dir(self):
        return (
            self._build_seed_root
            / "usr"
            / "libexec"
            / "gcc"
            / self._seed_triplet
            / self._seed_version
        )

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

        patch(
            self,
            base_path=self.source_folder,
            patch_file=os.path.join(
                self.export_sources_folder,
                "patches",
                "0002-gcc-ada-ohos-build-rules.patch",
            ),
            strip=1,
        )
        get(
            self,
            **sources["musl"],
            destination=str(self._source_loader_root),
            strip_root=True,
        )
        patch(
            self,
            base_path=str(self._source_loader_root),
            patch_file=os.path.join(
                self.export_sources_folder,
                "patches",
                "0001-musl-ohos-xpm-loader.patch",
            ),
            strip=1,
        )
        prepare_script = os.path.join(
            self.export_sources_folder, "files", "prepare_ohos_sources.py"
        )
        ohos_header = os.path.join(
            self.export_sources_folder, "files", "ohos.h"
        )
        subprocess.run(
            [sys.executable, prepare_script, self.source_folder, ohos_header],
            check=True,
        )

        self._source_seed_root.mkdir(parents=True, exist_ok=True)
        downloads = Path(self.source_folder) / "_gnat_seed_downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        packages = self.conan_data["bootstrap"]["alpine_gnat"]["packages"]
        pending_links = []
        for package_name, package in packages.items():
            archive = downloads / package_name
            download(
                self,
                url=package["url"],
                filename=str(archive),
                sha256=package["sha256"],
            )
            self._extract_apk(
                archive, self._source_seed_root, pending_links
            )
        self._materialize_seed_links(self._source_seed_root, pending_links)
        shutil.rmtree(downloads)
        self._validate_seed_layout(self._source_seed_root)
        if hasattr(os, "sync"):
            os.sync()

    @staticmethod
    def _extract_apk(archive, destination, pending_links):
        """Extract safe payload entries from an APKv2 gzip member chain."""
        compressed = archive.read_bytes()
        member_count = 0
        while compressed:
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            payload = decoder.decompress(compressed) + decoder.flush()
            if not decoder.eof:
                raise ConanInvalidConfiguration(
                    "Truncated Alpine APK gzip member: {}".format(archive)
                )
            compressed = decoder.unused_data
            member_count += 1
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as apk_tar:
                for member in apk_tar.getmembers():
                    name = member.name
                    if name.startswith("./"):
                        name = name[2:]
                    parts = PurePosixPath(name).parts
                    if (
                        not parts
                        or PurePosixPath(name).is_absolute()
                        or ".." in parts
                        or parts[0] not in ("lib", "usr")
                    ):
                        continue
                    target = destination.joinpath(*parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    if target.exists() or target.is_symlink():
                        if target.is_dir() and not target.is_symlink():
                            shutil.rmtree(target)
                        else:
                            target.unlink()
                    if member.isfile():
                        source = apk_tar.extractfile(member)
                        if source is None:
                            raise ConanInvalidConfiguration(
                                "Cannot extract {} from {}".format(
                                    member.name, archive
                                )
                            )
                        with source, target.open("wb") as output:
                            shutil.copyfileobj(source, output)
                        target.chmod(member.mode)
                    elif member.issym():
                        link_target = member.linkname
                        if link_target.startswith("/"):
                            resolved = destination / link_target.lstrip("/")
                        else:
                            resolved = target.parent / link_target
                        pending_links.append((target, resolved))
                    elif member.islnk():
                        resolved = destination / member.linkname.lstrip("/")
                        pending_links.append((target, resolved))
            del payload
        if member_count < 2:
            raise ConanInvalidConfiguration(
                "Unexpected Alpine APK member layout: {}".format(archive)
            )

    @staticmethod
    def _materialize_seed_links(seed_root, pending_links):
        root = seed_root.resolve()
        link_map = {
            link.absolute(): target.absolute()
            for link, target in pending_links
        }
        for link, first_target in link_map.items():
            target = first_target
            visited = {link}
            while target in link_map:
                if target in visited:
                    raise ConanInvalidConfiguration(
                        "Alpine seed contains a link cycle at {}".format(link)
                    )
                visited.add(target)
                target = link_map[target]
            if not target.exists():
                continue
            target = target.resolve(strict=True)
            try:
                target.relative_to(root)
            except ValueError as error:
                raise ConanInvalidConfiguration(
                    "Alpine seed link escapes its root: {}".format(link)
                ) from error
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.exists() or link.is_symlink():
                link.unlink()
            shutil.copy2(target, link)
            link.chmod(stat.S_IMODE(target.stat().st_mode))

    def _validate_seed_layout(self, seed_root):
        required = (
            Path("usr/bin/gcc"),
            Path("usr/bin/{}-gcc".format(self._seed_triplet)),
            Path("usr/bin/gnatmake"),
            Path("usr/bin/gnatbind"),
            Path("usr/bin/gnatlink"),
            Path("usr/bin/gnatchop"),
            Path("usr/libexec/gcc")
            / self._seed_triplet
            / self._seed_version
            / "gnat1",
            Path("usr/lib/gcc")
            / self._seed_triplet
            / self._seed_version
            / "adalib/libgnat.a",
            Path("usr/lib/libisl.so.15"),
            Path("usr/lib/libmpc.so.3"),
            Path("usr/lib/libmpfr.so.6"),
            Path("usr/lib/libgmp.so.10"),
            Path("lib/libz.so.1"),
        )
        missing = [
            str(item) for item in required if not (seed_root / item).is_file()
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "Incomplete Alpine GNAT seed: {}".format(", ".join(missing))
            )

    @property
    def _ohos_sysroot(self):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, cc_args = self._split_command(configured.get("c"), "clang")
        candidates = []

        try:
            resource = subprocess.run(
                [cc, *cc_args, "-print-resource-dir"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            resource = None
        if resource and resource.returncode == 0:
            resource_dir = resource.stdout.strip()
            if resource_dir:
                candidates.append(
                    os.path.join(
                        resource_dir,
                        "..",
                        "..",
                        "..",
                        "..",
                        "sysroot",
                    )
                )

        for compiler in (os.path.realpath(cc), os.path.abspath(cc)):
            compiler_dir = os.path.dirname(compiler)
            candidates.extend(
                (
                    os.path.join(compiler_dir, "..", "..", "sysroot"),
                    os.path.join(compiler_dir, "..", "sysroot"),
                )
            )

        checked = []
        for candidate in candidates:
            sysroot = os.path.normpath(candidate)
            if sysroot in checked:
                continue
            checked.append(sysroot)
            if os.path.isdir(os.path.join(sysroot, "usr", "include")):
                return sysroot

        raise ConanInvalidConfiguration(
            "OHOS SDK sysroot headers were not found; checked: {}".format(
                ", ".join(checked)
            )
        )

    @property
    def _ohos_target_include(self):
        include = os.path.join(
            self._ohos_sysroot, "usr", "include", self._target_triplet
        )
        if not os.path.isfile(os.path.join(include, "bits", "alltypes.h")):
            raise ConanInvalidConfiguration(
                "OHOS target C library headers were not found: {}".format(include)
            )
        return include

    @property
    def _ohos_target_lib(self):
        library = os.path.join(
            self._ohos_sysroot, "usr", "lib", self._target_triplet
        )
        required = ("Scrt1.o", "crti.o", "crtn.o", "libc.so")
        missing = [
            name
            for name in required
            if not os.path.isfile(os.path.join(library, name))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS target C runtime files were not found in {}: {}".format(
                    library, ", ".join(missing)
                )
            )
        return library

    @property
    def _ohos_libunwind(self):
        library = os.path.join(
            os.path.dirname(self._ohos_sysroot),
            "llvm",
            "lib",
            self._target_triplet,
            "libunwind.a",
        )
        if not os.path.isfile(library):
            raise ConanInvalidConfiguration(
                "OHOS SDK static unwind library was not found: {}".format(library)
            )
        return library

    @property
    def _ohos_llvm_lib(self):
        library = os.path.join(
            os.path.dirname(self._ohos_sysroot), "llvm", "lib"
        )
        required = ("libxml2.so.16", os.path.join("..", "bin", "lld"))
        missing = [
            name
            for name in required
            if not os.path.isfile(os.path.join(library, name))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS SDK linker runtime files were not found in {}: {}".format(
                    library, ", ".join(missing)
                )
            )
        return library

    def _ohos_tool_env(self):
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            value
            for value in (self._ohos_llvm_lib, env.get("LD_LIBRARY_PATH"))
            if value
        )
        return env

    @staticmethod
    def _split_command(configured, fallback):
        try:
            command = shlex.split(configured or fallback)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                "Invalid compiler command: {}".format(configured)
            ) from error
        if not command:
            raise ConanInvalidConfiguration("Compiler command is empty")
        executable = shutil.which(command[0])
        if not executable and os.path.isfile(command[0]):
            executable = os.path.abspath(command[0])
        if not executable:
            raise ConanInvalidConfiguration(
                "Compiler executable was not found: {}".format(command[0])
            )
        return executable, command[1:]

    @staticmethod
    def _required_executable(name, *candidates):
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate):
                resolved = os.path.abspath(candidate)
            if resolved and os.access(resolved, os.X_OK):
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name)
        )

    @staticmethod
    def _signing_wrapper_text(
        real_compiler, signer, objcopy, readelf, extra_args, link_args=()
    ):
        extra = " ".join(shlex.quote(value) for value in extra_args)
        setup = 'set -- {} "$@"'.format(extra) if extra else 'set -- "$@"'
        link_extra = " ".join(shlex.quote(value) for value in link_args)
        link_setup = (
            'set -- {} "$@"'.format(link_extra) if link_extra else ":"
        )
        return """#!/bin/sh
set -eu
real_compiler={real_compiler}
signer={signer}
objcopy={objcopy}
readelf={readelf}
{setup}

link=1
has_input=0
takes_value=0
for argument in "$@"; do
    if [ "$takes_value" -eq 1 ]; then
        takes_value=0
        continue
    fi
    case "$argument" in
        -c|-S|-E|-M|-MM|-fsyntax-only) link=0 ;;
        -o|-x|-isystem|-include|-imacros|-MF|-MT|-MQ|-B|-L|-I|-D|-U|-specs)
            takes_value=1 ;;
        -) has_input=1 ;;
        -*) ;;
        *) has_input=1 ;;
    esac
done
if [ "$link" -eq 1 ] && [ "$has_input" -eq 1 ]; then
    {link_setup}
fi

"$real_compiler" "$@"

output=""
previous=""
compile_only=0
for argument in "$@"; do
    if [ "$previous" = "-o" ]; then
        output="$argument"
        previous=""
        continue
    fi
    case "$argument" in
        -o) previous="-o" ;;
        -openmp*|-object*|-objc*|-ObjC*) ;;
        -o?*) output="${{argument#-o}}" ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done
if [ -z "$output" ] && [ "$compile_only" -eq 0 ]; then output=a.out; fi
if [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        unsigned="${{output}}.ohos-unsigned-$$"
        signed="${{output}}.ohos-signed-$$"
        trap 'rm -f "$unsigned" "$signed"' EXIT HUP INT TERM
        cp -p "$output" "$unsigned"
        "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
        "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
        "$readelf" -S "$signed" | grep -q '[.]codesign'
        mv "$signed" "$output"
        rm -f "$unsigned"
        trap - EXIT HUP INT TERM
        chmod +x "$output" 2>/dev/null || true
    fi
fi
""".format(
            real_compiler=shlex.quote(real_compiler),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
            setup=setup,
            link_setup=link_setup,
        )

    def _write_signing_wrapper(
        self, directory, name, real_compiler, extra_args=(), link_args=()
    ):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        wrapper = directory / name
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS compiler wrappers require binary-sign-tool, llvm-objcopy and llvm-readelf"
            )
        wrapper.write_text(
            self._signing_wrapper_text(
                real_compiler,
                signer,
                objcopy,
                readelf,
                tuple(extra_args),
                tuple(link_args),
            ),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        return str(wrapper)

    def _install_native_collect_ld(self):
        linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )
        collect_ld = Path(self.build_folder) / "gcc" / "collect-ld"
        if not collect_ld.is_file():
            raise ConanInvalidConfiguration(
                "GCC collect-ld script was not generated: {}".format(collect_ld)
            )
        with open(linker, "rb") as source, open(collect_ld, "wb") as destination:
            shutil.copyfileobj(source, destination)
        collect_ld.chmod(0o755)

    def _build_bootstrap_loader(self, configured):
        script = Path(self.export_sources_folder) / "files" / "build_ohos_loader.sh"
        cc, cc_args = self._split_command(configured.get("c"), "clang")
        ar, _ = self._split_command(configured.get("ar"), "llvm-ar")
        ranlib, _ = self._split_command(configured.get("ranlib"), "llvm-ranlib")
        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        configure_shell = self._required_executable(
            "POSIX shell", "/bin/sh", "sh"
        )
        loader_build_root = self._build_loader_root
        loader_build_root.parent.mkdir(parents=True, exist_ok=True)
        env = self._ohos_tool_env()
        env["CC"] = shlex.join([cc] + cc_args)
        env["AR"] = ar
        env["RANLIB"] = ranlib
        env["CONFIG_SHELL"] = configure_shell
        env["PATH"] = ":".join(
            [
                "/data/service/hnp/make.org/make_4.4.1/bin",
                "/data/service/hnp/bin",
                env.get("PATH", ""),
            ]
        )
        subprocess.run(
            [
                shell,
                str(script),
                str(self._source_loader_root),
                str(loader_build_root),
                str(self._built_bootstrap_loader),
            ],
            cwd=str(loader_build_root.parent),
            env=env,
            check=True,
        )
        if not self._built_bootstrap_loader.is_file():
            raise ConanInvalidConfiguration(
                "musl bootstrap loader was not built"
            )

    def _prepare_bootstrap_seed(self):
        script = (
            Path(self.export_sources_folder)
            / "files"
            / "prepare_ohos_bootstrap.py"
        )
        subprocess.run(
            [
                sys.executable,
                str(script),
                str(self._build_seed_root),
                str(self._bootstrap_root),
                str(self._built_bootstrap_loader),
            ],
            check=True,
        )

        adalib = self._seed_gcc_dir / "adalib"
        seed_major = self._seed_version.split(".", 1)[0]
        for library in ("gnat", "gnarl"):
            unversioned = adalib / "lib{}.a".format(library)
            versioned = adalib / "lib{}-{}.a".format(
                library, seed_major
            )
            if not unversioned.is_file():
                raise ConanInvalidConfiguration(
                    "Alpine GNAT static runtime was not found: {}".format(
                        unversioned
                    )
                )
            shutil.copy2(unversioned, versioned)

        self._sign_elf_tree(self._build_seed_root)
        self._sign_elf_tree(self._bootstrap_root)

    def _write_seed_runtime_launcher(self, wrapper_dir):
        wrapper_dir = Path(wrapper_dir)
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        launcher = wrapper_dir / "exec-with-seed-loader.py"
        library_dir = str(self._bootstrap_root / "lib")
        launcher.write_text(
            """#!{python}
import os
import sys


loader_fd = os.open({loader!r}, os.O_RDONLY)
if loader_fd != 9:
    os.dup2(loader_fd, 9, inheritable=True)
    os.close(loader_fd)
os.set_inheritable(9, True)
seed_library_paths = (
    {library_dir!r},
    {seed_lib!r},
    {seed_base_lib!r},
    {seed_gcc_lib!r},
    {seed_adalib!r},
)
os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
    seed_library_paths
    + (
        (os.environ["LD_LIBRARY_PATH"],) if os.environ.get("LD_LIBRARY_PATH") else ()
    )
)
os.environ["LIBRARY_PATH"] = os.pathsep.join(
    seed_library_paths
    + (
        (os.environ["LIBRARY_PATH"],) if os.environ.get("LIBRARY_PATH") else ()
    )
)
os.environ["GCC_EXEC_PREFIX"] = {gcc_exec_prefix!r}
target = sys.argv[1]
os.execv(target, [target] + sys.argv[2:])
""".format(
                python=sys.executable,
                library_dir=library_dir,
                loader=str(self._bootstrap_loader),
                seed_lib=str(self._build_seed_root / "usr/lib"),
                seed_base_lib=str(self._build_seed_root / "lib"),
                seed_gcc_lib=str(self._seed_gcc_dir),
                seed_adalib=str(self._seed_gcc_dir / "adalib"),
                gcc_exec_prefix=(
                    str(self._build_seed_root / "usr/libexec/gcc") + os.sep
                ),
            ),
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        return launcher

    def _write_seed_launcher(self, wrapper_dir):
        runtime = self._write_seed_runtime_launcher(wrapper_dir)
        seed_specs = Path(wrapper_dir) / "ohos-seed.specs"
        seed_specs.write_text(
            "*link_ssp:\n%{fno-stack-protector:}\n\n",
            encoding="ascii",
        )
        gcc_args = (
            "-B{}{}".format(self._seed_libexec_dir, os.sep),
            "-B{}{}".format(self._seed_gcc_dir, os.sep),
            "-B{}{}".format(self._ohos_target_lib, os.sep),
            "-B/data/service/hnp/bin/",
            "--sysroot={}".format(self._ohos_sysroot),
            "-specs={}".format(seed_specs),
            "-Wl,-rpath-link,{}".format(self._bootstrap_root / "lib"),
            "-Wl,-rpath-link,{}".format(self._build_seed_root / "lib"),
            "-Wl,-rpath-link,{}".format(self._build_seed_root / "usr/lib"),
            "-Wl,-rpath-link,{}".format(self._seed_gcc_dir),
            "-Wl,-rpath-link,{}".format(self._seed_gcc_dir / "adalib"),
            "-isystem",
            self._ohos_target_include,
            "-isystem",
            os.path.join(self._ohos_sysroot, "usr", "include"),
            "-D__availability__(...)=",
            "-D_FORTIFY_SOURCE=0",
        )
        seed_gcc = (
            self._build_seed_root
            / "usr/bin"
            / "{}-gcc".format(self._seed_triplet)
        )
        tools = {
            "alpine-gnat-gcc": (
                seed_gcc,
                gcc_args,
            ),
            "gnatmake": (self._build_seed_root / "usr/bin/gnatmake", ()),
            "gnatbind": (self._build_seed_root / "usr/bin/gnatbind", ()),
            "gnatlink": (self._build_seed_root / "usr/bin/gnatlink", ()),
            "gnatchop": (self._build_seed_root / "usr/bin/gnatchop", ()),
        }
        for name, (target, extra_args) in tools.items():
            wrapper = Path(wrapper_dir) / name
            wrapper.write_text(
                """#!{python}
import os
import sys

runtime = {runtime!r}
target = {target!r}
extra_args = {extra_args!r}
os.execv(runtime, [runtime, target, *extra_args, *sys.argv[1:]])
""".format(
                    python=sys.executable,
                    runtime=str(runtime),
                    target=str(target),
                    extra_args=tuple(str(item) for item in extra_args),
                ),
                encoding="utf-8",
            )
            wrapper.chmod(0o755)

        return str(Path(wrapper_dir) / "alpine-gnat-gcc")

    def generate(self):
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        full_upstream_tests = self._full_upstream_ada_tests_enabled()
        # GCC's parallel DejaGNU result combiner creates mode-0700 children.
        # The HMDFS build tree rejects later shell writes to those children.
        tmpdir = self._bootstrap_work_root / "testsuite-tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        tmpdir.chmod(0o775)

        if self._build_seed_root.exists():
            shutil.rmtree(self._build_seed_root)
        shutil.copytree(self._source_seed_root, self._build_seed_root)
        self._validate_seed_layout(self._build_seed_root)

        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        self._build_bootstrap_loader(configured)
        self._prepare_bootstrap_seed()
        cxx, cxx_args = self._split_command(configured.get("cpp"), "clang++")
        wrappers = Path(self.build_folder) / ".ohos-wrappers"
        seed_launcher = self._write_seed_launcher(wrappers)
        cc = self._write_signing_wrapper(wrappers, "gcc", seed_launcher)
        self._install_seed_driver_proxy(configured, cc)

        cxx = self._write_signing_wrapper(
            wrappers, "clangxx-sign", cxx, cxx_args
        )

        shell = self._required_executable(
            "POSIX shell", "/bin/sh", "sh"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")
        if full_upstream_tests:
            runtest = self._build_requirement_tool("dejagnu", "runtest")
            expect = self._build_requirement_tool("expect", "expect")
            tcl = self.dependencies.build["tcl"]
            tcl_libdir = os.path.join(tcl.package_folder, "lib")
            tcl_library = os.path.join(tcl_libdir, "tcl8.6")
        assembler = self._required_executable(
            "GNU assembler", "as", "/data/service/hnp/bin/as"
        )
        linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )
        cc_command = shlex.join([shell, cc])
        cxx_command = shlex.join([shell, cxx])

        env = Environment()
        env.define("CC", cc_command)
        env.define("CXX", cxx_command)
        env.define("CC_FOR_BUILD", cc_command)
        env.define("CXX_FOR_BUILD", cxx_command)
        env.define("GNATMAKE", str(wrappers / "gnatmake"))
        env.define("GNATBIND", str(wrappers / "gnatbind"))
        env.define("GNATLINK", str(wrappers / "gnatlink"))
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("TMPDIR", str(tmpdir))
        env.define("MAKEINFO", true_tool)
        env.define("HELP2MAN", true_tool)
        if full_upstream_tests:
            env.define("RUNTEST", runtest)
            env.define("EXPECT", expect)
            env.define("TCL_LIBRARY", tcl_library)
            env.define("DEJAGNU_TIMEOUT", "120")
        env.define("gcc_cv_c_no_fpie", "no")
        env.define("gcc_cv_no_pie", "no")
        env.define("ac_cv_header_sys_capability_h", "no")
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        env.define("AR", configured.get("ar", "llvm-ar"))
        env.define("RANLIB", configured.get("ranlib", "llvm-ranlib"))
        env.define("NM", configured.get("nm", "llvm-nm"))
        env.unset("ADA_INCLUDE_PATH")
        env.unset("ADA_OBJECT_PATH")
        env.unset("ADA_OBJECTS_PATH")
        if full_upstream_tests:
            env.prepend_path("PATH", os.path.dirname(runtest))
            env.prepend_path("PATH", os.path.dirname(expect))
        env.prepend_path("PATH", str(self._build_seed_root / "usr/bin"))
        env.prepend_path("PATH", str(wrappers))
        if full_upstream_tests:
            env.prepend_path("LD_LIBRARY_PATH", tcl_libdir)
        env.prepend_path("LD_LIBRARY_PATH", str(self._build_seed_root / "lib"))
        env.prepend_path("LD_LIBRARY_PATH", str(self._build_seed_root / "usr/lib"))
        env.prepend_path("LD_LIBRARY_PATH", self._ohos_llvm_lib)
        env.vars(self).save_script("gcc_ada_build_env")

    def _configure_args(self):
        return [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(self._target_triplet),
            "--host={}".format(self._target_triplet),
            "--target={}".format(self._target_triplet),
            "--enable-languages=c,ada",
            "--enable-threads=posix",
            "--enable-libada",
            "--disable-bootstrap",
            "--disable-lto",
            "--disable-plugin",
            "--disable-multilib",
            "--disable-nls",
            "--disable-shared",
            "--disable-libatomic",
            "--disable-libitm",
            "--disable-libsanitizer",
            "--disable-libgomp",
            "--disable-libquadmath",
            "--disable-libssp",
            "--disable-libvtv",
            "--disable-werror",
            "--without-isl",
            "--with-sysroot={}".format(self._ohos_sysroot),
            "--with-native-system-header-dir=/usr/include",
        ]

    def _run_unlimited(self, command, cwd):
        shell = self._required_executable(
            "POSIX shell", os.environ.get("CONFIG_SHELL"), "/bin/sh", "sh"
        )
        wrapped = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("gcc-ada-build"),
            shlex.quote(shell),
            shlex.quote(command),
        )
        result = self.run(
            wrapped,
            cwd=cwd,
            env="gcc_ada_build_env",
            ignore_errors=True,
        )
        if result in (-11, 139):
            if hasattr(os, "sync"):
                os.sync()
            time.sleep(1)
            result = self.run(
                wrapped,
                cwd=cwd,
                env="gcc_ada_build_env",
                ignore_errors=True,
            )
        if result != 0:
            raise ConanException(
                "GCC Ada command failed with exit code {}".format(result)
            )

    def _sign_elf_tree(self, root):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, llvm-objcopy and llvm-readelf"
            )
        for candidate in Path(root).rglob("*"):
            if (
                not candidate.is_file()
                or candidate.is_symlink()
                or not candidate.stat().st_mode
                & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            ):
                continue
            probe = subprocess.run(
                [readelf, "-h", "-S", str(candidate)],
                capture_output=True,
                text=True,
            )
            if probe.returncode != 0 or not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", probe.stdout
            ):
                continue
            if ".codesign" in probe.stdout:
                continue
            mode = stat.S_IMODE(candidate.stat().st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=str(candidate.parent)
            ) as temp_dir:
                os.chmod(temp_dir, 0o775)
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(candidate, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed, "-selfSign", "1"],
                    check=True,
                )
                sections = subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if ".codesign" not in sections.stdout:
                    raise ConanInvalidConfiguration(
                        "Signing did not add .codesign: {}".format(candidate)
                    )
                os.replace(signed, candidate)
                candidate.chmod(mode)

    def _probe_seed(self):
        probe_dir = Path(self.build_folder) / "seed-probe"
        probe_dir.mkdir(parents=True, exist_ok=True)
        source = probe_dir / "seed_probe.adb"
        source.write_text(
            "procedure Seed_Probe is\nbegin\n   null;\nend Seed_Probe;\n",
            encoding="ascii",
        )
        gnatmake = Path(self.build_folder) / ".ohos-wrappers" / "gnatmake"
        self.run(
            "{} --version".format(shlex.quote(str(gnatmake))),
            cwd=str(probe_dir),
            env="gcc_ada_build_env",
        )
        self.run(
            "{} -q -f -c {}".format(
                shlex.quote(str(gnatmake)), shlex.quote(str(source))
            ),
            cwd=str(probe_dir),
            env="gcc_ada_build_env",
        )
        if not (probe_dir / "seed_probe.o").is_file():
            raise ConanInvalidConfiguration(
                "Alpine GNAT seed did not compile the Ada probe"
            )

    def _install_upstream_test_driver(self, configured):
        gcc_dir = Path(self.build_folder) / "gcc"
        driver = gcc_dir / "xgcc"
        real_driver = gcc_dir / "xgcc.ohos-real"
        shell_driver = gcc_dir / "xgcc.ohos-test-wrapper"
        if not driver.is_file() or real_driver.exists():
            raise ConanInvalidConfiguration(
                "Cannot prepare the GCC Ada upstream test driver"
            )

        os.replace(driver, real_driver)
        try:
            self._write_signing_wrapper(
                gcc_dir,
                shell_driver.name,
                str(real_driver),
                extra_args=(
                    "-B/data/service/hnp/bin/",
                    "-B{}{}".format(gcc_dir, os.sep),
                    "-B{}{}".format(self._ohos_target_lib, os.sep),
                    "-isystem",
                    self._ohos_target_include,
                    "-D__availability__(...)=",
                ),
                link_args=(
                    "-Wl,--whole-archive",
                    self._ohos_libunwind,
                    "-Wl,--no-whole-archive",
                ),
            )
            proxy = self._build_signed_shell_proxy(
                configured,
                shell_driver,
                Path(self.build_folder) / ".upstream-test-driver",
                "xgcc",
                relocatable=True,
            )
            shutil.copy2(proxy, driver)
            driver.chmod(0o755)
        except Exception:
            if driver.exists():
                driver.unlink()
            if shell_driver.exists():
                shell_driver.unlink()
            os.replace(real_driver, driver)
            raise
        return driver, real_driver, shell_driver

    @staticmethod
    def _testsuite_result_counts(summary_path):
        labels = (
            "PASS",
            "FAIL",
            "XFAIL",
            "XPASS",
            "UNSUPPORTED",
            "UNRESOLVED",
            "ERROR",
        )
        counts = {label: 0 for label in labels}
        with open(summary_path, encoding="utf-8", errors="replace") as summary:
            for line in summary:
                match = re.match(
                    r"^(PASS|FAIL|XFAIL|XPASS|UNSUPPORTED|UNRESOLVED|ERROR):",
                    line,
                )
                if match:
                    counts[match.group(1)] += 1
        return counts

    def _report_upstream_test_results(self, suite, summary_path, minimum):
        evidence_root = os.path.dirname(summary_path)
        if not os.path.isfile(summary_path):
            self._emit_upstream_failure_evidence(suite, evidence_root)
            raise ConanInvalidConfiguration(
                "{} did not produce its DejaGNU summary: {}".format(
                    suite, summary_path
                )
            )
        counts = self._testsuite_result_counts(summary_path)
        executed = sum(counts.values())
        if executed < minimum:
            self._emit_upstream_failure_evidence(suite, evidence_root)
            raise ConanInvalidConfiguration(
                "{} executed only {} results; expected a full-suite result "
                "set of at least {}".format(suite, executed, minimum)
            )
        self.output.info(
            "UPSTREAM_{}_FULL_RESULTS={} PASS={} FAIL={} XFAIL={} "
            "XPASS={} UNSUPPORTED={} UNRESOLVED={} ERROR={}".format(
                suite,
                executed,
                counts["PASS"],
                counts["FAIL"],
                counts["XFAIL"],
                counts["XPASS"],
                counts["UNSUPPORTED"],
                counts["UNRESOLVED"],
                counts["ERROR"],
            )
        )
        if any(
            counts[label]
            for label in ("FAIL", "XPASS", "UNRESOLVED", "ERROR")
        ):
            self._emit_upstream_failure_evidence(suite, evidence_root)

    def _emit_upstream_failure_evidence(self, suite, log_root):
        pattern = re.compile(
            r"cannot locate|fatal error|gnatmake:|compilation abandoned|"
            r"(?:^|:\s)error:|inaccessible or not found|permission denied|"
            r"undefined reference|collect2:",
            re.IGNORECASE,
        )
        evidence = []
        seen = set()
        root = Path(log_root)
        if root.exists():
            for log_path in sorted(root.rglob("*.log*")):
                try:
                    log = log_path.open(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                with log:
                    for raw_line in log:
                        if not pattern.search(raw_line):
                            continue
                        line = raw_line.strip()
                        line = line.replace(self.build_folder, "<build>")
                        line = line.replace(self.source_folder, "<source>")
                        if line in seen:
                            continue
                        seen.add(line)
                        evidence.append(line[:500])
                        if len(evidence) == 40:
                            break
                if len(evidence) == 40:
                    break
        if not evidence:
            self.output.info(
                "UPSTREAM_{}_FAILURE_EVIDENCE=none-found".format(suite)
            )
            return
        for index, line in enumerate(evidence, 1):
            self.output.info(
                "UPSTREAM_{}_FAILURE_EVIDENCE[{}]={}".format(
                    suite, index, line
                )
            )

    def _run_full_upstream_ada_tests(self, make, configured):
        driver = real_driver = shell_driver = None
        try:
            driver, real_driver, shell_driver = (
                self._install_upstream_test_driver(configured)
            )
            self._run_unlimited(
                "{} -C gcc check-gnat check-acats".format(make),
                self.build_folder,
            )
            self._report_upstream_test_results(
                "GNAT",
                os.path.join(
                    self.build_folder, "gcc", "testsuite", "gnat", "gnat.sum"
                ),
                900,
            )
            self._report_upstream_test_results(
                "ACATS",
                os.path.join(
                    self.build_folder,
                    "gcc",
                    "testsuite",
                    "ada",
                    "acats",
                    "acats.sum",
                ),
                2200,
            )
            self.output.info("UPSTREAM_ADA_FULL_EXECUTION=complete")
        finally:
            if driver is not None and driver.exists():
                driver.unlink()
            if shell_driver is not None and shell_driver.exists():
                shell_driver.unlink()
            if real_driver is not None and real_driver.exists():
                os.replace(real_driver, driver)

    def build(self):
        self._probe_seed()
        shell = self._required_executable(
            "POSIX shell", "/bin/sh", "sh"
        )
        configure = os.path.join(self.source_folder, "configure")
        configure_command = "{} {} {}".format(
            shlex.quote(shell),
            shlex.quote(configure),
            " ".join(shlex.quote(item) for item in self._configure_args()),
        )
        self._run_unlimited(configure_command, self.build_folder)

        jobs = max(1, min(build_jobs(self), 8))
        self.output.info(
            "Using {} parallel jobs for the GCC Ada build".format(jobs)
        )
        make = "make --jobserver-style=pipe -j{}".format(jobs)
        self._run_unlimited("{} all-gcc".format(make), self.build_folder)
        self._install_native_collect_ld()
        self._sign_elf_tree(self.build_folder)

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc_wrapper = self._write_signing_wrapper(
            Path(self.build_folder) / ".ohos-wrappers",
            "xgcc-sign",
            xgcc,
            extra_args=(
                "-B/data/service/hnp/bin/",
                "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                "-B{}{}".format(self._ohos_target_lib, os.sep),
                "-isystem",
                self._ohos_target_include,
                "-D__availability__(...)=",
            ),
        )
        target_cc = shlex.join([shell, target_cc_wrapper])
        self._run_unlimited(
            "{} all-target-libgcc CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            self.build_folder,
        )
        self._sign_elf_tree(self.build_folder)
        self._run_unlimited(
            "{} all-target-libada CC_FOR_TARGET={} "
            "CFLAGS_FOR_TARGET={}".format(
                make,
                shlex.quote(target_cc),
                shlex.quote("-g -O2 -fPIC"),
            ),
            self.build_folder,
        )
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        proxy_root = Path(self.build_folder) / ".gnattools-proxies"
        target_cc_proxy = self._build_signed_shell_proxy(
            configured, target_cc_wrapper, proxy_root / "cc", "xgcc"
        )
        target_cxx_proxy = self._build_signed_shell_proxy(
            configured,
            Path(self.build_folder)
            / ".ohos-wrappers"
            / "clangxx-sign",
            proxy_root / "cxx",
            "clangxx",
        )
        self._run_unlimited(
            "{} -C gcc gnattools CC_FOR_TARGET={} CXX={} "
            "LDFLAGS=-static".format(
                make,
                shlex.quote(str(target_cc_proxy)),
                shlex.quote(str(target_cxx_proxy)),
            ),
            self.build_folder,
        )
        self._sign_elf_tree(self.build_folder)
        self._run_unlimited("make -C gcc selftest", self.build_folder)
        if self._full_upstream_ada_tests_enabled():
            self._run_full_upstream_ada_tests(make, configured)
        else:
            self.output.info(
                "UPSTREAM_ADA_FULL_EXECUTION=previous_ci_evidence "
                "(full build-tree GNAT/ACATS results are recorded in CI "
                "#42755; set GCC_ADA_FULL_UPSTREAM_TESTS=1 to rerun)"
            )

    def _install_driver_wrapper(self):
        bindir = Path(self.package_folder) / "bin"
        driver_proxy = bindir / "gcc"
        real_driver = bindir / "gcc.real"
        shell_driver = bindir / "gcc.ohos-wrapper"
        if not driver_proxy.is_file():
            raise ConanInvalidConfiguration(
                "The installed GCC driver was not found: {}".format(driver_proxy)
            )
        os.replace(driver_proxy, real_driver)
        shell_driver.write_text(
            """#!/bin/sh
set -eu
driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/gcc.real"
target={target}
version={version}
export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"
sysroot=$("$real_driver" -print-sysroot)
if [ -z "$sysroot" ] || [ ! -d "$sysroot/usr/lib/$target" ]; then
    echo "GCC Ada OHOS sysroot is unavailable: $sysroot" >&2
    exit 1
fi
link=1
has_input=0
takes_value=0
for argument in "$@"; do
    if [ "$takes_value" -eq 1 ]; then
        takes_value=0
        continue
    fi
    case "$argument" in
        -c|-S|-E|-M|-MM|-fsyntax-only) link=0 ;;
        -o|-x|-isystem|-include|-imacros|-MF|-MT|-MQ|-B|-L|-I|-D|-U|-specs)
            takes_value=1 ;;
        -) has_input=1 ;;
        -*) ;;
        *) has_input=1 ;;
    esac
done
if [ "$link" -eq 1 ] && [ "$has_input" -eq 1 ]; then
    sdk_native=$(CDPATH= cd "$sysroot/.." && pwd -P)
    libunwind="$sdk_native/llvm/lib/$target/libunwind.a"
    if [ ! -f "$libunwind" ]; then
        echo "GCC Ada OHOS unwind library is unavailable: $libunwind" >&2
        exit 1
    fi
    set -- -Wl,--whole-archive "$libunwind" -Wl,--no-whole-archive "$@"
fi
set -- '-D__availability__(...)=' "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
exec "$real_driver" "$@"
""".format(
                target=shlex.quote(self._target_triplet),
                version=shlex.quote(str(self.version)),
            ),
            encoding="utf-8",
        )
        shell_driver.chmod(0o755)
        self._ohos_libunwind

        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        proxy = self._build_signed_shell_proxy(
            configured,
            shell_driver,
            Path(self.build_folder) / ".package-driver-proxy",
            "gcc",
            relocatable=True,
        )
        shutil.copy2(proxy, driver_proxy)
        driver_proxy.chmod(0o755)

    def _package_upstream_test_sources(self):
        """Keep the selected upstream inputs with the installed package."""
        destination_root = (
            Path(self.package_folder) / "share" / "gcc-ada" / "upstream-tests"
        )
        for destination, source, filenames in self._upstream_test_sources:
            source_root = Path(self.source_folder, *source.split("/"))
            destination_dir = Path(
                destination_root, *destination.split("/")
            )
            destination_dir.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                source_path = source_root / filename
                if not source_path.is_file():
                    raise ConanInvalidConfiguration(
                        "Selected upstream test source is missing: {}".format(
                            source_path
                        )
                    )
                destination_path = destination_dir / filename
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination_path)
        self.output.info(
            "Packaged 46 selected upstream Ada test sources under {}".format(
                destination_root
            )
        )

    def package(self):
        self._run_unlimited(
            "make install-gcc install-target-libgcc install-target-libada DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            self.build_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._package_upstream_test_sources()
        self._install_driver_wrapper()
        self._sign_elf_tree(self.package_folder)

        required = (
            Path("bin/gcc"),
            Path("bin/gnatmake"),
            Path("bin/gnatbind"),
            Path("bin/gnatlink"),
            Path("libexec/gcc")
            / self._target_triplet
            / str(self.version)
            / "gnat1",
            Path("lib/gcc")
            / self._target_triplet
            / str(self.version)
            / "adalib/libgnat.a",
            Path("lib/gcc")
            / self._target_triplet
            / str(self.version)
            / "adalib/libgnarl.a",
        )
        missing = [
            str(item)
            for item in required
            if not (Path(self.package_folder) / item).is_file()
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "Missing GCC Ada package artifacts: {}".format(", ".join(missing))
            )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        ada_root = os.path.join(
            self.package_folder,
            "lib",
            "gcc",
            self._target_triplet,
            str(self.version),
        )
        exec_prefix = os.path.join(self.package_folder, "libexec", "gcc") + os.sep
        self.buildenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
        self.buildenv_info.define_path("GNAT_ROOT", self.package_folder)
        self.buildenv_info.define_path("ADA_INCLUDE_PATH", os.path.join(ada_root, "adainclude"))
        self.buildenv_info.define_path("ADA_OBJECTS_PATH", os.path.join(ada_root, "adalib"))
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
        self.runenv_info.define_path("GNAT_ROOT", self.package_folder)
        self.runenv_info.define_path("ADA_INCLUDE_PATH", os.path.join(ada_root, "adainclude"))
        self.runenv_info.define_path("ADA_OBJECTS_PATH", os.path.join(ada_root, "adalib"))

    def _build_signed_shell_proxy(
        self, configured, signing_wrapper, proxy_dir, proxy_name, relocatable=False
    ):
        signing_wrapper = Path(signing_wrapper)
        if not signing_wrapper.is_file():
            raise ConanInvalidConfiguration(
                "OHOS signing wrapper was not found: {}".format(
                    signing_wrapper
                )
            )
        proxy_dir = Path(proxy_dir)
        if proxy_dir.exists():
            shutil.rmtree(proxy_dir)
        proxy_dir.mkdir(parents=True)

        source = proxy_dir / "{}-proxy.c".format(proxy_name)
        proxy = proxy_dir / proxy_name
        if relocatable:
            source_text = """#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {{
    char executable[4096];
    char wrapper[4096];
    char *forwarded[argc + 2];
    char *separator;
    ssize_t length;
    int index;
    int saved_errno;

    length = readlink("/proc/self/exe", executable, sizeof(executable) - 1);
    if (length < 0 || (size_t)length >= sizeof(executable) - 1) {{
        perror("gcc-ada proxy executable path");
        return 126;
    }}
    executable[length] = '\\0';
    separator = strrchr(executable, '/');
    if (separator == NULL) {{
        fputs("gcc-ada proxy executable path has no directory\\n", stderr);
        return 126;
    }}
    *separator = '\\0';
    if (snprintf(wrapper, sizeof(wrapper), "%s/%s", executable,
                 {wrapper}) >= (int)sizeof(wrapper)) {{
        fputs("gcc-ada proxy wrapper path is too long\\n", stderr);
        return 126;
    }}
    forwarded[0] = (char *)"/bin/sh";
    forwarded[1] = wrapper;
    for (index = 1; index < argc; ++index) {{
        forwarded[index + 1] = argv[index];
    }}
    forwarded[argc + 1] = NULL;
    execv(forwarded[0], forwarded);
    saved_errno = errno;
    perror("gcc-ada shell proxy");
    return saved_errno == ENOENT ? 127 : 126;
}}
""".format(wrapper=json.dumps(signing_wrapper.name))
        else:
            source_text = """#include <errno.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv) {{
    char *forwarded[argc + 2];
    int index;
    int saved_errno;

    forwarded[0] = (char *)"/bin/sh";
    forwarded[1] = (char *){wrapper};
    for (index = 1; index < argc; ++index) {{
        forwarded[index + 1] = argv[index];
    }}
    forwarded[argc + 1] = NULL;
    execv(forwarded[0], forwarded);
    saved_errno = errno;
    perror("gcc-ada shell proxy");
    return saved_errno == ENOENT ? 127 : 126;
}}
""".format(wrapper=json.dumps(str(signing_wrapper)))
        source.write_text(source_text, encoding="ascii")

        cc, cc_args = self._split_command(configured.get("c"), "clang")
        command = [
            cc,
            *cc_args,
            "-std=c99",
            str(source),
            "-o",
            str(proxy),
        ]
        subprocess.run(
            command,
            cwd=str(proxy_dir),
            env=self._ohos_tool_env(),
            check=True,
        )
        if not proxy.is_file():
            raise ConanInvalidConfiguration(
                "OHOS shell proxy was not built: {}".format(proxy_name)
            )
        proxy.chmod(0o755)
        self._sign_elf_tree(proxy_dir)
        return proxy

    def _install_seed_driver_proxy(self, configured, signing_wrapper):
        proxy_dir = Path(self.build_folder) / ".seed-driver-proxy"
        proxy = self._build_signed_shell_proxy(
            configured, signing_wrapper, proxy_dir, "gcc"
        )

        seed_driver = self._build_seed_root / "usr/bin/gcc"
        seed_driver_tmp = seed_driver.with_name("gcc.ohos-proxy")
        shutil.copy2(proxy, seed_driver_tmp)
        seed_driver_tmp.chmod(0o755)
        os.replace(seed_driver_tmp, seed_driver)
