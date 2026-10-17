#!/usr/bin/env python3
"""Conan recipe for plugin~ 0.2.1, a LADSPA host external for Pure Data."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PdPluginConan(ConanFile):
    name = "pd-plugin"
    version = "0.2.1"
    description = "Pure Data external that hosts LADSPA audio plugins"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info/downloads/plugin"
    url = "https://sourceforge.net/projects/pure-data/files/libraries/plugin~/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    no_copy_source = False

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("puredata/0.54.1")
        self.requires("ladspa-sdk/1.17")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "plugin~ is a Pure Data external loaded with dlopen and must be shared"
            )

    def source(self):
        # SourceForge's canonical redirect endpoint ends in `/download`, so
        # Conan cannot infer the archive type from the URL alone.
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename="plugin~-0.2.1.tar.gz",
            strip_root=True,
        )

    def _header_dir(self, dependency, header, suffixes):
        package_folder = self.dependencies[dependency].package_folder
        for suffix in suffixes:
            candidate = os.path.join(package_folder, *suffix)
            if os.path.isfile(os.path.join(candidate, header)):
                return candidate
        raise ConanInvalidConfiguration(
            f"{dependency} does not provide {header} below {package_folder}"
        )

    def _pd_include(self):
        return self._header_dir("puredata", "m_pd.h", (("include", "pd"), ("include",)))

    def _ladspa_include(self):
        return self._header_dir("ladspa-sdk", "ladspa.h", (("include",),))

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = shlex.quote(self._compiler())
        include_flags = " ".join(
            f"-I{shlex.quote(path)}" for path in (self._pd_include(), self._ladspa_include())
        )
        common = (
            "-std=gnu11 -fPIC -O2 -DNDEBUG -DPD -DUNIX -DHAVE_LOCALE_H "
            f"{include_flags}"
        )
        objects = []
        for source in ("plugin~.c", "jload.c", "jsearch.c"):
            obj = source[:-2].replace("~", "_tilde") + ".o"
            self.run(
                f"{cc} {common} -c {shlex.quote(os.path.join(self.source_folder, source))} "
                f"-o {shlex.quote(os.path.join(self.build_folder, obj))}",
                env="conanbuild",
            )
            objects.append(shlex.quote(os.path.join(self.build_folder, obj)))
        output = shlex.quote(os.path.join(self.build_folder, "plugin~.pd_linux"))
        self.run(
            f"{cc} -shared -Wl,-soname,plugin~.pd_linux -o {output} "
            f"{' '.join(objects)} -ldl -lm",
            env="conanbuild",
        )

    def package(self):
        plugin_dir = os.path.join(self.package_folder, "lib", "pd", "extra", "plugin~")
        copy(self, "plugin~.pd_linux", src=self.build_folder, dst=plugin_dir, keep_path=False)
        for pattern in ("plugin~-help.pd", "plugin~-gui.pd", "plugin~-meta.pd", "README.txt", "ChangeLog"):
            copy(self, pattern, src=self.source_folder, dst=plugin_dir, keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/pd/extra/plugin~"]
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PD_PATH", os.path.join(self.package_folder, "lib", "pd", "extra")
        )
