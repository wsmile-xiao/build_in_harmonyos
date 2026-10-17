from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy
import os
import subprocess


class SherpaOnnxConan(ConanFile):
    name = "sherpa-onnx"
    version = "1.13.7"
    description = "Speech recognition, TTS, speaker diarization, and VAD using next-gen kaldi and onnxruntime"
    license = "Apache-2.0"
    url = "https://github.com/k2-fsa/sherpa-onnx"
    topics = ("speech-recognition", "tts", "onnxruntime", "asr", "vad")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "shared-library"

    options = {
        "enable_tts": [True, False],
        "enable_speaker_diarization": [True, False],
        "enable_c_api": [True, False],
        "enable_websocket": [True, False],
    }
    default_options = {
        "enable_tts": True,
        "enable_speaker_diarization": False,
        "enable_c_api": True,
        "enable_websocket": False,
        "onnxruntime/*:shared": True,
    }

    def requirements(self):
        self.requires("onnxruntime/1.27.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Override default extraction to handle symlinks in the tarball
        # Python 3.12+ tarfile filter='data' rejects absolute path symlinks
        # Use system tar command instead
        src_dir = self.source_folder
        # Check if CMakeLists.txt already exists (extraction succeeded)
        if os.path.exists(os.path.join(src_dir, "CMakeLists.txt")):
            return
        import hashlib
        import urllib.request
        data = self.conan_data["sources"]
        url = data["url"]
        sha256 = data["sha256"]
        tarball = os.path.join(src_dir, "_sherpa_onnx_source.tar.gz")
        # Try multiple URLs for download resilience
        urls = [url]
        # Add ghfast.top proxy fallback for GitHub URLs
        if "github.com" in url or "api.github.com" in url:
            urls.append(f"https://ghfast.top/{url}")
        # Add local file fallback
        local_tar = "/storage/Users/currentUser/.opendesk-tmp/sherpa-onnx/sherpa-onnx-1.13.7.tar.gz"
        if os.path.exists(local_tar):
            urls.append(f"file://{local_tar}")
        downloaded = False
        for try_url in urls:
            try:
                if try_url.startswith("file://"):
                    tarball = try_url[7:]
                else:
                    req = urllib.request.Request(try_url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        with open(tarball, "wb") as f:
                            while True:
                                chunk = resp.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                # Verify SHA256
                h = hashlib.sha256()
                with open(tarball, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                if h.hexdigest() == sha256:
                    downloaded = True
                    break
            except Exception:
                continue
        if not downloaded:
            raise Exception("Failed to download source from any URL")
        # Extract using tar (handles symlinks correctly)
        import shutil
        tar_cmd = shutil.which("tar") or "/usr/bin/tar"
        subprocess.run([tar_cmd, "xzf", tarball, "--strip-components=1", "-C", src_dir], check=True)
        # Clean up downloaded tarball (keep local file)
        if not url.startswith("file://") and os.path.exists(tarball):
            os.unlink(tarball)

    def generate(self):
        tc = CMakeToolchain(self)
        onnxrt = self.dependencies["onnxruntime"]
        onnxrt_info = onnxrt.cpp_info.aggregated_components()
        # onnxruntime headers are in <prefix>/include/onnxruntime/
        # sherpa-onnx includes "onnxruntime_cxx_api.h" without prefix
        onnxrt_inc = onnxrt_info.includedirs[0]
        onnxrt_inc_subdir = os.path.join(onnxrt_inc, "onnxruntime")
        if os.path.isdir(onnxrt_inc_subdir):
            onnxrt_inc = onnxrt_inc_subdir
        onnxrt_lib = onnxrt_info.libdirs[0]
        env = Environment()
        env.define("SHERPA_ONNXRUNTIME_INCLUDE_DIR", onnxrt_inc)
        env.define("SHERPA_ONNXRUNTIME_LIB_DIR", onnxrt_lib)
        tc.generate()
        envvars = env.vars(self, scope="build")
        envvars.save_script("sherpa_onnx_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "BUILD_SHARED_LIBS": "ON",
            "SHERPA_ONNX_ENABLE_TTS": "ON" if self.options.enable_tts else "OFF",
            "SHERPA_ONNX_ENABLE_BINARY": "OFF",
            "SHERPA_ONNX_ENABLE_PYTHON": "OFF",
            "SHERPA_ONNX_ENABLE_TESTS": "OFF",
            "SHERPA_ONNX_ENABLE_CHECK": "OFF",
            "SHERPA_ONNX_ENABLE_PORTAUDIO": "OFF",
            "SHERPA_ONNX_ENABLE_JNI": "OFF",
            "SHERPA_ONNX_ENABLE_C_API": "ON" if self.options.enable_c_api else "OFF",
            "SHERPA_ONNX_ENABLE_WEBSOCKET": "ON" if self.options.enable_websocket else "OFF",
            "SHERPA_ONNX_ENABLE_SPEAKER_DIARIZATION": "ON" if self.options.enable_speaker_diarization else "OFF",
            "BUILD_PIPER_PHONMIZE_EXE": "OFF",
            "BUILD_PIPER_PHONMIZE_TESTS": "OFF",
            "BUILD_ESPEAK_NG_EXE": "OFF",
            "BUILD_ESPEAK_NG_TESTS": "OFF",
        })
        cmake.build()
        cmake.install()

    def package(self):
        # Copy onnxruntime shared libraries alongside sherpa-onnx libs (upstream pattern)
        onnxrt = self.dependencies["onnxruntime"]
        onnxrt_info = onnxrt.cpp_info.aggregated_components()
        onnxrt_lib_dir = onnxrt_info.libdirs[0]
        for f in os.listdir(onnxrt_lib_dir):
            if f.startswith("libonnxruntime") and (f.endswith(".so") or ".so." in f):
                copy(self, f, onnxrt_lib_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sherpa-onnx")
        self.cpp_info.set_property("cmake_target_name", "sherpa-onnx::sherpa-onnx-c-api")
        self.cpp_info.libs = ["sherpa-onnx-c-api", "sherpa-onnx-cxx-api"]
        self.cpp_info.requires = ["onnxruntime::onnxruntime"]
        self.cpp_info.includedirs = [os.path.join("include", "sherpa-onnx", "c-api")]
