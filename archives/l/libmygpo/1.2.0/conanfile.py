import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, load, replace_in_file, save, unzip


class LibmygpoConan(ConanFile):
    name = "libmygpo"
    version = "1.2.0"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/gpodder/libmygpo-qt"
    description = "Qt client library for the gpodder.net podcast API"
    def export_sources(self):
        copy(self, "upstream.py", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("qt/5.15.19")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.libmygpo:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        # Qt 5.15 no longer supplies this complete type transitively.
        replace_in_file(self, os.path.join(self.source_folder, "src", "EpisodeAction.cpp"),
                        '#include "EpisodeAction_p.h"',
                        '#include "EpisodeAction_p.h"\n#include <QDateTime>')
        # Preserve all five original JSON cases and their exact comparisons,
        # but bind dates to UTC rather than the device's local timezone.
        # Qt 5.15 serializes QVariant QDateTime with ISO milliseconds and Z;
        # the production episode serializer explicitly uses UTC ISODate.
        test = os.path.join(self.source_folder, "tests", "JsonCreatorTest.cpp")
        text = load(self, test)
        if text.count("QDateTime::fromString(") != 3:
            raise ConanInvalidConfiguration("Original date fixture inventory changed")
        text = text.replace("QDateTime::fromString(", "parseUtcFixture(")
        text = text.replace("using namespace mygpo;", '''using namespace mygpo;

static QDateTime parseUtcFixture(const QString &value, const QString &format)
{
    QDateTime result = QDateTime::fromString(value, format);
    result.setTimeSpec(Qt::UTC);
    return result;
}''')
        text = text.replace('1998-01-01T00:01:02', '1998-01-01T00:01:02Z')
        text = text.replace('1920-01-01T12:01:02', '1920-01-01T12:01:02Z')
        # Only setting5 is serialized by QJsonDocument::fromVariant.
        text = text.replace('setting5\\\":\\\"1998-01-01T00:01:02Z',
                            'setting5\\\":\\\"1998-01-01T00:01:02.000Z')
        save(self, test, text)
        # Export a genuinely relocatable native config, retaining its public
        # upstream package/target names and real Qt5 dependency targets.
        config = os.path.join(self.source_folder, "Mygpo-qtConfig.cmake.in")
        replace_in_file(self, config, 'set(LIBMYGPO_QT_INCLUDE_DIRS "@INCLUDE_INSTALL_DIR@")',
                        'set(LIBMYGPO_QT_INCLUDE_DIRS "${rootDir}/include/mygpo-qt5")\n'
                        'include(CMakeFindDependencyMacro)\n'
                        'find_dependency(Qt5 REQUIRED COMPONENTS Core Network CONFIG)')
        replace_in_file(self, config, 'set(LIBMYGPO_QT_LIBRARIES mygpo-qt@MYGPO_QT_VERSION_SUFFIX@ )',
                        'set_property(TARGET mygpo-qt@MYGPO_QT_VERSION_SUFFIX@ APPEND PROPERTY '
                        'INTERFACE_INCLUDE_DIRECTORIES "${LIBMYGPO_QT_INCLUDE_DIRS}")\n'
                        'set(LIBMYGPO_QT_LIBRARIES mygpo-qt@MYGPO_QT_VERSION_SUFFIX@ )')
        if self.source_folder != self.export_sources_folder:
            copy(self, "upstream.py", self.export_sources_folder, self.source_folder)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        qt = self.dependencies["qt"].package_folder
        for module in ("Qt5", "Qt5Core", "Qt5Network", "Qt5Test"):
            config = os.path.join(qt, "lib", "cmake", module)
            if not os.path.isfile(os.path.join(config, module + "Config.cmake")):
                raise ConanInvalidConfiguration("Published Qt is missing " + module)
            tc.variables[module + "_DIR"] = config.replace("\\", "/")
        tc.variables["MYGPO_BUILD_TESTS"] = True
        tc.variables["BUILD_WITH_QT6"] = False
        tc.variables["CMAKE_SKIP_RPATH"] = True
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run("python3 " + shlex.quote(os.path.join(self.source_folder, "upstream.py"))
                     + " " + shlex.quote(self.source_folder) + " " + shlex.quote(self.build_folder),
                     env=["conanbuild", "conanrun"])

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mygpo-qt5"]
        self.cpp_info.includedirs = ["include/mygpo-qt5"]
        self.cpp_info.requires = ["qt::core", "qt::network"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "Mygpo-qt5")
        self.cpp_info.set_property("cmake_target_name", "mygpo-qt5")
        self.cpp_info.builddirs = ["lib/cmake/mygpo-qt5"]
