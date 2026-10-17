#!/usr/bin/env python3
"""Conan recipe preparation for alsa-lib 1.2.16."""

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    copy,
    download,
    export_conandata_patches,
    patch,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AlsaLibConan(ConanFile):
    name = "alsa-lib"
    version = "1.2.16"
    description = "ALSA userspace library and topology API"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.alsa-project.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"alsa-lib supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        archive = Path(self.source_folder, f"alsa-lib-{self.version}.tar.bz2")
        download(
            self,
            source["url"],
            str(archive),
            sha256=source["sha256"],
        )
        self._extract_official_source(archive)
        archive.unlink()

    def generate(self):
        VirtualBuildEnv(self).generate()

        temp_dir = Path(self.build_folder, ".tmp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temp_dir))
        if str(self.settings.os) == "OHOS":
            environment.define_path("CONFIG_SHELL", "/system/bin/sh")
            environment.define_path("SHELL", "/system/bin/sh")
            wrapper = self._write_signing_compiler_wrapper()
            environment.define("CC", shlex.join([self._shell(), str(wrapper)]))
        environment.vars(self).save_script("alsa_build_env")

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            (
                "--disable-python",
                "--disable-mixer-pymods",
                "--disable-silent-rules",
            )
        )
        if not self.options.shared and self.options.get_safe("fPIC"):
            with_pic = [
                argument
                for argument in toolchain.configure_args
                if argument.split("=", 1)[0] == "--with-pic"
            ]
            if len(with_pic) > 1:
                raise ConanException(
                    f"static toolchain generated duplicate --with-pic: {with_pic}"
                )
            for argument in with_pic:
                toolchain.configure_args.remove(argument)
            if toolchain.cflags.count("-fPIC") != 1:
                raise ConanException(
                    "static fPIC must produce exactly one -fPIC compiler flag"
                )
        toolchain.generate()

    def build(self):
        work_source = self._prepare_source_copy()
        for patch_entry in self._patch_entries():
            entry = patch_entry.copy()
            patch_file = entry.pop("patch_file")
            patch(
                self,
                base_path=str(work_source),
                patch_file=os.path.join(self.export_sources_folder, patch_file),
                **entry,
            )
        self._refresh_generated_build_files(work_source)

        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        configure_script = work_source / "configure"
        command = shlex.join([self._shell(), str(configure_script)])
        if configure_args:
            command = f"{command} {configure_args}"
        self.run(command, cwd=self.build_folder, env=["conanbuild", "alsa_build_env"])
        if str(self.settings.os) == "OHOS":
            self._materialize_build_include_alias(work_source)

        autotools = Autotools(self)
        autotools.make(args=self._make_args())
        self._exclude_static_oldapi_check_program()
        autotools.make(target="check", args=self._upstream_test_make_args())
        self._validate_upstream_test_results()
        if str(self.settings.os) == "OHOS":
            self._validate_build_sign_chain()

    def package(self):
        Autotools(self).install(args=self._make_args())
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        self._make_pkg_config_relocatable("alsa.pc")
        self._make_pkg_config_relocatable("alsa-topology.pc")
        self._write_feature_contract()
        if str(self.settings.os) == "OHOS":
            self._sign_package_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "ALSA")
        self.cpp_info.set_property("cmake_target_name", "ALSA::ALSA")
        self.cpp_info.set_property("pkg_config_name", "alsa-lib")

        asound = self.cpp_info.components["asound"]
        asound.libs = ["asound"]
        asound.set_property("cmake_target_name", "ALSA::asound")
        asound.set_property("pkg_config_name", "alsa")
        system_libs, link_flags = self._pkg_config_private_linkage("alsa.pc")
        asound.system_libs = system_libs
        asound.sharedlinkflags = link_flags
        asound.exelinkflags = link_flags

        topology = self.cpp_info.components["atopology"]
        topology.libs = ["atopology"]
        topology.requires = ["asound"]
        topology.set_property("cmake_target_name", "ALSA::atopology")
        topology.set_property("pkg_config_name", "alsa-topology")

        config_dir = os.path.join(self.package_folder, "share", "alsa")
        self.runenv_info.define_path("ALSA_CONFIG_DIR", config_dir)
        self.runenv_info.define_path(
            "ALSA_CONFIG_PATH", os.path.join(config_dir, "alsa.conf")
        )
        self.runenv_info.define_path(
            "ALSA_PLUGIN_DIR", os.path.join(self.package_folder, "lib", "alsa-lib")
        )

    def _prepare_source_copy(self):
        work_source = Path(self.build_folder, "source-copy")
        if work_source.exists():
            shutil.rmtree(work_source)
        source_root = Path(self.source_folder).resolve()
        build_root = Path(self.build_folder).resolve()
        ignored_root_entry = None
        try:
            ignored_root_entry = build_root.relative_to(source_root).parts[0]
        except (ValueError, IndexError):
            pass

        def ignore_nested_build(directory, _entries):
            if Path(directory).resolve() == source_root and ignored_root_entry:
                return (ignored_root_entry,)
            return ()

        self._assert_no_links(source_root)
        shutil.copytree(source_root, work_source, ignore=ignore_nested_build)
        self._assert_no_links(work_source)
        return work_source

    def _patch_entries(self):
        patches = self.conan_data.get("patches")
        if isinstance(patches, dict):
            entries = patches.get(str(self.version))
        elif isinstance(patches, list):
            entries = patches
        else:
            raise ConanException(
                "conandata patches must be a list or a version-to-list mapping"
            )
        if not isinstance(entries, list) or not entries:
            raise ConanException(f"no patches declared for alsa-lib {self.version}")
        if any(
            not isinstance(entry, dict) or "patch_file" not in entry
            for entry in entries
        ):
            raise ConanException("every alsa-lib patch entry needs patch_file")
        return entries

    @staticmethod
    def _refresh_generated_build_files(work_source):
        generated = [
            work_source / "aclocal.m4",
            work_source / "configure",
            work_source / "include" / "config.h.in",
            *sorted(work_source.rglob("Makefile.in")),
        ]
        missing = [str(path) for path in generated if not path.is_file()]
        if missing:
            raise ConanException(
                f"generated Autotools input is missing: {missing}"
            )
        for path in generated:
            path.touch()

    def _materialize_build_include_alias(self, work_source):
        source_alias = work_source / "include" / "alsa"
        build_alias = Path(self.build_folder, "include", "alsa")
        if not source_alias.is_dir() or os.path.lexists(build_alias):
            raise ConanException("build include/alsa materialization precondition failed")
        self._assert_no_links(source_alias)
        shutil.copytree(source_alias, build_alias)
        self._assert_no_links(build_alias)
        if self._file_manifest(source_alias) != self._file_manifest(build_alias):
            raise ConanException("build include/alsa tree does not match source alias")

    def _extract_official_source(self, archive_path):
        root_name = f"alsa-lib-{self.version}"
        expected_link = f"{root_name}/include/alsa"
        extraction = Path(self.source_folder, ".official-extract")
        if extraction.exists():
            shutil.rmtree(extraction)
        extraction.mkdir(parents=True)

        try:
            with tarfile.open(archive_path, "r:bz2") as bundle:
                regular_members = []
                links = []
                for member in bundle.getmembers():
                    member_path = PurePosixPath(member.name)
                    if (
                        member_path.is_absolute()
                        or ".." in member_path.parts
                        or not member_path.parts
                        or member_path.parts[0] != root_name
                    ):
                        raise ConanException(
                            f"unsafe official archive member: {member.name}"
                        )
                    if member.issym():
                        links.append((member.name, member.linkname))
                        continue
                    if member.islnk() or member.isdev() or member.isfifo():
                        raise ConanException(
                            f"unsupported official archive member: {member.name}"
                        )
                    if not (member.isdir() or member.isfile()):
                        raise ConanException(
                            f"unknown official archive member: {member.name}"
                        )
                    regular_members.append(member)

                if links != [(expected_link, ".")]:
                    raise ConanException(
                        "official archive must contain only "
                        f"{expected_link} -> ., found {links}"
                    )
                bundle.extractall(
                    path=extraction,
                    members=regular_members,
                    filter="data",
                )

            extracted_root = extraction / root_name
            if not extracted_root.is_dir():
                raise ConanException("official archive root was not extracted")
            self._materialize_alsa_include_alias(extracted_root)
            self._assert_no_links(extracted_root)

            for child in extracted_root.iterdir():
                destination = Path(self.source_folder, child.name)
                if os.path.lexists(destination):
                    raise ConanException(
                        f"source extraction would overwrite {destination}"
                    )
                shutil.move(str(child), str(destination))
        finally:
            if extraction.exists():
                shutil.rmtree(extraction)

    def _materialize_alsa_include_alias(self, source_root):
        include_dir = source_root / "include"
        alias_dir = include_dir / "alsa"
        if not include_dir.is_dir() or os.path.lexists(alias_dir):
            raise ConanException("include/alsa materialization precondition failed")

        source_entries = list(include_dir.iterdir())
        expected_manifest = self._file_manifest(include_dir)
        alias_dir.mkdir()
        for entry in source_entries:
            destination = alias_dir / entry.name
            if entry.is_dir():
                shutil.copytree(entry, destination)
            elif entry.is_file():
                shutil.copy2(entry, destination)
            else:
                raise ConanException(f"unsupported include entry: {entry}")

        actual_manifest = self._file_manifest(alias_dir)
        if actual_manifest != expected_manifest:
            raise ConanException("materialized include/alsa tree does not match include")

    @staticmethod
    def _file_manifest(root):
        manifest = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return manifest

    @staticmethod
    def _assert_no_links(root):
        links = []
        for current, directories, files in os.walk(root, followlinks=False):
            for name in (*directories, *files):
                path = os.path.join(current, name)
                if os.path.islink(path):
                    links.append(os.path.relpath(path, root))
        if links:
            raise ConanException(f"source tree retains symbolic links: {links}")

    def _write_signing_compiler_wrapper(self):
        tools = self._require_ohos_sign_tools()
        shell_tools = {
            "awk": "/system/bin/awk",
            "chmod": "/system/bin/chmod",
            "cp": "/system/bin/cp",
            "grep": "/system/bin/grep",
            "mv": "/system/bin/mv",
            "rm": "/system/bin/rm",
            "sha256sum": "/system/bin/sha256sum",
            "wc": "/system/bin/wc",
        }
        missing = [
            path for path in shell_tools.values() if not os.path.isfile(path)
        ]
        if missing:
            raise ConanInvalidConfiguration(
                f"OHOS signing wrapper tools are missing: {missing}"
            )

        evidence_dir = Path(self.build_folder, "alsa-signing")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        compile_events = evidence_dir / "compile-events.tsv"
        sign_events = evidence_dir / "sign-events.tsv"
        compile_events.write_text("", encoding="utf-8")
        sign_events.write_text("", encoding="utf-8")

        wrapper = Path(self.generators_folder, "alsa-clang-sign-wrapper.sh")
        script = """#!/system/bin/sh
set -euo pipefail

real_cc=@REAL_CC@
objcopy=@OBJCOPY@
readelf=@READELF@
signer=@SIGNER@
awk=@AWK@
chmod_tool=@CHMOD@
cp_tool=@CP@
grep_tool=@GREP@
mv_tool=@MV@
rm_tool=@RM@
sha256sum=@SHA256SUM@
wc_tool=@WC@
compile_events=@COMPILE_EVENTS@
sign_events=@SIGN_EVENTS@

set +e
"$real_cc" "$@"
compiler_status=$?
set -e
if [ "$compiler_status" -ne 0 ]; then
  exit "$compiler_status"
fi

output=""
expect_output=0
for argument in "$@"; do
  if [ "$expect_output" -eq 1 ]; then
    output="$argument"
    expect_output=0
    continue
  fi
  if [ "$argument" = "-o" ]; then
    expect_output=1
  fi
done
if [ "$expect_output" -ne 0 ]; then
  printf 'ALSA_SIGN_MISSING_OUTPUT_ARGUMENT\n' >&2
  exit 91
fi
if [ -z "$output" ]; then
  output="a.out"
fi
case "$output" in
  /*) ;;
  *) output="$(pwd)/$output" ;;
esac
if printf '%s' "$output" | LC_ALL=C "$grep_tool" -q '[[:cntrl:]]'; then
  printf 'ALSA_SIGN_UNSAFE_OUTPUT_PATH=%s\n' "$output" >&2
  exit 92
fi
if [ ! -f "$output" ]; then
  exit 0
fi

set +e
elf_header="$($readelf -h "$output" 2>/dev/null)"
readelf_status=$?
set -e
if [ "$readelf_status" -ne 0 ]; then
  exit 0
fi
elf_type="$(printf '%s\n' "$elf_header" | $awk '$1 == "Type:" {print $2; exit}')"
case "$elf_type" in
  EXEC|DYN) ;;
  *) exit 0 ;;
esac

clean="${output}.alsa-codesign-clean.$$"
signed="${output}.alsa-codesign-signed.$$"
codesign_dump="${output}.alsa-codesign-dump.$$"
inspect="${output}.alsa-codesign-inspect.$$"
cleanup() {
  "$rm_tool" -f "$clean" "$signed" "$inspect" "$codesign_dump"
}
trap cleanup EXIT HUP INT TERM
cleanup

before_size="$($wc_tool -c < "$output" | $awk '{print $1}')"
before_sha="$($sha256sum "$output" | $awk '{print $1}')"
printf '%s\t%s\t%s\n' "$before_sha" "$before_size" "$output" \
  >> "$compile_events"

"$objcopy" --remove-section .codesign "$output" "$clean"
"$signer" sign -inFile "$clean" -outFile "$signed" -selfSign 1
codesign_count="$($readelf -SW "$signed" | \
  $awk 'index($0, ".codesign") {count++} END {print count + 0}')"
if [ "$codesign_count" -ne 1 ]; then
  printf 'ALSA_SIGN_BAD_SECTION_COUNT=%s:%s\n' \
    "$codesign_count" "$output" >&2
  exit 93
fi
"$cp_tool" "$signed" "$inspect"
"$objcopy" --dump-section ".codesign=$codesign_dump" "$inspect"
codesign_size="$($wc_tool -c < "$codesign_dump" | $awk '{print $1}')"
if [ "$codesign_size" -le 0 ]; then
  printf 'ALSA_SIGN_EMPTY_SECTION=%s\n' "$output" >&2
  exit 94
fi
codesign_sha="$($sha256sum "$codesign_dump" | $awk '{print $1}')"
after_sha="$($sha256sum "$signed" | $awk '{print $1}')"
"$chmod_tool" 755 "$signed"
"$rm_tool" -f "$output"
"$mv_tool" "$signed" "$output"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$before_sha" "$before_size" "$after_sha" "$codesign_size" \
  "$codesign_sha" "$output" >> "$sign_events"

trap - EXIT HUP INT TERM
cleanup
"""
        replacements = {
            "@REAL_CC@": "/data/service/hnp/bin/clang",
            "@OBJCOPY@": tools["objcopy"],
            "@READELF@": tools["readelf"],
            "@SIGNER@": tools["signer"],
            "@AWK@": shell_tools["awk"],
            "@CHMOD@": shell_tools["chmod"],
            "@CP@": shell_tools["cp"],
            "@GREP@": shell_tools["grep"],
            "@MV@": shell_tools["mv"],
            "@RM@": shell_tools["rm"],
            "@SHA256SUM@": shell_tools["sha256sum"],
            "@WC@": shell_tools["wc"],
            "@COMPILE_EVENTS@": str(compile_events),
            "@SIGN_EVENTS@": str(sign_events),
        }
        for marker, value in replacements.items():
            script = script.replace(marker, shlex.quote(value))
        if re.search(r"@[A-Z_]+@", script):
            raise ConanException("signing compiler wrapper has unresolved markers")
        wrapper.write_text(script, encoding="utf-8", newline="\n")
        wrapper.chmod(0o755)
        return wrapper

    def _upstream_test_make_args(self):
        arguments = self._make_args()
        if str(self.settings.os) == "OHOS":
            timeout = "/system/bin/timeout"
            if not os.path.isfile(timeout):
                raise ConanInvalidConfiguration(
                    "OHOS upstream tests require /system/bin/timeout"
                )
            launcher = self._write_upstream_test_launcher()
            arguments.extend((
                f"LOG_COMPILER={self._shell()}",
                shlex.quote(f"AM_LOG_FLAGS={launcher} 180"),
            ))
        return arguments

    def _exclude_static_oldapi_check_program(self):
        if (
            str(self.settings.os) != "OHOS"
            or str(self.options.shared).lower() == "true"
        ):
            return

        makefile = Path(self.build_folder, "test", "Makefile")
        text = makefile.read_text(encoding="utf-8")
        match = re.search(
            r"^check_PROGRAMS = .*?(?=^[A-Za-z_][A-Za-z0-9_]*\s*=)",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not match or match.group(0).count("oldapi$(EXEEXT)") != 1:
            raise ConanException(
                "static upstream test build did not contain exactly one oldapi target"
            )
        replacement = match.group(0).replace(" oldapi$(EXEEXT)", "", 1)
        makefile.write_text(
            text[: match.start()] + replacement + text[match.end() :],
            encoding="utf-8",
            newline="\n",
        )

    def _write_upstream_test_launcher(self):
        launcher = Path(self.build_folder, "conan", "alsa-test-launcher.sh")
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(
            """#!/system/bin/sh
set -eu
test "$#" -ge 2
seconds=$1
executable=$2
shift 2
magic=$(dd if="$executable" bs=1 count=2 2>/dev/null)
case "$magic" in
  '#!') exec /system/bin/timeout "$seconds" /system/bin/sh "$executable" "$@" ;;
  *) exec /system/bin/timeout "$seconds" "$executable" "$@" ;;
esac
""",
            encoding="utf-8",
            newline="\n",
        )
        return launcher

    def _validate_upstream_test_results(self):
        expected = {
            "test/lsb/config.trs",
            "test/lsb/midi_event.trs",
        }
        actual = {
            path.relative_to(self.build_folder).as_posix()
            for path in Path(self.build_folder).rglob("*.trs")
        }
        if actual != expected:
            raise ConanException(
                f"upstream test result set is {sorted(actual)}, "
                f"expected {sorted(expected)}"
            )

        expected_fields = {
            "test-result": "PASS",
            "global-test-result": "PASS",
            "recheck": "no",
            "copy-in-global-log": "no",
        }
        for relative in sorted(expected):
            path = Path(self.build_folder, *relative.split("/"))
            fields = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.fullmatch(r":([^:]+):\s*(\S+)\s*", line)
                if not match or match.group(1) in fields:
                    raise ConanException(f"invalid Automake result line in {relative}")
                fields[match.group(1)] = match.group(2)
            if fields != expected_fields:
                raise ConanException(
                    f"upstream test {relative} has terminal fields {fields}"
                )

    def _validate_build_sign_chain(self):
        evidence_dir = Path(self.build_folder, "alsa-signing")
        compile_events = self._read_tsv(
            evidence_dir / "compile-events.tsv", 3
        )
        sign_events = self._read_tsv(evidence_dir / "sign-events.tsv", 6)
        if not compile_events or len(compile_events) != len(sign_events):
            raise ConanException(
                "compiler/sign event counts are empty or do not match: "
                f"{len(compile_events)} != {len(sign_events)}"
            )

        hash_pattern = re.compile(r"[0-9a-f]{64}")
        signed_outputs = []
        signed_metadata = {}
        for index, (compiled, signed) in enumerate(
            zip(compile_events, sign_events), start=1
        ):
            before_sha, before_size, output = compiled
            (
                signed_before_sha,
                signed_before_size,
                after_sha,
                codesign_size,
                codesign_sha,
                signed_output,
            ) = signed
            if (
                not hash_pattern.fullmatch(before_sha)
                or not hash_pattern.fullmatch(after_sha)
                or not hash_pattern.fullmatch(codesign_sha)
                or int(before_size) <= 0
                or int(codesign_size) <= 0
                or (before_sha, before_size, output)
                != (signed_before_sha, signed_before_size, signed_output)
            ):
                raise ConanException(f"invalid compiler/sign event pair {index}")
            output_path = Path(output)
            signed_outputs.append(output_path)
            signed_metadata[os.path.normpath(str(output_path))] = {
                "after_sha256": after_sha,
                "codesign_size": int(codesign_size),
                "codesign_sha256": codesign_sha,
            }

        if not any(path.name.startswith("conftest") for path in signed_outputs):
            raise ConanException("configure produced no signed conftest event")

        tools = self._require_ohos_sign_tools()
        program_dir = Path(self.build_folder, "test", "lsb")
        if str(self.options.shared).lower() == "true":
            program_dir /= ".libs"
        expected_programs = (
            program_dir / "config",
            program_dir / "midi_event",
        )
        normalized_events = {
            os.path.normpath(str(path)) for path in signed_outputs
        }
        for program in expected_programs:
            if os.path.normpath(str(program)) not in normalized_events:
                raise ConanException(
                    f"upstream test executable lacks a sign event: {program.name}"
                )
            current_codesign = self._codesign_metadata(program, tools)
            recorded = signed_metadata[os.path.normpath(str(program))]
            if (
                self._sha256(program) != recorded["after_sha256"]
                or current_codesign["size"] != recorded["codesign_size"]
                or current_codesign["sha256"]
                != recorded["codesign_sha256"]
            ):
                raise ConanException(
                    f"upstream test signing evidence drifted: {program.name}"
                )

    def _sign_package_elfs(self):
        shared = str(self.options.shared).lower() == "true"
        expected = {"bin/aserver"}
        if shared:
            expected.update(("lib/libasound.so", "lib/libatopology.so"))

        package = Path(self.package_folder)
        actual = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file() and self._is_elf(path)
        }
        if actual != expected:
            raise ConanException(
                f"package ELF set is {sorted(actual)}, expected {sorted(expected)}"
            )

        tools = self._require_ohos_sign_tools()
        entries = []
        for relative in sorted(expected):
            path = package / PurePosixPath(relative)
            if path.is_symlink():
                raise ConanException(f"package ELF must be a real file: {relative}")
            entry = self._sign_elf(path, tools)
            entry["path"] = relative
            entries.append(entry)

        manifest = {
            "schema": 1,
            "package_mode": "shared" if shared else "static",
            "entries": entries,
        }
        destination = Path(
            self.package_folder,
            "share",
            "alsa",
            "conan-elf-signatures.json",
        )
        destination.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _sign_elf(self, path, tools):
        if not path.is_file() or path.is_symlink() or not self._is_elf(path):
            raise ConanException(f"invalid ELF signing input: {path}")
        before_sha = self._sha256(path)
        mode = path.stat().st_mode & 0o7777
        clean = Path(f"{path}.alsa-codesign-clean-{os.getpid()}")
        signed = Path(f"{path}.alsa-codesign-signed-{os.getpid()}")
        for temporary in (clean, signed):
            if os.path.lexists(temporary):
                temporary.unlink()

        try:
            self._run_subprocess(
                [
                    tools["objcopy"],
                    "--remove-section",
                    ".codesign",
                    str(path),
                    str(clean),
                ],
                f"remove old .codesign from {path.name}",
            )
            if not self._is_elf(clean):
                raise ConanException(f"ELF cleanup produced invalid output: {path}")
            if self._codesign_count(clean, tools["readelf"]) != 0:
                raise ConanException(f"ELF cleanup retained .codesign: {path}")
            self._run_subprocess(
                [
                    tools["signer"],
                    "sign",
                    "-inFile",
                    str(clean),
                    "-outFile",
                    str(signed),
                    "-selfSign",
                    "1",
                ],
                f"sign {path.name}",
            )
            if not self._is_elf(signed):
                raise ConanException(f"ELF signer produced invalid output: {path}")
            codesign = self._codesign_metadata(signed, tools)
            os.chmod(signed, mode)
            after_sha = self._sha256(signed)
            path.unlink()
            os.replace(signed, path)
        finally:
            for temporary in (clean, signed):
                if os.path.lexists(temporary):
                    temporary.unlink()

        return {
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "codesign_size": codesign["size"],
            "codesign_sha256": codesign["sha256"],
        }

    def _codesign_metadata(self, path, tools):
        count = self._codesign_count(path, tools["readelf"])
        if count != 1:
            raise ConanException(
                f"{path.name} has {count} .codesign sections, expected one"
            )
        dump = Path(f"{path}.alsa-codesign-dump-{os.getpid()}")
        inspect = Path(f"{path}.alsa-codesign-inspect-{os.getpid()}")
        for temporary in (dump, inspect):
            if os.path.lexists(temporary):
                temporary.unlink()
        try:
            shutil.copy2(path, inspect)
            self._run_subprocess(
                [
                    tools["objcopy"],
                    "--dump-section",
                    f".codesign={dump}",
                    str(inspect),
                ],
                f"dump .codesign from {path.name}",
            )
            if not dump.is_file() or dump.stat().st_size <= 0:
                raise ConanException(f"{path.name} has an empty .codesign section")
            return {
                "size": dump.stat().st_size,
                "sha256": self._sha256(dump),
            }
        finally:
            for temporary in (dump, inspect):
                if os.path.lexists(temporary):
                    temporary.unlink()

    def _codesign_count(self, path, readelf):
        completed = self._run_subprocess(
            [readelf, "-SW", str(path)],
            f"inspect sections for {path.name}",
        )
        return sum(
            1
            for line in completed.stdout.splitlines()
            if ".codesign" in line.split()
        )

    def _require_ohos_sign_tools(self):
        tools = {
            "objcopy": "/data/service/hnp/bin/llvm-objcopy",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        compiler = "/data/service/hnp/bin/clang"
        missing = [
            path
            for path in (*tools.values(), compiler)
            if not os.path.isfile(path)
        ]
        if missing:
            raise ConanInvalidConfiguration(
                f"OHOS ELF signing toolchain is missing: {missing}"
            )
        return tools

    @staticmethod
    def _read_tsv(path, field_count):
        if not path.is_file():
            raise ConanException(f"signing evidence is missing: {path.name}")
        rows = []
        for index, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            fields = line.split("\t")
            if len(fields) != field_count or any(not field for field in fields):
                raise ConanException(f"invalid {path.name} row {index}")
            rows.append(tuple(fields))
        return rows

    @staticmethod
    def _sha256(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def _is_elf(path):
        try:
            with Path(path).open("rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _run_subprocess(command, purpose):
        try:
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ConanException(f"{purpose} failed: {error}") from error
        if completed.returncode != 0:
            detail = completed.stdout.strip()[-500:]
            raise ConanException(
                f"{purpose} failed with rc={completed.returncode}: {detail}"
            )
        return completed

    def _make_args(self):
        arguments = ["-j1"]
        if (
            str(self.settings.os) == "OHOS"
            and str(self.options.shared).lower() == "true"
        ):
            arguments.append("ALSA_LIBTOOL_VERSION_FLAGS=-avoid-version")
        return arguments

    def _shell(self):
        if str(self.settings.os) == "OHOS":
            shell = "/system/bin/sh"
        else:
            shell = shutil.which("sh") or shutil.which("bash")
        if not shell or not os.path.isfile(shell):
            raise ConanException(f"configure shell is unavailable: {shell}")
        return shell

    def _make_pkg_config_relocatable(self, name):
        path = Path(self.package_folder, "lib", "pkgconfig", name)
        if not path.is_file():
            raise ConanException(f"upstream install did not produce {name}")
        lines = path.read_text(encoding="utf-8").splitlines()
        prefix_lines = [
            index for index, line in enumerate(lines) if line.startswith("prefix=")
        ]
        if len(prefix_lines) > 1:
            raise ConanException(f"{name} contains multiple prefix assignments")
        if prefix_lines:
            lines[prefix_lines[0]] = "prefix=${pcfiledir}/../.."
        else:
            lines[0:0] = [
                "prefix=${pcfiledir}/../..",
                "exec_prefix=${prefix}",
                "libdir=${exec_prefix}/lib",
                "includedir=${prefix}/include",
                "",
            ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_feature_contract(self):
        config_path = Path(self.build_folder, "include", "config.h")
        if not config_path.is_file():
            raise ConanException("configured include/config.h is missing")
        config_text = config_path.read_text(encoding="utf-8")

        component_macros = {
            "mixer": "BUILD_MIXER",
            "pcm": "BUILD_PCM",
            "rawmidi": "BUILD_RAWMIDI",
            "hwdep": "BUILD_HWDEP",
            "seq": "BUILD_SEQ",
            "ucm": "BUILD_UCM",
            "topology": "BUILD_TOPOLOGY",
        }
        components = {
            name: self._config_define(config_text, macro) is not None
            for name, macro in component_macros.items()
        }

        pcm_plugins = (
            "copy",
            "linear",
            "route",
            "mulaw",
            "alaw",
            "adpcm",
            "rate",
            "plug",
            "multi",
            "shm",
            "file",
            "null",
            "empty",
            "share",
            "meter",
            "hooks",
            "lfloat",
            "ladspa",
            "dmix",
            "dshare",
            "dsnoop",
            "asym",
            "iec958",
            "softvol",
            "extplug",
            "ioplug",
            "mmap_emul",
        )
        object_dir = Path(self.build_folder, "src", "pcm")
        if str(self.options.shared).lower() == "true":
            object_dir /= ".libs"
        enabled_plugins = [
            name
            for name in pcm_plugins
            if any(
                (object_dir / f"pcm_{name}{suffix}").is_file()
                for suffix in (".o", ".obj")
            )
        ]
        if components["pcm"] and not enabled_plugins:
            raise ConanException("PCM is enabled but no plug-in objects were found")

        paths = {
            name: self._config_define(config_text, name)
            for name in (
                "ALSA_CONFIG_DIR",
                "ALSA_PLUGIN_DIR",
                "ALSA_DEVICE_DIRECTORY",
                "TMPDIR",
            )
        }
        if any(value is None for value in paths.values()):
            missing = sorted(name for name, value in paths.items() if value is None)
            raise ConanException(
                f"configured ALSA path definitions are missing: {', '.join(missing)}"
            )

        aserver = Path(self.package_folder, "bin", "aserver").is_file()
        contract = {
            "schema": 1,
            "version": str(self.version),
            "components": components,
            "pcm_plugins": enabled_plugins,
            "compiled_paths": paths,
            "path_policy": {
                "ALSA_CONFIG_DIR": "overridden by Conan run environment",
                "ALSA_PLUGIN_DIR": "overridden by Conan run environment",
                "ALSA_DEVICE_DIRECTORY": "fixed target device namespace",
                "TMPDIR": "compile-time socket default; target verification pending",
            },
            "aserver": aserver,
            "commands_required": aserver,
        }
        destination = Path(
            self.package_folder, "share", "alsa", "conan-feature-contract.json"
        )
        destination.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _config_define(config_text, name):
        match = re.search(
            rf"^#define\s+{re.escape(name)}\s+(.+?)\s*$",
            config_text,
            flags=re.MULTILINE,
        )
        if not match:
            return None
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        return value

    def _pkg_config_private_linkage(self, name):
        path = Path(self.package_folder, "lib", "pkgconfig", name)
        lines = path.read_text(encoding="utf-8").splitlines()
        private_lines = [
            line.split(":", 1)[1].strip()
            for line in lines
            if line.startswith("Libs.private:")
        ]
        if len(private_lines) != 1:
            raise ConanException(f"{name} must contain one Libs.private field")

        system_libs = []
        link_flags = []
        for token in shlex.split(private_lines[0]):
            if token.startswith("-l") and len(token) > 2:
                system_libs.append(token[2:])
            elif token:
                link_flags.append(token)
        return system_libs, link_flags
