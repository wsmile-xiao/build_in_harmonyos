#!/usr/bin/env python3
"""Conan recipe for alcotest 1.9.1 — OCaml test framework.

Built from source on HarmonyOS (arm64) using a monorepo workspace approach:
  - OCaml compiler via tool_requires (ocaml/4.14.1)
  - dune 3.17.0 compiled from source (bootstrapped)
  - All OCaml dependencies compiled alongside alcotest in one workspace

alcotest provides three sub-libraries:
  - alcotest           (main library: test runner with CLI)
  - alcotest.engine    (internal engine)
  - alcotest.stdlib_ext (stdlib extensions)
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches

# Mirror prefixes for GitHub source downloads (CI workers may not have direct access)
_GITHUB_MIRRORS = [
    "https://gh-proxy.com/",
    "https://ghfast.top/",
]


class AlcotestConan(ConanFile):
    name = "alcotest"
    version = "1.9.1"
    description = "Alcotest is a lightweight and colourful test framework for OCaml"
    license = "ISC"
    homepage = "https://github.com/mirage/alcotest"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    tool_requires = "ocaml/4.14.1"

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "build_alcotest.sh",
             os.path.dirname(os.path.abspath(__file__)),
             self.export_sources_folder)

    def source(self):
        # Download alcotest source (monorepo root)
        info = self.conan_data["sources"][self.version]
        self._get_with_mirrors(info["url"], info["sha256"], strip_root=True)
        # Download dune + all OCaml dependency sources into the monorepo
        deps = self.conan_data.get("deps", {})
        for dep_name, dep_info in deps.items():
            # dune goes to hidden dir (.dune) so it's not part of the workspace build
            dest = ".dune" if dep_name == "dune" else dep_name
            self._get_with_mirrors(dep_info["url"], dep_info["sha256"],
                                   strip_root=True, destination=dest)

    def _get_with_mirrors(self, url, sha256, **kwargs):
        """Try original URL first, then GitHub mirrors if direct access fails."""
        urls = [url]
        if "github.com" in url:
            gh_path = url.split("github.com", 1)[1]
            for mirror in _GITHUB_MIRRORS:
                urls.append(f"{mirror}https://github.com{gh_path}")
        last_err = None
        for try_url in urls:
            try:
                get(self, url=try_url, sha256=sha256, **kwargs)
                return
            except Exception as e:
                last_err = e
                if try_url != urls[-1]:
                    self.output.warning(f"Download from {try_url} failed, trying mirror...")
        raise last_err

    def build(self):
        build_script = os.path.join(self.source_folder, "build_alcotest.sh")
        self.run(f'bash "{build_script}" "{self.source_folder}" "{self.package_folder}"',
                 env="conanbuild")

    def package(self):
        # Artifacts are already copied to package_folder by build_alcotest.sh
        pass

    def package_info(self):
        self.cpp_info.libs = ["alcotest"]
        self.cpp_info.includedirs = []

        self.cpp_info.components["engine"].libs = ["alcotest_engine"]
        self.cpp_info.components["engine"].libdirs = [os.path.join("lib", "alcotest", "engine")]
        self.cpp_info.components["engine"].includedirs = []

        self.cpp_info.components["stdlib_ext"].libs = ["alcotest_stdlib_ext"]
        self.cpp_info.components["stdlib_ext"].libdirs = [os.path.join("lib", "alcotest", "stdlib_ext")]
        self.cpp_info.components["stdlib_ext"].includedirs = []

# v1.1
