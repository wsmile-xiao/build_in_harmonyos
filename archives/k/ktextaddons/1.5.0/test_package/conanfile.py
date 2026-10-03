import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KtextaddonsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The tested package (ktextaddons) ships its own
        # KF6<TextAddon>Config.cmake files (cmake_find_mode=none, so
        # CMakeDeps generates no find module for them), and those configs
        # chain through Qt6/KF6 targets. Both the ktextaddons and qtbase
        # cmake dirs must be on CMAKE_PREFIX_PATH (sonnet 6.26.0 test
        # package precedent).
        tc = CMakeToolchain(self)
        lines = []
        for dep_name in ("ktextaddons", "qtbase"):
            dep = self.dependencies.get(dep_name)
            if dep:
                pkg = dep.package_folder
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
        if lines:
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        self._prepare_runtime_links()
        cmake = CMake(self)
        with self._test_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _prepare_runtime_links(self):
        """The KF6 dependency packages in the graph record build-layout
        relative DT_NEEDED sonames (../../bin/libKF6ConfigCore.so from
        libKF6ConfigGui.so, libKF6SonnetCore.so from libKF6SonnetUi.so, ...).
        The musl loader resolves slash-containing DT_NEEDED entries from the
        process CWD, not from LD_LIBRARY_PATH, so drop symlinks of every KF6
        library into test_package/bin, which is where the ctest CWD (the
        conan build folder) resolves ../../bin to (kxmlgui 6.26.0
        test_package precedent)."""
        tp_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if name.startswith("libKF6") and name.endswith(".so"):
                    link = os.path.join(tp_bin, name)
                    if not os.path.lexists(link):
                        os.symlink(os.path.join(libdir, name), link)

    def _test_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.append(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, "lib"),
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        # Sandbox libc++_shared.so shadowing (kconfig 6.26.0 precedent).
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # SlideContainer is a QWidget; run headless (no xcb on OHOS).
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def test(self):
        with self._test_env().vars(self).apply():
            cmake = CMake(self)
            cmake.test()
        # Also run the binary directly (R34: real API execution). Source the
        # conanrun env script (it exports the LD_LIBRARY_PATH of every
        # dependency package, needed for the flat sonames like
        # libKF6TextUtils.so.1), then prepend /system/lib64 and select the
        # offscreen platform via an inline assignment: the ambient
        # LD_LIBRARY_PATH on the worker contains the SDK llvm/lib dir whose
        # libc++_shared.so shadows the compatible system one (kconfig
        # 6.26.0 precedent), and the inline prefix wins over every exported
        # value (validated by a manual run: 6/6 assertions PASS).
        self.run(
            '. ./generators/conanrun.sh && '
            'LD_LIBRARY_PATH="/system/lib64:$LD_LIBRARY_PATH" '
            'QT_QPA_PLATFORM=offscreen ./test_ktextaddons',
            cwd=self.build_folder,
        )
