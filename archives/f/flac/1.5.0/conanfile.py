#!/usr/bin/env python3
"""Conan recipe — flac 1.5.0 (Free Lossless Audio Codec).

Build system: CMake (upstream CMakeLists.txt, cmake >= 3.12)
Dependencies: libogg/1.3.5 (static from conan, wired via OGG_INCLUDE_DIR/OGG_LIBRARY
              cache variables — upstream cmake/FindOgg.cmake uses find_path/find_library)

Upstream tests executed in build():
  - test_libFLAC (unit tests: bitreader/bitwriter/crc/encoders/decoders/metadata)
  - test_libFLAC++ (C++ binding unit tests)
  - test_grabbag cuesheet (6 good + 44 bad cuesheets + output diff vs cuesheet.ok)
  - test_grabbag picture (output diff vs picture.ok)
  - test_seeking (preprogrammed + random seeks)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import cmake_layout


class FlacConan(ConanFile):
    name = "flac"
    version = "1.5.0"
    description = "Free Lossless Audio Codec - lossless audio compression library and command-line tools"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/flac/"
    url = "https://github.com/xiph/flac"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # G1: 补丁导出钩子（本包零补丁，patches 段为空时是 no-op）
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.5")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下只有 llvm-ar，没有 llvm-ranlib，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指向 <sdk>/llvm/bin/llvm-ranlib。cmake 造静态库是
        # `<AR> qc ... && <RANLIB> <lib>`，于是 .o 全编得动、一造 .a 就 ENOENT：
        #   Error running link command: no such file or directory
        # （且报错不说是哪个程序找不到）。对策：PATH 里找 llvm-ranlib
        # （hnp 布局 /data/service/hnp/bin/llvm-ranlib 是指向 llvm-ar 的别名，ar 兼容 ranlib 调用）。
        sdk_ranlib = os.path.join(toolchain, "..", "..", "..", "llvm", "bin", "llvm-ranlib")
        if os.path.isfile(sdk_ranlib):
            return ""  # SDK 自带就用它的
        return shutil.which("llvm-ranlib") or ""

    def build(self):
        # glfw/libjpeg-turbo/zstd/opus 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035：System is unknown to cmake）。
        apply_conandata_patches(self)  # 本包零补丁（patches: {}），此处为 no-op，保留管线完整性
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        shared = "ON" if self.options.shared else "OFF"
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS={}".format(shared),
            "-DWITH_OGG=ON",
            "-DBUILD_PROGRAMS=ON",                  # flac / metaflac CLI
            "-DBUILD_CXXLIBS=ON",                   # libFLAC++
            "-DBUILD_TESTING=ON",                   # 上游测试
            "-DBUILD_EXAMPLES=OFF",
            "-DBUILD_DOCS=OFF",
            "-DINSTALL_MANPAGES=OFF",
            "-DINSTALL_PKGCONFIG_MODULES=ON",
            "-DINSTALL_CMAKE_CONFIG_MODULE=ON",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        # ── 依赖接线：上游 cmake/FindOgg.cmake 用 find_path(OGG_INCLUDE_DIR) + find_library(OGG_LIBRARY)。
        # 交叉链 FIND_ROOT_PATH_MODE=ONLY 会把 sysroot 外的 conan 包路径滤掉，
        # 故直接预置 find cache 变量为 libogg 包的真实路径（assimp ZLIB 同法）。
        ogg = self.dependencies["libogg"]
        ogg_lib = "libogg.a" if not self.options.shared else "libogg.so"
        ogg_lib_path = os.path.join(ogg.package_folder, "lib", ogg_lib)
        if not os.path.isfile(ogg_lib_path):
            # libogg 包可能只有一种变体，回退取目录里实际存在的
            cands = glob.glob(os.path.join(ogg.package_folder, "lib", "libogg.*"))
            if cands:
                ogg_lib_path = cands[0]
        defs.append('-DOGG_INCLUDE_DIR="{}/include"'.format(ogg.package_folder))
        defs.append('-DOGG_LIBRARY="{}"'.format(ogg_lib_path))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}" -j 4'.format(bdir))

        # ── 上游官方测试（ADAPTATION_GUIDE §3，在 build() 内执行并记录通过率）──
        self._run_upstream_tests(bdir)

    def _pick_test_dir(self):
        """选择 chmod 语义正确的测试目录（tempfs）。

        HMDFS（/storage/...）上 chmod 只读对以可写模式 open 不生效（mode 位被
        忽略），test_libFLAC 的 metadata level-1 "read-only file" 断言会误报
        writable。逐个候选目录实测 chmod 语义：创建文件→chmod 0444→尝试
        O_RDWR 打开→成功即该 FS 不可用，继续下一个。全部失败时回退 TMPDIR
        （测试会失败但保留诊断信息）。
        注意：不使用 ctypes 调 libc.fopen——实测在 HMDFS 路径上会段错误。
        """
        import tempfile

        def _chmod_respected(d):
            try:
                os.makedirs(d, exist_ok=True)
                probe = os.path.join(d, ".chmod-probe")
                with open(probe, "wb") as f:
                    f.write(b"x")
                os.chmod(probe, 0o444)
                try:
                    fd = os.open(probe, os.O_RDWR)
                    os.close(fd)
                    return False  # still writable -> chmod ignored (HMDFS)
                except PermissionError:
                    return True
                finally:
                    os.chmod(probe, 0o644)
                    os.unlink(probe)
            except OSError:
                return False

        tdir = os.environ.get("TMPDIR", tempfile.gettempdir())
        cands = []
        base = os.path.join(tdir, "flac-1.5.0-tests")
        cands.append(base)
        # OHOS 设备级 tempfs（本地实测 chmod 语义正确；CI worker 同为 OHOS 设备布局）
        cands.append("/data/storage/el2/base/temp/flac-1.5.0-tests")
        for c in cands:
            if _chmod_respected(c):
                return c
        # fallback：无 tempfs 可用，仍返回 TMPDIR（read-only 断言将失败并留诊断）
        os.makedirs(base, exist_ok=True)
        return base

    def _run_upstream_tests(self, bdir):
        # 测试工作目录：优先 tempfs（chmod 只读语义正确，见 _pick_test_dir 说明）
        # 注意：test_cuesheet/test_picture 需要相对路径 cuesheets/，一并在 tdir 下准备。
        tdir = self._pick_test_dir()
        os.makedirs(os.path.join(tdir, "cuesheets"), exist_ok=True)
        # 1) test_libFLAC：上游单元测试（bitreader/bitwriter/crc/format/encoders/decoders/metadata_*）
        self.run('cd "{t}" && "{b}/src/test_libFLAC/test_libFLAC" > "{b}/test_libFLAC.log" 2>&1; ec=$?; tail -1 "{b}/test_libFLAC.log"; exit $ec'.format(b=bdir, t=tdir))
        # 2) test_libFLAC++：C++ 绑定单元测试（需 libc++_shared.so，从 OHOS SDK 提供）
        llvm_lib = ""
        for cand in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos")):
            llvm_lib = cand
        env_prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(llvm_lib) if llvm_lib else ""
        self.run('cd "{t}" && {env}"{b}/src/test_libFLAC++/test_libFLAC++" > "{b}/test_libFLACpp.log" 2>&1; ec=$?; tail -1 "{b}/test_libFLACpp.log"; exit $ec'.format(b=bdir, env=env_prefix, t=tdir))
        # 3) test_grabbag/picture：输出与上游 test/picture.ok 基准比对（等价 test_grabbag.sh 的 diff 步骤）
        self.run('cd "{t}" && "{b}/src/test_grabbag/picture/test_picture" "{s}/test/pictures" > picture.log 2>&1 && diff "{s}/test/picture.ok" picture.log'.format(b=bdir, s=self.source_folder, t=tdir))
        # 4) test_grabbag/cuesheet：6 good + 44 bad cuesheets，输出与 test/cuesheet.ok 比对（等价 test_grabbag.sh）
        #    注意 rm -f cuesheet.log：test_grabbag.sh 用 rm -f 清 log，避免重复运行时追加导致 diff 偏差
        self.run('cd "{t}" && rm -f cuesheet.log picture.log && good_leadout=$((80*60*44100)); '
                 'for cue in "{s}/test/cuesheets/bad."*.cue; do '
                 'echo "NEGATIVE $cue" | sed "s|{s}/test/||" >> cuesheet.log; '
                 '"{b}/src/test_grabbag/cuesheet/test_cuesheet" "$cue" $good_leadout 44100 cdda >> cuesheet.log 2>&1; done; '
                 'for cue in "{s}/test/cuesheets/good."*.cue; do '
                 'echo "POSITIVE $cue" | sed "s|{s}/test/||" >> cuesheet.log; '
                 '"{b}/src/test_grabbag/cuesheet/test_cuesheet" "$cue" $good_leadout 44100 cdda >> cuesheet.log 2>&1 || exit 1; '
                 'cuesheet_out=$(echo "$cue" | sed "s|{s}/test/||"); '
                 'diff "$cuesheet_out.1" "$cuesheet_out.2" >> cuesheet.log 2>&1; rm -f "$cuesheet_out.1" "$cuesheet_out.2"; done; '
                 'diff "{s}/test/cuesheet.ok" cuesheet.log'.format(b=bdir, s=self.source_folder, t=tdir))
        # 5) test_seeking：预编程 + 随机 seek 校验（等价 test_seeking.sh 核心，用 test_streams 生成的流）
        self.run('cd "{t}" && "{b}/src/test_streams/test_streams" > /dev/null 2>&1; '
                 '"{b}/src/flac/flac" --silent --no-error-on-compression-fail -f -o seek-test.flac rpg-tone-44100.wav; '
                 'samples=$("{b}/src/metaflac/metaflac" --show-total-samples seek-test.flac); '
                 '{env}"{b}/src/test_seeking/test_seeking" seek-test.flac 50 $samples > "{b}/test_seeking.log" 2>&1; ec=$?; tail -1 "{b}/test_seeking.log"; exit $ec'.format(b=bdir, env=env_prefix, t=tdir))
        # 6) flac CLI 编码/解码往返 + md5 自洽（等价 test_flac.sh 的 md5cmp 核心断言）
        self.run('cd "{t}" && "{b}/src/flac/flac" --silent --no-error-on-compression-fail -f -o rt.flac rt-1-16-1.wav 2>/dev/null; '
                 '"{b}/src/flac/flac" --silent -d -f -o rt.dec.wav rt.flac; '
                 '"{b}/src/flac/flac" --silent -f -o rt.re.flac rt.dec.wav; '
                 'm1=$("{b}/src/metaflac/metaflac" --show-md5sum --no-filename rt.flac); '
                 'm2=$("{b}/src/metaflac/metaflac" --show-md5sum --no-filename rt.re.flac); '
                 '[ "$m1" = "$m2" ] || {{ echo "MD5 mismatch: $m1 vs $m2"; exit 1; }}; echo "flac CLI encode/decode roundtrip md5 OK"'.format(b=bdir, t=tdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（flac/metaflac CLI）——产可执行文件的包必须签 bin。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # 工具路径优先取环境变量，回退 CI/设备默认；签名工具仅在 CI/设备环境存在。
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool 不存在（{}）：跳过代码签名。设备上 dlopen/exec 未签名产物会因 "
                "XPM 报 Permission denied，请在 CI/设备环境或经 BINARY_SIGN_TOOL 指定后重打包。".format(signer))
            return
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.components["flac"].libs = ["FLAC"]
        self.cpp_info.components["flac"].requires = ["libogg::libogg"]
        self.cpp_info.components["flac"].set_property("cmake_target_name", "FLAC::FLAC")
        self.cpp_info.components["flac"].set_property("pkg_config_name", "flac")
        self.cpp_info.components["flac++"].libs = ["FLAC++"]
        self.cpp_info.components["flac++"].requires = ["flac"]
        self.cpp_info.components["flac++"].set_property("cmake_target_name", "FLAC::FLAC++")
        self.cpp_info.components["flac++"].set_property("pkg_config_name", "flac++")
        # 上游 install 的 cmake config 名为 FLAC（lib/cmake/FLAC/flac-config.cmake）
        self.cpp_info.set_property("cmake_file_name", "FLAC")
        self.cpp_info.bindirs = ["bin"]
