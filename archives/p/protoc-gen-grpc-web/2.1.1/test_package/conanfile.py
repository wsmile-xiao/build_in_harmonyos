#!/usr/bin/env python3
"""Consumer tests for protoc-gen-grpc-web 2.1.1 (R34 end-to-end codegen)."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ProtocGenGrpcWebTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct require: in the test_package context only direct
        # dependencies expose package_folder (transitive ones yield None),
        # and we need protobuf's bin/protoc to drive the end-to-end test.
        self.requires("protobuf/33.6.1")

    def test(self):
        plugin = self.dependencies["protoc-gen-grpc-web"]
        plugin_bin = os.path.join(
            plugin.package_folder, "bin", "protoc-gen-grpc-web"
        )
        protobuf = self.dependencies["protobuf"]
        protoc = os.path.join(protobuf.package_folder, "bin", "protoc")

        assert os.path.isfile(plugin_bin), (
            f"plugin binary not found: {plugin_bin}"
        )
        assert os.path.isfile(protoc), f"protoc not found: {protoc}"

        if not can_run(self):
            # Cross-building: only the binary-presence assertion (T1) can run.
            self.run(
                f'python3 "{os.path.join(self.recipe_folder, "test_grpc_web.py")}" '
                f'--plugin-bin "{plugin_bin}" --protoc "{protoc}" '
                f'--workdir "{os.path.join(self.build_folder, "grpc-web-e2e")}" '
                f"--smoke-only",
                env="conanrun",
            )
            return

        # R34: real end-to-end assertions (T1-T9) live in test_grpc_web.py;
        # a non-zero exit propagates the failure (no || masking here).
        self.run(
            f'python3 "{os.path.join(self.recipe_folder, "test_grpc_web.py")}" '
            f'--plugin-bin "{plugin_bin}" --protoc "{protoc}" '
            f'--workdir "{os.path.join(self.build_folder, "grpc-web-e2e")}"',
            env="conanrun",
        )
