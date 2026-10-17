#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Build2, build2, 0.18.0, build2 0.18.0, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Build2Conan(ConanFile):
    name = "build2"
    version = "0.18.0"
    description = "build2 0.18.0"
    license = "MIT"
    homepage = "https://build2.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {
        "shared": False,
        "uuid/*:shared": False,
        "uuid/*:fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if str(self.settings.os) == "OHOS":
            self.requires("uuid/2.40.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            filename="build2-0.18.0.tar.gz",
            strip_root=True,
        )
        get(
            self,
            url=source["libbutl_url"],
            sha256=source["libbutl_sha256"],
            filename="libbutl-0.18.0.tar.gz",
            destination="libbutl-0.18.0",
            strip_root=True,
        )
        get(
            self,
            url=source["libpkg_config_url"],
            sha256=source["libpkg_config_sha256"],
            filename="libpkg-config-0.1.3.tar.gz",
            destination=os.path.join(
                "libbutl-0.18.0", "upstream", "libpkg-config"
            ),
            strip_root=True,
        )

    def build(self):
        # Conan runs build() and test_package in the same Python process. The
        # private build HOME/TMP/tool paths must not survive their own cleanup.
        keys = ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "TMPDIR",
                "TMPPREFIX", "TMP", "TEMP", "PATH", "LD_LIBRARY_PATH")
        previous = {key: os.environ.get(key) for key in keys}
        try:
            self._build_with_private_environment()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _build_with_private_environment(self):
        apply_conandata_patches(self)

        executables = self.conf.get("tools.build:compiler_executables", default=None)
        cc = None
        cxx = None
        if isinstance(executables, dict):
            cc = executables.get("c")
            cxx = executables.get("cpp") or executables.get("cxx")
        elif isinstance(executables, str):
            cc = executables
            cxx = executables

        if not cc:
            cc = shutil.which("clang" if str(self.settings.os) == "OHOS" else "gcc")
        if not cxx:
            cxx = shutil.which("clang++" if str(self.settings.os) == "OHOS" else "g++")
        if not cc:
            raise RuntimeError("build2 requires a target C compiler; set tools.build:compiler_executables.c")
        if not cxx:
            raise RuntimeError("build2 requires a target C++ compiler; set tools.build:compiler_executables.cpp")

        make = shutil.which("make")
        if not make:
            raise RuntimeError("build2 requires GNU make in PATH")

        # The bootstrap makefile searches beside the source directory. Keep the
        # vendored libbutl tree inside the copied source tree and bind it explicitly.
        libbutl = os.path.join(self.source_folder, "libbutl-0.18.0")
        if not os.path.isdir(libbutl):
            raise RuntimeError("libbutl-0.18.0 was not unpacked beside build2")

        # HarmonyOS user storage can reject the rename/locking operations used by
        # Phase 2 even though the bootstrap binary itself is executable there.
        # Prefer the worker/device application cache, then the conventional
        # temporary directory, and validate the Phase 2 filesystem operations
        # before copying the source tree.
        work_root = None
        if str(self.settings.os) == "OHOS":
            candidates = []
            for parent in (
                "/data/local/tmp",
                "/data/app",
                "/data/storage/el2/base/cache",
                os.environ.get("TMPDIR"),
            ):
                if parent and parent not in candidates and os.path.isdir(parent):
                    candidates.append(parent)

            for parent in candidates:
                candidate_root = None
                try:
                    candidate_root = tempfile.mkdtemp(
                        prefix="build2-0.18.0-", dir=parent
                    )
                    probe = os.path.join(candidate_root, ".write-probe")
                    renamed = probe + ".renamed"
                    with open(probe, "wb") as stream:
                        stream.write(b"ok")
                    os.chmod(probe, 0o600)
                    if os.stat(probe).st_mode & 0o777 != 0o600:
                        raise OSError("work-root chmod probe did not stick")
                    os.replace(probe, renamed)
                    os.unlink(renamed)
                    # build2 replaces an existing executable during the Phase 2
                    # self-update. Probe that exact operation before selecting
                    # a target root.
                    existing = os.path.join(candidate_root, ".replace-target")
                    replacement = existing + ".tmp"
                    with open(existing, "wb") as stream:
                        stream.write(b"old")
                    with open(replacement, "wb") as stream:
                        stream.write(b"new")
                    os.chmod(replacement, 0o700)
                    os.replace(replacement, existing)
                    if os.stat(existing).st_mode & 0o700 != 0o700:
                        raise OSError(
                            "work-root executable replacement probe did not stick"
                        )
                    os.unlink(existing)
                    lock_probe = os.path.join(candidate_root, ".lock-probe")
                    with open(lock_probe, "w+b") as stream:
                        import fcntl

                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                    os.unlink(lock_probe)
                    nested = os.path.join(candidate_root, "nested")
                    os.makedirs(nested)
                    shutil.rmtree(nested)
                    work_root = candidate_root
                    break
                except OSError:
                    if candidate_root and os.path.isdir(candidate_root):
                        shutil.rmtree(candidate_root, ignore_errors=True)

        if work_root is None:
            # Keep the copied source tree outside Conan's source/build layout.
            # basic_layout may place source_folder above build_folder; putting
            # this directory below build_folder makes copytree recurse forever.
            work_root = tempfile.mkdtemp(prefix="build2-0.18.0-")

        source_abs = os.path.abspath(self.source_folder)
        work_abs = os.path.abspath(work_root)
        if os.path.commonpath((source_abs, work_abs)) == source_abs:
            raise RuntimeError(
                "build2 test work root must be outside Conan source_folder"
            )

        source_root = os.path.join(work_root, "build2")
        build_abs = os.path.abspath(self.build_folder)
        build_rel = os.path.relpath(build_abs, source_abs)
        ignored_root = None
        if build_rel != os.curdir and not build_rel.startswith(os.pardir + os.sep):
            ignored_root = build_rel.split(os.sep, 1)[0]

        def ignore_conan_build(path, names):
            if ignored_root and os.path.abspath(path) == source_abs:
                return [ignored_root] if ignored_root in names else []
            return []

        # basic_layout may place Conan's build-release directory below the
        # source folder. It contains generated conan/ metadata, not upstream
        # sources, and must not become a build2 test input.
        shutil.copytree(
            self.source_folder,
            source_root,
            symlinks=True,
            ignore=ignore_conan_build,
        )
        work_libbutl = os.path.join(source_root, "libbutl-0.18.0")

        tmpdir = os.path.join(work_root, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        home_root = os.path.join(work_root, "home")
        os.makedirs(home_root, exist_ok=True)
        os.environ["HOME"] = home_root
        os.environ["XDG_CONFIG_HOME"] = os.path.join(home_root, ".config")
        os.environ["XDG_CACHE_HOME"] = os.path.join(home_root, ".cache")
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = tmpdir + os.sep
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        if str(self.settings.os) == "OHOS":
            # Nested official test invocations pass config.cxx but not its id.
            # Fix only the bare -v probe; all compilation remains delegated to
            # the original target wrapper with its original link/sign flags.
            probe_bin = os.path.join(work_root, "compiler-probes")
            os.makedirs(probe_bin)
            adapted = []
            for compiler, mode, name in ((cc, "gcc", "clang"), (cxx, "g++", "clang++")):
                probe = subprocess.run([compiler, "-v"], capture_output=True)
                if probe.returncode == 0:
                    adapted.append(compiler)
                    continue
                with open(compiler, "rb") as stream:
                    wrapper = stream.read()
                match = re.search(rb'exec "\$DIR/(clang-[0-9]+)"', wrapper)
                if not match:
                    raise RuntimeError("Cannot bind the failing clang wrapper to its real compiler")
                native = os.path.join(os.path.dirname(compiler), match.group(1).decode("ascii"))
                with open(native, "rb") as stream:
                    if stream.read(4) != b"\x7fELF":
                        raise RuntimeError("Bound native compiler is not an ELF executable")
                native_probe = subprocess.run([native, "--driver-mode="+mode, "-v"], capture_output=True)
                if native_probe.returncode != 0 or b"clang version" not in native_probe.stderr:
                    raise RuntimeError("Native compiler identification probe failed")
                adapter = os.path.join(probe_bin, name)
                with open(adapter, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write("#!/bin/sh\nif [ \"$#\" -eq 1 ] && [ \"$1\" = -v ]; then\n  exec "
                                 + shlex.quote(native)+" --driver-mode="+shlex.quote(mode)+" -v\nfi\nexec "
                                  + shlex.quote(compiler)+" -Qunused-arguments \"$@\"\n")
                os.chmod(adapter, 0o700)
                adapted.append(adapter)
            cc, cxx = adapted
            # Nested test projects also auto-detect the conventional ar name.
            configured_ar = executables.get("ar") if isinstance(executables, dict) else None
            native_ar = configured_ar or shutil.which("llvm-ar") or shutil.which("ar")
            if not native_ar or not os.path.isfile(native_ar):
                raise RuntimeError("Target archive tool is absent")
            with open(os.path.join(probe_bin, "ar"), "w", encoding="utf-8", newline="\n") as stream:
                stream.write("#!/bin/sh\nexec "+shlex.quote(native_ar)+" \"$@\"\n")
            os.chmod(os.path.join(probe_bin, "ar"), 0o700)
            os.environ["PATH"] = os.pathsep.join([probe_bin, os.environ.get("PATH", "")])
        print(f"HMBS_WORK_ROOT={work_root}")
        print(f"HMBS_BUILD_HOME={home_root}")

        tool_dirs = [
            os.path.dirname(os.path.abspath(cc)),
            os.path.dirname(os.path.abspath(cxx)),
            os.path.dirname(os.path.abspath(make)),
        ]
        os.environ["PATH"] = os.pathsep.join(tool_dirs + [os.environ.get("PATH", "")])
        if str(self.settings.os) == "OHOS":
            llvm_lib_dirs = []
            for compiler in (cxx, shutil.which("clang++")):
                if not compiler:
                    continue
                compiler_bin = os.path.dirname(os.path.realpath(compiler))
                candidate = os.path.normpath(os.path.join(compiler_bin, os.pardir, "lib"))
                if candidate not in llvm_lib_dirs and os.path.isdir(candidate):
                    llvm_lib_dirs.append(candidate)
            # The CI clang++ wrapper may live in /data/service/hnp/bin while
            # its SDK is unpacked under ohos-sdk.org; discover that fixed SDK
            # layout without scanning unrelated user storage.
            llvm_lib_dirs.extend(
                path
                for path in sorted(
                    glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
                )
                if path not in llvm_lib_dirs and os.path.isdir(path)
            )
            if llvm_lib_dirs:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                    llvm_lib_dirs + [os.environ.get("LD_LIBRARY_PATH", "")]
                )
                print(
                    "HMBS_LLVM_LIBRARY_PATH="
                    + os.pathsep.join(llvm_lib_dirs)
                )

        # libbutl's Linux UUID backend intentionally loads libuuid.so.1 at
        # runtime. OHOS does not provide that SONAME, so materialize it from
        # the published PIC uuid package without changing upstream sources or
        # tests. Probe both target loading and the real uuid_generate ABI
        # before the full upstream runner consumes it.
        uuid_runtime_library = None
        if str(self.settings.os) == "OHOS":
            uuid_dependency = self.dependencies["uuid"]
            uuid_archive = os.path.join(
                uuid_dependency.package_folder, "lib", "libuuid.a"
            )
            if not os.path.isfile(uuid_archive):
                raise RuntimeError(
                    "uuid/2.40.1 package does not contain lib/libuuid.a"
                )
            uuid_runtime_dir = os.path.join(work_root, "runtime-lib")
            os.makedirs(uuid_runtime_dir)
            uuid_runtime_library = os.path.join(
                uuid_runtime_dir, "libuuid.so.1"
            )
            uuid_link = subprocess.run(
                [
                    cc,
                    "-shared",
                    "-Wl,-soname,libuuid.so.1",
                    "-Wl,--whole-archive",
                    uuid_archive,
                    "-Wl,--no-whole-archive",
                    "-o",
                    uuid_runtime_library,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if uuid_link.returncode != 0 or not os.path.isfile(
                uuid_runtime_library
            ):
                raise RuntimeError(
                    "failed to materialize libuuid.so.1: "
                    + json.dumps(
                        {
                            "rc": uuid_link.returncode,
                            "stdout": uuid_link.stdout.decode(
                                "utf-8", errors="replace"
                            ),
                            "stderr": uuid_link.stderr.decode(
                                "utf-8", errors="replace"
                            ),
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                )
            os.chmod(uuid_runtime_library, 0o755)
            previous_library_path = os.environ.get("LD_LIBRARY_PATH")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                [uuid_runtime_dir]
                + ([previous_library_path] if previous_library_path else [])
            )
            uuid_probe_source = os.path.join(
                uuid_runtime_dir, "uuid-runtime-probe.c"
            )
            uuid_probe_binary = os.path.join(
                uuid_runtime_dir, "uuid-runtime-probe"
            )
            with open(
                uuid_probe_source, "w", encoding="utf-8", newline="\n"
            ) as stream:
                stream.write(
                    "#include <stddef.h>\n"
                    "#include <stdio.h>\n"
                    "extern void uuid_generate(unsigned char *);\n"
                    "extern int uuid_generate_time_safe(unsigned char *);\n"
                    "int main(void) {\n"
                    "  unsigned char value[16] = {0};\n"
                    "  int nonzero = 0;\n"
                    "  size_t i;\n"
                    "  uuid_generate(value);\n"
                    "  for (i = 0; i != sizeof(value); ++i) nonzero |= value[i];\n"
                    "  if (!nonzero || (value[8] & 0xc0) != 0x80) return 2;\n"
                    "  if ((value[6] >> 4) != 4) {\n"
                    "    if (uuid_generate_time_safe(value) == -1) return 3;\n"
                    "    if ((value[8] & 0xc0) != 0x80) return 4;\n"
                    "  }\n"
                    '  if (puts("HMBS_UUID_RUNTIME_PROBE=pass") < 0) return 5;\n'
                    "  return 0;\n"
                    "}\n"
                )
            uuid_probe_link = subprocess.run(
                [
                    cc,
                    uuid_probe_source,
                    uuid_runtime_library,
                    "-o",
                    uuid_probe_binary,
                ],
                cwd=uuid_runtime_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if uuid_probe_link.returncode != 0 or not os.path.isfile(
                uuid_probe_binary
            ):
                raise RuntimeError(
                    "failed to link libuuid.so.1 target runtime probe: "
                    + json.dumps(
                        {
                            "rc": uuid_probe_link.returncode,
                            "stdout": uuid_probe_link.stdout.decode(
                                "utf-8", errors="replace"
                            ),
                            "stderr": uuid_probe_link.stderr.decode(
                                "utf-8", errors="replace"
                            ),
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                )
            os.chmod(uuid_probe_binary, 0o755)
            uuid_probe = subprocess.run(
                [uuid_probe_binary],
                cwd=uuid_runtime_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if (
                uuid_probe.returncode != 0
                or uuid_probe.stdout.strip() != b"HMBS_UUID_RUNTIME_PROBE=pass"
            ):
                raise RuntimeError(
                    "libuuid.so.1 target SONAME/ABI probe failed: "
                    + json.dumps(
                        {
                            "rc": uuid_probe.returncode,
                            "stdout": uuid_probe.stdout.decode(
                                "utf-8", errors="replace"
                            ),
                            "stderr": uuid_probe.stderr.decode(
                                "utf-8", errors="replace"
                            ),
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                )
            print(f"HMBS_UUID_RUNTIME={uuid_runtime_library}")
            print(uuid_probe.stdout.decode("utf-8"), end="")
        quote = shlex.quote
        args = (
            f"-f bootstrap.gmake -j1 CXX={quote(cxx)} "
            f"libbutl={quote(work_libbutl)} "
            "host=aarch64-unknown-linux-musl chost=aarch64-unknown-linux-musl"
        )
        try:
            self.run(f"{quote(make)} {args}", cwd=source_root)

            phase1_binary = os.path.join(source_root, "b", "b-boot")
            if not os.path.isfile(phase1_binary):
                raise RuntimeError("build2 bootstrap did not produce b/b-boot")
            self.run(f"{quote(phase1_binary)} --version", cwd=source_root)

            # Build the documented Phase 2 driver. The resulting b/b is the
            # runner required by the official tests/ testscript suite.
            phase2_args = (
                f"-V config.cxx={quote(cxx)} config.bin.lib=static "
                f"config.import.libbutl={quote(work_libbutl)} b/exe{{b}}"
            )
            # OHOS clang wrappers inject link/sign flags even for bare -v,
            # making that probe fail with missing main. An explicit id enables
            # build2's documented --version fallback; real builds still run.
            compiler_identity_args = (
                ["config.c=" + cc, "config.c.id=clang", "config.cxx.id=clang"]
                if str(self.settings.os) == "OHOS" and str(self.settings.compiler) == "clang"
                else []
            )
            phase2_args += " " + " ".join(quote(arg) for arg in compiler_identity_args)
            bin_tool_args = []
            if str(self.settings.os) == "OHOS":
                configured_ar = executables.get("ar") if isinstance(executables, dict) else None
                ar = configured_ar or shutil.which("llvm-ar") or shutil.which("ar")
                if not ar or not os.path.isfile(ar):
                    raise RuntimeError("build2 requires a real native archive tool")
                bin_tool_args.append("config.bin.ar=" + ar)
                phase2_args += " " + " ".join(quote(arg) for arg in bin_tool_args)
            self.run(f"{quote(phase1_binary)} {phase2_args}", cwd=source_root)
            tested_binary = os.path.join(source_root, "b", "b")
            if not os.path.isfile(tested_binary):
                raise RuntimeError("build2 Phase 2 did not produce b/b")
            self.run(f"{quote(tested_binary)} --version", cwd=source_root)

            # libbutl changes a child process cwd without synchronizing PWD.
            # Bash then diagnoses getcwd() before reading a script on some
            # OHOS data roots. Keep the tests byte-identical and interpose only
            # Bash startup: /system/bin/sh reads the real cwd through /proc,
            # exports a matching PWD, and preserves the original argv and cwd.
            real_bash = shutil.which("bash")
            if not real_bash:
                raise RuntimeError("build2 upstream tests require Bash")
            real_cat = shutil.which("cat")
            if not real_cat:
                raise RuntimeError("build2 upstream tests require cat")
            test_source_root = source_root
            test_libbutl = work_libbutl
            test_shell = real_bash
            if str(self.settings.os) == "OHOS":
                system_shell = "/system/bin/sh"
                readlink = shutil.which("readlink")
                if not os.path.isfile(system_shell) or not readlink:
                    raise RuntimeError(
                        "build2 upstream tests require /system/bin/sh and readlink on OHOS"
                    )

                wrapper_dir = os.path.join(work_root, "stable-bash")
                os.makedirs(wrapper_dir)
                bash_wrapper = os.path.join(wrapper_dir, "bash")
                with open(bash_wrapper, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(
                        "#!/system/bin/sh\n"
                        "set -eu\n"
                        f"cwd=$({quote(readlink)} /proc/self/cwd) || exit 125\n"
                        "case $cwd in\n"
                        "  /*) ;;\n"
                        "  *) exit 125 ;;\n"
                        "esac\n"
                        "PWD=$cwd\n"
                        "export PWD\n"
                        f"exec {quote(real_bash)} \"$@\"\n"
                    )
                os.chmod(bash_wrapper, 0o755)

                # OHOS cat lacks GNU --squeeze-blank, which is exercised by
                # the unchanged upstream process.run() tests. Compile a
                # task-private target helper for that option and delegate all
                # ordinary invocations to the real platform cat.
                cat_source = os.path.join(wrapper_dir, "cat-squeeze.c")
                cat_wrapper = os.path.join(wrapper_dir, "cat")
                with open(cat_source, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(
                        "#include <stdio.h>\n"
                        "#include <string.h>\n"
                        "#include <unistd.h>\n"
                        f"#define HMBS_REAL_CAT {json.dumps(real_cat)}\n"
                        "static int copy_squeezed(FILE *input, const char *name, "
                        "int *line_start, int *blank_seen) {\n"
                        "  int value;\n"
                        "  while ((value = fgetc(input)) != EOF) {\n"
                        "    if (value == '\\n') {\n"
                        "      if (*line_start) {\n"
                        "        if (*blank_seen) continue;\n"
                        "        *blank_seen = 1;\n"
                        "      } else {\n"
                        "        *line_start = 1;\n"
                        "        *blank_seen = 0;\n"
                        "      }\n"
                        "    } else {\n"
                        "      *line_start = 0;\n"
                        "      *blank_seen = 0;\n"
                        "    }\n"
                        "    if (fputc(value, stdout) == EOF) {\n"
                        "      fprintf(stderr, \"cat: unable to write stdout\\n\");\n"
                        "      return 1;\n"
                        "    }\n"
                        "  }\n"
                        "  if (ferror(input)) {\n"
                        "    fprintf(stderr, \"cat: unable to read %s\\n\", name);\n"
                        "    return 1;\n"
                        "  }\n"
                        "  return 0;\n"
                        "}\n"
                        "int main(int argc, char **argv) {\n"
                        "  int squeeze = 0;\n"
                        "  int end_options = 0;\n"
                        "  int inputs = 0;\n"
                        "  int status = 0;\n"
                        "  int line_start = 1;\n"
                        "  int blank_seen = 0;\n"
                        "  int i;\n"
                        "  for (i = 1; i < argc; ++i) {\n"
                        "    if (!end_options && strcmp(argv[i], \"--\") == 0) {\n"
                        "      end_options = 1;\n"
                        "      continue;\n"
                        "    }\n"
                        "    if (!end_options && (strcmp(argv[i], \"-s\") == 0 ||\n"
                        "                         strcmp(argv[i], \"--squeeze-blank\") == 0)) {\n"
                        "      squeeze = 1;\n"
                        "      continue;\n"
                        "    }\n"
                        "    if (!end_options && argv[i][0] == '-' && argv[i][1] != '\\0') {\n"
                        "      fprintf(stderr, \"cat: unsupported combined option: %s\\n\", argv[i]);\n"
                        "      return 2;\n"
                        "    }\n"
                        "  }\n"
                        "  if (!squeeze) {\n"
                        "    execv(HMBS_REAL_CAT, argv);\n"
                        "    fprintf(stderr, \"cat: unable to execute platform cat\\n\");\n"
                        "    return 127;\n"
                        "  }\n"
                        "  end_options = 0;\n"
                        "  for (i = 1; i < argc; ++i) {\n"
                        "    FILE *input;\n"
                        "    if (!end_options && strcmp(argv[i], \"--\") == 0) {\n"
                        "      end_options = 1;\n"
                        "      continue;\n"
                        "    }\n"
                        "    if (!end_options && (strcmp(argv[i], \"-s\") == 0 ||\n"
                        "                         strcmp(argv[i], \"--squeeze-blank\") == 0))\n"
                        "      continue;\n"
                        "    ++inputs;\n"
                        "    input = strcmp(argv[i], \"-\") == 0 ? stdin : fopen(argv[i], \"rb\");\n"
                        "    if (input == NULL) {\n"
                        "      fprintf(stderr, \"cat: unable to open %s\\n\", argv[i]);\n"
                        "      status = 1;\n"
                        "      continue;\n"
                        "    }\n"
                        "    if (copy_squeezed(input, argv[i], &line_start, &blank_seen) != 0)\n"
                        "      status = 1;\n"
                        "    if (input != stdin && fclose(input) != 0) status = 1;\n"
                        "  }\n"
                        "  if (inputs == 0 && copy_squeezed(stdin, \"stdin\", "
                        "&line_start, &blank_seen) != 0)\n"
                        "    status = 1;\n"
                        "  if (fflush(stdout) == EOF) status = 1;\n"
                        "  return status;\n"
                        "}\n"
                    )
                cat_compile = subprocess.run(
                    [cc, "-std=c99", "-O2", cat_source, "-o", cat_wrapper],
                    cwd=wrapper_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if cat_compile.returncode != 0 or not os.path.isfile(cat_wrapper):
                    raise RuntimeError(
                        "failed to compile target cat --squeeze-blank helper: "
                        + json.dumps(
                            {
                                "rc": cat_compile.returncode,
                                "stdout": cat_compile.stdout.decode(
                                    "utf-8", errors="replace"
                                ),
                                "stderr": cat_compile.stderr.decode(
                                    "utf-8", errors="replace"
                                ),
                            },
                            ensure_ascii=True,
                            sort_keys=True,
                        )
                    )
                os.chmod(cat_wrapper, 0o755)
                os.environ["PATH"] = os.pathsep.join(
                    [wrapper_dir, os.environ.get("PATH", "")]
                )
                if shutil.which("bash") != bash_wrapper:
                    raise RuntimeError("stable Bash wrapper is not first in PATH")
                if shutil.which("cat") != cat_wrapper:
                    raise RuntimeError("compatible cat wrapper is not first in PATH")
                cat_probe_input = b"a\n\n\nb\n"
                cat_probe = subprocess.run(
                    [cat_wrapper, "--squeeze-blank"],
                    input=cat_probe_input,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                cat_passthrough_probe = subprocess.run(
                    [cat_wrapper],
                    input=b"plain\n",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if (
                    cat_probe.returncode != 0
                    or cat_probe.stdout != b"a\n\nb\n"
                    or cat_probe.stderr
                    or cat_passthrough_probe.returncode != 0
                    or cat_passthrough_probe.stdout != b"plain\n"
                    or cat_passthrough_probe.stderr
                ):
                    raise RuntimeError(
                        "target cat --squeeze-blank helper probe failed: "
                        + json.dumps(
                            {
                                "squeeze_rc": cat_probe.returncode,
                                "squeeze_stdout": cat_probe.stdout.decode(
                                    "utf-8", errors="replace"
                                ),
                                "squeeze_stderr": cat_probe.stderr.decode(
                                    "utf-8", errors="replace"
                                ),
                                "passthrough_rc": cat_passthrough_probe.returncode,
                                "passthrough_stdout": cat_passthrough_probe.stdout.decode(
                                    "utf-8", errors="replace"
                                ),
                                "passthrough_stderr": cat_passthrough_probe.stderr.decode(
                                    "utf-8", errors="replace"
                                ),
                            },
                            ensure_ascii=True,
                            sort_keys=True,
                        )
                    )
                print(f"HMBS_TEST_CAT={cat_wrapper}")
                print("HMBS_CAT_SQUEEZE_PROBE=pass")
                test_shell = bash_wrapper

            cwd_probe = subprocess.run(
                [test_shell, "-c", "pwd -P"],
                cwd=test_source_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            expected_cwd = os.path.realpath(test_source_root)
            actual_cwd = cwd_probe.stdout.decode(
                "utf-8", errors="replace"
            ).strip()
            if (
                cwd_probe.returncode != 0
                or cwd_probe.stderr
                or actual_cwd != expected_cwd
            ):
                raise RuntimeError(
                    "build2 stable Bash cwd probe failed: "
                    + json.dumps(
                        {
                            "rc": cwd_probe.returncode,
                            "expected": expected_cwd,
                            "actual": actual_cwd,
                            "stderr": cwd_probe.stderr.decode(
                                "utf-8", errors="replace"
                            ),
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                )
            print(f"HMBS_TEST_ROOT={test_source_root}")
            print(f"HMBS_TEST_BASH={test_shell}")

            # The libbutl release tarball carries optional dependency tests as
            # dangling ODB symlinks. They are outside build2's upstream suite
            # and make the recursive test operation fail rule matching before
            # any build2 testscript runs. Remove only that vendored test tree
            # from the task-private copy; the libbutl library and all 51
            # build2 tests remain unchanged.
            dependency_tests = os.path.join(test_libbutl, "tests")
            if os.path.isdir(dependency_tests):
                shutil.rmtree(dependency_tests)

            # Execute the complete official suite through build2's own test
            # runner. The root-level entry is the upstream invocation: it
            # resolves testscript targets and their common harness files using
            # each directory's buildfile. Passing raw *.testscript paths makes
            # build2 search for file{...} targets and is not equivalent.
            # Both *.testscript and extensionless testscript are official
            # entry points. The latter include Bash, filesystem and recipe
            # tests and must not disappear from inventory accounting.
            test_scripts = sorted(set(glob.glob(
                os.path.join(test_source_root, "tests", "**", "*.testscript"),
                recursive=True,
            ) + glob.glob(
                os.path.join(test_source_root, "tests", "**", "testscript"),
                recursive=True,
            )))
            discovered = len(test_scripts)
            if discovered != 89:
                raise RuntimeError(
                    f"unexpected build2 upstream input inventory: expected 89, found {discovered}"
                )

            def sha256_file(path):
                digest = hashlib.sha256()
                with open(path, "rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                return digest.hexdigest()

            test_script_hashes = {
                os.path.relpath(path, test_source_root).replace(os.sep, "/"):
                sha256_file(path)
                for path in test_scripts
            }

            test_log = os.path.join(self.build_folder, "build2-upstream-tests.log")
            # Four common.testscript files are official harness inputs listed
            # in the source inventory and consumed by the runnable targets via
            # the directory buildfiles. Keep them in the denominator instead
            # of silently dropping them from the upstream file count.
            support_scripts = [
                os.path.relpath(path, test_source_root).replace(os.sep, "/")
                for path in test_scripts
                if os.path.basename(path) == "common.testscript"
            ]
            if len(support_scripts) != 4:
                raise RuntimeError(
                    "unexpected build2 common.testscript harness inventory: "
                    f"expected 4, found {len(support_scripts)}"
                )

            with open(test_log, "wb") as stream:
                result = subprocess.run(
                    [
                        tested_binary,
                        f"config.cxx={cxx}",
                        *compiler_identity_args,
                        *bin_tool_args,
                        "config.bin.lib=static",
                        "-s",
                        "test",
                    ],
                    cwd=test_source_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                output = result.stdout or b""
                stream.write(output)
                print(output.decode("utf-8", errors="replace"), end="")

            output_text = output.decode("utf-8", errors="replace")
            final_test_script_hashes = {
                os.path.relpath(path, test_source_root).replace(os.sep, "/"):
                sha256_file(path)
                for path in test_scripts
            }
            if final_test_script_hashes != test_script_hashes:
                raise RuntimeError(
                    "build2 upstream testscript bytes changed during execution"
                )
            runnable_scripts = [
                path for path in test_scripts if path not in {
                    os.path.join(test_source_root, rel.replace("/", os.sep))
                    for rel in support_scripts
                }
            ]
            missing_targets = []
            for path in runnable_scripts:
                rel = os.path.relpath(path, test_source_root).replace(os.sep, "/")
                parent, filename = rel.rsplit("/", 1)
                stem = filename if filename == "testscript" else filename[: -len(".testscript")]
                marker = f"{parent}/testscript{{{stem}}}"
                if marker not in output_text:
                    missing_targets.append(rel)

            if result.returncode != 0 or missing_targets:
                print(
                    "HMBS_UPSTREAM_TEST_RESULT="
                    + json.dumps(
                        {
                            "status": "failed",
                            "discovered": discovered,
                            "runnable": len(runnable_scripts),
                            "support": len(support_scripts),
                            "missing_targets": missing_targets,
                            "execution_accounting": "unavailable_after_nonzero_runner",
                            "command": f"b/b config.cxx={cxx} config.bin.lib=static -s test",
                            "log": test_log,
                            "rc": result.returncode,
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                )
                raise RuntimeError(
                    f"build2 upstream tests failed with exit code {result.returncode}"
                )

            print(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(
                    {
                        "status": "passed",
                        "discovered": discovered,
                        "executed": len(runnable_scripts),
                        "passed": len(runnable_scripts),
                        "failed": 0,
                        "runnable": len(runnable_scripts),
                        "support": len(support_scripts),
                        "skipped": 0,
                        "command": f"b/b config.cxx={cxx} config.bin.lib=static -s test",
                        "log": test_log,
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            )
            print(f"UPSTREAM_TEST_PASS={len(runnable_scripts)}/{len(runnable_scripts)}; "
                  f"INPUT_FILES={discovered}; SUPPORT_FILES={len(support_scripts)}; NO_SKIPS")

            staged_binary = os.path.join(self.build_folder, "build2-tested")
            shutil.copy2(tested_binary, staged_binary)
            self._tested_binary = staged_binary
            self._upstream_test_log = test_log
            if uuid_runtime_library:
                staged_uuid = os.path.join(
                    self.build_folder, "libuuid.so.1"
                )
                shutil.copy2(uuid_runtime_library, staged_uuid)
                self._uuid_runtime_library = staged_uuid
        finally:
            if work_root and os.path.isdir(work_root):
                shutil.rmtree(work_root, ignore_errors=True)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        binary = getattr(
            self,
            "_tested_binary",
            os.path.join(self.source_folder, "b", "b-boot"),
        )
        for name in ("build2", "b"):
            shutil.copy2(binary, os.path.join(bindir, name))
        uuid_runtime_library = getattr(self, "_uuid_runtime_library", None)
        if uuid_runtime_library:
            libdir = os.path.join(self.package_folder, "lib")
            os.makedirs(libdir, exist_ok=True)
            shutil.copy2(
                uuid_runtime_library, os.path.join(libdir, "libuuid.so.1")
            )
            uuid_licenses = os.path.join(
                self.dependencies["uuid"].package_folder, "licenses"
            )
            if os.path.isdir(uuid_licenses):
                shutil.copytree(
                    uuid_licenses,
                    os.path.join(self.package_folder, "licenses", "uuid"),
                )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        package_bin = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", package_bin)
        self.buildenv_info.prepend_path("PATH", package_bin)
        uuid_runtime = os.path.join(self.package_folder, "lib", "libuuid.so.1")
        if os.path.isfile(uuid_runtime):
            self.cpp_info.libdirs = ["lib"]
            package_lib = os.path.join(self.package_folder, "lib")
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", package_lib)
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", package_lib)
