import os
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.gnu import PkgConfigDeps


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["librsvg"].cpp_info
        # Collect include dirs from all dependencies, including versioned
        # subdirectories (e.g. glib-2.0, gdk-pixbuf-2.0, pango-1.0).
        # Also scan libdirs for include subdirs (glib puts glibconfig.h
        # in lib/glib-2.0/include/).
        incs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.includedirs:
                incs.append("-I" + _p)
                if not os.path.isdir(_p):
                    continue
                for _name in sorted(os.listdir(_p)):
                    _sub = os.path.join(_p, _name)
                    if os.path.isdir(_sub) and any(
                            f.endswith((".h", ".hpp", ".hh", ".hxx"))
                            for f in os.listdir(_sub)):
                        incs.append("-I" + _sub)
            # Also check libdirs for nested include paths (glibconfig.h)
            for _ld in _d.cpp_info.libdirs:
                if not os.path.isdir(_ld):
                    continue
                for _name in sorted(os.listdir(_ld)):
                    _sub = os.path.join(_ld, _name)
                    if not os.path.isdir(_sub):
                        continue
                    _inc = os.path.join(_sub, "include")
                    if os.path.isdir(_inc):
                        incs.append("-I" + _inc)
        inc = " ".join(dict.fromkeys(incs))
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # --- Link flags ---
        # librsvg-2.a is a static archive. It references symbols from
        # ~20 transitive dependencies (glib, cairo, pango, gdk-pixbuf,
        # harfbuzz, libxml2, freetype, ...). The consumer must explicitly
        # link every transitive library.
        #
        # Some packages (e.g. glib) use cpp_info.components with per-
        # component libs rather than cpp_info.libs. We must collect from
        # BOTH cpp_info.libs AND cpp_info.components[*].libs.
        #
        # Link order for static archives: a library must appear *before*
        # the libraries that satisfy its undefined symbols. So we put
        # librsvg first, then all other dependencies' libs, then system
        # libs last.
        link_libs = []
        # First: librsvg itself (the package under test)
        for _l in dep.libs:
            link_libs.append("-l" + _l)
        for _sl in dep.system_libs:
            link_libs.append("-l" + _sl)
        # Then: all other dependencies' libs and system_libs
        for _ref, _d in self.dependencies.items():
            if str(_ref.ref).split("/")[0] == "librsvg":
                continue
            # Collect from top-level cpp_info.libs
            for _l in _d.cpp_info.libs:
                link_libs.append("-l" + _l)
            # Collect from components (glib uses components)
            for _cname, _comp in _d.cpp_info.components.items():
                for _l in _comp.libs:
                    link_libs.append("-l" + _l)
                for _sl in _comp.system_libs:
                    link_libs.append("-l" + _sl)
            # Collect from top-level system_libs
            for _sl in _d.cpp_info.system_libs:
                link_libs.append("-l" + _sl)
        # Always add dl and m/pthread for static linking safety
        for _sys in ("dl", "m", "pthread"):
            _flag = "-l" + _sys
            if _flag not in link_libs:
                link_libs.append(_flag)

        cc = os.environ.get("CC", "clang")
        link = " ".join(["-L" + p for p in libdirs]
                        + link_libs
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
