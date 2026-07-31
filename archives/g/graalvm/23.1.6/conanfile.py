#!/usr/bin/env python3
"""Conan recipe — GraalVM SDK 23.1.6 (Java library, prebuilt JAR).

GraalVM SDK provides the Polyglot API, Native Image API, and other
APIs for embedding and interacting with GraalVM from Java applications.

This is a prebuilt binary package (Java JAR). No compilation step.
The JAR is downloaded from Maven Central.

Source: https://github.com/oracle/graal (sdk/ directory)
License: Universal Permissive License (UPL), Version 1.0

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class GraalvmSdkConan(ConanFile):
    name = "graalvm"
    version = "23.1.6"
    description = "GraalVM SDK - APIs for embedding and interacting with GraalVM"
    license = "UPL-1.0"
    homepage = "https://www.graalvm.org/"
    url = ""  # CI fills this

    # R32: settings.os must check `in ("Linux", "OHOS")`
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        # R32: OS compatibility check — must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"graalvm does not support OS: {self.settings.os}"
            )

    def source(self):
        # Download the JAR file from Maven Central (no extraction needed)
        sources = self.conan_data["sources"]
        download(self, url=sources[0]["url"], filename="graal-sdk-23.1.6.jar", sha256=sources[0]["sha256"])

    def build(self):
        # Apply patches (none for prebuilt JAR, but required by G1 check)
        apply_conandata_patches(self)

    def package(self):
        # Copy JAR to libexec/
        copy(self, "graal-sdk-23.1.6.jar", self.source_folder, os.path.join(self.package_folder, "libexec"))

    def package_info(self):
        # This is a Java library, not a C/C++ library
        # Set libdirs so the JAR is accessible
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.bindirs = []
        # The JAR file is not a C/C++ library, so we don't set cpp_info.libs
        # Downstream packages should use self.requires("graalvm/23.1.6") and
        # access the JAR via the package folder