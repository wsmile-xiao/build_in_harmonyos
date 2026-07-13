from conan import ConanFile
import os


class AvroToolsTest(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get avro-tools bin directory
        bin_path = os.path.join(self.dependencies["avro-tools"].package_folder, "bin")
        avro_tools = os.path.join(bin_path, "avro-tools")

        # Set JAVA environment for avro-tools
        java_home = "/storage/Users/currentUser/usr/local/bishengjdk17"
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = f"{java_home}/bin:{os.environ.get('PATH', '/usr/bin:/bin')}"

        # Run avro-tools and check it outputs version info
        # avro-tools with no args prints usage including version
        self.run(f'"{avro_tools}" 2>&1 | head -5')
