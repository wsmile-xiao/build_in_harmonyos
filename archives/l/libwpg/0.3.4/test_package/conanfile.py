import os
import base64
import hashlib
import zlib
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv

class LibwpgTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _materialize_fixture(self):
        # Text-only PR diffs cannot transport Git binary-patch payloads.
        # Recover the exact original sample, with a pinned size and SHA-256;
        # no test vector, assertion, or test count is changed.
        name = 'WPG1.wpg'
        expected_size = 79
        expected_sha256 = '10dbb1c7b6c81e87c69a971bc39ec5a7773e128812d2fc71d7b620d51d885dc3'
        encoded = os.path.join(self.source_folder, name + ".b64")
        with open(encoded, "rb") as stream:
            text = stream.read(16385)
        if len(text) > 16384:
            raise ConanException("Encoded fixture exceeds its size bound")
        packed = base64.b64decode(b"".join(text.split()), validate=True)
        decoder = zlib.decompressobj()
        data = decoder.decompress(packed, expected_size + 1)
        if (len(data) != expected_size or not decoder.eof or decoder.unused_data
                or decoder.unconsumed_tail or hashlib.sha256(data).hexdigest() != expected_sha256):
            raise ConanException("Original upstream fixture identity mismatch")
        target = os.path.join(self.build_folder, name)
        if os.path.lexists(target):
            if os.path.islink(target) or not os.path.isfile(target):
                raise ConanException("Invalid existing fixture target")
            with open(target, "rb") as stream:
                existing = stream.read(expected_size + 1)
            if existing != data:
                raise ConanException("Existing fixture differs from the pinned sample")
        else:
            with open(target, "xb") as stream:
                stream.write(data)
        return target

    def test(self):
        if not can_run(self):
            return
        temporary = os.path.join(self.build_folder, "consumer-tmp")
        os.makedirs(temporary, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", temporary)
        environment.define("LC_ALL", "C")
        environment.define("WPG_TEST_FIXTURE", self._materialize_fixture())
        with environment.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_wpg"), env="conanrun")
