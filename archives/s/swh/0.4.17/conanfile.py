import os
import shlex
import sys
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, unzip, replace_in_file


class SwhConan(ConanFile):
    name = "swh"
    version = "0.4.17"
    description = "Steve Harris' complete LADSPA audio plugin collection"
    license = "GPL-2.0-or-later"
    homepage = "https://plugin.org.uk/"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "config.h.cmake", "generate_plugins.py", "xml_tree.py"

    def requirements(self):
        self.requires("fftw3f/3.3.10")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.swh:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        if self.export_sources_folder != self.source_folder:
            for leaf in self.exports_sources:
                copy(self, leaf, self.export_sources_folder, self.source_folder)
        generator = os.path.join(self.source_folder, "makestub.pl")
        replace_in_file(self, generator, "use XML::Parser;", "use JSON::PP;")
        replace_in_file(self, generator, "if (@ARGV != 1)", "if (@ARGV != 2)")
        replace_in_file(self, generator,
                        "$xmlp = new XML::Parser(Style => 'Tree', ParseParamEnt => 1, ErrorContext => 3, NoLWP => 1);\n@tree = $xmlp -> parsefile($filename);",
                        "open(my $tree_fh, '<', $ARGV[1]) or die $!;\n"
                        "my $tree_json; { local $/; $tree_json = <$tree_fh>; } close($tree_fh);\n"
                        "@tree = @{JSON::PP->new->decode($tree_json)};")
        # These header-defined functions have no external implementation.
        # C99 inline alone can leave unresolved calls when not inlined.
        replace_in_file(self, os.path.join(self.source_folder, "util", "waveguide_nl.h"),
                        "\ninline void waveguide_nl_", "\nstatic inline void waveguide_nl_")
    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SKIP_RPATH"] = True
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if not can_run(self):
            raise ConanInvalidConfiguration("Native Perl/XML source generation must be executable")
        if self.settings.os == "OHOS":
            # source() is settings-independent in Conan. Select the platform
            # planning policy here before the original Perl generator runs.
            # Transform parameters and audio result assertions are unchanged.
            for leaf in ("mbeq_1197.xml", "imp_1199.xml", "pitch_scale_1193.xml", "util/pitchscale.c"):
                replace_in_file(self, os.path.join(self.source_folder, leaf),
                                "FFTW_MEASURE", "FFTW_ESTIMATE")
        perl = os.path.join(self.dependencies.build["perl"].package_folder, "bin", "perl")
        perl_core = os.path.join(self.dependencies.build["perl"].package_folder, "lib", "perl5", "5.42.2")
        self.run(shlex.quote(sys.executable) + " " + shlex.quote(os.path.join(self.source_folder, "generate_plugins.py"))
                 + " " + shlex.quote(perl) + " " + shlex.quote(perl_core),
                 cwd=self.source_folder, env=["conanbuild", "conanrun"])
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/ladspa"]
        self.runenv_info.prepend_path("LADSPA_PATH", os.path.join(self.package_folder, "lib", "ladspa"))
