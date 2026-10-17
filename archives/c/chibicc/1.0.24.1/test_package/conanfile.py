#!/usr/bin/env python3
"""Conan test_package for chibicc 1.0.24.1."""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, load, rmdir, save


def resolve_source_include(source_root, roots, including_file, header, quoted):
    candidates = []
    if quoted:
        candidates.append(os.path.join(os.path.dirname(including_file), header))
    candidates.extend(os.path.join(root, header) for root in roots)
    for candidate in candidates:
        resolved = os.path.realpath(candidate)
        if (
            os.path.commonpath((source_root, resolved)) == source_root
            and os.path.isfile(resolved)
        ):
            return resolved
    return None


class ChibiccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _stage2_sources = (
        "builtin.c",
        "codegen.c",
        "debug.c",
        "extended_asm.c",
        "hashmap.c",
        "main.c",
        "parse.c",
        "preprocess.c",
        "printast.c",
        "strings.c",
        "tokenize.c",
        "type.c",
        "unicode.c",
    )
    _xfail_kinds = {
        "const-expr",
        "line-directive",
        "primary-expression",
        "qualifiers-static-assert",
        "redefinition-main",
        "token-paste",
    }
    _test_header_opening = (
        "#if defined(__slimcc__) || defined(__chibicc__)\n"
        "#include <stdio.h>\n"
    )
    _test_header_separator = "\n#else\n"
    _test_header_ending = "\n#endif\n"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _validate_upstream_tree(self, source_dir):
        test_dir = os.path.join(source_dir, "test")
        test_header = os.path.join(test_dir, "test.h")
        if not os.path.isfile(test_header):
            raise ConanInvalidConfiguration(
                f"chibicc source cache is incomplete: missing {test_header}"
            )

        for header in ("immintrin.h", "stdarg.h", "stddef.h"):
            header_path = os.path.join(source_dir, "include", header)
            if not os.path.isfile(header_path):
                raise ConanInvalidConfiguration(
                    f"chibicc source cache is incomplete: missing {header_path}"
                )

        test_sources = sorted(
            name
            for name in os.listdir(test_dir)
            if name.endswith(".c") and os.path.isfile(os.path.join(test_dir, name))
        )
        if len(test_sources) != 980:
            raise ConanInvalidConfiguration(
                f"Expected 980 upstream test sources, found {len(test_sources)}"
            )

        stage2_sources = sorted(
            name
            for name in os.listdir(source_dir)
            if name.endswith(".c") and os.path.isfile(os.path.join(source_dir, name))
        )
        if stage2_sources != sorted(self._stage2_sources):
            raise ConanInvalidConfiguration(
                "Unexpected stage2 source inventory: " + ", ".join(stage2_sources)
            )

    def _validate_xfails(self, source_dir, xfail_inventory):
        entries = []
        for raw_line in load(self, xfail_inventory).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 2 or fields[1] not in self._xfail_kinds:
                raise ConanInvalidConfiguration(
                    f"Invalid known XFAIL entry: {raw_line}"
                )
            entries.append(tuple(fields))

        names = [name for name, _ in entries]
        if len(entries) != 62 or len(set(names)) != 62 or names != sorted(names):
            raise ConanInvalidConfiguration(
                "Expected exactly 62 unique, sorted known XFAIL entries"
            )
        for name in names:
            source = os.path.join(source_dir, "test", f"{name}.c")
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    f"Known XFAIL source is missing: {source}"
                )

    def generate(self):
        dependency = self.dependencies["chibicc"]
        source_cache = os.path.normpath(
            os.path.join(dependency.recipe_folder, os.pardir, "s")
        )
        self._validate_upstream_tree(source_cache)

        upstream_dir = os.path.join(self.build_folder, "upstream")
        rmdir(self, upstream_dir)
        copy(self, "*", src=source_cache, dst=upstream_dir)
        self._validate_upstream_tree(upstream_dir)

    def build(self):
        upstream_dir = os.path.join(self.build_folder, "upstream")
        test_header = os.path.join(upstream_dir, "test", "test.h")
        contents = load(self, test_header).replace("\r\n", "\n")
        if (
            not contents.startswith(self._test_header_opening)
            or contents.count(self._test_header_separator) != 1
            or not contents.endswith(self._test_header_ending)
        ):
            raise ConanInvalidConfiguration(
                "Unexpected upstream test.h conditional structure"
            )
        selected_end = contents.index(self._test_header_separator)
        selected = contents[len(self._test_header_opening) : selected_end] + "\n"
        test_env = (
            "#define NULL ((void *)0)\n"
            "typedef long __int64_t;\n"
            "int puts(const char *s);\n"
            "int putchar(int c);\n"
        )
        save(self, test_header, test_env + selected)

    _include_directive_re = re.compile(
        r"^\s*#\s*(?P<directive>include|include_next)\s+"
        r"(?P<value>[^\r\n]+)",
        re.MULTILINE,
    )
    _literal_include_re = re.compile(
        r'^\s*(?P<delimiter>[<"])(?P<name>[^>"]+)[>"]'
    )

    def _source_owned_tests(self, source_dir):
        source_root = os.path.realpath(source_dir)
        roots = (
            source_dir,
            os.path.join(source_dir, "include"),
            os.path.join(source_dir, "test"),
        )
        cache = {}
        active = set()

        def resolve_include(including_file, header, quoted):
            return resolve_source_include(
                source_root, roots, including_file, header, quoted
            )

        def has_source_owned_closure(path):
            path = os.path.realpath(path)
            if path in cache:
                return cache[path]
            if path in active:
                return True

            active.add(path)
            result = True
            for directive in self._include_directive_re.finditer(load(self, path)):
                literal = self._literal_include_re.match(directive.group("value"))
                if directive.group("directive") == "include_next" or not literal:
                    result = False
                    break
                dependency = resolve_include(
                    path,
                    literal.group("name"),
                    literal.group("delimiter") == '"',
                )
                if not dependency or not has_source_owned_closure(dependency):
                    result = False
                    break
            active.remove(path)
            cache[path] = result
            return result

        test_dir = os.path.join(source_dir, "test")
        names = sorted(
            os.path.splitext(name)[0]
            for name in os.listdir(test_dir)
            if name.endswith(".c")
            and has_source_owned_closure(os.path.join(test_dir, name))
        )
        if len(names) != 607:
            raise ConanInvalidConfiguration(
                f"Expected exactly 607 source-owned tests, found {len(names)}"
            )
        return names

    def _target_header_blockers(self, source_dir):
        source_root = os.path.realpath(source_dir)
        roots = (
            source_dir,
            os.path.join(source_dir, "include"),
            os.path.join(source_dir, "test"),
        )
        def collect(path, active=None):
            path = os.path.realpath(path)
            active = set() if active is None else active
            if path in active:
                return set()

            active.add(path)
            headers = set()
            for directive in self._include_directive_re.finditer(load(self, path)):
                literal = self._literal_include_re.match(directive.group("value"))
                if not literal:
                    continue

                header = literal.group("name")
                if os.path.isabs(header) or ".." in header.split("/"):
                    continue
                dependency = resolve_source_include(
                    source_root,
                    roots,
                    path,
                    header,
                    literal.group("delimiter") == '"',
                )
                if directive.group("directive") == "include_next" or not dependency:
                    headers.add(header)
                else:
                    headers.update(collect(dependency, active))

            active.remove(path)
            return headers

        blockers = []
        test_dir = os.path.join(source_dir, "test")
        for name in sorted(os.listdir(test_dir)):
            if not name.endswith(".c"):
                continue
            stem = os.path.splitext(name)[0]
            if stem in ("csmith_102", "csmith_275", "csmith_4204"):
                continue
            for header in sorted(collect(os.path.join(test_dir, name))):
                blockers.append(f"upstream/{stem} {header}")

        for name in self._stage2_sources:
            stem = os.path.splitext(name)[0]
            for header in sorted(collect(os.path.join(source_dir, name))):
                blockers.append(f"stage2/{stem} {header}")

        if len(blockers) != 1037:
            raise ConanInvalidConfiguration(
                f"Expected exactly 1037 target-header blockers, found {len(blockers)}"
            )
        return blockers

    def _prepare_runtime(self, source_dir, chibicc):
        runtime_dir = os.path.join(source_dir, "runtime")
        merged_include = os.path.join(runtime_dir, "include")
        rmdir(self, runtime_dir)

        # Keep the x86-64 compiler runtime free of arm64 OHOS libc headers.
        copy(
            self,
            "*",
            src=os.path.join(os.path.dirname(chibicc), "include"),
            dst=merged_include,
            overwrite_equal=True,
        )


        # Candidate stat probes miss workspace files on the OHOS worker. Keep
        # quoted test headers in the fallback working directory as well.
        copy(
            self,
            "*.h",
            src=os.path.join(source_dir, "test"),
            dst=merged_include,
            keep_path=False,
        )
        copy(self, "chibicc.h", src=source_dir, dst=merged_include, keep_path=False)
        copy(
            self,
            "pragma-once.c",
            src=os.path.join(source_dir, "test"),
            dst=os.path.join(merged_include, "test"),
            keep_path=False,
        )
        copy(self, "chibicc", src=os.path.dirname(chibicc), dst=runtime_dir)
        source_owned_tests = os.path.join(runtime_dir, "source-owned-tests.txt")
        target_header_blockers = os.path.join(
            runtime_dir, "target-header-blockers.txt"
        )
        save(
            self,
            source_owned_tests,
            "\n".join(self._source_owned_tests(source_dir)) + "\n",
        )
        save(
            self,
            target_header_blockers,
            "\n".join(self._target_header_blockers(source_dir)) + "\n",
        )

        runtime_chibicc = os.path.join(runtime_dir, "chibicc")
        for inventory in (source_owned_tests, target_header_blockers):
            if not os.path.isfile(inventory):
                raise ConanInvalidConfiguration(
                    f"Test inventory was not created: {inventory}"
                )
        if not os.path.isfile(runtime_chibicc):
            raise ConanInvalidConfiguration(
                f"Test runtime compiler was not created: {runtime_chibicc}"
            )
        os.chmod(runtime_chibicc, 0o755)

        for header in (
            "immintrin.h",
            "stdarg.h",
            "test.h",
            "chibicc.h",
            os.path.join("test", "pragma-once.c"),
        ):
            if not os.path.isfile(os.path.join(merged_include, header)):
                raise ConanInvalidConfiguration(
                    f"Merged chibicc compile tree is missing header {header}"
                )
        return runtime_dir

    def test(self):
        if not can_run(self):
            return

        package_folder = self.dependencies["chibicc"].package_folder
        chibicc = os.path.join(package_folder, "bin", "chibicc")
        source_dir = os.path.join(self.build_folder, "upstream")
        script = os.path.join(self.source_folder, "test_chibicc.sh")
        xfail_inventory = os.path.join(self.source_folder, "known-xfails.txt")
        shell = os.environ.get("CONFIG_SHELL") or "sh"
        self._validate_xfails(source_dir, xfail_inventory)
        runtime_dir = self._prepare_runtime(source_dir, chibicc)
        self.run(
            f'CHIBICC_BIN="{chibicc}" '
            f'CHIBICC_SOURCE_DIR="{source_dir}" '
            f'CHIBICC_RUNTIME_DIR="{runtime_dir}" '
            f'CHIBICC_XFAILS="{xfail_inventory}" '
            f'"{shell}" "{script}"',
            env="conanrun",
        )
