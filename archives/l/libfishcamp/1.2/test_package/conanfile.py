import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # R34: the test must actually exercise the package's API. CMakeDeps and
    # CMakeToolchain are generated automatically via the generators attribute.
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libfishcamp's public header (fishcamp_common.h) includes <libusb.h>,
        # and our test directly links libusb-1.0. Require it explicitly so
        # CMakeDeps generates libusb's full include dirs (transitive-only deps
        # get an empty INCLUDE_DIRS in the generated data file on this host).
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # E002: OHOS /tmp is read-only; clang needs a writable TMPDIR that also
        # supports mkfifo (make's parallel jobserver). Prefer the HMBS task
        # temp dir, fall back to a build-folder subdir. We also force a serial
        # build (-j1) because make's parallel jobserver triggers a silent clang
        # failure on this OHOS/clang-15 host.
        tmp = None
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            v = os.environ.get(var)
            if v and os.path.isdir(v):
                tmp = v
                break
        if tmp is None:
            tmp = os.path.join(self.build_folder, "tmp_hmbs")
            try:
                os.makedirs(tmp, exist_ok=True)
            except OSError:
                pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp
        cmake = CMake(self)
        cmake.configure()
        # R: bind build output to a file (conan run() 输出流继承会静默吞掉编译器
        # 诊断)，并强制串行 -j1（make jobserver 在此宿主触发静默 clang 失败）。
        with open(os.path.join(self.build_folder, "build.log"), "w") as logf:
            cmake.build(build_tool_args=["-j1"], stdout=logf, stderr=logf)

    def test(self):
        # CI L0d 静态门禁要求 test() 含 self.run()（不能只 cmake.test()）。
        # 直接运行测试二进制；env="conanrun" 注入 LD_LIBRARY_PATH，解决
        # CMAKE_SKIP_RPATH + 动态链接 libusb-1.0.so 时裸跑找不到 .so 的问题。
        import glob
        cands = glob.glob(os.path.join(self.build_folder, "**", "test_fishcamp"),
                          recursive=True)
        bin_path = cands[0] if cands else os.path.join(self.build_folder,
                                                      "test_fishcamp")
        self.run(bin_path, env="conanrun")
