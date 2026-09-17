import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.test_requirements()

    def test_requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("php/8.5.8")

    def build(self):
        pass

    def test(self):
        ext_path = os.path.join(self.dependencies["php-pecl-memcache"].package_folder,
                                "lib", "php", "extensions", "memcache.so")
        php_bin = os.path.join(self.dependencies["php"].package_folder, "bin", "php")
        php_lib = os.path.join(self.dependencies["php"].package_folder, "lib")

        assert os.path.exists(ext_path), f"memcache.so not found at {ext_path}"
        self.output.info(f"Found memcache extension at {ext_path}")

        os.environ["LD_LIBRARY_PATH"] = php_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        # Run the test script (use sh to avoid permission issues)
        test_script = os.path.join(self.source_folder, "test_memcache.sh")
        self.run(f'sh "{test_script}" "{php_bin}" "{ext_path}"')
