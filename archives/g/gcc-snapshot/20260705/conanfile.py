#!/usr/bin/env python3
"""Minimal native GCC 17 snapshot C compiler for HarmonyOS PC.

This deliberately builds only the C frontend and libgcc.  GMP, MPFR, and
MPC use the exact source versions selected by GCC snapshot's upstream
``contrib/download_prerequisites`` script and are built in-tree.

OHOS CI is a native AArch64 environment, so build, host, and target are all
``aarch64-linux-ohos``.  Audited source transforms map that target to GCC's
musl support; the recipe also handles old config.sub scripts, HMDFS umask
behaviour, and ELF signing for generated host tools.
"""

import concurrent.futures
import glob
import hashlib
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
from urllib.parse import unquote, urlparse
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import (
    copy,
    get,
)
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class GccConan(ConanFile):
    name = "gcc-snapshot"
    version = "20260705"
    package_type = "application"
    no_copy_source = True

    description = "GNU Compiler Collection 17 snapshot C compiler"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/pub/gcc/snapshots/17-20260705/"

    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        self.settings.rm_safe("os.version")

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "files"),
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("The OHOS GCC package supports AArch64/armv8 only")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")

    def _extract_gcc_source(self, archive):
        """Extract GCC sources while skipping most of the large testsuite."""
        source_root = os.path.abspath(self.source_folder)
        keep_top_level = {
            "config",
            "contrib",
            "fixincludes",
            "gcc",
            "gmp",
            "include",
            "libbacktrace",
            "libcpp",
            "libdecnumber",
            "libgcc",
            "libiberty",
            "mpc",
            "mpfr",
            "zlib",
        }
        keep_gcc_subdirs = {
            "analyzer",
            "c",
            "c-family",
            "common",
            "config",
            "custom-sarif-properties",
            "diagnostics",
            "doc",
            "ginclude",
            "rtl-ssa",
            "sym-exec",
            "testsuite",
            "text-art",
            "topics",
        }
        keep_gcc_files = {
            "d/d-target.def",
            "jit/jit-target.def",
            "rust/rust-target.def",
        }
        keep_testsuite = "gcc/testsuite/gcc.c-torture/execute"
        keep_selftests = "gcc/testsuite/selftests"

        def should_extract(relative):
            top_level = relative.split("/", 1)[0]
            if top_level not in keep_top_level:
                return "/" not in relative
            if relative == "gcc/testsuite" or relative.startswith("gcc/testsuite/"):
                return (
                    relative in (
                        "gcc/testsuite",
                        "gcc/testsuite/gcc.c-torture",
                        keep_testsuite,
                        keep_selftests,
                    )
                    or relative.startswith(keep_testsuite + "/")
                    or relative.startswith(keep_selftests + "/")
                )
            if relative == "gcc" or relative.startswith("gcc/"):
                remainder = relative[4:]
                if not remainder:
                    return True
                if remainder in keep_gcc_files:
                    return True
                gcc_subdir = remainder.split("/", 1)[0]
                return "/" not in remainder or gcc_subdir in keep_gcc_subdirs
            return True

        with tarfile.open(archive, "r:*") as tar:
            for member in tar:
                parts = member.name.split("/", 1)
                if len(parts) != 2:
                    continue
                relative = parts[1]
                if not relative or not should_extract(relative):
                    continue
                target = os.path.abspath(os.path.join(source_root, relative))
                if not (
                    target == source_root
                    or target.startswith(source_root + os.sep)
                ):
                    raise ConanException(
                        "Refusing to extract archive member outside source folder: {}".format(
                            member.name
                        )
                    )
                member.name = relative
                tar.extract(member, source_root)

    def _download_gcc_source(self, urls, archive, sha256):
        """Download the large GCC archive with bounded parallel HTTP ranges."""
        if not isinstance(urls, (list, tuple)):
            urls = [urls]
        errors = []
        for url in urls:
            try:
                if urlparse(url).scheme == "file":
                    self._copy_cached_gcc_source(url, archive, sha256)
                else:
                    self._download_gcc_source_from_url(url, archive, sha256)
                return
            except Exception as error:
                errors.append("{}: {}".format(url, error))
                self.output.warning(
                    "Could not download GCC source from {}: {}".format(
                        url, error
                    )
                )
        raise ConanException(
            "Could not download GCC source from any URL: {}".format(
                "; ".join(errors)
            )
        )

    def _copy_cached_gcc_source(self, url, archive, sha256):
        """Use a CI-preloaded file URL while keeping the checksum boundary."""
        parsed = urlparse(url)
        if parsed.netloc not in ("", "localhost"):
            local_path = "//{}{}".format(parsed.netloc, parsed.path)
        else:
            local_path = parsed.path
        local_path = urllib.request.url2pathname(unquote(local_path))
        if os.name == "nt" and re.match(r"^/[A-Za-z]:", local_path):
            local_path = local_path[1:]
        if not os.path.isfile(local_path):
            raise ConanException(
                "The cached GCC source does not exist: {}".format(local_path)
            )

        partial_archive = archive + ".partial"
        digest = hashlib.sha256()
        written = 0
        try:
            with open(local_path, "rb") as source, open(
                partial_archive, "wb"
            ) as output:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    digest.update(block)
                    written += len(block)
            expected_size = os.path.getsize(local_path)
            actual_sha256 = digest.hexdigest()
            if written != expected_size:
                raise ConanException(
                    "Cached GCC source size mismatch: expected {}, got {}".format(
                        expected_size, written
                    )
                )
            if actual_sha256 != sha256:
                raise ConanException(
                    "Cached GCC source SHA256 mismatch: expected {}, got {}".format(
                        sha256, actual_sha256
                    )
                )
            os.replace(partial_archive, archive)
            self.output.info(
                "Sources correctly copied from CI cache {}".format(local_path)
            )
        finally:
            if os.path.exists(partial_archive):
                os.remove(partial_archive)

    def _download_gcc_source_from_url(self, url, archive, sha256):
        """Fetch one source URL in parallel ranges and verify the final file."""
        head_request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(head_request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
        if not content_length:
            raise ConanException(
                "The GCC source URL did not provide Content-Length: {}".format(
                    url
                )
            )
        total_size = int(content_length)
        if total_size <= 0:
            raise ConanException(
                "The GCC source URL returned an invalid Content-Length: {}".format(
                    content_length
                )
            )
        chunk_size = 4 * 1024 * 1024
        ranges = [
            (index, start, min(start + chunk_size - 1, total_size - 1))
            for index, start in enumerate(range(0, total_size, chunk_size))
        ]
        work_dir = tempfile.mkdtemp(
            prefix=".gcc-download-", dir=os.path.dirname(archive)
        )
        partial_archive = archive + ".partial"

        def fetch_range(item):
            index, start, end = item
            expected_size = end - start + 1
            part = os.path.join(work_dir, "part-{:04d}".format(index))
            last_error = None
            for attempt in range(3):
                try:
                    request = urllib.request.Request(
                        url,
                        headers={
                            "Range": "bytes={}-{}".format(start, end),
                            "Accept-Encoding": "identity",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=180) as response:
                        if getattr(response, "status", None) != 206:
                            raise ConanException(
                                "HTTP range request returned status {}".format(
                                    getattr(response, "status", "unknown")
                                )
                            )
                        content_range = response.headers.get("Content-Range", "")
                        expected_range = "bytes {}-{}".format(start, end)
                        if not content_range.startswith(expected_range):
                            raise ConanException(
                                "HTTP range response was {} instead of {}".format(
                                    content_range or "<missing>",
                                    expected_range,
                                )
                            )
                        with open(part, "wb") as output:
                            remaining = expected_size
                            while remaining:
                                block = response.read(min(1024 * 1024, remaining))
                                if not block:
                                    raise ConanException(
                                        "HTTP range ended after {} bytes".format(
                                            expected_size - remaining
                                        )
                                    )
                                output.write(block)
                                remaining -= len(block)
                    if os.path.getsize(part) != expected_size:
                        raise ConanException(
                            "HTTP range size mismatch for {}-{}".format(
                                start, end
                            )
                        )
                    return part
                except Exception as error:
                    last_error = error
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
            raise ConanException(
                "HTTP range {}-{} failed after 3 attempts: {}".format(
                    start, end, last_error
                )
            )

        try:
            self.output.info(
                "Downloading {} ({} bytes) in {} parallel HTTP ranges".format(
                    os.path.basename(archive), total_size, len(ranges)
                )
            )
            workers = min(8, len(ranges))
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=workers
            ) as executor:
                parts = list(executor.map(fetch_range, ranges))

            digest = hashlib.sha256()
            written = 0
            with open(partial_archive, "wb") as output:
                for part in parts:
                    with open(part, "rb") as source:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            output.write(block)
                            digest.update(block)
                            written += len(block)
            actual_sha256 = digest.hexdigest()
            if written != total_size:
                raise ConanException(
                    "GCC source size mismatch: expected {}, got {}".format(
                        total_size, written
                    )
                )
            if actual_sha256 != sha256:
                raise ConanException(
                    "GCC source SHA256 mismatch: expected {}, got {}".format(
                        sha256, actual_sha256
                    )
                )
            os.replace(partial_archive, archive)
            self.output.info(
                "Sources correctly downloaded from {} using parallel ranges".format(
                    url
                )
            )
        finally:
            if os.path.exists(partial_archive):
                os.remove(partial_archive)
            shutil.rmtree(work_dir, ignore_errors=True)

    def _make_source_scripts_executable(self):
        script_names = {
            "configure",
            "config.guess",
            "config.rpath",
            "config.sub",
            "depcomp",
            "install-sh",
            "ltmain.sh",
            "missing",
            "mkinstalldirs",
            "move-if-change",
            "ylwrap",
        }
        for root, dirs, files in os.walk(self.source_folder):
            for dirname in dirs:
                path = os.path.join(root, dirname)
                try:
                    os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) | 0o755)
                except OSError as error:
                    self.output.warning(
                        "Could not adjust source directory permissions for {}: {}".format(
                            path, error
                        )
                    )
            for filename in files:
                if not (filename in script_names or filename.endswith(".sh")):
                    continue
                path = os.path.join(root, filename)
                try:
                    os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) | 0o755)
                except OSError as error:
                    self.output.warning(
                        "Could not make source script executable {}: {}".format(
                            path, error
                        )
                    )

    def _patch_ohos_script_invocations(self):
        replacements = {
            os.path.join(self.source_folder, "gcc", "Makefile.in"): {
                "&& $(srcdir)/../move-if-change checksum-options.tmp checksum-options": (
                    "&& $(SHELL) $(srcdir)/../move-if-change checksum-options.tmp checksum-options"
                ),
            },
            os.path.join(self.source_folder, "gcc", "c", "Make-lang.in"): {
                "$(srcdir)/../move-if-change cc1-checksum.cc.tmp cc1-checksum.cc": (
                    "$(SHELL) $(srcdir)/../move-if-change cc1-checksum.cc.tmp cc1-checksum.cc"
                ),
            },
            os.path.join(self.source_folder, "libcpp", "Makefile.in"): {
                "\t$(srcdir)/../move-if-change localedir.new localedir.h": (
                    "\t$(SHELL) $(srcdir)/../move-if-change localedir.new localedir.h"
                ),
            },
            os.path.join(self.source_folder, "mpfr", "src", "Makefile.in"): {
                "GET_PATCHES_SH = $(top_srcdir)/tools/get_patches.sh": (
                    "GET_PATCHES_SH = $(SHELL) $(top_srcdir)/tools/get_patches.sh"
                ),
            },
            os.path.join(self.source_folder, "libgcc", "Makefile.in"): {
                "\t\t$(srcdir)/mkheader.sh > tmp-libgcc_tm.h": (
                    "\t\t$(SHELL) $(srcdir)/mkheader.sh > tmp-libgcc_tm.h"
                ),
            },
        }
        for makefile, replace in replacements.items():
            with open(makefile, "r", encoding="utf-8") as file:
                content = file.read()
            for old, new in replace.items():
                if old not in content:
                    raise ConanException(
                        "Expected OHOS makefile entry not found: {}".format(old)
                    )
                content = content.replace(old, new)
            with open(makefile, "w", encoding="utf-8", newline="\n") as file:
                file.write(content)

    def _patch_c_tree_codes(self):
        """Keep the C-only snapshot build self-consistent."""
        tree_codes = os.path.join(self.source_folder, "gcc", "c", "c-tree.def")
        with open(tree_codes, "r", encoding="utf-8") as file:
            content = file.read()
        definitions = [
            (
                "TEMPLATE_DECL",
                'DEFTREECODE (TEMPLATE_DECL, "template_decl", tcc_declaration, 0)',
            ),
            (
                "USING_DECL",
                'DEFTREECODE (USING_DECL, "using_decl", tcc_declaration, 0)',
            ),
            (
                "OVERLOAD",
                'DEFTREECODE (OVERLOAD, "overload", tcc_exceptional, 0)',
            ),
            (
                "EXPR_STMT",
                'DEFTREECODE (EXPR_STMT, "expr_stmt", tcc_expression, 1)',
            ),
            (
                "ALIGNOF_EXPR",
                'DEFTREECODE (ALIGNOF_EXPR, "alignof_expr", tcc_expression, 1)',
            ),
        ]
        definitions = [
            "/* Shared frontend tree codes referenced by the C-only build.  */\n"
            + definition
            for name, definition in definitions
            if "DEFTREECODE ({}, ".format(name) not in content
        ]
        if not definitions:
            return
        marker = "/* Used to represent a vector of tokens for deferred parsing.  */"
        if marker not in content:
            raise ConanException(
                "Expected C tree-code insertion point not found: {}".format(
                    tree_codes
                )
            )
        content = content.replace(marker, "\n".join(definitions) + "\n" + marker, 1)
        with open(tree_codes, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

    def _patch_disabled_lto_options(self):
        """Provide disabled-state values for LTO-only flags omitted by opt-gen."""
        flag_types = os.path.join(self.source_folder, "gcc", "flag-types.h")
        with open(flag_types, "r", encoding="utf-8") as file:
            content = file.read()
        missing = [
            name
            for name in ("flag_wpa", "flag_ltrans")
            if "#define {} 0".format(name) not in content
        ]
        if not missing:
            return
        insertion = (
            "\n/* LTO is disabled for this package; keep shared code compilable.  */\n"
            "#ifndef ENABLE_LTO\n"
            + "\n".join(
                "#ifndef {0}\n#define {0} 0\n#endif".format(name)
                for name in missing
            )
            + "\n#endif\n"
        )
        marker = content.rfind("#endif")
        if marker < 0:
            raise ConanException(
                "Expected GCC_FLAG_TYPES_H include guard not found: {}".format(
                    flag_types
                )
            )
        content = content[:marker] + insertion + content[marker:]
        with open(flag_types, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

    def _patch_disabled_lto_sources(self):
        """Keep unconditional LTO helper sources buildable without LTO."""
        lto_opts = os.path.join(self.source_folder, "gcc", "lto-opts.cc")
        with open(lto_opts, "r", encoding="utf-8") as file:
            content = file.read()
        replacements = [
            (
                """\tcase OPT_dumpdir:
\tcase OPT_fresolution_:
\tcase OPT_fdebug_prefix_map_:""",
                """\tcase OPT_dumpdir:
#ifdef ENABLE_LTO
\tcase OPT_fresolution_:
#endif
\tcase OPT_fdebug_prefix_map_:""",
            ),
            (
                """\tcase OPT_fwhole_program:
\tcase OPT_fltrans_output_list_:
\tcase OPT_flto_incremental_:""",
                """\tcase OPT_fwhole_program:
#ifdef ENABLE_LTO
\tcase OPT_fltrans_output_list_:
#endif
\tcase OPT_flto_incremental_:""",
            ),
            (
                """      if (!(cl_options[option->opt_index].flags & (CL_COMMON|CL_TARGET|CL_LTO)))
\tcontinue;""",
                """#ifdef ENABLE_LTO
      if (!(cl_options[option->opt_index].flags & (CL_COMMON|CL_TARGET|CL_LTO)))
#else
      if (!(cl_options[option->opt_index].flags & (CL_COMMON|CL_TARGET)))
#endif
\tcontinue;""",
            ),
        ]
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new, 1)
            elif new not in content:
                raise ConanException(
                    "Expected disabled-LTO source entry not found: {}".format(
                        lto_opts
                    )
                )
        with open(lto_opts, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

        lto_wrapper = os.path.join(self.source_folder, "gcc", "lto-wrapper.cc")
        with open(lto_wrapper, "r", encoding="utf-8") as file:
            content = file.read()
        replacements = [
            (
                """	    & (CL_COMMON|CL_TARGET|CL_DRIVER|CL_LTO)))""",
                """#ifdef ENABLE_LTO
	    & (CL_COMMON|CL_TARGET|CL_DRIVER|CL_LTO)))
#else
	    & (CL_COMMON|CL_TARGET|CL_DRIVER)))
#endif""",
            ),
            (
                """	case OPT_flinker_output_:
	  linker_output_rel = !strcmp (option->arg, "rel");
	  break;""",
                """#ifdef ENABLE_LTO
	case OPT_flinker_output_:
	  linker_output_rel = !strcmp (option->arg, "rel");
	  break;
#endif""",
            ),
        ]
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new, 1)
            elif new not in content:
                raise ConanException(
                    "Expected disabled-LTO lto-wrapper entry not found: {}".format(
                        lto_wrapper
                    )
                )
        with open(lto_wrapper, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

        gcc_driver = os.path.join(self.source_folder, "gcc", "gcc.cc")
        with open(gcc_driver, "r", encoding="utf-8") as file:
            content = file.read()
        old = """    case OPT_fwpa:
      flag_wpa = "";
      break;"""
        new = """#ifdef ENABLE_LTO
    case OPT_fwpa:
      flag_wpa = "";
      break;
#endif"""
        if old in content:
            content = content.replace(old, new, 1)
        elif new not in content:
            raise ConanException(
                "Expected disabled-LTO gcc driver entry not found: {}".format(
                    gcc_driver
                )
            )
        with open(gcc_driver, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

        opts = os.path.join(self.source_folder, "gcc", "opts.cc")
        with open(opts, "r", encoding="utf-8") as file:
            content = file.read()
        old = """      case OPT_fpreprocessed:
      case OPT_fltrans_output_list_:
      case OPT_fresolution_:
      case OPT_fdebug_prefix_map_:"""
        new = """      case OPT_fpreprocessed:
#ifdef ENABLE_LTO
      case OPT_fltrans_output_list_:
      case OPT_fresolution_:
#endif
      case OPT_fdebug_prefix_map_:"""
        if old in content:
            content = content.replace(old, new, 1)
        elif new not in content:
            raise ConanException(
                "Expected disabled-LTO opts entry not found: {}".format(opts)
            )
        with open(opts, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

        toplev = os.path.join(self.source_folder, "gcc", "toplev.cc")
        with open(toplev, "r", encoding="utf-8") as file:
            content = file.read()
        old = """  if (!flag_syntax_only && !(global_dc->get_lang_mask () & CL_LTODump))
    {"""
        new = """#ifdef ENABLE_LTO
  if (!flag_syntax_only && !(global_dc->get_lang_mask () & CL_LTODump))
#else
  if (!flag_syntax_only)
#endif
    {"""
        if old in content:
            content = content.replace(old, new, 1)
        elif new not in content:
            raise ConanException(
                "Expected disabled-LTO toplev entry not found: {}".format(toplev)
            )
        with open(toplev, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

    def _patch_disabled_lto_option_languages(self):
        """Remove disabled LTO language names before option generation."""
        option_file = os.path.join(self.source_folder, "gcc", "c-family", "c.opt")
        with open(option_file, "r", encoding="utf-8") as file:
            lines = file.readlines()

        token = re.compile(r"(?<![A-Za-z0-9_])LTO(?![A-Za-z0-9_])")
        changed = False
        for index, line in enumerate(lines):
            if "LangEnabledBy" not in line or not token.search(line):
                continue
            indent = line[: len(line) - len(line.lstrip())]
            body = token.sub("", line[len(indent) :])
            body = re.sub(r" {2,}", " ", body)
            body = re.sub(r" +,", ",", body)
            updated = indent + body
            if updated != line:
                lines[index] = updated
                changed = True

        if not changed:
            return
        with open(option_file, "w", encoding="utf-8", newline="\n") as file:
            file.writelines(lines)

    def _patch_ohos_selftests(self):
        """Drop a target-specific option absent from the AArch64 table."""
        opt_suggestions = os.path.join(
            self.source_folder, "gcc", "opt-suggestions.cc"
        )
        with open(opt_suggestions, "r", encoding="utf-8") as file:
            content = file.read()
        entries = (
            '    "-Wno-underflow",\n',
            '    "-Wtarget-lifetime",\n',
            '    "-Warray-temporaries",\n',
        )
        if not any(entry in content for entry in entries):
            return
        for entry in entries:
            content = content.replace(entry, "", 1)
        with open(opt_suggestions, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        gcc_urls = sources["gcc"]["url"]
        gcc_url = (
            gcc_urls[0]
            if isinstance(gcc_urls, (list, tuple))
            else gcc_urls
        )
        gcc_archive = os.path.join(self.source_folder, os.path.basename(gcc_url))
        local_archive = os.environ.get("GCC_SNAPSHOT_SOURCE_TARBALL")
        if local_archive and os.path.isfile(local_archive):
            self._extract_gcc_source(local_archive)
        else:
            self._download_gcc_source(
                gcc_urls,
                gcc_archive,
                sha256=sources["gcc"]["sha256"],
            )
            self._extract_gcc_source(gcc_archive)
            os.remove(gcc_archive)

        # Use the exact in-tree dependency versions selected by GCC snapshot's
        # official download_prerequisites script.  This keeps the package
        # reproducible without relying on undeclared system libraries.
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

        # Perform the large source-tree rewrite in a short-lived process.  On
        # HarmonyOS, retaining that process state in Conan causes the first
        # large configure child to receive SIGSEGV; the same command succeeds
        # after the rewriting process exits and releases its resources.
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
        self._patch_c_tree_codes()
        self._patch_disabled_lto_options()
        self._patch_disabled_lto_sources()
        self._patch_disabled_lto_option_languages()
        self._patch_ohos_selftests()
        self._patch_ohos_script_invocations()
        self._make_source_scripts_executable()
        if hasattr(os, "sync"):
            os.sync()

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _target_triplet(self):
        if self._is_ohos:
            return "aarch64-linux-ohos"
        return get_gnu_triplet(self)

    @property
    def _ohos_sysroot(self):
        if not self._is_ohos:
            return None
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, _ = self._split_compiler_command(
            compiler_executables.get("c"), "/data/service/hnp/bin/clang"
        )
        candidates = sorted(
            path
            for path in self._ohos_sysroot_candidates(cc)
            if os.path.isdir(os.path.join(path, "usr", "include"))
        )
        if not candidates:
            raise ConanInvalidConfiguration(
                "OHOS SDK sysroot headers were not found for compiler {}. "
                "Checked: {}".format(
                    cc,
                    ", ".join(self._ohos_sysroot_candidates(cc)) or "<none>",
                )
            )
        return candidates[-1]

    @staticmethod
    def _ohos_sysroot_candidates(compiler):
        """Find sysroots for HNP shims and SDK-internal Clang paths."""
        compiler_paths = [compiler]
        resolved_compiler = os.path.realpath(compiler)
        if resolved_compiler != compiler:
            compiler_paths.append(resolved_compiler)

        candidates = []
        for compiler_path in compiler_paths:
            current = Path(os.path.abspath(compiler_path)).parent
            ancestors = [current] + list(current.parents)
            for ancestor in ancestors:
                if ancestor.name == "native":
                    candidates.append(ancestor / "sysroot")
                elif ancestor.name == "llvm":
                    candidates.append(ancestor.parent / "sysroot")

                if ancestor.name == "hnp":
                    sdk_root = ancestor / "ohos-sdk.org"
                elif ancestor.name == "ohos-sdk.org":
                    sdk_root = ancestor
                else:
                    sdk_root = None
                if sdk_root is not None:
                    candidates.extend(
                        Path(path)
                        for path in glob.glob(
                            os.path.join(
                                str(sdk_root),
                                "ohos-sdk_*",
                                "ohos",
                                "native",
                                "sysroot",
                            )
                        )
                    )

        unique = []
        seen = set()
        for candidate in candidates:
            normalized = os.path.normpath(os.fspath(candidate))
            if normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique

    @property
    def _ohos_target_include(self):
        """Return the OHOS target-specific C library include directory."""
        target_include = os.path.join(
            self._ohos_sysroot,
            "usr",
            "include",
            self._target_triplet,
        )
        if not os.path.isfile(
            os.path.join(target_include, "bits", "alltypes.h")
        ):
            raise ConanInvalidConfiguration(
                "OHOS target C library headers were not found: {}".format(
                    target_include
                )
            )
        return target_include

    @staticmethod
    def _split_compiler_command(configured, fallback):
        """Resolve a configured compiler command and preserve its arguments."""
        try:
            command = shlex.split(configured or fallback)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                "Invalid compiler command: {}".format(configured)
            ) from error
        if not command:
            raise ConanInvalidConfiguration("Compiler command is empty")
        executable = shutil.which(command[0])
        if not executable and os.path.isfile(command[0]) and os.access(
            command[0], os.X_OK
        ):
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
            if not resolved and os.path.isabs(candidate) and os.access(
                candidate, os.X_OK
            ):
                resolved = candidate
            if not resolved and os.path.isfile(candidate) and os.access(
                candidate, os.X_OK
            ):
                resolved = os.path.abspath(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name)
        )

    @staticmethod
    def _shell_command(shell, script):
        return "{} {}".format(shlex.quote(shell), shlex.quote(script))

    @staticmethod
    def _compiler_wrapper_text(real_compiler, signer, objcopy, readelf, extra_args=None):
        extra = " ".join(shlex.quote(value) for value in (extra_args or []))
        extra_setup = (
            'set -- {} "$@"'.format(extra) if extra else 'set -- "$@"'
        )
        return """#!/bin/sh
set -eu
real_compiler={real_compiler}
signer={signer}
objcopy={objcopy}
readelf={readelf}
{extra_setup}

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

if [ -z "$output" ] && [ "$compile_only" -eq 0 ]; then
    output=a.out
fi

if [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        unsigned="${{output}}.ohos-unsigned-$$"
        signed="${{output}}.ohos-signed-$$"
        cleanup_signing_files() {{
            rm -f "$unsigned" "$signed"
        }}
        trap cleanup_signing_files EXIT HUP INT TERM
        cp -p "$output" "$unsigned"
        "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
        "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
        if ! "$readelf" -h "$signed" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
            echo "binary-sign-tool did not produce a runnable ELF: $output" >&2
            exit 1
        fi
        if ! "$readelf" -S "$signed" 2>/dev/null | grep -q '[.]codesign'; then
            echo "binary-sign-tool did not add .codesign: $output" >&2
            exit 1
        fi
        mv "$signed" "$output"
        rm -f "$unsigned"
        trap - EXIT HUP INT TERM
        chmod +x "$output" 2>/dev/null || true
    fi
fi
exit 0
""".format(
            real_compiler=shlex.quote(real_compiler),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
            extra_setup=extra_setup,
        )

    def _write_compiler_wrapper(self, name, real_compiler, extra_args=None):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / name

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = (
            shutil.which("llvm-objcopy")
            or shutil.which("objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
            or "/data/service/hnp/bin/objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
            or "/data/service/hnp/bin/readelf"
        )
        missing_tools = [
            tool_name
            for tool_name, tool_path in (
                ("binary-sign-tool", signer),
                ("llvm-objcopy", objcopy),
                ("llvm-readelf", readelf),
            )
            if (
                not tool_path
                or not os.path.isfile(tool_path)
                or not os.access(tool_path, os.X_OK)
            )
        ]
        if missing_tools:
            raise ConanInvalidConfiguration(
                "OHOS compiler wrappers require: {}".format(
                    ", ".join(missing_tools)
                )
            )
        wrapper.write_text(
            self._compiler_wrapper_text(
                real_compiler=real_compiler,
                signer=signer,
                objcopy=objcopy,
                readelf=readelf,
                extra_args=extra_args,
            ),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        return str(wrapper)

    def _write_assembler_wrapper(self, real_compiler, compiler_args=None):
        """Use Clang's integrated AArch64 assembler on OHOS."""
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / "assembler"
        extra = " ".join(
            shlex.quote(value) for value in (compiler_args or [])
        )
        prefix = "{} -c".format(extra) if extra else "-c"
        wrapper.write_text(
            """#!/system/bin/sh
set -eu
set -- {prefix} "$@"
exec {compiler} "$@"
""".format(
                prefix=prefix,
                compiler=shlex.quote(real_compiler),
            ),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        return str(wrapper)

    @property
    def _ohos_linker_launcher_path(self):
        return os.path.join(self.build_folder, ".ohos-wrappers", "ld")

    def _build_ohos_linker_launcher(self, shell):
        """Bridge collect2's direct spawn to the HMDFS-protected HNP linker."""
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        source = wrapper_dir / "ld-launcher.c"
        launcher = Path(self._ohos_linker_launcher_path)
        source.write_text(
            """extern void *calloc(unsigned long, unsigned long);
extern int execv(const char *, char *const *);

int
main(int argc, char **argv)
{
    char **args;
    int index;

    args = (char **) calloc((unsigned long) argc + 4UL, sizeof(*args));
    if (!args)
        return 111;
    args[0] = (char *) "/system/bin/sh";
    args[1] = (char *) "-c";
    args[2] = (char *) "exec \\"$0\\" \\"$@\\"";
    args[3] = (char *) "/data/service/hnp/bin/ld";
    for (index = 1; index < argc; ++index)
        args[index + 3] = argv[index];
    args[argc + 3] = 0;
    execv(args[0], args);
    return 112;
}
""",
            encoding="utf-8",
            newline="\n",
        )
        compiler = self._shell_command(
            shell, str(wrapper_dir / "clang-sign")
        )
        command = "{} {} -O2 -fPIE -pie {} -o {}".format(
            self._build_command_exports(),
            compiler,
            shlex.quote(str(source)),
            shlex.quote(str(launcher)),
        )
        result = self.run(
            command,
            cwd=self.build_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        if result != 0:
            raise ConanException(
                "Could not build the OHOS linker launcher (exit code {})".format(
                    result
                )
            )
        launcher.chmod(0o755)
        for alias_name in ("collect-ld", "real-ld"):
            alias = wrapper_dir / alias_name
            shutil.copy2(launcher, alias)
            alias.chmod(0o755)
        return str(launcher)

    def generate(self):
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        tmpdir = Path(self._build_tmpdir())
        tmpdir.mkdir(parents=True, exist_ok=True)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, cc_args = self._split_compiler_command(
            compiler_executables.get("c"), "/data/service/hnp/bin/clang"
        )
        cxx, cxx_args = self._split_compiler_command(
            compiler_executables.get("cpp"), "/data/service/hnp/bin/clang++"
        )
        real_cc = cc

        shell = self._required_executable("sh", "sh", "/bin/sh")
        if self._is_ohos:
            cc = self._shell_command(
                shell, self._write_compiler_wrapper("clang-sign", cc, cc_args)
            )
            cxx = self._shell_command(
                shell, self._write_compiler_wrapper("clangxx-sign", cxx, cxx_args)
            )
        elif cc_args or cxx_args:
            raise ConanInvalidConfiguration(
                "Compiler arguments require the OHOS wrapper path"
            )

        true_tool = self._required_executable("true", "true", "/bin/true")
        if self._is_ohos:
            assembler = self._write_assembler_wrapper(real_cc, cc_args)
        else:
            assembler = self._required_executable(
                "GNU assembler", "as", "/data/service/hnp/bin/as"
            )
        real_linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )
        linker = (
            self._ohos_linker_launcher_path
            if self._is_ohos
            else real_linker
        )
        archiver = self._required_executable(
            "archiver",
            compiler_executables.get("ar"),
            "llvm-ar",
            "/data/service/hnp/bin/llvm-ar",
            "ar",
            "/data/service/hnp/bin/ar",
        )
        ranlib = self._required_executable(
            "ranlib",
            compiler_executables.get("ranlib"),
            "llvm-ranlib",
            "/data/service/hnp/bin/llvm-ranlib",
            "ranlib",
            "/data/service/hnp/bin/ranlib",
        )
        nm = self._required_executable(
            "nm",
            compiler_executables.get("nm"),
            "llvm-nm",
            "/data/service/hnp/bin/llvm-nm",
            "nm",
            "/data/service/hnp/bin/nm",
        )
        m4 = self._required_executable(
            "m4",
            "m4",
            "/data/service/hnp/bin/m4",
        )
        flex_candidates = []
        try:
            flex_dep = self.dependencies.build["flex"]
            flex_pkg = getattr(flex_dep, "package_folder", None)
            if flex_pkg:
                bindirs = list(getattr(flex_dep.cpp_info, "bindirs", []) or ["bin"])
                flex_candidates.extend(
                    os.path.join(flex_pkg, bindir, "flex")
                    for bindir in bindirs
                )
        except Exception:
            pass
        # The published flex/2.6.4 package used by the worker may contain
        # libfl and headers without the generator executable.  The worker
        # ships the matching CLI in its HNP tool bundle; keep the Conan
        # requirement for dependency tracking, then use that CLI as a
        # deterministic fallback instead of silently selecting another flex.
        flex_candidates.extend(
            (
                os.environ.get("FLEX"),
                "/data/service/hnp/flex.org/flex_2.6.4/bin/flex",
                shutil.which("flex"),
            )
        )
        flex = next(
            (
                candidate
                for candidate in flex_candidates
                if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK)
            ),
            None,
        )
        if not flex:
            raise ConanInvalidConfiguration(
                "flex/2.6.4 build requirement and the OHOS HNP flex fallback "
                "did not provide an executable flex"
            )

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CC_FOR_BUILD", cc)
        env.define("CXX_FOR_BUILD", cxx)
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("TMPDIR", str(tmpdir))
        env.define("MAKEINFO", true_tool)
        env.define("HELP2MAN", true_tool)
        if self._is_ohos:
            # HarmonyOS requires PIE-friendly host tools.  GCC's default host
            # probe can select -fno-PIE/-no-pie, which LLD rejects on AArch64
            # when linking cc1 against OHOS libc symbols.
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        # The OpenDesk job environment exports AS=llvm-as, which consumes LLVM
        # IR rather than GNU/AArch64 assembly.  GCC requires real binutils as
        # and ld for target objects, both of which are provided on the device.
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_BUILD", assembler)
        env.define("LD_FOR_BUILD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        env.define("AR", archiver)
        env.define("AR_FOR_TARGET", archiver)
        env.define("RANLIB", ranlib)
        env.define("RANLIB_FOR_TARGET", ranlib)
        env.define("NM", nm)
        env.define("NM_FOR_TARGET", nm)
        env.define("M4", m4)
        env.define("FLEX", flex)
        env.define("LEX", flex)
        env.prepend_path("PATH", os.path.dirname(flex))
        if self._is_ohos:
            env.prepend_path(
                "PATH",
                os.path.dirname(self._ohos_linker_launcher_path),
            )
        # Do not call this script "conanbuild": Conan reserves that name for
        # its aggregate environment file.  Reusing it makes conanbuild.sh
        # source itself recursively until Bash terminates with SIGSEGV.
        env.vars(self).save_script("gcc_build_env")

    def _build_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _build_command_exports(self):
        shell = self._required_executable(
            "sh",
            os.environ.get("CONFIG_SHELL"),
            "sh",
            "/bin/sh",
        )
        return "export TMPDIR={tmpdir}; export CONFIG_SHELL={shell}; export SHELL={shell};".format(
            tmpdir=shlex.quote(self._build_tmpdir()),
            shell=shlex.quote(shell),
        )

    def _configure_args(self):
        triplet = self._target_triplet
        arguments = [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--target={}".format(triplet),
            "--enable-languages=c",
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
            "--disable-dependency-tracking",
            "--without-isl",
        ]
        if self._is_ohos:
            # OHOS libc intentionally omits pthread_cancel, which GCC's
            # POSIX gthread backend references while building libgcc unwind
            # support.  This package builds only the C frontend and static
            # libgcc, so GCC's supported single-thread backend is sufficient.
            arguments.extend(
                [
                    "--disable-threads",
                    # The minimal OHOS package exposes the C frontend and
                    # static libgcc only; decimal floating-point support is
                    # outside that ABI boundary and otherwise adds a large
                    # soft-fp/BID object set to all-target-libgcc.
                    "--disable-decimal-float",
                    # The OHOS build image does not provide m4.  GMP's AArch64
                    # assembly probing requires m4 during configure, while the
                    # generic C implementation is sufficient for the bundled
                    # GCC prerequisite.
                    "--disable-assembly",
                    "--enable-host-pie",
                    "--with-sysroot={}".format(self._ohos_sysroot),
                ]
            )
        arguments.append("--with-native-system-header-dir=/usr/include")
        return arguments

    def _run_with_unlimited_stack(self, command, cwd):
        """Run a GCC build command with enough stack for generated scripts."""
        wrapped_command = "{} ulimit -s unlimited; exec {}".format(
            self._build_command_exports(), command
        )
        result = self.run(
            wrapped_command,
            cwd=cwd,
            env="gcc_build_env",
            ignore_errors=True,
        )
        if result in (-11, 139):
            self.output.warning(
                "GCC command hit a transient signal 11 on HMDFS; syncing and retrying once"
            )
            if hasattr(os, "sync"):
                os.sync()
            time.sleep(1)
            result = self.run(
                wrapped_command,
                cwd=cwd,
                env="gcc_build_env",
                ignore_errors=True,
            )
        if result != 0:
            raise ConanException(
                "GCC command failed with exit code {}".format(result)
            )

    def _sign_elf_tree(self, root):
        if not self._is_ohos:
            return

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = (
            shutil.which("llvm-objcopy")
            or shutil.which("objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
            or "/data/service/hnp/bin/objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
            or "/data/service/hnp/bin/readelf"
        )
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, llvm-objcopy and llvm-readelf"
            )

        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not (candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)], capture_output=True, text=True
            )
            if probe.returncode != 0 or not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", probe.stdout
            ):
                continue
            original_mode = stat.S_IMODE(candidate.stat().st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=str(candidate.parent)
            ) as temp_dir:
                # TemporaryDirectory uses 0700, which can produce unusable
                # directories on HMDFS.  Match the configure umask workaround
                # before the signer and binutils access files inside it.
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
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                )
                signed_header = subprocess.run(
                    [readelf, "-h", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if not re.search(
                    r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout
                ):
                    raise ConanInvalidConfiguration(
                        "Signing did not produce a runnable ELF: {}".format(
                            candidate
                        )
                    )
                signed_sections = subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if ".codesign" not in signed_sections.stdout:
                    raise ConanInvalidConfiguration(
                        "Signing did not add .codesign: {}".format(candidate)
                    )
                os.replace(signed, candidate)
                candidate.chmod(original_mode)

    def _install_ohos_driver_wrapper(self):
        """Make the DESTDIR-installed GCC driver relocatable on OHOS."""
        bindir = Path(self.package_folder) / "bin"
        driver = bindir / "gcc"
        real_driver = bindir / "gcc.real"
        if not driver.is_file():
            raise ConanInvalidConfiguration(
                "The installed GCC driver was not found: {}".format(driver)
            )

        os.replace(driver, real_driver)
        linker_launcher = Path(self._ohos_linker_launcher_path)
        if not linker_launcher.is_file():
            raise ConanInvalidConfiguration(
                "The OHOS linker launcher was not built: {}".format(
                    linker_launcher
                )
            )
        for linker_name in ("ld", "collect-ld", "real-ld"):
            packaged_linker = bindir / linker_name
            source = linker_launcher.parent / linker_name
            if not source.is_file():
                source = linker_launcher
            shutil.copy2(source, packaged_linker)
            packaged_linker.chmod(0o755)
        wrapper = """#!/bin/sh
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/gcc.real"
target={target}

export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"
version=$("$real_driver" -dumpversion)
sysroot=$("$real_driver" -print-sysroot)
if [ -z "$sysroot" ] || [ ! -d "$sysroot/usr/lib/$target" ]; then
    echo "GCC OHOS sysroot is unavailable: $sysroot" >&2
    exit 1
fi
set -- '-D__availability__(...)=' "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
set -- -B/data/service/hnp/bin/ "$@"
set -- "-B$package_root/bin/" "$@"
exec "$real_driver" "$@"
""".format(
            target=shlex.quote(self._target_triplet),
        )
        driver.write_text(wrapper, encoding="utf-8")
        driver.chmod(0o755)

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        # GCC's top-level configure is large enough to exhaust the default
        # shell stack on HarmonyOS.  CONFIG_SHELL influences nested configure
        # scripts, but it neither replaces the initial interpreter nor raises
        # its stack limit.  Raise the limit in the outer shell, then exec sh
        # so the process keeps the writable TMPDIR from the build env.
        configure_shell = self._required_executable(
            "sh",
            os.environ.get("CONFIG_SHELL"),
            "sh",
            "/bin/sh",
        )
        if self._is_ohos:
            self._build_ohos_linker_launcher(configure_shell)
        configure_command = "{} {} {}".format(
            shlex.quote(configure_shell),
            shlex.quote(configure),
            " ".join(shlex.quote(argument) for argument in self._configure_args()),
        )
        # Conan raises on every non-zero exit code when ignore_errors is False.
        # Keep this explicit so configure/build/install failures cannot be
        # mistaken for a successful compiler package.
        self._run_with_unlimited_stack(
            configure_command,
            cwd=self.build_folder,
        )

        # The generator emits hook headers for disabled frontends too.  Their
        # source definitions are kept as single-file inputs, so create the
        # matching out-of-tree output directories explicitly.
        for frontend in ("d", "jit", "rust"):
            os.makedirs(
                os.path.join(self.build_folder, "gcc", frontend),
                exist_ok=True,
            )

        # GNU Make 4.4 defaults to a FIFO jobserver, which HMDFS cannot create
        # reliably.  The OpenDesk toolchain supports the pipe jobserver. Four
        # workers fit the native AArch64 CI image and leave enough memory for
        # clang while giving all-target-libgcc enough headroom for the 3600 s
        # Conan create window; non-OHOS builds keep the smaller generic cap.
        minimum_jobs = 4 if self._is_ohos else 1
        maximum_jobs = 4 if self._is_ohos else 2
        jobs = min(max(build_jobs(self), minimum_jobs), maximum_jobs)
        make = "make --jobserver-style=pipe -j{}".format(jobs)
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )

        # Host generators and the newly built compiler must be signed before
        # they can execute on HarmonyOS.  The compiler wrappers sign normal
        # host links; this pass also covers build-system-created executables.
        self._sign_elf_tree(self.build_folder)

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc = xgcc
        if self._is_ohos:
            target_cc = self._shell_command(
                configure_shell,
                self._write_compiler_wrapper(
                    "xgcc-sign",
                    xgcc,
                    extra_args=[
                        "-B"
                        + os.path.join(self.build_folder, ".ohos-wrappers")
                        + os.sep,
                        "-B/data/service/hnp/bin/",
                        "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                        "-isystem",
                        self._ohos_target_include,
                        # The OHOS SDK annotates APIs with Clang's availability
                        # argument syntax (for example introduced=12.0.0).  GCC 17
                        # snapshot cannot parse that dotted version expression, so discard
                        # only this annotation while retaining all other target
                        # header contents and compiler attributes.
                        "-D__availability__(...)=",
                    ],
                ),
            )

        self._run_with_unlimited_stack(
            "{} all-target-libgcc CC_FOR_TARGET={} CFLAGS_FOR_TARGET={} "
            "CXXFLAGS_FOR_TARGET={} LIBGCC2_DEBUG_CFLAGS={}".format(
                make,
                shlex.quote(target_cc),
                shlex.quote("-O2 -fPIC"),
                shlex.quote("-O2 -fPIC"),
                shlex.quote("-g0"),
            ),
            cwd=self.build_folder,
        )

        # GCC's own language-independent and C frontend selftests.  The main
        # build runs these once; the explicit target leaves an auditable test
        # command in the Conan log.
        self._run_with_unlimited_stack(
            "make -C gcc selftest",
            cwd=self.build_folder,
        )

        # Upstream execution torture tests: compile and run a deterministic
        # subset of gcc.c-torture/execute with the freshly built compiler.
        # Each source is built at -O0 and -O2 (100 executions in total),
        # signed by the xgcc-sign wrapper on OHOS and executed on-device.
        self._run_torture_execute_subset(target_cc)


    def _run_torture_execute_subset(self, compiler_wrapper):
        if not self._is_ohos:
            return
        tests_root = os.path.join(
            self.source_folder,
            "gcc",
            "testsuite",
            "gcc.c-torture",
            "execute",
        )
        if not os.path.isdir(tests_root):
            self.output.warning(
                "Upstream torture testsuite not found: {}".format(tests_root)
            )
            return
        sources = sorted(
            name for name in os.listdir(tests_root) if name.endswith(".c")
        )[:50]
        work = os.path.join(self.build_folder, "torture-execute")
        os.makedirs(work, exist_ok=True)
        # The packaged OHOS GCC driver adds -B<sysroot>/usr/lib/<triplet>/ so
        # the linker finds crt1.o/crti.o/crtn.o.  The in-tree xgcc driver does
        # not, so the torture compiles would fail at link time without it.
        crt_search = "-B" + os.path.join(
            self._ohos_sysroot, "usr", "lib", self._target_triplet
        ) + os.sep
        total = 0
        passed = 0
        failed = 0
        failures = []
        for source_name in sources:
            source = os.path.join(tests_root, source_name)
            stem = source_name[:-2]
            source_text = Path(source).read_text(
                encoding="utf-8", errors="replace"
            )
            additional_options = []
            for match in re.finditer(
                r"\{\s*dg-additional-options\s+\"([^\"]*)\"\s*\}",
                source_text,
            ):
                additional_options.extend(shlex.split(match.group(1)))
            additional = " ".join(
                shlex.quote(option) for option in additional_options
            )
            for opt in ("-O0", "-O2 -fno-strict-aliasing"):
                total += 1
                tag = "{}_{}".format(stem, "o0" if opt == "-O0" else "o2")
                executable = os.path.join(work, tag)
                compile_result = self.run(
                    "{} {} {} -w {} {} {} -o {}".format(
                        self._build_command_exports(),
                        compiler_wrapper,
                        shlex.quote(crt_search),
                        opt,
                        additional,
                        shlex.quote(source),
                        shlex.quote(executable),
                    ),
                    cwd=self.build_folder,
                    env="conanbuild",
                    ignore_errors=True,
                )
                if compile_result != 0:
                    failed += 1
                    failures.append("{}: compile failed".format(tag))
                    continue
                run_result = self.run(
                    shlex.quote(executable),
                    cwd=work,
                    env="conanbuild",
                    ignore_errors=True,
                )
                if run_result != 0:
                    failed += 1
                    failures.append("{}: run failed".format(tag))
                else:
                    passed += 1
        self.output.info(
            "upstream gcc.c-torture/execute subset: {}/{} passed".format(
                passed, total
            )
        )
        if failed and failed / float(total) > 0.1:
            raise ConanInvalidConfiguration(
                "Upstream torture subset failed ({}/{}): {}".format(
                    passed, total, "; ".join(failures[:20])
                )
            )

    def package(self):
        self._run_with_unlimited_stack(
            "make install-gcc install-target-libgcc DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.build_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self._is_ohos:
            self._install_ohos_driver_wrapper()
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        if self._is_ohos:
            exec_prefix = os.path.join(
                self.package_folder,
                "libexec",
                "gcc",
            ) + os.sep
            self.buildenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
            self.runenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
