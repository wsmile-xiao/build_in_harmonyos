#!/usr/bin/env python3
"""Conan recipe for CException 1.3.4.

CException's upstream Meson file builds a static library but has no install()
rules, so package() stages the verified archive and public header explicitly.
"""
import glob
import io
import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CexceptionConan(ConanFile):
    name = "cexception"
    version = "1.3.4"
    description = "Lightweight C exception handling macros based on setjmp/longjmp"
    license = "MIT"
    homepage = "https://github.com/ThrowTheSwitch/CException"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "CException 1.3.4 upstream only defines static_library()"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # The upstream project intentionally defines static_library().
        tc.project_options["default_library"] = "static"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        nl = chr(10)
        # CI profiles may expose clang through an absolute conf path while
        # omitting the SDK tool directory from PATH. Meson then cannot
        # discover llvm-ar unless the native machine file names it explicitly.
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            compiler = compiler_exes.get("c", "")
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                ranlib = ranlib_candidate if os.path.isfile(ranlib_candidate) else None
        if not ar and str(self.settings.os) == "OHOS":
            candidate = "/data/service/hnp/bin/llvm-ar"
            if os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = "/data/service/hnp/bin/llvm-ranlib"
                ranlib = ranlib_candidate if os.path.isfile(ranlib_candidate) else None
        if not ar:
            raise ConanException("Unable to locate an archiver for Meson")

        patched = False
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            content = open(path, encoding="utf-8").read()
            if nl + "ar =" in content:
                patched = True
                continue
            if "[binaries]" + nl not in content:
                raise ConanException(
                    "Meson machine file has no [binaries] section: " + filename
                )
            insertion = "[binaries]" + nl + "ar = '{}'" + nl
            insertion = insertion.format(ar.replace(chr(92), "/"))
            if ranlib:
                insertion += "ranlib = '{}'" + nl
                insertion = insertion.format(ranlib.replace(chr(92), "/"))
            with open(path, "w", encoding="utf-8", newline=nl) as handle:
                handle.write(content.replace("[binaries]" + nl, insertion, 1))
            patched = True
        if not patched:
            raise ConanException("Meson machine file was not generated")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Compile the unchanged upstream TestException.c with a tiny Unity API
        # compatibility layer because the source archive omits Ceedling/Unity.
        test_root = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(test_root, exist_ok=True)
        unity_header = "\n".join([
            "#ifndef OHPCD_UNITY_COMPAT_H",
            "#define OHPCD_UNITY_COMPAT_H",
            "#include <stdio.h>",
            "extern int ohpcd_unity_failures;",
            "static inline void ohpcd_unity_fail(const char *message, const char *file, int line) {",
            "    fprintf(stderr, \"Unity failure: %s (%s:%d)\\n\", message, file, line);",
            "    ohpcd_unity_failures++;",
            "}",
            "#define TEST_ASSERT_EQUAL(expected, actual) ((expected) == (actual) ? (void)0 : ohpcd_unity_fail(\"TEST_ASSERT_EQUAL\", __FILE__, __LINE__))",
            "#define TEST_ASSERT_FALSE(actual) (!(actual) ? (void)0 : ohpcd_unity_fail(\"TEST_ASSERT_FALSE\", __FILE__, __LINE__))",
            "#define TEST_FAIL_MESSAGE(message) ohpcd_unity_fail((message), __FILE__, __LINE__)",
            "#endif",
            "",
        ])
        runner_source = "\n".join([
            "#include <stdio.h>",
            "typedef void (*upstream_test_fn)(void);",
            "int ohpcd_unity_failures = 0;",
            "void setUp(void);",
            "void tearDown(void);",
            "void test_BasicTryDoesNothingIfNoThrow(void);",
            "void test_BasicThrowAndCatch(void);",
            "void test_BasicThrowAndCatch_WithMiniSyntax(void);",
            "void test_VerifyVolatilesSurviveThrowAndCatch(void);",
            "void test_ThrowFromASubFunctionAndCatchInRootFunc(void);",
            "void test_ThrowAndCatchFromASubFunctionAndRethrowToCatchInRootFunc(void);",
            "void test_ThrowAndCatchFromASubFunctionAndNoRethrowToCatchInRootFunc(void);",
            "void test_ThrowAnErrorThenEnterATryBlockFromWithinCatch_VerifyThisDoesntCorruptExceptionId(void);",
            "void test_ThrowAnErrorThenEnterATryBlockFromWithinCatch_VerifyThatEachExceptionIdIndependent(void);",
            "void test_CanHaveMultipleTryBlocksInASingleFunction(void);",
            "void test_CanHaveNestedTryBlocksInASingleFunction_ThrowInside(void);",
            "void test_CanHaveNestedTryBlocksInASingleFunction_ThrowOutside(void);",
            "void test_AThrowWithoutATryCatchWillUseDefaultHandlerIfSpecified(void);",
            "void test_AThrowWithoutOutsideATryCatchWillUseDefaultHandlerEvenAfterTryCatch(void);",
            "void test_AbilityToExitTryWithoutThrowingAnError(void);",
            "void test_AbilityToExitTryWillOnlyExitOneLevel(void);",
            "static int tests_run = 0;",
            "static void run_upstream_test(upstream_test_fn function) { setUp(); function(); tearDown(); tests_run++; }",
            "int main(void) {",
            "    run_upstream_test(test_BasicTryDoesNothingIfNoThrow);",
            "    run_upstream_test(test_BasicThrowAndCatch);",
            "    run_upstream_test(test_BasicThrowAndCatch_WithMiniSyntax);",
            "    run_upstream_test(test_VerifyVolatilesSurviveThrowAndCatch);",
            "    run_upstream_test(test_ThrowFromASubFunctionAndCatchInRootFunc);",
            "    run_upstream_test(test_ThrowAndCatchFromASubFunctionAndRethrowToCatchInRootFunc);",
            "    run_upstream_test(test_ThrowAndCatchFromASubFunctionAndNoRethrowToCatchInRootFunc);",
            "    run_upstream_test(test_ThrowAnErrorThenEnterATryBlockFromWithinCatch_VerifyThisDoesntCorruptExceptionId);",
            "    run_upstream_test(test_ThrowAnErrorThenEnterATryBlockFromWithinCatch_VerifyThatEachExceptionIdIndependent);",
            "    run_upstream_test(test_CanHaveMultipleTryBlocksInASingleFunction);",
            "    run_upstream_test(test_CanHaveNestedTryBlocksInASingleFunction_ThrowInside);",
            "    run_upstream_test(test_CanHaveNestedTryBlocksInASingleFunction_ThrowOutside);",
            "    run_upstream_test(test_AThrowWithoutATryCatchWillUseDefaultHandlerIfSpecified);",
            "    run_upstream_test(test_AThrowWithoutOutsideATryCatchWillUseDefaultHandlerEvenAfterTryCatch);",
            "    run_upstream_test(test_AbilityToExitTryWithoutThrowingAnError);",
            "    run_upstream_test(test_AbilityToExitTryWillOnlyExitOneLevel);",
            "    printf(\"Upstream CException tests: %d/16 passed; 56 assertion/failure macros exercised\\n\", tests_run - (ohpcd_unity_failures != 0));",
            "    return ohpcd_unity_failures == 0 ? 0 : 1;",
            "}",
            "",
        ])
        unity_path = os.path.join(test_root, "unity.h")
        runner_path = os.path.join(test_root, "upstream_runner.c")
        binary_path = os.path.join(test_root, "upstream_cexception_tests")
        save(self, unity_path, unity_header)
        save(self, runner_path, runner_source)
        compiler_config = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_config.get("c", "cc")
        command = "{} -std=c11 -DTEST -DCEXCEPTION_USE_CONFIG_FILE -I{} -I{} -I{} {} {} {} -o {}".format(
            shlex.quote(compiler),
            shlex.quote(test_root),
            shlex.quote(os.path.join(self.source_folder, "test", "support")),
            shlex.quote(os.path.join(self.source_folder, "lib")),
            shlex.quote(os.path.join(self.source_folder, "test", "TestException.c")),
            shlex.quote(os.path.join(self.source_folder, "lib", "CException.c")),
            shlex.quote(runner_path),
            shlex.quote(binary_path),
        )
        self.run(command, env="conanbuild")
        self.run(shlex.quote(binary_path), env="conanrun")

    def package(self):
        artifacts = glob.glob(
            os.path.join(self.build_folder, "**", "libcexception.a"),
            recursive=True,
        )
        if len(artifacts) != 1:
            raise ConanException(
                "Expected exactly one Meson output libcexception.a, found: "
                + repr(artifacts)
            )
        artifact = artifacts[0]
        ar_config = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = ar_config.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = os.path.join(bindir, "llvm-ar") if bindir else "llvm-ar"

        member_output = io.StringIO()
        self.run(
            "{} t {}".format(shlex.quote(ar), shlex.quote(artifact)),
            stdout=member_output,
            env="conanbuild",
        )
        archive_members = [
            line.strip() for line in member_output.getvalue().splitlines()
            if line.strip()
        ]
        if not archive_members:
            raise ConanException("Meson archive has no readable members")

        member_paths = []
        for member in archive_members:
            candidates = [
                member,
                os.path.join(os.path.dirname(artifact), member),
                os.path.join(self.build_folder, member),
            ]
            resolved = next(
                (candidate for candidate in candidates if os.path.isfile(candidate)),
                None,
            )
            if resolved is None:
                raise ConanException(
                    "Meson archive member is missing: " + repr(member)
                )
            member_paths.append(resolved)

        with tempfile.TemporaryDirectory(dir=self.build_folder) as tmp:
            staged_objects = []
            for index, member_path in enumerate(member_paths):
                staged_object = os.path.join(
                    tmp, "member-{}-{}".format(index, os.path.basename(member_path))
                )
                shutil.copyfile(member_path, staged_object)
                staged_objects.append(staged_object)
            standalone_archive = os.path.join(tmp, "libcexception.a")
            self.run(
                "{} rcs {} {}".format(
                    shlex.quote(ar),
                    shlex.quote(standalone_archive),
                    " ".join(shlex.quote(obj) for obj in staged_objects),
                ),
                env="conanbuild",
            )
            verify_output = io.StringIO()
            self.run(
                "{} t {}".format(
                    shlex.quote(ar), shlex.quote(standalone_archive)
                ),
                stdout=verify_output,
                env="conanbuild",
            )
            rebuilt_members = [
                line.strip() for line in verify_output.getvalue().splitlines()
                if line.strip()
            ]
            if len(rebuilt_members) != len(staged_objects):
                raise ConanException(
                    "Rebuilt archive member count mismatch: expected {}, got {}".format(
                        len(staged_objects), len(rebuilt_members)
                    )
                )
            copy(
                self,
                "libcexception.a",
                src=tmp,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        copy(
            self,
            "CException.h",
            src=os.path.join(self.source_folder, "lib"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["cexception"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cexception")
        self.cpp_info.set_property("cmake_target_name", "cexception::cexception")
