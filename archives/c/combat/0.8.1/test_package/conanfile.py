import os

from conan import ConanFile


class CombatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        combat = self.dependencies["combat"]
        orb_dir = os.path.join(combat.package_folder, "lib", "combat")
        kill_dir = os.path.join(combat.package_folder, "lib", "tclkill")
        runner = os.path.join(self.source_folder, "run_test.sh")
        # tclsh8.6 来自依赖 tcl/8.6.16 的 runenv PATH（conanrun 环境）
        self.run(
            f'bash "{runner}" "{orb_dir}" "{kill_dir}" "{self.source_folder}"',
            env="conanrun",
        )
