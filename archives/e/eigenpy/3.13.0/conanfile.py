#!/usr/bin/env python3
"""Conan recipe - eigenpy 3.13.0 (CMake + Boost.Python)."""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    download,
    export_conandata_patches,
    get,
    replace_in_file,
    unzip,
)


class EigenpyConan(ConanFile):
    name = "eigenpy"
    version = "3.13.0"
    description = "Bindings between NumPy and Eigen using Boost.Python"
    license = "BSD-2-Clause"
    homepage = "https://github.com/stack-of-tasks/eigenpy"
    url = "https://github.com/stack-of-tasks/eigenpy"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("eigen/3.4.0")
        # eigenpy requires the Boost.Python-enabled Boost revision.
        self.requires("boost/1.90.0.2.1", force=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["cmake_submodule"],
            destination=os.path.join(self.source_folder, "cmake"),
            filename="jrl-cmakemodules-f07de7952b35caf1c7a53a49138772cb9c534cf5.tar.gz",
            verify=False,
            retry=3,
            retry_wait=5,
            strip_root=True,
        )
        numpy_headers = self.conan_data["numpy_headers"]
        numpy_archive = os.path.join(self.source_folder, "numpy-headers.whl")
        download(
            self,
            url=numpy_headers["url"],
            filename=numpy_archive,
            sha256=numpy_headers["sha256"],
        )
        unzip(
            self,
            numpy_archive,
            destination=os.path.join(self.source_folder, "third_party", "numpy-wheel"),
        )

    def build(self):
        apply_conandata_patches(self)
        python = self._discover_python()
        self._patch_ohos_python_linkage()
        boost_python = self._boost_python_library(python)
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = self._cmake_defs(python, boost_python)

        self._run_cmake_configure(python, bdir, defs)
        self._run_cmake_build(bdir)

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder)
        )
        self._sign_binaries()

    def _cmake_defs(self, python, boost_python):
        defs = [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(
                self.package_folder.replace("\\", "/")
            ),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DBUILD_TESTING=OFF",
            "-DBUILD_TESTING_SCIPY=OFF",
            "-DBUILD_WITH_CHOLMOD_SUPPORT=OFF",
            "-DBUILD_WITH_ACCELERATE_SUPPORT=OFF",
            "-DGENERATE_PYTHON_STUBS=OFF",
            "-DINSTALL_DOCUMENTATION=OFF",
            "-DSUFFIX_SO_VERSION=OFF",
            "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            '-DEigen3_DIR="{}/share/eigen3/cmake"'.format(
                self.dependencies["eigen"].package_folder.replace("\\", "/")
            ),
        ]

        if self.settings.os == "OHOS":
            toolchain = self._ohos_toolchain()
            defs.extend(
                [
                    '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain.replace("\\", "/")),
                    "-DOHOS_ARCH=arm64-v8a",
                ]
            )
            ranlib = self._llvm_ranlib(toolchain)
            if ranlib:
                defs.append('-DCMAKE_RANLIB="{}"'.format(ranlib.replace("\\", "/")))

        preload = self._find_deps_preload(python)
        if preload:
            defs.append(
                '-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(
                    preload.replace("\\", "/")
                )
            )

        boost = self.dependencies["boost"].package_folder.replace("\\", "/")
        boost_libdir = os.path.join(boost, "lib").replace("\\", "/")
        boost_includedir = os.path.join(boost, "include").replace("\\", "/")
        component = boost_python["component"]
        component_upper = component.upper().replace("-", "_")
        boost_python_library = boost_python["library"].replace("\\", "/")
        python_library = python["library"].replace("\\", "/")
        defs.extend(
            [
                '-DBOOST_ROOT="{}"'.format(boost),
                '-DBoost_INCLUDE_DIR="{}"'.format(boost_includedir),
                '-DBoost_LIBRARY_DIR_RELEASE="{}"'.format(boost_libdir),
                '-DBoost_{}_LIBRARY="{}"'.format(
                    component_upper, boost_python_library
                ),
                '-DBoost_{}_LIBRARY_RELEASE="{}"'.format(
                    component_upper, boost_python_library
                ),
                '-DBoost_PYTHON_LIBRARY="{}"'.format(boost_python_library),
                '-DPYTHON_EXECUTABLE="{}"'.format(python["executable"]),
                '-DPYTHON_LIBRARY="{}"'.format(python_library),
                '-DPYTHON_LIBRARIES="{}"'.format(python_library),
                '-DOHOS_PYTHON_LIBRARY="{}"'.format(python_library),
                '-DPython_EXECUTABLE="{}"'.format(python["executable"]),
                '-DPython_ROOT_DIR="{}"'.format(python["prefix"]),
                '-DPython_INCLUDE_DIR="{}"'.format(python["include_dir"]),
                '-DPython_INCLUDE_DIRS="{}"'.format(python["include_dir"]),
                '-DPython_LIBRARY="{}"'.format(python_library),
                '-DPython_LIBRARIES="{}"'.format(python_library),
                "-DPython_FIND_STRATEGY=LOCATION",
                '-DPython3_EXECUTABLE="{}"'.format(python["executable"]),
                '-DPython3_ROOT_DIR="{}"'.format(python["prefix"]),
                '-DPYTHON_INCLUDE_DIR="{}"'.format(python["include_dir"]),
                '-DPython3_INCLUDE_DIR="{}"'.format(python["include_dir"]),
                '-DPython3_INCLUDE_DIRS="{}"'.format(python["include_dir"]),
                '-DPython3_LIBRARY="{}"'.format(python_library),
                '-DPython3_LIBRARIES="{}"'.format(python_library),
                "-DPython3_FIND_STRATEGY=LOCATION",
                '-DNUMPY_INCLUDE_DIRS="{}"'.format(python["numpy_include"]),
                '-DNUMPY_VERSION="{}"'.format(python["numpy_version"]),
                '-DPython_NumPy_INCLUDE_DIR="{}"'.format(python["numpy_include"]),
                '-DPython_NumPy_INCLUDE_DIRS="{}"'.format(python["numpy_include"]),
                '-DPython_NumPy_VERSION="{}"'.format(python["numpy_version"]),
                '-DPython3_NumPy_INCLUDE_DIR="{}"'.format(python["numpy_include"]),
                '-DPython3_NumPy_INCLUDE_DIRS="{}"'.format(python["numpy_include"]),
                '-DPython3_NumPy_VERSION="{}"'.format(python["numpy_version"]),
                "-DPYTHON_STANDARD_LAYOUT=ON",
                "-DPYTHON_SITELIB=lib/python{}/site-packages".format(
                    python["ver"]
                ),
            ]
        )
        return defs

    def _run_cmake_configure(self, python, bdir, defs):
        old_pythonpath = os.environ.get("PYTHONPATH", "")
        stub_pythonpath = python.get("numpy_pythonpath", "")
        if stub_pythonpath:
            os.environ["PYTHONPATH"] = os.pathsep.join(
                [stub_pythonpath] + ([old_pythonpath] if old_pythonpath else [])
            )
        try:
            self.run(
                'cmake {} -B "{}" -S "{}" {}'.format(
                    self._cmake_generator_arg(),
                    bdir,
                    self.source_folder,
                    " ".join(defs),
                )
            )
        finally:
            if stub_pythonpath:
                if old_pythonpath:
                    os.environ["PYTHONPATH"] = old_pythonpath
                else:
                    os.environ.pop("PYTHONPATH", None)

    def _cmake_generator_arg(self):
        if self.settings.os == "OHOS" and shutil.which("ninja"):
            return '-G "Ninja"'
        return ""

    def _run_cmake_build(self, bdir):
        jobs = self._build_jobs()
        self.run('cmake --build "{}" --parallel {}'.format(bdir, jobs))

    def _build_jobs(self):
        default_jobs = 2 if self.settings.os == "OHOS" else (os.cpu_count() or 1)
        configured = self.conf.get(
            "tools.build:jobs", default=default_jobs, check_type=int
        )
        if self.settings.os == "OHOS":
            return max(1, min(configured, 2))
        return max(1, configured)

    def _discover_python(self):
        candidates = [
            os.environ.get("EIGENPY_PYTHON"),
            os.environ.get("NANOBIND_PYTHON"),
            shutil.which("python3.12"),
            shutil.which("python3"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/data/service/hnp/bin/python3",
            "/data/app/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        executable = next((c for c in candidates if c and os.path.isfile(c)), None)
        if not executable:
            raise ConanInvalidConfiguration(
                "python3 not found; eigenpy needs CPython with Python.h and NumPy"
            )

        code = (
            "import json,os,sys,sysconfig;"
            "inc=sysconfig.get_path('include');"
            "incpy=sysconfig.get_config_var('INCLUDEPY') or inc;"
            "print(json.dumps({"
            "'inc':inc,'incpy':incpy,"
            "'prefix':sys.base_prefix,"
            "'ver':sysconfig.get_python_version(),"
            "'major':sys.version_info[0],"
            "'minor':sys.version_info[1],"
            "'libdir':sysconfig.get_config_var('LIBDIR'),"
            "'libpl':sysconfig.get_config_var('LIBPL'),"
            "'ldlibrary':sysconfig.get_config_var('LDLIBRARY'),"
            "'libpython':next((l.split()[-1] for l in open('/proc/self/maps') "
            "if 'libpython' in l), '') if os.path.exists('/proc/self/maps') else ''"
            "}))"
        )
        try:
            info = json.loads(
                subprocess.check_output([executable, "-c", code], text=True)
            )
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to query Python from {}: {}".format(executable, exc)
            ) from exc

        ver = info["ver"]
        root = os.path.dirname(os.path.dirname(os.path.realpath(executable)))
        include_candidates = [
            info.get("incpy"),
            info.get("inc"),
            os.path.join(info.get("prefix") or "", "include", "python{}".format(ver)),
            os.path.join(info.get("prefix") or "", "include", "python{}m".format(ver)),
            os.path.join(root, "include", "python{}".format(ver)),
            os.path.expanduser("~/usr/local/include/python{}".format(ver)),
            "/data/service/hnp/include/python{}".format(ver),
            "/usr/local/include/python{}".format(ver),
            "/usr/include/python{}".format(ver),
        ]
        include_dir = next(
            (
                d
                for d in include_candidates
                if d and os.path.isfile(os.path.join(d, "Python.h"))
            ),
            None,
        )
        if not include_dir:
            raise ConanInvalidConfiguration(
                "Python.h not found for {}. Checked: {}".format(
                    executable, [d for d in include_candidates if d]
                )
            )

        numpy = self._numpy_info(executable)

        library = self._libpython_file(executable, info, ver)
        return {
            "executable": executable.replace("\\", "/"),
            "include_dir": include_dir.replace("\\", "/"),
            "library": library.replace("\\", "/"),
            "numpy_include": numpy["include"].replace("\\", "/"),
            "numpy_version": numpy["version"],
            "numpy_pythonpath": numpy.get("pythonpath", "").replace("\\", "/"),
            "prefix": (info.get("prefix") or root).replace("\\", "/"),
            "ver": ver,
            "major": int(info["major"]),
            "minor": int(info["minor"]),
        }

    def _numpy_info(self, executable):
        code = (
            "import json,numpy;"
            "print(json.dumps({'include':numpy.get_include(),"
            "'version':getattr(numpy,'__version__','0')}))"
        )
        try:
            numpy = json.loads(
                subprocess.check_output([executable, "-c", code], text=True)
            )
        except Exception:
            numpy = {}

        include_dir = numpy.get("include")
        if self._has_numpy_header(include_dir):
            return {
                "include": include_dir,
                "version": numpy.get("version") or self._fallback_numpy_version(),
            }

        include_dir = self._vendored_numpy_include()
        version = self._fallback_numpy_version()
        return {
            "include": include_dir,
            "version": version,
            "pythonpath": self._write_numpy_stub(include_dir, version),
        }

    def _has_numpy_header(self, include_dir):
        return bool(
            include_dir
            and os.path.isfile(os.path.join(include_dir, "numpy", "arrayobject.h"))
        )

    def _vendored_numpy_include(self):
        candidates = [
            os.path.join(
                self.source_folder, "third_party", "numpy-wheel", "numpy", "_core", "include"
            ),
            os.path.join(
                self.source_folder, "third_party", "numpy-wheel", "numpy", "core", "include"
            ),
        ]
        for include_dir in candidates:
            if self._has_numpy_header(include_dir):
                return include_dir
        raise ConanInvalidConfiguration(
            "NumPy headers not found in Python environment or vendored wheel. "
            "Checked: {}".format(candidates)
        )

    def _fallback_numpy_version(self):
        return str(self.conan_data.get("numpy_headers", {}).get("version", "0"))

    def _write_numpy_stub(self, include_dir, version):
        stub_root = os.path.join(self.build_folder, "numpy-stub")
        package_dir = os.path.join(stub_root, "numpy")
        os.makedirs(package_dir, exist_ok=True)
        with open(os.path.join(package_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(
                "__version__ = {!r}\n"
                "def get_include():\n"
                "    return {!r}\n".format(version, include_dir.replace("\\", "/"))
            )
        return stub_root

    def _boost_python_library(self, python):
        boost = self.dependencies["boost"].package_folder
        libdir = os.path.join(boost, "lib")
        stems = [
            "boost_python{}{}".format(python["major"], python["minor"]),
            "boost_python{}".format(python["major"]),
            "boost_python",
        ]
        suffixes = [".so", ".so.*", ".a", ".dylib", ".lib"]
        for stem in stems:
            matches = []
            for suffix in suffixes:
                matches.extend(glob.glob(os.path.join(libdir, "lib" + stem + suffix)))
                matches.extend(glob.glob(os.path.join(libdir, stem + suffix)))
            matches = sorted(set(matches))
            if matches:
                component = stem.replace("boost_", "")
                return {"component": component, "library": matches[0]}

        raise ConanInvalidConfiguration(
            "boost/1.90.0.2.1 package does not contain Boost.Python for "
            "Python {}.{} (looked for libboost_python{}{}.so, "
            "libboost_python{}.so, or libboost_python.so). Adapt/publish Boost "
            "with the python component in a separate PR before building eigenpy.".format(
                python["major"],
                python["minor"],
                python["major"],
                python["minor"],
                python["major"],
            )
        )

    def _patch_ohos_python_linkage(self):
        if self.settings.os != "OHOS":
            return

        self._patch_cmake_python_linkage(
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "target_link_boost_python(${PROJECT_NAME} PUBLIC)",
            "${PROJECT_NAME}",
            "building libeigenpy.so",
        )
        self._patch_cmake_python_linkage(
            os.path.join(self.source_folder, "python", "CMakeLists.txt"),
            "target_link_libraries(${PYWRAP} PUBLIC ${PROJECT_NAME})",
            "${PYWRAP}",
            "building eigenpy_pywrap",
        )

    def _patch_cmake_python_linkage(self, cmakelists, needle, target, context):
        marker = "OHOS_PYTHON_LINK_LIBRARIES"
        with open(cmakelists, "r", encoding="utf-8") as f:
            contents = f.read()
        if marker in contents:
            return

        replacement = """{}

# OHOS_PYTHON_LINK_LIBRARIES: lld requires Python symbols to be resolved when
# {}; upstream only links Boost.Python here.
if(OHOS_PYTHON_LIBRARY)
  target_link_libraries({} PRIVATE "${{OHOS_PYTHON_LIBRARY}}")
elseif(TARGET Python::Python)
  target_link_libraries({} PRIVATE Python::Python)
elseif(TARGET Python3::Python)
  target_link_libraries({} PRIVATE Python3::Python)
elseif(Python_LIBRARIES)
  target_link_libraries({} PRIVATE ${{Python_LIBRARIES}})
elseif(Python3_LIBRARIES)
  target_link_libraries({} PRIVATE ${{Python3_LIBRARIES}})
elseif(PYTHON_LIBRARIES)
  target_link_libraries({} PRIVATE ${{PYTHON_LIBRARIES}})
endif()""".format(
            needle, context, target, target, target, target, target, target
        )
        replace_in_file(self, cmakelists, needle, replacement)

    def _libpython_file(self, executable, info, ver):
        libpython = info.get("libpython") or ""
        if libpython and os.path.isfile(libpython):
            return libpython

        root = os.path.dirname(os.path.dirname(os.path.realpath(executable)))
        names = [
            info.get("ldlibrary"),
            "libpython{}.so".format(ver),
            "libpython{}m.so".format(ver),
        ]
        dirs = [
            info.get("libpl"),
            info.get("libdir"),
            os.path.join(info.get("prefix") or "", "lib"),
            os.path.join(root, "lib"),
            os.path.expanduser("~/usr/local/lib"),
            "/data/service/hnp/lib",
            "/usr/local/lib",
            "/usr/lib",
        ]
        patterns = [
            name
            for name in names
            if name and (name.startswith("libpython") or name.endswith((".so", ".a")))
        ]
        patterns.extend(["libpython{}.so.*".format(ver), "libpython{}m.so.*".format(ver)])
        for directory in dirs:
            if not directory:
                continue
            matches = []
            for pattern in patterns:
                matches.extend(glob.glob(os.path.join(directory, pattern)))
            matches = [m for m in sorted(set(matches)) if os.path.isfile(m)]
            if matches:
                return matches[0]

        for root_dir in (info.get("prefix"), root, os.path.expanduser("~/usr/local")):
            if not root_dir or not os.path.isdir(root_dir):
                continue
            try:
                out = subprocess.check_output(
                    ["find", root_dir, "-name", "libpython{}*.so*".format(ver)],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=30,
                ).splitlines()
            except Exception:
                out = []
            matches = [p for p in out if os.path.isfile(p)]
            if matches:
                return sorted(matches)[0]

        raise ConanInvalidConfiguration(
            "libpython{}.so not found for {}. Checked: {}".format(
                ver, executable, [d for d in dirs if d]
            )
        )

    def _find_deps_preload(self, python):
        deps = [
            d.package_folder.replace("\\", "/")
            for _ref, d in self.dependencies.items()
            if d.package_folder
        ]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for dep in deps:
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "{}")\n'.format(dep))
                f.write('list(APPEND CMAKE_PREFIX_PATH "{}")\n'.format(dep))
            self._write_python_preload(f, python)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM BOTH)\n")
        return path

    def _write_python_preload(self, f, python):
        entries = {
            "PYTHON_EXECUTABLE": ("FILEPATH", python["executable"]),
            "PYTHON_INCLUDE_DIR": ("PATH", python["include_dir"]),
            "PYTHON_LIBRARY": ("FILEPATH", python["library"]),
            "PYTHON_LIBRARIES": ("FILEPATH", python["library"]),
            "OHOS_PYTHON_LIBRARY": ("FILEPATH", python["library"]),
            "Python_EXECUTABLE": ("FILEPATH", python["executable"]),
            "Python_ROOT_DIR": ("PATH", python["prefix"]),
            "Python_INCLUDE_DIR": ("PATH", python["include_dir"]),
            "Python_INCLUDE_DIRS": ("PATH", python["include_dir"]),
            "Python_LIBRARY": ("FILEPATH", python["library"]),
            "Python_LIBRARIES": ("FILEPATH", python["library"]),
            "Python_FIND_STRATEGY": ("STRING", "LOCATION"),
            "Python3_EXECUTABLE": ("FILEPATH", python["executable"]),
            "Python3_ROOT_DIR": ("PATH", python["prefix"]),
            "Python3_INCLUDE_DIR": ("PATH", python["include_dir"]),
            "Python3_INCLUDE_DIRS": ("PATH", python["include_dir"]),
            "Python3_LIBRARY": ("FILEPATH", python["library"]),
            "Python3_LIBRARIES": ("FILEPATH", python["library"]),
            "Python3_FIND_STRATEGY": ("STRING", "LOCATION"),
            "NUMPY_INCLUDE_DIRS": ("PATH", python["numpy_include"]),
            "NUMPY_VERSION": ("STRING", python["numpy_version"]),
            "Python_NumPy_INCLUDE_DIR": ("PATH", python["numpy_include"]),
            "Python_NumPy_INCLUDE_DIRS": ("PATH", python["numpy_include"]),
            "Python_NumPy_VERSION": ("STRING", python["numpy_version"]),
            "Python3_NumPy_INCLUDE_DIR": ("PATH", python["numpy_include"]),
            "Python3_NumPy_INCLUDE_DIRS": ("PATH", python["numpy_include"]),
            "Python3_NumPy_VERSION": ("STRING", python["numpy_version"]),
        }
        for name, (kind, value) in entries.items():
            f.write('set({} "{}" CACHE {} "" FORCE)\n'.format(name, value, kind))

    def _ohos_toolchain(self):
        candidates = []
        user_toolchain = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[],
            check_type=list,
        )
        candidates.extend(user_toolchain)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
                )
            )
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "ohos.toolchain.cmake not found; set OHOS_NDK_HOME or profile user_toolchain"
        )

    def _llvm_ranlib(self, toolchain):
        sdk_bin = os.path.normpath(
            os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        )
        candidate = os.path.join(sdk_bin, "llvm-ranlib")
        if os.path.isfile(candidate):
            return candidate
        return shutil.which("llvm-ranlib") or ""

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools unavailable; native validation must sign shared objects"
            )
            return

        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets.extend(
                glob.glob(
                    os.path.join(self.package_folder, "**", pattern), recursive=True
                )
            )
        for path in sorted(set(targets)):
            if os.path.islink(path) or not self._is_elf(path):
                continue
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        signed_mode = original_mode | 0o111
        temporary = "{}.signing".format(path)
        try:
            shutil.copy2(path, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, temporary))
            self.run(
                '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, temporary, temporary
                )
            )
            os.chmod(temporary, signed_mode)
            os.replace(temporary, path)
            os.chmod(path, signed_mode)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            "/data/service/hnp/bin/{}".format(name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = ["eigenpy"] if "eigenpy" in libs else libs
        self.cpp_info.set_property("cmake_file_name", "eigenpy")
        self.cpp_info.set_property("cmake_target_name", "eigenpy::eigenpy")
        self.cpp_info.set_property("pkg_config_name", "eigenpy")
        self.cpp_info.requires = ["eigen::eigen", "boost::python312"]

        site_dirs = glob.glob(
            os.path.join(self.package_folder, "lib", "python*", "site-packages")
        )
        for site_dir in site_dirs:
            self.runenv_info.prepend_path("PYTHONPATH", site_dir)
