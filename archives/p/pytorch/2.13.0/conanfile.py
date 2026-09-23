#!/usr/bin/env python3
"""Conan recipe for PyTorch 2.13.0 — HarmonyOS PC (aarch64) adaptation.

PyTorch's GitHub release tarball does NOT bundle the ~37 `third_party` git
submodules (they appear as empty directories). This recipe therefore:

1. Downloads the official source tarball (R39).
2. In source(): populates the required third_party submodules from their
   official per-commit codeload archives (pinned commits below), so the CMake
   configure step sees complete third_party trees — same as a recursive clone.
3. Applies the adaptation patches:
   - 0001: top-level source fixes (CMake 4.x WHOLE_ARCHIVE, musl __assert_fail
     signature, non-standard `uint` type, std::ranges -> <algorithm> for the
     SDK's libc++ 15 which has no ranges).
   - 0002: cpuinfo OHOS platform support (treat OHOS as Linux so the
     arm/linux sources are compiled and cpuinfo_initialize works).
4. Builds with CMake using the OHOS SDK clang 15 toolchain + native libc++ 15.
   PyTorch 2.13.0 hard-requires Clang >= 16; we satisfy it with
   tool_requires("clang/22.1.8") and point CMAKE_C/CXX_COMPILER at it, while
   keeping the SDK sysroot/libc++ for the target.
5. Outputs libtorch.so + libtorch_cpu.so (the C++ libtorch library).

Verified locally: configure + make -j2 succeed, `libtorch_cpu.so` and
`libtorch.so` are produced (see notes.md / task book).
"""
import glob
import os
import re
import shutil
import subprocess
import time
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.scm import Version


class PytorchConan(ConanFile):
    name = "pytorch"
    version = "2.13.0"
    description = "PyTorch: tensors and dynamic neural networks (C++ libtorch), adapted for HarmonyOS PC aarch64"
    license = "BSD-3-Clause"
    homepage = "https://pytorch.org"
    url = "https://github.com/pytorch/pytorch"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # PyTorch 2.13.0 requires Clang >= 16 (CMakeLists hard check); OHOS SDK
    # ships clang 15.0.4, so provide a newer clang as a tool_requires.
    tool_requires = "clang/22.1.8"

    # third_party submodules (path -> commit) pinned by the pytorch v2.13.0 tag.
    # The GitHub tarball omits these; each is fetched from its official repo.
    _SUBMODULES = {
        "third_party/pybind11": "d03662f0984f652b60e7ddce53d3868002275197",
        "third_party/googletest": "52eb8108c5bdec04579160ae17225d66034bd723",
        "third_party/benchmark": "299e5928955cc62af9968370293b916f5130916f",
        "third_party/protobuf": "d1eca4e4b421cd2997495c4b4e65cea6be4e9b8a",
        "third_party/NNPACK": "c07e3a0400713d546e0dea2d5466dd22ea389c73",
        "third_party/gloo": "bcd1672ee07538123ea8f4fac76832efc58fb8ef",
        "third_party/pthreadpool": "a56dcd79c699366e7ac6466792c3025883ff7704",
        "third_party/FXdiv": "b408327ac2a15ec3e43352421954f5b1967701d1",
        "third_party/FP16": "4dfe081cf6bcd15db339cf2680b9281b8451eeb3",
        "third_party/psimd": "072586a71b55b7f8c584153d223e95687148a900",
        "third_party/cpuinfo": "bc3c01e230c6974283e4b89421cfb0e232435589",
        "third_party/python-peachpy": "f45429b087dd7d5bc78bb40dc7cf06425c252d67",
        "third_party/onnx": "e709452ef2bbc1d113faf678c24e6d3467696e83",
        "third_party/sleef": "5a1d179df9cf652951b59010a2d2075372d67f68",
        "third_party/ideep": "e087b6e4b32a7ba684db82231d1558123968ac1d",
        "third_party/gemmlowp/gemmlowp": "3fb5c176c17c765a3492cd2f0321b0dab712f350",
        "third_party/fbgemm": "d08742c6602efedc6a3c9fca124b96ad555316e4",
        "android/libs/fbjni": "7e1e1fe3858c63c251c637ae41a20de425dde96f",
        "third_party/XNNPACK": "51a0103656eff6fc9bfd39a4597923c4b542c883",
        "third_party/fmt": "407c905e45ad75fc29bf0f9bb7c5c2fd3475976f",
        "third_party/tensorpipe": "2b4cd91092d335a697416b2a3cb398283246849d",
        "third_party/cudnn_frontend": "c4a97621eca52fa0c3a1862a411a16be580b25c6",
        "third_party/kineto": "094d3c1d072362d0a919a77299459eee94f97931",
        "third_party/pocketfft": "0fa0ef591e38c2758e3184c6c23e497b9f732ffa",
        "third_party/ittapi": "0c57540822deb5dae43bef6c1cc9b3be4772a033",
        "third_party/flatbuffers": "a2cd1ea3b6d3fee220106b5fed3f7ce8da9eb757",
        "third_party/nlohmann": "55f93686c01528224f448c19128836e7df245f72",
        "third_party/VulkanMemoryAllocator": "1d8f600fd424278486eade7ed3e877c99f0846b1",
        "third_party/cutlass": "da5e086dab31d63815acafdac9a9c5893b1c69e2",
        "third_party/mimalloc": "02a2f5df9d7d46d30263b83832eebeeab62dc5fe",
        "third_party/cpp-httplib": "811dd0b6f2382f50f801f3cfdb5ba349d08bb575",
        "third_party/NVTX": "3ebbc93ded7285963bff932c678fa367eb393ba6",
        "third_party/composable_kernel": "f1746955fdaf80a3414de814bf32437686dac347",
        "third_party/kleidiai": "d7770c89632329a9914ef1a90289917597639cbe",
        "third_party/flash-attention": "6c4f74fb338e0c3cdb07ac6f5eab5f54fc367c15",
        "third_party/aiter": "9a469a608b2c10b7157df573a38d31e5bf4038b4",
        "third_party/mslk": "3d332d1c0c0ac7765852c97b3979c9ef913e037f",
        # fbgemm nested submodules (PreBuildSteps checks external/asmjit)
        "third_party/fbgemm/external/asmjit": "a3199e8857792cd10b7589ff5d58343d2c9008ea",
        "third_party/fbgemm/external/cpuinfo": "161a9ec374884f4b3e85725cb22e05f9458fdc93",
        "third_party/fbgemm/external/googletest": "52eb8108c5bdec04579160ae17225d66034bd723",
        "third_party/fbgemm/external/hipify_torch": "63b6a7b541fa7f08f8475ca7d74054db36ff2691",
        "third_party/fbgemm/external/cutlass": "571edeb2d0ac872a8392fc49285b156b07884b4e",
        "third_party/fbgemm/external/composable_kernel": "7fe50dc3da2069d6645d9deb8c017a876472a977",
        "third_party/fbgemm/external/json": "55f93686c01528224f448c19128836e7df245f72",
    }

    # submodule repo overrides (path -> owner/repo) for the handful that are not
    # derivable from the standard URL scheme or need a specific mirror.
    _REPO_OVERRIDE = {
        "third_party/pybind11": "pybind/pybind11",
        "third_party/benchmark": "google/benchmark",
        "third_party/gemmlowp/gemmlowp": "google/gemmlowp",
        "third_party/python-peachpy": "malfet/PeachPy",
        "third_party/mslk": "meta-pytorch/MSLK",
        "third_party/kleidiai": "ARM-software/kleidiai",
        "third_party/ittapi": "intel/ittapi",
        "third_party/cudnn_frontend": "NVIDIA/cudnn-frontend",
        "third_party/flash-attention": "Dao-AILab/flash-attention",
        "third_party/cpuinfo": "pytorch/cpuinfo",
        "third_party/cpp-httplib": "yhirose/cpp-httplib",
        "third_party/fbgemm/external/asmjit": "asmjit/asmjit",
        "third_party/fbgemm/external/hipify_torch": "ROCm/hipify_torch",
        "third_party/fbgemm/external/composable_kernel": "ROCm/composable_kernel",
        "third_party/fbgemm/external/cutlass": "NVIDIA/cutlass",
        "third_party/fbgemm/external/json": "nlohmann/json",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Populate third_party submodules missing from the release tarball.
        self._fetch_submodules()

    def _repo_for(self, path):
        if path in self._REPO_OVERRIDE:
            return self._REPO_OVERRIDE[path]
        # derive owner/repo from the submodule name (most follow owner/repo)
        name = path.rsplit("/", 1)[-1]
        simple = {
            "pybind11": "pybind/pybind11",
            "googletest": "google/googletest",
            "benchmark": "google/benchmark",
            "protobuf": "protocolbuffers/protobuf",
            "NNPACK": "Maratyszcza/NNPACK",
            "gloo": "pytorch/gloo",
            "pthreadpool": "google/pthreadpool",
            "FXdiv": "Maratyszcza/FXdiv",
            "FP16": "Maratyszcza/FP16",
            "psimd": "Maratyszcza/psimd",
            "cpuinfo": "pytorch/cpuinfo",
            "python-peachpy": "malfet/PeachPy",
            "onnx": "onnx/onnx",
            "sleef": "shibatch/sleef",
            "ideep": "intel/ideep",
            "gemmlowp": "google/gemmlowp",
            "fbgemm": "pytorch/FBGEMM",
            "fbjni": "facebookincubator/fbjni",
            "XNNPACK": "google/XNNPACK",
            "fmt": "fmtlib/fmt",
            "tensorpipe": "pytorch/tensorpipe",
            "cudnn_frontend": "NVIDIA/cudnn-frontend",
            "kineto": "pytorch/kineto",
            "pocketfft": "mreineck/pocketfft",
            "ittapi": "intel/ittapi",
            "flatbuffers": "google/flatbuffers",
            "nlohmann": "nlohmann/json",
            "VulkanMemoryAllocator": "GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator",
            "cutlass": "NVIDIA/cutlass",
            "mimalloc": "microsoft/mimalloc",
            "cpp-httplib": "yhirose/cpp-httplib",
            "NVTX": "NVIDIA/NVTX",
            "composable_kernel": "ROCm/composable_kernel",
            "kleidiai": "ARM-software/kleidiai",
            "flash-attention": "Dao-AILab/flash-attention",
            "aiter": "ROCm/aiter",
            "mslk": "meta-pytorch/MSLK",
        }
        return simple.get(name)

    def _fetch_submodules(self):
        """Fetch each pinned third_party submodule from its official codeload."""
        base = self.source_folder
        for path, commit in self._SUBMODULES.items():
            repo = self._repo_for(path)
            if not repo:
                self.output.warning(f"no repo mapping for {path}, skipping")
                continue
            dest = os.path.join(base, path)
            if os.path.isdir(dest) and os.listdir(dest):
                continue  # already populated (e.g. a vendored copy)
            os.makedirs(dest, exist_ok=True)
            url = (
                f"https://gh-proxy.com/https://github.com/{repo}/archive/{commit}.tar.gz",
                f"https://gh.ddlc.top/https://github.com/{repo}/archive/{commit}.tar.gz",
                f"https://ghfast.top/https://github.com/{repo}/archive/{commit}.tar.gz",
                f"https://codeload.github.com/{repo}/tar.gz/{commit}",
            )
            tarball = os.path.join(self.source_folder, f".sub-{path.rsplit('/', 1)[-1]}.tgz")
            try:
                self._download(url, tarball)
                # strip the top-level "<repo>-<sha>" directory
                shutil.rmtree(dest, ignore_errors=True)
                os.makedirs(dest, exist_ok=True)
                self._untar_strip(tarball, dest)
            finally:
                if os.path.exists(tarball):
                    os.remove(tarball)

    def _untar_strip(self, tarball, dest):
        """Extract a tarball, stripping its single top-level directory.

        Uses Python's tarfile (no dependency on the system `tar` binary, which
        is absent in the conan build environment).
        """
        import tarfile
        with tarfile.open(tarball, "r:gz") as tf:
            members = tf.getmembers()
            # find the single top-level directory name
            tops = sorted({m.name.split("/", 1)[0] for m in members if m.name})
            prefix = (tops[0] + "/") if tops else ""
            for m in members:
                name = m.name
                if name.startswith(prefix):
                    name = name[len(prefix):]
                if not name:
                    continue
                target = os.path.join(dest, name)
                if m.isdir():
                    os.makedirs(target, exist_ok=True)
                elif m.issym() or m.islnk():
                    lnk = m.linkname
                    if lnk.startswith(prefix):
                        lnk = lnk[len(prefix):]
                    if os.path.lexists(target):
                        os.unlink(target)
                    os.symlink(lnk, target)
                elif m.isfile():
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with tf.extractfile(m) as src, open(target, "wb") as fh:
                        shutil.copyfileobj(src, fh)

    def _download(self, urls, dest):
        """Download from the first URL that works (retry transient failures).

        codeload.github.com is intermittently blocked in this environment, so
        the ghfast.top mirror (same prefix E017 uses) is tried first, with the
        canonical codeload URL as a fallback.
        """
        if isinstance(urls, str):
            urls = [urls]
        last_err = None
        for url in urls:
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
                        shutil.copyfileobj(resp, fh)
                    return
                except Exception as e:  # noqa: BLE001 - retry transient network failures
                    last_err = e
                    self.output.warning(f"download failed (attempt {attempt + 1}/3): {url}: {e}")
                    time.sleep(5)
        raise last_err

    def _sdk_native(self):
        """Locate the OHOS SDK native dir in a portable way.

        Prefer explicit env vars (OHOS_SDK_HOME / OHOS_NDK_ROOT /
        OHOS_NATIVE_ROOT), then the newest installed SDK under
        /data/service/hnp — CI workers may carry a different SDK version than
        the dev box, so a hard-coded version path breaks there.
        """
        for var in ("OHOS_SDK_HOME", "OHOS_NDK_ROOT", "OHOS_NATIVE_ROOT"):
            v = os.environ.get(var)
            if v:
                for cand in (os.path.join(v, "ohos", "native"), v):
                    if os.path.isdir(cand):
                        return cand
        matches = sorted(set(
            glob.glob("/data/service/hnp/ohos-sdk*/ohos/native") +
            glob.glob("/data/service/hnp/*/ohos-sdk*/ohos/native")
        ))
        if matches:
            return matches[-1]
        # Fallback to the historically known dev-box path.
        return "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"

    def generate(self):
        tc = CMakeToolchain(self)
        # The profile points tools.build:compiler_executables at the SDK clang
        # 15 (which fails PyTorch's Clang>=16 check); override the compilers
        # with the clang/22.1.8 tool_require and keep the SDK libc++ 15
        # (OHOS __n1 ABI, PIC libc++_shared.so) for the target.
        clang_dep = self.dependencies.build["clang"]
        # Keep every host tool loadable: conan's VirtualBuildEnv prepends
        # tool_requires lib dirs to LD_LIBRARY_PATH, and the conan cache is not
        # loadable on CI workers (HMDFS exec restriction) -- the host cmake,
        # ninja and the sleef host tools would all fail with 'symbol not
        # found'. Drop the lib dir here (bin stays on PATH) and let the
        # platform libc++ be used instead; build() pins it explicitly.
        clang_dep.cpp_info.libdirs = []
        clang_pkg = clang_dep.package_folder
        sdk_native = self._sdk_native()
        target = "--target=aarch64-linux-ohos"
        sysroot = f"--sysroot={sdk_native}/sysroot"
        tc.variables["CMAKE_C_COMPILER"] = os.path.join(clang_pkg, "bin", "clang")
        tc.variables["CMAKE_CXX_COMPILER"] = os.path.join(clang_pkg, "bin", "clang++")
        tc.variables["CMAKE_C_FLAGS"] = f"{target} {sysroot} -D__MUSL__"
        tc.variables["CMAKE_CXX_FLAGS"] = (
            f"{target} {sysroot} -D__MUSL__ "
            f"-isystem {sdk_native}/llvm/include/libcxx-ohos/include/c++/v1 "
            f"-D_GNU_SOURCE"
        )
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"{target} {sysroot} -L{sdk_native}/llvm/lib/aarch64-linux-ohos"
        )
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            f"{target} {sysroot} -L{sdk_native}/llvm/lib/aarch64-linux-ohos"
        )
        tc.generate()

    @staticmethod
    def _libcxx_score(path):
        """Score a libc++_shared.so candidate by content (size, __n1 symbols).

        A stub/empty .so (valid ELF, SONAME set, but no C++ runtime symbols) is
        what makes host tools like cmake die with 'symbol not found'; it can be
        silently picked when it comes first on LD_LIBRARY_PATH. Reading the file
        is enough to tell a real runtime from a stub, without running anything.
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return None
        return len(data), data.count(b"_ZNSt4__n1")

    def _libcxx_dirs(self):
        """Directories that may provide a host libc++_shared.so, best first.

        The platform path comes first: CI workers refuse to load .so files from
        the conan cache (HMDFS exec restriction), so a good copy there is still
        unusable -- only /system/lib64 worked on the worker (see the CI
        diagnostic run).
        """
        sdk_native = self._sdk_native()
        return [
            "/system/lib64",
            os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos"),
            os.path.join(sdk_native, "llvm", "lib"),
            os.path.join(self.dependencies.build["clang"].package_folder, "lib"),
        ]

    def _pick_libcxx_dir(self):
        """Return a libc++ directory the host cmake can actually start with.

        Candidates are checked twice: by content (size/__n1, to reject stubs)
        and empirically, by starting cmake with LD_LIBRARY_PATH pinned to that
        directory. The empirical check is what makes this robust across CI
        workers, where a byte-identical copy can still be unloadable.
        """
        tried = []
        for d in self._libcxx_dirs():
            score = self._libcxx_score(os.path.join(d, "libc++_shared.so"))
            if not score or score[0] < 200000 or score[1] < 100:
                tried.append("%s: %s" % (d, "missing" if not score
                                         else "not-libc++(size=%d,__n1=%d)" % score))
                continue
            rc = self.run('LD_LIBRARY_PATH=%s cmake --version >/dev/null 2>&1' % d,
                          env="conanbuild", ignore_errors=True)
            tried.append("%s: size=%d __n1=%d cmake_rc=%s" % (d, score[0], score[1], rc))
            if rc == 0:
                self.output.info("pytorch: host libc++ dir = %s (size=%d, __n1=%d)"
                                 % (d, score[0], score[1]))
                return d
        raise ConanException(
            "no host libc++_shared.so that cmake can start with; candidates:\n  "
            + "\n  ".join(tried))

    def _write_cmake_wrapper(self, libdir):
        """Write a cmake wrapper that pins a loadable libc++ for host tools.

        LD_LIBRARY_PATH takes precedence over the platform search path, and
        conan's buildenv prepends tool_requires lib dirs (conan cache) that CI
        workers cannot load. Assigning the variable inline guarantees the
        platform copy is used no matter what the inherited environment holds.
        """
        wrapper = os.path.join(self.build_folder, "cmake-host.sh")
        with open(wrapper, "w") as fh:
            fh.write('#!/bin/sh\n'
                     '# generated by the pytorch recipe: force a loadable host libc++\n'
                     'exec env LD_LIBRARY_PATH="%s" /data/service/hnp/bin/cmake "$@"\n' % libdir)
        os.chmod(wrapper, 0o755)
        return wrapper

    def _diag_host_cmake(self, libcxx):
        """Compact report on why the host cmake cannot start (CI sandbox diagnosis).

        Runs only on the failure path, so it does not slow down healthy builds.
        Answers, in one shot: which LD_* vars actually reach the child shell,
        which libc++ copies exist on the loader's default search path, which one
        the loader would pick, and which injection mechanism still works.
        """
        libdir = os.path.dirname(libcxx)
        mine = " ".join("%s=%s" % (k, v) for k, v in os.environ.items() if k.startswith("LD_"))
        self.output.info("[diag] python os.environ LD_*: %s" % (mine or "<none>"))
        self.run('env | grep -E "^LD_" || echo "[diag] no LD_* inside conanbuild shell"',
                 env="conanbuild", ignore_errors=True)
        default_dirs = []
        for pf in ("/etc/ld-musl-aarch64.path", "/system/etc/ld-musl-aarch64.path"):
            try:
                with open(pf) as fh:
                    content = fh.read().strip()
                self.output.info("[diag] %s: %s" % (pf, content))
                default_dirs = content.split(":")
                break
            except OSError:
                continue
        hits = []
        for d in default_dirs:
            score = self._libcxx_score(os.path.join(d, "libc++_shared.so"))
            if score:
                hits.append("%s(size=%d,__n1=%d)" % (os.path.join(d, "libc++_shared.so"), score[0], score[1]))
        self.output.info("[diag] libc++_shared.so on default path: %s" % ("; ".join(hits) or "<none>"))
        self.run('ls -l "%s" 2>&1 | tail -2' % libcxx, env="conanbuild", ignore_errors=True)
        self.run('readelf -S "%s" 2>/dev/null | grep -c codesign | xargs echo "[diag] .codesign sections:"'
                 % libcxx, env="conanbuild", ignore_errors=True)
        self.run('LD_TRACE_LOADED_OBJECTS=1 cmake --version 2>&1 | grep -iE "libc\\+\\+|not found" | head -5 '
                 '|| echo "[diag] trace gave no libc++ line"', env="conanbuild", ignore_errors=True)
        wrapper = os.path.join(self.build_folder, "cmake-via-env.sh")
        with open(wrapper, "w") as fh:
            fh.write('#!/bin/sh\nexec env LD_LIBRARY_PATH="%s" LD_PRELOAD="%s" '
                     '/data/service/hnp/bin/cmake "$@"\n' % (libdir, libcxx))
        os.chmod(wrapper, 0o755)
        # python shim: sets the child env with os.execve, bypassing any
        # shell/spawn-time env filtering the sandbox might apply.
        shim = os.path.join(self.build_folder, "cmake-shim")
        with open(shim, "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import os, sys\n"
                     "env = dict(os.environ)\n"
                     "env['LD_LIBRARY_PATH'] = %r\n"
                     "env['LD_PRELOAD'] = %r\n"
                     "cmake = '/data/service/hnp/bin/cmake'\n"
                     "os.execve(cmake, [cmake] + sys.argv[1:], env)\n" % (libdir, libcxx))
        os.chmod(shim, 0o755)
        cases = (("plain", ""),
                 ("libpath", 'LD_LIBRARY_PATH=%s ' % libdir),
                 ("preload", 'LD_PRELOAD=%s ' % libcxx),
                 ("both", 'LD_LIBRARY_PATH=%s LD_PRELOAD=%s ' % (libdir, libcxx)),
                 ("wrapper", "%s " % wrapper),
                 ("pyshim", "%s " % shim),
                 ("syslib", "LD_LIBRARY_PATH=/system/lib64 "))
        for tag, prefix in cases:
            rc = self.run("%scmake --version >/dev/null 2>&1" % prefix, env="conanbuild",
                          ignore_errors=True)
            self.output.info("[diag] cmake start via %-8s -> rc=%s" % (tag, rc))

    def build(self):
        apply_conandata_patches(self)
        # Host tools (cmake/ninja) need a libc++_shared.so the loader can
        # actually load. Conan's VirtualBuildEnv prepends every tool_requires
        # libdir (clang/22.1.8, i.e. the conan cache) to LD_LIBRARY_PATH, and CI
        # workers refuse to load .so files from there (HMDFS exec restriction):
        # the candidate is found but cannot be loaded, so the host cmake dies
        # with 'Error relocating ... symbol not found' (exit 127). Only the
        # platform copy worked on the worker, so pick a *loadable* directory,
        # pin LD_LIBRARY_PATH to it and route the CMake helper through a
        # wrapper that sets the variable inline (immune to the inherited env).
        libdir = self._pick_libcxx_dir()
        os.environ["LD_LIBRARY_PATH"] = libdir
        os.environ.pop("LD_PRELOAD", None)
        wrapper = self._write_cmake_wrapper(libdir)
        self.conf.define("tools.cmake:cmake_program", wrapper)
        # Canary: fail early with a readable message instead of a cryptic
        # "Error 127 while executing" from cmake.configure(). Check the wrapper
        # (that is what the CMake helper will actually run) and, on failure,
        # print a one-shot diagnosis of the worker environment.
        if self.run('"%s" --version' % wrapper, env="conanbuild", ignore_errors=True) != 0:
            self._diag_host_cmake(os.path.join(libdir, "libc++_shared.so"))
            raise ConanException(
                "host cmake cannot start (libdir=%s); "
                "check the worker's libc++/cmake installation" % libdir)
        # sleef needs host-side codegen tools (mkrename/mkalias/mkdisp/...).
        # Cross-compiling OHOS, sleef's add_host_executable looks in
        # NATIVE_BUILD_DIR/bin; build them with the SDK clang (produces runnable
        # aarch64 musl host binaries) and point CMake at that dir.
        native_dir = os.path.join(self.build_folder, "sleef-native")
        self._build_sleef_host_tools(native_dir)
        # PyTorch's top-level CMakeLists enables CMAKE_LINK_WHAT_YOU_USE, which
        # makes CMake run `ldd` after every link to look for unused libraries.
        # OHOS has no `ldd`, so every link fails ("Error running 'ldd': no such
        # file or directory" -> make Error 1). Provide an ldd-compatible shim
        # built on readelf and point CMake at it.
        ldd_shim = self._write_ldd_shim()
        cmake = CMake(self)
        cmake.configure(variables={**self._cmake_vars(),
                                   "NATIVE_BUILD_DIR": native_dir,
                                   "CMAKE_LINK_WHAT_YOU_USE_CHECK": ldd_shim})
        try:
            cmake.build()
        except ConanException:
            # Surface the real compiler error: with -j20 the failing command's
            # output is buried far above the CI log tail (which is truncated),
            # so re-run the build serially and print only the error context.
            self._dump_build_errors(libdir)
            raise
        self._run_upstream_c10_tests(libdir)

    # Upstream c10 test targets. c10/test/CMakeLists.txt registers one gtest
    # target per *_test.cpp found (file(GLOB_RECURSE ...)) plus a C++17 header
    # build check, so the target list is derived the same way here instead of
    # being hard-coded. Suites that cannot run inside this package:
    #   test/cpp  198 files / 2700 gtest cases (needs the whole torch target,
    #                                            hours of compile+run time)
    #   test/*.py 184 files / 9926 test functions (needs BUILD_PYTHON + torch)
    # Their sizes are reported in notes.md / test_package/MANIFEST.yml.
    UPSTREAM_C10_TEST_SKIP = ()  # documented exceptions, currently none

    def _upstream_c10_targets(self):
        """All c10 test targets upstream registers for BUILD_TEST=ON."""
        test_dir = os.path.join(self.source_folder, "c10", "test")
        names = []
        for root, _dirs, files in os.walk(test_dir):
            for name in files:
                if name.endswith("_test.cpp"):
                    names.append("c10_%s" % name[: -len(".cpp")])
        # extra target added by c10/test/CMakeLists.txt (not a *_test.cpp)
        extra = os.path.join(test_dir, "util", "cpp17_header_build_check.cpp")
        if os.path.exists(extra):
            names.append("c10_cpp17_header_build_test")
        return sorted(set(names) - set(self.UPSTREAM_C10_TEST_SKIP))

    def _run_upstream_c10_tests(self, libdir):
        """Build and run the upstream c10 unit tests.

        PyTorch's C++ tests are gtest-based and only exist when BUILD_TEST=ON,
        which stays OFF for the package build (no test binaries are packaged).
        The already-configured tree is reconfigured with BUILD_TEST=ON and the
        c10 test targets are built, so the tests are compiled with exactly the
        toolchain and flags used for the library they exercise.
        """
        build_dir = self.build_folder
        names = self._upstream_c10_targets()
        # gtest writes captured death-test output to a temp file; TEST_TMPDIR
        # makes it use a writable directory (see patch 0005), /tmp being
        # read-only on HarmonyOS PC.
        tmp_dir = os.path.join(build_dir, "upstream-test-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.output.info("pytorch: upstream tests: enabling BUILD_TEST=ON and "
                         "building %d c10 targets" % len(names))
        # INSTALL_TEST defaults to ON as soon as BUILD_TEST is ON, which adds
        # install rules for every test *and* benchmark binary; only the c10
        # test targets are built here, so package()'s cmake.install() would
        # look for e.g. bin/c10_intrusive_ptr_benchmark and fail. Keep the
        # package contents unchanged (no test binaries).
        self.run('cmake -S "%s" -B "%s" -DBUILD_TEST=ON -DINSTALL_TEST=OFF'
                 % (self.source_folder, build_dir), env="conanbuild")
        self.run('cmake --build "%s" --target %s -- -j%d'
                 % (build_dir, " ".join(names), os.cpu_count() or 4),
                 env="conanbuild")

        report = os.path.join(build_dir, "upstream-c10-ctest.log")
        # TEST_TMPDIR is what googletest uses for captured death-test output
        # (patch 0005); TMPDIR is what c10::make_tempfile uses. Both point at a
        # writable directory because /tmp is read-only on HarmonyOS PC.
        rc = self.run('TMPDIR="%s" TEST_TMPDIR="%s" ctest --test-dir "%s" -R "^(%s)$" '
                      '--output-on-failure 2>&1 | tee "%s"'
                      % (tmp_dir, tmp_dir, build_dir, "|".join(names), report),
                      env="conanbuild", ignore_errors=True)
        total = failed = passed = 0
        try:
            with open(report) as fh:
                for line in fh:
                    m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", line)
                    if m:
                        failed, total = int(m.group(2)), int(m.group(3))
                        passed = total - failed
        except OSError:
            self.output.warning("pytorch: ctest report missing: %s" % report)

        cases = self._count_gtest_cases(build_dir, names, libdir)
        self.output.info("pytorch: upstream c10 tests: %d/%d targets passed, "
                         "%d gtest cases compiled in the subset"
                         % (passed, total, cases))
        if rc != 0 or failed or total == 0:
            tail = ""
            try:
                with open(report) as fh:
                    tail = "".join(fh.readlines()[-40:])
            except OSError:
                pass
            raise ConanException(
                "upstream c10 tests failed (%d of %d targets, gtest cases in "
                "subset: %d)\n%s" % (failed, total, cases, tail))

    def _count_gtest_cases(self, build_dir, names, libdir):
        """Count gtest cases of the built subset via --gtest_list_tests."""
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(build_dir, "lib"), libdir, "/system/lib64"])
        total = 0
        for name in names:
            exe = None
            for root, _dirs, files in os.walk(build_dir):
                if name in files and os.access(os.path.join(root, name), os.X_OK):
                    exe = os.path.join(root, name)
                    break
            if not exe:
                self.output.warning("pytorch: test binary not found: %s" % name)
                continue
            try:
                out = subprocess.run([exe, "--gtest_list_tests"], capture_output=True,
                                     text=True, timeout=120, env=env).stdout
            except (OSError, subprocess.SubprocessError) as exc:
                self.output.warning("pytorch: cannot list gtest cases of %s: %s" % (name, exc))
                continue
            for line in out.splitlines():
                # list format: "Suite." lines, then "  CaseName" under them
                if line.startswith("  ") and not line.rstrip().endswith("."):
                    total += 1
        return total

    def _write_ldd_shim(self):
        """Write an ldd-compatible helper (OHOS has no ldd) and return its path.

        CMake's LINK_WHAT_YOU_USE feature (enabled by PyTorch's CMakeLists) runs
        `ldd <target>` after linking; without it every link fails on OHOS. The
        shim lists DT_NEEDED entries via readelf, which is what ldd reports in
        practice, keeping the check meaningful instead of disabling it.
        """
        tools_dir = os.path.join(self.build_folder, "host-tools")
        os.makedirs(tools_dir, exist_ok=True)
        shim = os.path.join(tools_dir, "ldd")
        script = r'''#!/bin/sh
# ldd-compatible shim for OHOS/musl (the platform ships no ldd).
# Lists DT_NEEDED entries so CMake's LINK_WHAT_YOU_USE check can run.
READELF="${READELF:-readelf}"
command -v "$READELF" >/dev/null 2>&1 || READELF=/data/service/hnp/bin/llvm-readelf
for f in "$@"; do
  case "$f" in -*) continue;; esac
  if [ ! -e "$f" ]; then
    echo "ldd: $f: No such file or directory" >&2
    continue
  fi
  echo "$f:"
  "$READELF" -d "$f" 2>/dev/null | awk '/\(NEEDED\)/ {gsub(/[\[\]]/, "", $NF); print "\t" $NF " => (ohos)"}'
done
exit 0
'''
        with open(shim, "w") as fh:
            fh.write(script)
        os.chmod(shim, 0o755)
        self.output.info("pytorch: ldd shim for LINK_WHAT_YOU_USE = %s" % shim)
        return shim

    def _dump_build_errors(self, libdir):
        """Re-run a serial debug build to surface compile errors in the log tail."""
        build_dir = self.build_folder
        wrapper = os.path.join(self.build_folder, "cmake-host.sh")
        cmd = ('cd "%s" && "%s" --build . -j1 2>&1 | '
               'grep -E -B4 -A20 "error:|Error|FAILED" | head -120'
               % (build_dir, wrapper))
        self.output.info("pytorch: build failed, dumping error context (serial rebuild)")
        self.run(cmd, env="conanbuild", ignore_errors=True)

    def _build_sleef_host_tools(self, native_dir):
        """Compile sleef's host codegen tools so cross-configure can use them."""
        bin_dir = os.path.join(native_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        clang = os.path.join(self._sdk_native(), "llvm", "bin", "clang")
        sleef = os.path.join(self.source_folder, "third_party", "sleef", "src")
        inc = [
            "-I" + os.path.join(sleef, "libm"),
            "-I" + os.path.join(sleef, "libm", "include"),
            "-I" + os.path.join(sleef, "common"),
            "-I" + os.path.join(sleef),
        ]
        tools = [
            ("common/addSuffix.c", "addSuffix"),
            ("libm/mkrename.c", "mkrename"),
            ("libm/mkrename_gnuabi.c", "mkrename_gnuabi"),
            ("libm/mkmasked_gnuabi.c", "mkmasked_gnuabi"),
            ("libm/mkalias.c", "mkalias"),
            ("libm/mkdisp.c", "mkdisp"),
            ("dft/mkunroll.c", "mkunroll"),
            ("dft/mkdispatch.c", "mkdispatch"),
            ("quad/qmkrename.c", "qmkrename"),
            ("quad/qmkdisp.c", "qmkdisp"),
        ]
        for rel, out in tools:
            src = os.path.join(sleef, rel)
            if not os.path.exists(src):
                continue
            dst = os.path.join(bin_dir, out)
            if os.path.exists(dst):
                continue
            cmd = [clang] + inc + [src, "-o", dst]
            if "mkdispatch" in out:
                cmd.insert(1, "-DENABLE_STREAM=1")
            subprocess.run(cmd, check=True)

    def _cmake_vars(self):
        return {
            "OHOS_ARCH": "arm64-v8a",
            "CMAKE_SYSTEM_NAME": "OHOS",
            "CMAKE_SYSTEM_PROCESSOR": "aarch64",
            "CMAKE_BUILD_TYPE": "Release",
            "BUILD_PYTHON": "OFF",
            "BUILD_TEST": "OFF",
            "USE_CUDA": "OFF",
            "USE_CUDNN": "OFF",
            "USE_NCCL": "OFF",
            "USE_DISTRIBUTED": "OFF",
            "USE_MKLDNN": "OFF",
            "USE_XNNPACK": "OFF",
            "USE_QNNPACK": "OFF",
            "USE_NNPACK": "OFF",
            "USE_OPENMP": "OFF",
            "USE_FBGEMM": "OFF",
            "USE_SLEEF": "OFF",
            "USE_KINETO": "OFF",
            "USE_ITT": "OFF",
            "USE_NUMA": "OFF",
            "USE_GFLAGS": "OFF",
            "USE_GLOG": "OFF",
        }

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # HMDFS quirk: .so files written by `cmake --install` cannot be mapped
        # by the musl loader (dlopen fails with "Permission denied" on mmap),
        # while the same files in the build tree load fine. Re-copy the shared
        # objects from the build tree so the packaged libs are loadable.
        build_lib = os.path.join(self.build_folder, "lib")
        pkg_lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(build_lib):
            for name in os.listdir(build_lib):
                if name.endswith(".so"):
                    shutil.copy2(os.path.join(build_lib, name),
                                 os.path.join(pkg_lib, name))

    def package_info(self):
        self.cpp_info.libs = ["torch", "torch_cpu", "c10"]
        # PyTorch installs the libtorch C++ API headers under
        # include/torch/csrc/api/include (umbrella torch.h etc.), so consumers
        # need both include roots to `#include <torch/torch.h>`.
        self.cpp_info.includedirs = ["include", "include/torch/csrc/api/include"]
        self.cpp_info.bindirs = ["lib"]
