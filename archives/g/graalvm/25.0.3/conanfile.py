#!/usr/bin/env python3
"""Conan recipe for the GraalVM Community JDK 25.0.3 OHOS adaptation."""

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class GraalVMConan(ConanFile):
    name = "graalvm"
    version = "25.0.3"
    description = (
        "Headless GraalVM Community JDK and Native Image for OpenHarmony PC"
    )
    license = ("GPL-2.0-with-Classpath-exception", "NCSA", "Zlib")
    homepage = "https://www.graalvm.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = (
        "files/*.c",
        "files/*.py",
        "files/*.h",
        "files/*.map",
        "files/*.properties",
        "files/*.txt",
    )

    _EXPECTED_GRAAL_LINKS = {
        "LICENSE_NATIVEIMAGE.txt": "lib/svm/LICENSE_NATIVEIMAGE.txt",
        "bin/native-image": "../lib/svm/bin/native-image",
        "bin/native-image-configure": "../lib/svm/bin/native-image-configure",
        "bin/native-image-utils": "../lib/svm/bin/native-image-utils",
        "lib/svm/bin/native-image-configure": "native-image-utils",
    }
    _NATIVE_IMAGE_DRIVERS = {
        "bin/native-image": "bin/native-image.real",
        "lib/svm/bin/native-image": "lib/svm/bin/native-image.real",
    }
    _PRIVATE_RPATHS = {
        "bin/native-image.real": "$ORIGIN/../lib",
        "lib/libjimage.so": "$ORIGIN:$ORIGIN/server",
        "lib/jspawnhelper": "$ORIGIN",
        "lib/svm/bin/native-image.real": "$ORIGIN/../../../lib",
    }
    _RUNTIME_PROVIDER_EDGES = {
        ("lib/libfontmanager.so", "lib/libawt_headless.so"): {
            "AWTCharAdvance",
            "AWTCountFonts",
            "AWTDrawGlyphList",
            "AWTFontAscent",
            "AWTFontDefaultChar",
            "AWTFontDescent",
            "AWTFontGenerateImage",
            "AWTFontMaxBounds",
            "AWTFontMaxByte1",
            "AWTFontMaxCharOrByte2",
            "AWTFontMinByte1",
            "AWTFontMinCharOrByte2",
            "AWTFontPerChar",
            "AWTFontTextExtents16",
            "AWTFreeChar",
            "AWTFreeFont",
            "AWTLoadFont",
            "AccelGlyphCache_RemoveAllCellInfos",
        }
    }
    _UNSUPPORTED_RUNTIME_ELFS = (
        "bin/jconsole",
        "lib/libawt_xawt.so",
        "lib/libjawt.so",
        "lib/libjsound.so",
        "lib/libsplashscreen.so",
    )
    _SYSTEM_NEEDED_REPLACEMENTS = {
        "ld-linux-aarch64.so.1": "libg.so",
        "libc.so.6": "libg.so",
        "libdl.so.2": "libg.so",
        "libm.so.6": "libg.so",
        "libpthread.so.0": "libg.so",
        "librt.so.1": "libg.so",
        "libz.so.1": "libjz.so",
        "libfreetype.so.6": "libfreetype.so",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "graalvm/25.0.3 packages the official Linux aarch64 release "
                "adapted specifically for OHOS armv8"
            )

    def requirements(self):
        self.requires("freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19")

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        graal = sources["graalvm"]
        gcompat = sources["gcompat"]
        zlib = sources["zlib"]

        graal_archive = Path(self.source_folder, graal["filename"])
        gcompat_archive = Path(self.source_folder, gcompat["filename"])
        zlib_archive = Path(self.source_folder, zlib["filename"])
        download(
            self,
            graal["url"],
            str(graal_archive),
            sha256=graal["sha256"],
        )
        download(
            self,
            gcompat["url"],
            str(gcompat_archive),
            sha256=gcompat["sha256"],
        )
        download(
            self,
            zlib["url"],
            str(zlib_archive),
            sha256=zlib["sha256"],
        )

        self._extract_graalvm(graal_archive, graal["root"])
        self._extract_regular_archive(
            gcompat_archive,
            gcompat["root"],
            Path(self.source_folder, "gcompat"),
            "gcompat",
        )
        self._extract_regular_archive(
            zlib_archive,
            zlib["root"],
            Path(self.source_folder, "zlib"),
            "zlib",
        )
        apply_conandata_patches(self)
        graal_archive.unlink()
        gcompat_archive.unlink()
        zlib_archive.unlink()

    def build(self):
        source = Path(self.source_folder, "gcompat")
        work = Path(self.build_folder, "gcompat-src")
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(source, work)

        compiler = self._compiler()
        make = shutil.which("make") or "/data/service/hnp/bin/make"
        if not os.path.isfile(make):
            raise ConanInvalidConfiguration("GNU Make is required to build gcompat")
        command = [
            make,
            "-j1",
            "libg.so",
            f"CC={compiler}",
            "CFLAGS=-O2 -Werror",
            "LDFLAGS=-Wl,--no-undefined",
            "LIBGCOMPAT_NAME=libg.so",
            "LIBGCOMPAT_PATH=/lib/libg.so",
            "WITH_OBSTACK=no",
            "WITH_LIBUCONTEXT=",
            "LINKER_PATH=/lib/ld-musl-aarch64.so.1",
            "LOADER_NAME=ld-linux-aarch64.so.1",
        ]
        self.run(shlex.join(command), cwd=str(work))
        library = work / "libg.so"
        if not self._is_elf(library):
            raise ConanException("gcompat build did not produce libg.so")

        readelf = self._ohos_tools()["readelf"]
        dynamic = self._run([readelf, "-dW", str(library)], "inspect gcompat")
        if "Library soname: [libg.so]" not in dynamic.stdout:
            raise ConanException("gcompat SONAME is not libg.so")
        needed = self._needed(library, readelf)
        if needed != ["libc.so"]:
            raise ConanException(f"unexpected gcompat dependency set: {needed}")

        self._build_zlib_compat(compiler, readelf)
        self._build_native_image_launcher(compiler, readelf)

    def _build_native_image_launcher(self, compiler, readelf):
        source = Path(
            self.export_sources_folder,
            "files",
            "native_image_launcher.c",
        )
        launcher = Path(self.build_folder, "native-image-launcher")
        if not source.is_file():
            raise ConanException("Native Image launcher source is missing")
        if os.path.lexists(launcher):
            launcher.unlink()
        self._run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fPIE",
                "-pie",
                "-Wl,-z,relro,-z,now",
                source,
                "-o",
                launcher,
            ],
            "build native Native Image launcher",
        )
        if not self._is_elf(launcher):
            raise ConanException("Native Image launcher build did not produce an ELF")
        interpreter = self._interpreter(launcher, readelf)
        if interpreter != "/lib/ld-musl-aarch64.so.1":
            raise ConanException(
                f"Native Image launcher has an unexpected interpreter: {interpreter}"
            )
        needed = self._needed(launcher, readelf)
        if needed != ["libc.so"]:
            raise ConanException(
                f"Native Image launcher has unexpected dependencies: {needed}"
            )

    def _build_zlib_compat(self, compiler, readelf):
        source = Path(self.source_folder, "zlib")
        work = Path(self.build_folder, "zlib-src")
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(source, work)

        make = shutil.which("make") or "/data/service/hnp/bin/make"
        shell = shutil.which("sh") or "/system/bin/sh"
        if not os.path.isfile(make):
            raise ConanInvalidConfiguration("GNU Make is required to build zlib")
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration("a POSIX shell is required to build zlib")

        version_script = Path(self.export_sources_folder, "files", "zlib.map")
        upstream_version_script = work / "zlib.map"
        library = Path(self.build_folder, "libjz.so")
        if not version_script.is_file():
            raise ConanException(f"zlib version script is missing: {version_script}")
        if not upstream_version_script.is_file():
            raise ConanException("zlib source does not contain zlib.map")
        if self._sha256(version_script) != self._sha256(upstream_version_script):
            raise ConanException("bundled zlib.map differs from the zlib 1.3.2 source")

        environment = os.environ.copy()
        environment.update(
            {
                "CC": compiler,
                "CFLAGS": "-fPIC -O2",
                "SFLAGS": "-fPIC -O2",
            }
        )
        self._run(
            [shell, "./configure", "--static", "--prefix=/"],
            "configure private zlib",
            cwd=work,
            env=environment,
        )
        self._run(
            [make, "-j1", "libz.a"],
            "build private PIC zlib archive",
            cwd=work,
            env=environment,
        )
        self._run(
            [make, "-j1", "test"],
            "run private zlib tests",
            cwd=work,
            env=environment,
        )
        archive = work / "libz.a"
        if not archive.is_file():
            raise ConanException("zlib build did not produce the PIC libz.a")
        if os.path.lexists(library):
            library.unlink()

        self._run(
            [
                compiler,
                "-shared",
                "-Wl,--no-undefined",
                "-Wl,-soname,libjz.so",
                f"-Wl,--version-script={version_script}",
                "-Wl,--whole-archive",
                archive,
                "-Wl,--no-whole-archive",
                "-o",
                library,
            ],
            "link private zlib compatibility library",
        )
        if not self._is_elf(library):
            raise ConanException("zlib relink did not produce libjz.so")

        dynamic = self._run([readelf, "-dW", library], "inspect private zlib")
        if "Library soname: [libjz.so]" not in dynamic.stdout:
            raise ConanException("private zlib SONAME is not libjz.so")
        needed = self._needed(library, readelf)
        if any(name.startswith("libz.so") for name in needed):
            raise ConanException(f"private zlib retains a shared zlib input: {needed}")

        versions = self._run(
            [readelf, "--version-info", "--wide", library],
            "inspect private zlib symbol versions",
        ).stdout
        required_versions = ("ZLIB_1.2.0", "ZLIB_1.2.2", "ZLIB_1.3.2")
        missing = [
            name
            for name in required_versions
            if not re.search(rf"\b{re.escape(name)}\b", versions)
        ]
        if missing:
            raise ConanException(f"private zlib lacks version nodes: {missing}")

    def package(self):
        source = Path(self.source_folder, "graalvm")
        package = Path(self.package_folder)
        shutil.copytree(source, package, dirs_exist_ok=True)
        self._assert_no_links(package)
        font_configuration = self._install_font_configuration(package)

        tools = self._ohos_tools()
        official_elfs = [
            path
            for path in sorted(package.rglob("*"))
            if path.is_file() and self._is_elf(path)
        ]
        if len(official_elfs) != 76:
            raise ConanException(
                f"official materialized GraalVM tree has {len(official_elfs)} "
                "ELFs, expected 76"
            )

        self._run_elf_rewriter(
            "audit-tree", package, expected_elfs=76, expected_interpreters=34
        )
        self._remove_unsupported_runtime(package)
        supported_elfs = [
            path
            for path in sorted(package.rglob("*"))
            if path.is_file() and self._is_elf(path)
        ]
        if len(supported_elfs) != 71:
            raise ConanException(
                f"headless GraalVM tree has {len(supported_elfs)} ELFs, expected 71"
            )

        rewrite_report = self._run_elf_rewriter(
            "rewrite-tree", package, expected_elfs=71, expected_interpreters=33
        )
        rewrite_records = {
            record["path"]: record for record in rewrite_report["files"]
        }

        private_libraries = {
            "libg.so": Path(self.build_folder, "gcompat-src", "libg.so"),
            "libjz.so": Path(self.build_folder, "libjz.so"),
        }
        for name, source_path in private_libraries.items():
            if not self._is_elf(source_path):
                raise ConanException(
                    f"private compatibility library is missing: {name}"
                )
            shutil.copy2(source_path, package / "lib" / name)

        materialized_runtime_edges = self._materialize_runtime_provider_edges(
            package, tools
        )

        packaged_elfs = [
            path
            for path in sorted(package.rglob("*"))
            if path.is_file() and self._is_elf(path)
        ]
        if len(packaged_elfs) != 73:
            raise ConanException(
                f"pre-sign package has {len(packaged_elfs)} ELFs, expected 73"
            )
        records = []
        for index, path in enumerate(packaged_elfs):
            relative = path.relative_to(package).as_posix()
            records.append(
                self._sign_elf(path, index, tools, rewrite_records.get(relative))
            )

        self._install_native_image_support(package, records, tools)
        signed_audit = self._run_elf_rewriter(
            "audit-tree", package, expected_elfs=75, expected_interpreters=35
        )

        copy(
            self,
            "LICENSE.txt",
            src=str(source),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, "gcompat"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE-zlib.txt",
            src=os.path.join(self.export_sources_folder, "files"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        symbol_closure = self._validate_package(records, signed_audit, tools)
        report_dir = package / "share" / "graalvm"
        report_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "schema": 1,
            "graalvm_java_version": str(self.version),
            "graalvm_release": "25.1.3",
            "gcompat_version": "1.1.0",
            "official_elf_count": len(official_elfs),
            "supported_official_elf_count": len(supported_elfs),
            "packaged_elf_count": len(records),
            "unsupported_runtime_elfs_removed": self._UNSUPPORTED_RUNTIME_ELFS,
            "materialized_links": self._EXPECTED_GRAAL_LINKS,
            "needed_replacements": self._SYSTEM_NEEDED_REPLACEMENTS,
            "rewrite_totals": rewrite_report["rewrite_totals"],
            "post_sign_needed": signed_audit["needed"],
            "private_libraries": sorted(private_libraries),
            "native_image_launchers": {
                wrapper: {
                    "kind": "signed-ohos-pie",
                    "interpreter": "/lib/ld-musl-aarch64.so.1",
                    "needed": ["libc.so"],
                    "python_companion": f"{wrapper}.py",
                    "real_driver": real_driver,
                    "rpath": "",
                }
                for wrapper, real_driver in self._NATIVE_IMAGE_DRIVERS.items()
            },
            "zlib_source_version": "1.3.2",
            "external_dependencies": ["freetype/2.14.3"],
            "font_configuration": font_configuration,
            "materialized_runtime_provider_edges": materialized_runtime_edges,
            "symbol_closure": symbol_closure,
            "records": records,
        }
        (report_dir / "ohos-adaptation.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "lib/server"]
        for environment in (self.buildenv_info, self.runenv_info):
            environment.define_path("JAVA_HOME", self.package_folder)
            environment.define_path("GRAALVM_HOME", self.package_folder)
            environment.prepend_path("PATH", bindir)

    def _extract_graalvm(self, archive, root_name):
        extraction = Path(self.source_folder, ".graalvm-extract")
        destination = Path(self.source_folder, "graalvm")
        if extraction.exists():
            shutil.rmtree(extraction)
        if destination.exists():
            shutil.rmtree(destination)
        extraction.mkdir(parents=True)

        root = PurePosixPath(root_name)
        links = {}
        regular_members = []
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle.getmembers():
                relative = self._safe_member(member.name, root)
                if member.issym():
                    links[relative.as_posix()] = member.linkname
                    continue
                if member.islnk() or member.isdev() or member.isfifo():
                    raise ConanException(
                        f"unsupported GraalVM archive member: {member.name}"
                    )
                if not (member.isdir() or member.isfile()):
                    raise ConanException(
                        f"unknown GraalVM archive member: {member.name}"
                    )
                regular_members.append(member)

            if links != self._EXPECTED_GRAAL_LINKS:
                raise ConanException(
                    f"unexpected GraalVM symbolic-link inventory: {links}"
                )
            bundle.extractall(
                path=extraction,
                members=regular_members,
                filter="data",
            )

        extracted_root = extraction / root_name
        for relative, target in links.items():
            destination_path = extracted_root / Path(relative)
            resolved = self._resolve_archive_link(relative, target, links)
            source_path = extracted_root / Path(resolved)
            if not source_path.is_file() or source_path.is_symlink():
                raise ConanException(
                    "GraalVM link target is not a regular file: "
                    f"{relative} -> {resolved}"
                )
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)

        self._assert_no_links(extracted_root)
        shutil.move(str(extracted_root), destination)
        shutil.rmtree(extraction)

    def _extract_regular_archive(self, archive, root_name, destination, label):
        extraction = Path(self.source_folder, f".{label}-extract")
        if extraction.exists():
            shutil.rmtree(extraction)
        if destination.exists():
            shutil.rmtree(destination)
        extraction.mkdir(parents=True)
        root = PurePosixPath(root_name)
        with tarfile.open(archive, "r:gz") as bundle:
            members = []
            for member in bundle.getmembers():
                self._safe_member(member.name, root)
                if (
                    member.issym()
                    or member.islnk()
                    or member.isdev()
                    or member.isfifo()
                ):
                    raise ConanException(
                        f"unsupported {label} archive member: {member.name}"
                    )
                if not (member.isdir() or member.isfile()):
                    raise ConanException(
                        f"unknown {label} archive member: {member.name}"
                    )
                members.append(member)
            bundle.extractall(path=extraction, members=members, filter="data")
        extracted_root = extraction / root_name
        self._assert_no_links(extracted_root)
        shutil.move(str(extracted_root), destination)
        shutil.rmtree(extraction)

    @staticmethod
    def _safe_member(name, root):
        path = PurePosixPath(name)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise ConanException(f"unsafe archive member: {name}")
        if path.parts[0] != root.as_posix():
            raise ConanException(f"archive member escapes expected root: {name}")
        return PurePosixPath(*path.parts[1:])

    @classmethod
    def _resolve_archive_link(cls, relative, target, links):
        current = cls._normalized_relative(PurePosixPath(relative).parent / target)
        visited = {relative}
        while current in links:
            if current in visited:
                raise ConanException(f"cyclic GraalVM symbolic link: {relative}")
            visited.add(current)
            current = cls._normalized_relative(
                PurePosixPath(current).parent / links[current]
            )
        return current

    @staticmethod
    def _normalized_relative(path):
        parts = []
        for part in PurePosixPath(path).parts:
            if part in ("", "."):
                continue
            if part == "..":
                if not parts:
                    raise ConanException(f"archive link escapes root: {path}")
                parts.pop()
            else:
                parts.append(part)
        if not parts:
            raise ConanException(f"archive link resolves to root: {path}")
        return PurePosixPath(*parts).as_posix()

    def _run_elf_rewriter(self, mode, root, expected_elfs, expected_interpreters):
        script = Path(self.export_sources_folder, "files", "elf_rewriter.py")
        if not script.is_file():
            raise ConanException(f"ELF rewriter is missing: {script}")
        completed = self._run(
            [
                sys.executable,
                script,
                mode,
                root,
                "--expect-elf-count",
                expected_elfs,
                "--expect-interp-count",
                expected_interpreters,
            ],
            f"{mode} GraalVM ELF tree",
        )
        try:
            report = json.loads(completed.stdout)
        except (TypeError, ValueError) as exc:
            raise ConanException(f"ELF rewriter returned invalid JSON: {exc}") from exc
        if report.get("elf_count") != expected_elfs:
            raise ConanException("ELF rewriter report count does not match its gate")
        if report.get("interp_count") != expected_interpreters:
            raise ConanException(
                "ELF rewriter interpreter count does not match its gate"
            )
        if len(report.get("files", [])) != expected_elfs:
            raise ConanException("ELF rewriter report has an incomplete file inventory")
        return report

    def _sign_elf(self, path, index, tools, rewrite_record):
        package = Path(self.package_folder)
        relative = path.relative_to(package).as_posix()
        is_official = rewrite_record is not None
        mode = path.stat().st_mode & 0o777
        before_sha = self._sha256(path)
        needed_before = self._needed(path, tools["readelf"])

        work_dir = Path(self.build_folder, "elf-adaptation")
        work_dir.mkdir(parents=True, exist_ok=True)
        clean = work_dir / f"{index:03d}.clean"
        signed = work_dir / f"{index:03d}.signed"
        for temporary in (clean, signed):
            if os.path.lexists(temporary):
                temporary.unlink()
        self._run(
            [tools["objcopy"], "--remove-section", ".codesign", path, clean],
            f"remove old signature from {relative}",
        )
        driver_temp_rewrites = 0
        original_rpath = self._rpath(path, tools["patchelf"])
        if is_official:
            if relative in self._NATIVE_IMAGE_DRIVERS:
                driver_temp_rewrites = self._patch_native_image_driver(
                    clean, relative
                )
        rpath_identity = (
            self._NATIVE_IMAGE_DRIVERS.get(relative, relative)
            if is_official
            else relative
        )
        private_rpath = self._PRIVATE_RPATHS.get(rpath_identity, "")
        if private_rpath:
            self._run(
                [
                    tools["patchelf"],
                    "--force-rpath",
                    "--set-rpath",
                    private_rpath,
                    clean,
                ],
                f"set private RPATH on {relative}",
            )
        self._run(
            [
                tools["signer"],
                "sign",
                "-inFile",
                clean,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            f"sign {relative}",
        )
        if not self._is_elf(signed):
            raise ConanException(f"signing did not produce an ELF for {relative}")
        os.chmod(signed, mode or 0o755)
        path.unlink()
        shutil.copy2(signed, path)
        os.chmod(path, mode or 0o755)

        rewrite_record = rewrite_record or {}
        return {
            "path": relative,
            "before_sign_sha256": before_sha,
            "after_sign_sha256": self._sha256(path),
            "interpreter": self._interpreter(path, tools["readelf"]),
            "rewrite_changes": rewrite_record.get("changes", {}),
            "needed_after_rewrite": needed_before,
            "needed_after_sign": self._needed(path, tools["readelf"]),
            "rpath_before_sign": original_rpath,
            "rpath": self._rpath(path, tools["patchelf"]),
            "driver_temp_rewrites": driver_temp_rewrites,
            "codesign_size": self._codesign_size(path, tools),
        }

    def _validate_package(self, records, audit, tools):
        package = Path(self.package_folder)
        self._assert_no_links(package)
        elfs = [
            path
            for path in sorted(package.rglob("*"))
            if path.is_file() and self._is_elf(path)
        ]
        expected_paths = [path.relative_to(package).as_posix() for path in elfs]
        record_paths = [record["path"] for record in records]
        audit_paths = [record["path"] for record in audit["files"]]
        if len(elfs) != 75 or len(records) != 75:
            raise ConanException(
                f"packaged ELF inventory mismatch: files={len(elfs)}, "
                f"records={len(records)}"
            )
        if record_paths != expected_paths or audit_paths != expected_paths:
            raise ConanException("ELF records do not match the packaged tree")

        forbidden = set(self._SYSTEM_NEEDED_REPLACEMENTS)
        for path, audit_record, sign_record in zip(
            elfs, audit["files"], records
        ):
            relative = path.relative_to(package).as_posix()
            needed = set(audit_record["needed"])
            stale = sorted(
                (needed | set(audit_record["version_files"])) & forbidden
            )
            if stale:
                raise ConanException(f"{relative} retains GNU SONAMEs: {stale}")
            if audit_record["interpreter"] not in (
                None,
                "/lib/ld-musl-aarch64.so.1",
            ):
                raise ConanException(
                    f"{relative} has an unexpected interpreter: "
                    f"{audit_record['interpreter']}"
                )
            if (
                self._has_glibc_import(path, tools["readelf"])
                and "libg.so" not in needed
            ):
                raise ConanException(f"{relative} has uncovered GLIBC imports")
            expected_rpath = self._PRIVATE_RPATHS.get(relative)
            if expected_rpath is not None:
                if sign_record["rpath"] != expected_rpath:
                    raise ConanException(
                        f"{relative} has an unexpected RPATH: "
                        f"{sign_record['rpath']}"
                    )
            elif relative not in ("lib/libg.so", "lib/libjz.so"):
                if sign_record["rpath"] != sign_record["rpath_before_sign"]:
                    raise ConanException(
                        f"{relative} RPATH changed during signing: "
                        f"{sign_record['rpath_before_sign']} -> "
                        f"{sign_record['rpath']}"
                    )
            self._codesign_size(path, tools)

        unexpected_runtime = [
            name
            for name in self._UNSUPPORTED_RUNTIME_ELFS
            if (package / name).exists()
        ]
        if unexpected_runtime:
            raise ConanException(
                f"unsupported desktop/audio runtime remains: {unexpected_runtime}"
            )
        headless_libraries = (
            "lib/libawt.so",
            "lib/libawt_headless.so",
            "lib/libfontmanager.so",
        )
        missing_headless = [
            name for name in headless_libraries if not (package / name).is_file()
        ]
        if missing_headless:
            raise ConanException(
                f"headless GraalVM modules are missing: {missing_headless}"
            )

        packaged_names = {path.name for path in elfs}
        allowed_external = {"libc.so", "libfreetype.so"}
        unresolved = sorted(
            set(audit["needed"]) - packaged_names - allowed_external
        )
        if unresolved:
            raise ConanException(
                f"packaged runtime has unresolved SONAMEs: {unresolved}"
            )
        freetype = Path(
            self.dependencies["freetype"].package_folder, "lib", "libfreetype.so"
        )
        if not self._is_elf(freetype):
            raise ConanException(
                f"freetype/2.14.3 does not provide libfreetype.so: {freetype}"
            )

        for wrapper, real_driver in self._NATIVE_IMAGE_DRIVERS.items():
            data = (package / real_driver).read_bytes()
            if data.count(b"/tmp") != 0 or data.count(b"./.t") < 3:
                raise ConanException(
                    "native-image temporary path rewrite is incomplete: "
                    f"{real_driver}"
                )
            wrapper_path = package / wrapper
            if not self._is_elf(wrapper_path):
                raise ConanException(
                    f"native-image native launcher is invalid: {wrapper}"
                )
            if self._needed(wrapper_path, tools["readelf"]) != ["libc.so"]:
                raise ConanException(
                    f"native-image launcher dependencies are invalid: {wrapper}"
                )
            if self._interpreter(wrapper_path, tools["readelf"]) != (
                "/lib/ld-musl-aarch64.so.1"
            ):
                raise ConanException(
                    f"native-image launcher interpreter is invalid: {wrapper}"
                )
            if self._rpath(wrapper_path, tools["patchelf"]):
                raise ConanException(
                    f"native-image launcher must not have an RPATH: {wrapper}"
                )
            companion = wrapper_path.with_name(f"{wrapper_path.name}.py")
            if not companion.is_file() or self._is_elf(companion):
                raise ConanException(
                    f"native-image Python companion is invalid: {companion}"
                )

        for name in ("libg.so", "libjz.so"):
            library = package / "lib" / name
            dynamic = self._run([tools["readelf"], "-dW", library], f"inspect {name}")
            if f"Library soname: [{name}]" not in dynamic.stdout:
                raise ConanException(f"private library SONAME is not {name}")
        versions = self._run(
            [
                tools["readelf"],
                "--version-info",
                "--wide",
                package / "lib" / "libjz.so",
            ],
            "validate packaged zlib symbol versions",
        ).stdout
        for name in ("ZLIB_1.2.0", "ZLIB_1.2.2", "ZLIB_1.3.2"):
            if not re.search(rf"\b{re.escape(name)}\b", versions):
                raise ConanException(f"packaged libjz.so lacks {name}")
        return self._validate_symbol_closure(elfs, freetype, tools["readelf"])

    def _validate_symbol_closure(self, packaged_elfs, freetype, readelf):
        loader_candidates = (
            Path("/lib/ld-musl-aarch64.so.1"),
            Path("/system/lib/ld-musl-aarch64.so.1"),
        )
        loader = next(
            (path for path in loader_candidates if self._is_elf(path)), None
        )
        if loader is None:
            raise ConanInvalidConfiguration(
                "OpenHarmony musl loader is missing: "
                f"{list(loader_candidates)}"
            )

        provider_paths = [*packaged_elfs, freetype, loader]
        nodes = {}
        aliases_by_node = {}
        for path in provider_paths:
            needed, soname, search_dirs = self._dynamic_entries(path, readelf)
            interpreter = self._interpreter(path, readelf)
            demands, exports = self._dynamic_symbols(path, readelf)
            key = str(path)
            nodes[key] = {
                "path": path,
                "needed": needed,
                "interpreter": interpreter,
                "search_dirs": search_dirs,
                "demands": demands,
                "exports": exports,
                "providers": [],
            }
            aliases_by_node[key] = {path.name, soname} - {None, ""}

        package = Path(self.package_folder)
        package_nodes = {
            path.relative_to(package).as_posix(): str(path)
            for path in packaged_elfs
        }
        runtime_provider_edges = []
        for (consumer_path, provider_path), expected_symbols in sorted(
            self._RUNTIME_PROVIDER_EDGES.items()
        ):
            consumer = package_nodes.get(consumer_path)
            provider = package_nodes.get(provider_path)
            if consumer is None or provider is None:
                raise ConanException(
                    "runtime symbol provider edge is missing an endpoint: "
                    f"{consumer_path} -> {provider_path}"
                )
            provided_symbols = (
                nodes[consumer]["demands"] & nodes[provider]["exports"]
            )
            if provided_symbols != expected_symbols:
                raise ConanException(
                    "runtime symbol provider edge changed: "
                    f"{consumer_path} -> {provider_path}; "
                    f"expected={sorted(expected_symbols)}, "
                    f"actual={sorted(provided_symbols)}"
                )
            needed_name = Path(provider_path).name
            if needed_name not in nodes[consumer]["needed"]:
                raise ConanException(
                    "runtime symbol provider edge was not materialized as "
                    f"DT_NEEDED: {consumer_path} -> {needed_name}"
                )
            runtime_provider_edges.append(
                {
                    "consumer": consumer_path,
                    "provider": provider_path,
                    "symbols": sorted(provided_symbols),
                }
            )

        required_aliases = {
            needed
            for node in nodes.values()
            for needed in node["needed"]
        }
        required_aliases.update(
            Path(node["interpreter"]).name
            for node in nodes.values()
            if node["interpreter"] is not None
        )
        aliases = {}
        for key, node_aliases in aliases_by_node.items():
            for alias in sorted(node_aliases & required_aliases):
                aliases.setdefault(alias, []).append(key)

        missing_dependencies = []
        for node in nodes.values():
            interpreter = node["interpreter"]
            if interpreter is not None:
                provider = self._select_interpreter_provider(
                    interpreter, aliases
                )
                if provider is None:
                    missing_dependencies.append(
                        f"{node['path'].name}:PT_INTERP:{interpreter}"
                    )
                else:
                    node["providers"].append(provider)
            for needed in node["needed"]:
                provider = self._select_needed_provider(node, needed, aliases)
                if provider is None:
                    missing_dependencies.append(
                        f"{node['path'].name}:{needed}"
                    )
                    continue
                node["providers"].append(provider)
        if missing_dependencies:
            raise ConanException(
                "unresolved DT_NEEDED closure: "
                + ", ".join(sorted(missing_dependencies))
            )

        unresolved = []
        demand_count = 0
        reachable_count = 0
        for path in [*packaged_elfs, freetype]:
            root = str(path)
            pending = [root]
            reachable = set()
            while pending:
                current = pending.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                pending.extend(nodes[current]["providers"])
            reachable_count += len(reachable)
            providers = set()
            for current in reachable:
                providers.update(nodes[current]["exports"])
            demands = nodes[root]["demands"]
            demand_count += len(demands)
            for symbol in sorted(demands - providers):
                unresolved.append(f"{path.name}:{symbol}")
        if unresolved:
            preview = ", ".join(unresolved[:20])
            if len(unresolved) > 20:
                preview += f", ... ({len(unresolved)} total)"
            raise ConanException(f"unresolved dynamic-symbol closure: {preview}")
        return {
            "checked_package_elfs": len(packaged_elfs),
            "provider_files": len(provider_paths),
            "required_symbol_demands": demand_count,
            "reachable_provider_checks": reachable_count,
            "runtime_provider_edges": runtime_provider_edges,
            "unresolved": 0,
        }

    @staticmethod
    def _patch_native_image_driver(path, relative):
        data = path.read_bytes()
        old_count = data.count(b"/tmp")
        new_count = data.count(b"./.t")
        if old_count == 3:
            path.write_bytes(data.replace(b"/tmp", b"./.t"))
            return 3
        if old_count == 0 and new_count >= 3:
            return 0
        raise ConanException(
            f"unexpected temporary path markers in {relative}: "
            f"/tmp={old_count}, ./.t={new_count}"
        )

    def _install_native_image_support(self, package, records, tools):
        files = Path(self.export_sources_folder, "files")
        support = package / "libexec" / "graalvm-ohos"
        support.mkdir(parents=True, exist_ok=True)
        for name in (
            "elf_rewriter.py",
            "native_image_finalizer.py",
            "ohos-native-image-compat.h",
        ):
            source = files / name
            if not source.is_file():
                raise ConanException(f"Native Image support file is missing: {name}")
            shutil.copy2(source, support / name)
        os.chmod(support / "native_image_finalizer.py", 0o755)

        wrapper_source = files / "native_image_wrapper.py"
        if not wrapper_source.is_file():
            raise ConanException("Native Image wrapper source is missing")
        launcher_source = Path(self.build_folder, "native-image-launcher")
        if not self._is_elf(launcher_source):
            raise ConanException("Native Image native launcher is missing")
        by_path = {record["path"]: record for record in records}
        for launcher_index, (wrapper, real_driver) in enumerate(
            self._NATIVE_IMAGE_DRIVERS.items(), start=len(records)
        ):
            wrapper_path = package / wrapper
            real_path = package / real_driver
            companion_path = wrapper_path.with_name(f"{wrapper_path.name}.py")
            if (
                not self._is_elf(wrapper_path)
                or os.path.lexists(real_path)
                or os.path.lexists(companion_path)
            ):
                raise ConanException(f"cannot wrap Native Image driver: {wrapper}")
            os.replace(wrapper_path, real_path)
            shutil.copy2(wrapper_source, companion_path)
            os.chmod(companion_path, 0o644)
            shutil.copy2(launcher_source, wrapper_path)
            os.chmod(wrapper_path, 0o755)
            record = by_path.get(wrapper)
            if record is None:
                raise ConanException(f"missing signed driver record: {wrapper}")
            record["path"] = real_driver
            record["wrapper_path"] = wrapper
            launcher_record = self._sign_elf(
                wrapper_path,
                launcher_index,
                tools,
                rewrite_record=None,
            )
            launcher_record["launcher_for"] = real_driver
            records.append(launcher_record)
        records.sort(key=lambda record: record["path"])

    def _install_font_configuration(self, package):
        relative = "conf/fonts/fontconfig.HarmonyOS.properties"
        source = Path(
            self.export_sources_folder,
            "files",
            "fontconfig.HarmonyOS.properties",
        )
        if not source.is_file():
            raise ConanException("OpenHarmony font configuration is missing")

        properties = {}
        for line in source.read_text(encoding="ascii").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key or not value:
                raise ConanException(
                    f"invalid OpenHarmony font configuration line: {line!r}"
                )
            if key in properties:
                raise ConanException(
                    f"duplicate OpenHarmony font configuration key: {key}"
                )
            properties[key] = value

        required_sequences = {
            "version": "1",
            "sequence.allfonts": "latin-1,chinese-gb18030",
            "sequence.fallback": "chinese-gb18030",
        }
        if any(
            properties.get(key) != value
            for key, value in required_sequences.items()
        ):
            raise ConanException("OpenHarmony logical-font sequences changed")

        system_fonts = sorted(
            value
            for key, value in properties.items()
            if key.startswith("filename.")
        )
        expected_system_fonts = [
            "/system/fonts/HarmonyOS_Sans.ttf",
            "/system/fonts/HarmonyOS_Sans_Italic.ttf",
            "/system/fonts/HarmonyOS_Sans_SC.ttf",
            "/system/fonts/NotoSansMono[wdth,wght].ttf",
        ]
        if system_fonts != expected_system_fonts:
            raise ConanException(
                "OpenHarmony system-font mapping changed: "
                f"expected={expected_system_fonts}, actual={system_fonts}"
            )
        missing_fonts = [name for name in system_fonts if not Path(name).is_file()]
        if missing_fonts:
            raise ConanInvalidConfiguration(
                f"OpenHarmony system fonts are missing: {missing_fonts}"
            )

        destination = package / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if self._sha256(source) != self._sha256(destination):
            raise ConanException("packaged OpenHarmony font configuration changed")
        return {
            "path": relative,
            "system_font_files": system_fonts,
        }

    def _remove_unsupported_runtime(self, package):
        for relative in self._UNSUPPORTED_RUNTIME_ELFS:
            path = package / relative
            if not self._is_elf(path):
                raise ConanException(
                    "upstream unsupported runtime ELF changed or is missing: "
                    f"{relative}"
                )
            path.unlink()

    def _materialize_runtime_provider_edges(self, package, tools):
        results = []
        for consumer_path, provider_path in sorted(self._RUNTIME_PROVIDER_EDGES):
            consumer = package / consumer_path
            provider = package / provider_path
            if not self._is_elf(consumer) or not self._is_elf(provider):
                raise ConanException(
                    "cannot materialize runtime provider edge: "
                    f"{consumer_path} -> {provider_path}"
                )

            needed_name = provider.name
            before = self._needed(consumer, tools["readelf"])
            if needed_name in before:
                raise ConanException(
                    "upstream runtime provider edge unexpectedly already exists: "
                    f"{consumer_path} -> {needed_name}"
                )
            self._run(
                [tools["patchelf"], "--add-needed", needed_name, consumer],
                f"materialize runtime provider for {consumer_path}",
            )
            after = self._needed(consumer, tools["readelf"])
            if after.count(needed_name) != 1 or set(after) != {
                *before,
                needed_name,
            }:
                raise ConanException(
                    "runtime provider DT_NEEDED mutation changed unexpected entries: "
                    f"{consumer_path}; before={before}, after={after}"
                )
            results.append(
                {"consumer": consumer_path, "provider": provider_path}
            )
        return results

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _assert_no_links(root):
        links = []
        for current, directories, files in os.walk(root, followlinks=False):
            for name in (*directories, *files):
                path = os.path.join(current, name)
                if os.path.islink(path):
                    links.append(os.path.relpath(path, root))
        if links:
            raise ConanException(f"tree retains symbolic links: {links}")

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or "/data/service/hnp/bin/clang"
        if not os.path.isfile(compiler):
            raise ConanInvalidConfiguration(f"OHOS C compiler is missing: {compiler}")
        return compiler

    @staticmethod
    def _ohos_tools():
        tools = {
            "objcopy": "/data/service/hnp/bin/llvm-objcopy",
            "patchelf": "/data/service/hnp/bin/patchelf",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                f"OHOS ELF adaptation tools are missing: {missing}"
            )
        return tools

    @staticmethod
    def _run(arguments, description, cwd=None, env=None):
        completed = subprocess.run(
            [str(argument) for argument in arguments],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
        )
        if completed.returncode != 0:
            raise ConanException(
                f"{description} failed with exit {completed.returncode}: "
                f"{completed.stderr.strip()}"
            )
        return completed

    @classmethod
    def _needed(cls, path, readelf):
        needed, _soname, _search_dirs = cls._dynamic_entries(path, readelf)
        return needed

    @classmethod
    def _dynamic_entries(cls, path, readelf):
        output = cls._run(
            [readelf, "-dW", str(path)], f"read dynamic entries for {path}"
        ).stdout
        needed = re.findall(r"Shared library: \[([^]]+)\]", output)
        sonames = re.findall(r"Library soname: \[([^]]+)\]", output)
        if len(sonames) > 1:
            raise ConanException(f"{path} has multiple DT_SONAME entries")
        runpaths = re.findall(r"Library runpath: \[([^]]*)\]", output)
        rpaths = re.findall(r"Library rpath: \[([^]]*)\]", output)
        if len(runpaths) > 1 or len(rpaths) > 1:
            raise ConanException(f"{path} has duplicate dynamic search paths")
        raw_search = runpaths[0] if runpaths else (rpaths[0] if rpaths else "")
        search_dirs = []
        for entry in raw_search.split(":"):
            if not entry:
                continue
            expanded = entry.replace("${ORIGIN}", str(Path(path).parent))
            expanded = expanded.replace("$ORIGIN", str(Path(path).parent))
            if "$" in expanded:
                raise ConanException(
                    f"unsupported dynamic search token in {path}: {entry}"
                )
            search_dirs.append(Path(os.path.abspath(expanded)))
        return needed, sonames[0] if sonames else None, search_dirs

    @classmethod
    def _interpreter(cls, path, readelf):
        output = cls._run(
            [readelf, "-lW", str(path)], f"read program headers for {path}"
        ).stdout
        interpreters = re.findall(
            r"Requesting program interpreter:\s*([^]\r\n]+)\]", output
        )
        if len(interpreters) > 1:
            raise ConanException(f"{path} has multiple PT_INTERP entries")
        return interpreters[0] if interpreters else None

    @staticmethod
    def _select_interpreter_provider(interpreter, aliases):
        candidates = aliases.get(Path(interpreter).name, [])
        exact = [
            key
            for key in candidates
            if Path(os.path.abspath(key)) == Path(interpreter)
        ]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ConanException(
                f"ambiguous PT_INTERP provider for {interpreter}: {exact}"
            )
        return None

    @classmethod
    def _select_needed_provider(cls, node, needed, aliases):
        candidates = cls._deduplicate_provider_files(aliases.get(needed, []))
        if not candidates:
            return None

        loaded = [key for key in candidates if key in node["providers"]]
        if len(loaded) == 1:
            return loaded[0]
        if len(candidates) == 1:
            return candidates[0]

        for directory in node["search_dirs"]:
            matches = [
                key
                for key in candidates
                if Path(os.path.abspath(key)).parent == directory
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ConanException(
                    f"ambiguous ELF provider for {needed} from "
                    f"{node['path']}: {matches}"
                )
        raise ConanException(
            f"ambiguous ELF provider for {needed} from {node['path']}: "
            f"candidates={candidates}, search_dirs={node['search_dirs']}"
        )

    @staticmethod
    def _deduplicate_provider_files(candidates):
        unique = []
        for candidate in candidates:
            duplicate = False
            for previous in unique:
                try:
                    duplicate = os.path.samefile(candidate, previous)
                except OSError:
                    duplicate = os.path.abspath(candidate) == os.path.abspath(
                        previous
                    )
                if duplicate:
                    break
            if not duplicate:
                unique.append(candidate)
        return unique

    @classmethod
    def _has_glibc_import(cls, path, readelf):
        completed = cls._run(
            [readelf, "--dyn-syms", "--wide", str(path)],
            f"read dynamic symbols for {path}",
        )
        return bool(
            re.search(
                r"\bUND\b[^\r\n]*@GLIBC_[0-9]",
                completed.stdout,
                flags=re.IGNORECASE,
            )
        )

    @classmethod
    def _dynamic_symbols(cls, path, readelf):
        output = cls._run(
            [readelf, "--dyn-syms", "--wide", str(path)],
            f"read dynamic symbol table for {path}",
        ).stdout
        demands = set()
        exports = set()
        pattern = re.compile(
            r"^\s*\d+:\s+\S+\s+\S+\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)"
            r"(?:\s+(.+?))?\s*$"
        )
        for line in output.splitlines():
            match = pattern.match(line)
            if match is None:
                continue
            binding, visibility, section, raw_name = match.groups()
            if not raw_name:
                continue
            name = re.sub(r"\s+\(\d+\)$", "", raw_name)
            if section == "UND":
                if binding == "GLOBAL":
                    demands.add(cls._musl_symbol_key(name))
                continue
            if binding not in ("GLOBAL", "WEAK", "UNIQUE"):
                continue
            if visibility not in ("DEFAULT", "PROTECTED"):
                continue
            exports.add(cls._musl_symbol_key(name))
        return demands, exports

    @staticmethod
    def _musl_symbol_key(name):
        return name.split("@", 1)[0]

    @classmethod
    def _rpath(cls, path, patchelf):
        return cls._run(
            [patchelf, "--print-rpath", path], f"read RPATH for {path}"
        ).stdout.strip()

    @classmethod
    def _codesign_size(cls, path, tools):
        sections = cls._run(
            [tools["readelf"], "-SW", str(path)],
            f"inspect signature section for {path}",
        ).stdout
        matches = [
            line for line in sections.splitlines() if ".codesign" in line.split()
        ]
        if len(matches) != 1:
            raise ConanException(f"{path} has {len(matches)} .codesign sections")
        dump = Path(f"{path}.codesign-dump-{os.getpid()}")
        inspect = Path(f"{path}.codesign-inspect-{os.getpid()}")
        for temporary in (dump, inspect):
            if os.path.lexists(temporary):
                temporary.unlink()
        try:
            shutil.copy2(path, inspect)
            cls._run(
                [tools["objcopy"], "--dump-section", f".codesign={dump}", str(inspect)],
                f"dump signature section for {path}",
            )
            if not dump.is_file() or dump.stat().st_size <= 0:
                raise ConanException(f"{path} has an empty .codesign section")
            return dump.stat().st_size
        finally:
            for temporary in (dump, inspect):
                if os.path.lexists(temporary):
                    temporary.unlink()

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
