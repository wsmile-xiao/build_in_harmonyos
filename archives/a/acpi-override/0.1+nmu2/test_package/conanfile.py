from conan import ConanFile
import os


class AcpiOverrideTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        hook = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                            "share", "initramfs-tools", "hooks", "acpi-override")
        if not os.path.isfile(hook):
            raise RuntimeError("acpi-override hook was not packaged")
        test_script = os.path.join(self.recipe_folder, "test_hook.sh")
        self.run(f'ACPI_OVERRIDE_HOOK="{hook}" sh "{test_script}"',
                 env="conanrun", ignore_errors=False)
        self.output.info("acpi-override hook functional test passed")
