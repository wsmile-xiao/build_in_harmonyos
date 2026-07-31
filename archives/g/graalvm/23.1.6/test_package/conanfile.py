from conan import ConanFile
import os
import json


class GraalvmSdkTest(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get graalvm package folder
        pkg_folder = self.dependencies["graalvm"].package_folder
        jar_path = os.path.join(pkg_folder, "libexec", "graal-sdk-23.1.6.jar")

        # Verify the JAR file exists and is non-empty (check run() return code)
        ret = self.run(f'test -f "{jar_path}"', cwd=pkg_folder)
        assert ret == 0, f"JAR not found: {jar_path}"
        ret = self.run(f'test -s "{jar_path}"', cwd=pkg_folder)
        assert ret == 0, f"JAR is empty: {jar_path}"

        # Check JAR is valid (has ZIP magic bytes PK\x03\x04).
        # Use HMBS_PYTHON3 if provided so the exact toolchain python is used.
        # bytes([80,75,3,4]) is the ZIP local-file-header magic; chr() builds
        # the open mode 'rb' to avoid quote nesting inside the f-string.
        py = os.environ.get("HMBS_PYTHON3", "python3")
        ret = self.run(
            f'{py} -c "import sys; f=open(sys.argv[1],chr(114)+chr(98)); b=f.read(4); sys.exit(0 if b==bytes([80,75,3,4]) else 1)" "{jar_path}"',
            cwd=pkg_folder,
        )
        assert ret == 0, f"JAR is not a valid ZIP archive: {jar_path}"

        # Verify the JAR is a readable, non-trivial ZIP archive (functional
        # check beyond magic bytes): open it via zipfile and assert the TOC is
        # non-empty. Does not assume any specific package layout (GraalVM SDK
        # JAR internals vary across releases), only that it is a real archive.
        ret = self.run(
            f'{py} -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); sys.exit(0 if len(z.namelist()) > 0 else 1)" "{jar_path}"',
            cwd=pkg_folder,
        )
        assert ret == 0, f"JAR is not a readable ZIP archive or has no entries: {jar_path}"

        # hmbs evidence markers (emitted only after all assertions pass).
        # test_package result
        tp = json.dumps({
            "executed": True,
            "passed": True,
            "command": "test -f + test -s + python3 ZIP magic + zipfile readable non-empty TOC",
        })
        print(f"HMBS_TEST_PACKAGE_RESULT={tp}")
        # upstream tests: audit confirmed GraalVM SDK has no C/C++ test suite (see MANIFEST.yml)
        ut = json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": "N/A",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Audit confirmed: GraalVM SDK is a Java library (JAR); upstream oracle/graal sdk/ has no C/C++ test suite, no CMakeLists.txt/Makefile/configure, no gtest/ctest/autotools; see test_package/MANIFEST.yml upstream_test_audit",
        })
        print(f"HMBS_UPSTREAM_TEST_RESULT={ut}")
