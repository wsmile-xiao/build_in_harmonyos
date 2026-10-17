import os

from conan import ConanFile


class DhcpstarvTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        # r60: conanrun env 的 PATH 在 OHOS 下不保证包含包 bin —— 显式传包内二进制路径给 test.sh。
        # r60-fix2: OHOS application 包产物在 DESTDIR storage 前缀下（storage/Users/.../usr/local/bin），
        # 自发现常见位置：优先 cpp_info.bindirs，其次 bin/，再次 storage 前缀 bin/。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["dhcpstarv"]
        candidates = []
        if dep.cpp_info.bindirs:
            candidates += [os.path.join(dep.package_folder, d, "dhcpstarv") for d in dep.cpp_info.bindirs]
        candidates += [
            os.path.join(dep.package_folder, "bin", "dhcpstarv"),
            os.path.join(dep.package_folder, "storage", "Users", "currentUser", "usr", "local", "bin", "dhcpstarv"),
        ]
        bin_path = next((p for p in candidates if os.path.exists(p)), candidates[0] if candidates else "dhcpstarv")
        self.run(f"{bash} test.sh {bin_path}", env="conanrun")
