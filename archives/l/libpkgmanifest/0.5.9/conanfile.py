#!/usr/bin/env python3
"""Conan recipe for libpkgmanifest - Library for managing RPM manifests."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm, rmdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibpkgmanifestConan(ConanFile):
    name = "libpkgmanifest"
    version = "0.5.9"
    description = "Library for working with RPM manifests"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rpm-software-management/libpkgmanifest"
    url = "https://github.com/rpm-software-management/libpkgmanifest"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.compiler.cppstd = "20"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("yaml-cpp/0.8.0")

    def build_requirements(self):
        if self.conf.get("tools.build:skip_test", default=False) == False:
            self.test_requires("gtest/1.17.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libpkgmanifest is supported only on Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_PYTHON"] = False
        tc.variables["WITH_DOCS"] = False
        tc.variables["WITH_CODE_COVERAGE"] = False
        tc.variables["WITH_TESTS"] = not self.conf.get("tools.build:skip_test", default=False)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()
        # Remove CMakeDeps-generated gtest config so the package's own
        # GTestConfig.cmake (with GTest::gtest, GTest::gmock targets) is used.
        import glob
        for f in glob.glob(os.path.join(self.generators_folder, "gtest*")):
            os.remove(f)
        for f in glob.glob(os.path.join(self.generators_folder, "GTest*")):
            os.remove(f)

    def _apply_portability_fixes(self):
        """Replace C++20 features unsupported by Clang15 libc++ on OHOS."""
        src = self.source_folder
        # Fix .pc.in library name: -llibpkgmanifest → -lpkgmanifest
        replace_in_file(self, os.path.join(src, "src/libpkgmanifest.pc.in"),
            "-llibpkgmanifest", "-lpkgmanifest", strict=False)
        # Add yaml-cpp include/link dirs (upstream relies on system install paths)
        replace_in_file(self, os.path.join(src, "CMakeLists.txt"),
            "pkg_check_modules(YAMLCPP REQUIRED yaml-cpp)\n",
            "pkg_check_modules(YAMLCPP REQUIRED yaml-cpp)\ninclude_directories(${YAMLCPP_INCLUDE_DIRS})\nlink_directories(${YAMLCPP_LIBRARY_DIRS})\n",
            strict=False)
        # Remove -Werror (C++20 portability changes trigger new warnings)
        replace_in_file(self, os.path.join(src, "CMakeLists.txt"),
            "add_compile_options(-Wall -Wextra -Werror)",
            "add_compile_options(-Wall -Wextra)", strict=False)
        # std::format → string concatenation in source files
        _fmt_files = [
            ("src/api/input/parser.cpp", None),
            ("src/api/manifest/parser.cpp", None),
            ("src/api/manifest/serializer.cpp", None),
            ("src/impl/common/objects/version/versionserializer.cpp", None),
            ("src/impl/input/operations/prototypefileconverter/prototypefileconverter.cpp", None),
            ("src/impl/manifest/objects/nevra/nevra.cpp", None),
            ("src/impl/manifest/objects/package/package.cpp", None),
            ("src/impl/manifest/operations/packagerepositorybinder/packagerepositorybinder.cpp", None),
            ("test/impl/input/operations/prototypefileconvertertest.cpp", None),
        ]
        for f, _ in _fmt_files:
            replace_in_file(self, os.path.join(src, f), "#include <format>", "", strict=False)
        # versionserializer.cpp
        replace_in_file(self, os.path.join(src, "src/impl/common/objects/version/versionserializer.cpp"),
            'std::format("{}.{}.{}", version.get_major(), version.get_minor(), version.get_patch())',
            'std::to_string(version.get_major()) + "." + std::to_string(version.get_minor()) + "." + std::to_string(version.get_patch())',
            strict=False)
        # prototypefileconverter.cpp
        replace_in_file(self, os.path.join(src, "src/impl/input/operations/prototypefileconverter/prototypefileconverter.cpp"),
            'version_node->set(std::format("{}.{}.{}",',
            'version_node->set(std::to_string(', strict=False)
        replace_in_file(self, os.path.join(src, "src/impl/input/operations/prototypefileconverter/prototypefileconverter.cpp"),
            "        INPUT_PROTOTYPE_DOCUMENT_VERSION_MAJOR,\n        INPUT_PROTOTYPE_DOCUMENT_VERSION_MINOR,\n        INPUT_PROTOTYPE_DOCUMENT_VERSION_PATCH));",
            "INPUT_PROTOTYPE_DOCUMENT_VERSION_MAJOR) + \".\" + std::to_string(INPUT_PROTOTYPE_DOCUMENT_VERSION_MINOR) + \".\" + std::to_string(INPUT_PROTOTYPE_DOCUMENT_VERSION_PATCH));",
            strict=False)
        # nevra.cpp
        replace_in_file(self, os.path.join(src, "src/impl/manifest/objects/nevra/nevra.cpp"),
            'std::format("{}-{}.{}", name, to_evr_string(), arch)',
            'name + "-" + to_evr_string() + "." + arch', strict=False)
        replace_in_file(self, os.path.join(src, "src/impl/manifest/objects/nevra/nevra.cpp"),
            'std::format("{}{}-{}", epoch_string, version, release)',
            'epoch_string + version + "-" + release', strict=False)
        # package.cpp
        replace_in_file(self, os.path.join(src, "src/impl/manifest/objects/package/package.cpp"),
            "throw PackageRepositoryNotAttachedError(std::format(\n            \"Repository is not configured yet for package '{}'\", nevra->to_string()));",
            "throw PackageRepositoryNotAttachedError(\"Repository is not configured yet for package '\" + nevra->to_string() + \"'\");",
            strict=False)
        # packagerepositorybinder.cpp
        replace_in_file(self, os.path.join(src, "src/impl/manifest/operations/packagerepositorybinder/packagerepositorybinder.cpp"),
            "throw PackageRepositoryBinderIdNotFoundError(std::format(\n            \"Repository with '{}' id does not exist in configured repositories for package '{}'\",\n            repo_id, package.get_nevra().to_string()));",
            "throw PackageRepositoryBinderIdNotFoundError(\"Repository with '\" + repo_id + \"' id does not exist in configured repositories for package '\" + package.get_nevra().to_string() + \"'\");",
            strict=False)
        # parser.cpp (input)
        replace_in_file(self, os.path.join(src, "src/api/input/parser.cpp"),
            'std::format("An error occurred during parsing of the input file at \\"{}\\": {}", path, error.what())',
            '"An error occurred during parsing of the input file at \\"" + path + "\\": " + error.what()',
            strict=False)
        replace_in_file(self, os.path.join(src, "src/api/input/parser.cpp"),
            'std::format("An error occurred during parsing of the input prototype file at \\"{}\\": {}", path, error.what())',
            '"An error occurred during parsing of the input prototype file at \\"" + path + "\\": " + error.what()',
            strict=False)
        # parser.cpp (manifest)
        replace_in_file(self, os.path.join(src, "src/api/manifest/parser.cpp"),
            'std::format("An error occurred during parsing of the manifest file at \\"{}\\": {}", path, error.what())',
            '"An error occurred during parsing of the manifest file at \\"" + path + "\\": " + error.what()',
            strict=False)
        # serializer.cpp
        replace_in_file(self, os.path.join(src, "src/api/manifest/serializer.cpp"),
            'std::format("An error occurred during serialization of the manifest file at \\"{}\\": {}", path, error.what())',
            '"An error occurred during serialization of the manifest file at \\"" + path + "\\": " + error.what()',
            strict=False)
        # test: prototypefileconvertertest.cpp
        replace_in_file(self, os.path.join(src, "test/impl/input/operations/prototypefileconvertertest.cpp"),
            '    EXPECT_EQ(std::format("{}.{}.{}", \n        INPUT_PROTOTYPE_DOCUMENT_VERSION_MAJOR,\n        INPUT_PROTOTYPE_DOCUMENT_VERSION_MINOR,\n        INPUT_PROTOTYPE_DOCUMENT_VERSION_PATCH), node->get("version")->as_string());',
            '    EXPECT_EQ(std::to_string(INPUT_PROTOTYPE_DOCUMENT_VERSION_MAJOR) + "." + std::to_string(INPUT_PROTOTYPE_DOCUMENT_VERSION_MINOR) + "." + std::to_string(INPUT_PROTOTYPE_DOCUMENT_VERSION_PATCH), node->get("version")->as_string());',
            strict=False)
        # impl/manifest/objects/packages/packages.cpp: std::views::values/keys + std::ranges::copy
        replace_in_file(self, os.path.join(src, "src/impl/manifest/objects/packages/packages.cpp"),
            "#include <ranges>", "", strict=False)
        replace_in_file(self, os.path.join(src, "src/impl/manifest/objects/packages/packages.cpp"),
            "    for (const auto & arch_packages : other.packages | std::views::values) {",
            "    for (const auto & [arch, arch_packages] : other.packages) {", strict=False)
        replace_in_file(self, os.path.join(src, "src/impl/manifest/objects/packages/packages.cpp"),
            "    std::ranges::copy(packages | std::views::keys, std::back_inserter(archs));",
            "    for (const auto & [arch, _] : packages) { archs.push_back(arch); }", strict=False)
        # std::views::filter → manual loops
        replace_in_file(self, os.path.join(src, "src/api/manifest/packages.cpp"),
            "#include <ranges>", "", strict=False)
        replace_in_file(self, os.path.join(src, "src/api/manifest/packages.cpp"),
            "        auto filtered_noarch = noarch_internal_packages | std::views::filter([&basearch](const auto & package) {\n"
            "            auto parent_archs = package->get_parent_archs();\n"
            "            return parent_archs.empty() || std::find(parent_archs.begin(), parent_archs.end(), basearch) != parent_archs.end();\n"
            "        });\n"
            "        auto noarch_packages = p_impl->wrap_internal_items(filtered_noarch);\n"
            "        std::move(noarch_packages.begin(), noarch_packages.end(), std::back_inserter(packages));",
            "        for (const auto & package : noarch_internal_packages) {\n"
            "            auto parent_archs = package->get_parent_archs();\n"
            "            if (parent_archs.empty() || std::find(parent_archs.begin(), parent_archs.end(), basearch) != parent_archs.end()) {\n"
            "                packages.push_back(p_impl->wrap_internal_item(package.get()));\n"
            "            }\n"
            "        }",
            strict=False)
        replace_in_file(self, os.path.join(src, "src/api/manifest/packages.cpp"),
            "        auto filtered_src = src_internal_packages | std::views::filter([&packages](const auto & source) {\n"
            "            return !std::any_of(packages.begin(), packages.end(), [&source](auto & package) {\n"
            "                return package.get_nevra().to_string() == source->get_nevra().to_string();\n"
            "            });\n"
            "        });\n"
            "        auto source_packages = p_impl->wrap_internal_items(filtered_src);\n"
            "        std::move(source_packages.begin(), source_packages.end(), std::back_inserter(packages));",
            "        for (const auto & source : src_internal_packages) {\n"
            "            bool found = std::any_of(packages.begin(), packages.end(), [&source](auto & package) {\n"
            "                return package.get_nevra().to_string() == source->get_nevra().to_string();\n"
            "            });\n"
            "            if (!found) {\n"
            "                packages.push_back(p_impl->wrap_internal_item(source.get()));\n"
            "            }\n"
            "        }",
            strict=False)

    def build(self):
        apply_conandata_patches(self)
        self._apply_portability_fixes()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游 gtest 测试（本地为 OHOS aarch64 真机，可直接执行）
        # /tmp 只读，设置 TMPDIR 到可写目录
        if not self.conf.get("tools.build:skip_test", default=False):
            # /tmp 只读，设置 TMPDIR 到可写目录
            from conan.tools.env import Environment
            test_env = Environment()
            test_env.define("TMPDIR", os.environ.get("TMPDIR", "/data/storage/el2/base/cache"))
            envvars = test_env.vars(self, scope="build")
            with envvars.apply():
                self.run("ctest --output-on-failure -j4", cwd=self.build_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["pkgmanifest"]
        self.cpp_info.set_property("pkg_config_name", "libpkgmanifest")
        self.cpp_info.requires = ["yaml-cpp::yaml-cpp"]
