#!/usr/bin/env python3
"""Conan recipe for slang 2026.14 — CMake-based shader compiler.

Slang is a shading language compiler supporting HLSL/Slang→SPIR-V/GLSL/HLSL.
Built as a static library (R26) with command-line tools (slangc, slangi).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
)


class SlangConan(ConanFile):
    name = "slang"
    version = "2026.14"
    description = "Slang is a shading language compiler supporting HLSL/Slang to SPIR-V/GLSL/HLSL targets"
    license = "MIT"
    homepage = "https://github.com/shader-slang/slang"
    url = ""  # CI fills this

    package_type = "library"

    # R32: settings.os must use in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download the main tarball
        get(self, **self.conan_data["sources"], strip_root=True)
        # The GitHub tarball does not include git submodules.
        # Download required submodules.
        self._download_submodules()

    def _find_git(self):
        """Find git executable in common HarmonyOS paths."""
        for path in ["/data/service/hnp/bin/git", "/usr/bin/git", "/usr/local/bin/git"]:
            if os.path.exists(path):
                return path
        return shutil.which("git")

    def _download_submodules(self):
        """Download git submodules required for building slang.

        The GitHub release tarball does not include submodule contents.
        We download each required submodule as a tarball from GitHub's
        archive API, which works without git and without SSL issues.
        Submodule metadata (repo, commit, sha256) is declared in conandata.yml.
        """
        submodules = self.conan_data.get("submodules", [])

        src_folder = self.source_folder
        git_bin = self._find_git()

        for sub in submodules:
            path = sub["path"]
            repo = sub["repo"]
            commit = sub["commit"]
            sha256 = sub.get("sha256")

            full_path = os.path.join(src_folder, path)
            # Check if already populated
            if os.listdir(full_path) if os.path.exists(full_path) else []:
                has_content = any(
                    os.path.exists(os.path.join(full_path, f))
                    for f in ["CMakeLists.txt", "meson.build", "onelua.c", "include"]
                )
                if has_content:
                    continue  # Already populated

            self.output.info(f"Downloading submodule: {path}")
            os.makedirs(full_path, exist_ok=True)

            # Try git clone first, then fallback to tarball download
            cloned = False
            if git_bin:
                # Try GitHub direct first, then proxies (CI workers may need gh-proxy)
                for git_url in [
                    f"https://github.com/{repo}.git",
                    f"https://gh-proxy.com/https://github.com/{repo}.git",
                    f"https://ghfast.top/https://github.com/{repo}.git",
                ]:
                    try:
                        subprocess.run(
                            [git_bin, "clone", "--depth", "1", git_url, full_path],
                            check=True, capture_output=True, timeout=300
                        )
                        subprocess.run(
                            [git_bin, "fetch", "--depth", "1", git_url, commit],
                            cwd=full_path, check=True, capture_output=True, timeout=300
                        )
                        subprocess.run(
                            [git_bin, "checkout", commit],
                            cwd=full_path, check=True, capture_output=True, timeout=30
                        )
                        cloned = True
                        break
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                        continue

            if not cloned:
                # Fallback: download as tarball from GitHub archive API
                self._download_submodule_tarball(path, repo, commit, sha256)

    def _download_submodule_tarball(self, path, repo, commit, sha256=None):
        """Fallback: download submodule as tarball.

        Tries GitHub direct URL first, then ghfast.top proxy.
        Uses Conan's built-in get() which handles SSL verification and
        SHA256 integrity checking internally.
        Falls back to urllib with SSL verification enabled (not disabled).
        """
        # Try GitHub direct first, then proxies (CI workers may need gh-proxy)
        archive_urls = [
            f"https://github.com/{repo}/archive/{commit}.tar.gz",
            f"https://gh-proxy.com/https://github.com/{repo}/archive/{commit}.tar.gz",
            f"https://ghfast.top/https://github.com/{repo}/archive/{commit}.tar.gz",
        ]

        src_folder = self.source_folder
        full_path = os.path.join(src_folder, path)
        os.makedirs(full_path, exist_ok=True)

        last_error = None
        for archive_url in archive_urls:
            # Preferred: use Conan's built-in download (handles SSL + SHA256)
            try:
                get(self, archive_url, destination=full_path, strip_root=True,
                    sha256=sha256)
                return
            except Exception as e:
                last_error = e
                self.output.warning(f"Conan get() failed for {path} via {archive_url}: {e}")
                continue

        # Last resort: urllib with SSL verification enabled
        import ssl
        import urllib.request
        import tarfile
        import io
        import hashlib

        self.output.info(f"Trying urllib fallback for {path}...")
        ctx = ssl.create_default_context()

        for archive_url in archive_urls:
            try:
                req = urllib.request.Request(archive_url, headers={"User-Agent": "conan/2"})
                with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
                    data = resp.read()
                break
            except Exception as e:
                last_error = e
                continue
        else:
            raise ConanException(
                f"Failed to download submodule {path} from all URLs: {last_error}"
            )

        # Verify SHA256 if provided
        if sha256:
            actual_sha256 = hashlib.sha256(data).hexdigest()
            if actual_sha256 != sha256:
                raise ConanException(
                    f"SHA256 mismatch for submodule {path}: "
                    f"expected {sha256}, got {actual_sha256}"
                )
            self.output.info(f"SHA256 verified for {path}")

        # Extract tarball with path traversal protection
        extract_dir = full_path + "_extract"
        os.makedirs(extract_dir, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            safe_members = [
                m for m in tar.getmembers()
                if not (m.name.startswith("/") or ".." in m.name)
            ]
            tar.extractall(extract_dir, members=safe_members)

        # Move contents from the top-level directory to the target path
        extracted = os.listdir(extract_dir)
        if extracted:
            src_dir = os.path.join(extract_dir, extracted[0])
            for item in os.listdir(src_dir):
                src_item = os.path.join(src_dir, item)
                dst_item = os.path.join(full_path, item)
                if os.path.exists(dst_item):
                    if os.path.isdir(dst_item):
                        shutil.rmtree(dst_item)
                    else:
                        os.remove(dst_item)
                shutil.move(src_item, dst_item)
        shutil.rmtree(extract_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-same-name library must be static
        tc.variables["SLANG_LIB_TYPE"] = "STATIC"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Disable platform-specific features not available on OHOS
        tc.variables["SLANG_ENABLE_CUDA"] = "OFF"
        tc.variables["SLANG_ENABLE_OPTIX"] = "OFF"
        tc.variables["SLANG_ENABLE_DXIL"] = "OFF"
        tc.variables["SLANG_ENABLE_TESTS"] = "OFF"
        tc.variables["SLANG_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["SLANG_ENABLE_SLANG_RHI"] = "OFF"
        tc.variables["SLANG_ENABLE_GFX"] = "OFF"
        tc.variables["SLANG_SLANG_LLVM_FLAVOR"] = "DISABLE"
        tc.variables["SLANG_EXCLUDE_DAWN"] = "ON"
        tc.variables["SLANG_EXCLUDE_TINT"] = "ON"
        tc.variables["SLANG_ENABLE_SLANGD"] = "OFF"
        tc.variables["SLANG_ENABLE_REPLAYER"] = "OFF"
        tc.variables["SLANG_ENABLE_PCH"] = "OFF"
        tc.variables["SLANG_STANDARD_MODULE_DEVELOP_BUILD"] = "OFF"
        # Set RPATH so slangc can dlopen runtime .so modules from its own dir
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()

        # On HarmonyOS, newly built binaries need ELF signing before execution.
        # The build process generates and executes build-time tools (generators),
        # so we need to sign binaries during the build, not just after.
        if self.settings.os == "OHOS":
            self._build_with_signing(cmake)
        else:
            cmake.build()

        # Sign all final binaries (OHOS only)
        if self.settings.os == "OHOS":
            self._sign_binaries()

    def _build_with_signing(self, cmake):
        """Run cmake build with automatic binary signing on HarmonyOS.

        Two-phase approach:
        Phase 1: Build with make -k (keep going) to build all generators,
                 then batch-sign all executables.
        Phase 2: Normal build — generators are signed, execution succeeds.
        Falls back to retry loop if new unsigned binaries appear.
        Uses -j2 in phase 2+ to speed up compilation and stay within CI timeout.
        """
        import select
        import time

        build_dir = self.build_folder
        already_signed = set()
        failed_sign_bins = set()

        # Pre-check signing tools
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            raise ConanException(
                f"Signing tools missing on OHOS: "
                f"binary-sign-tool={'found' if sign_tool else 'MISSING'}, "
                f"llvm-objcopy={'found' if objcopy else 'MISSING'}. "
                f"Build requires these tools for ELF binary signing."
            )

        max_retries = 5
        idle_timeout = 300  # 5 min with no output = probably hung
        # Use writable TMPDIR to avoid make jobserver fifo permission issues
        build_env = os.environ.copy()
        build_env["TMPDIR"] = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        os.makedirs(build_env["TMPDIR"], exist_ok=True)

        for attempt in range(max_retries):
            # Phase 1 uses -j2 -k (keep going, find all generators)
            # Phase 2+ uses -j4 (multi-threaded, generators already signed)
            make_flags = ["-j2", "-k"] if attempt == 0 else ["-j4"]
            self.output.info(f"Build attempt {attempt+1} (flags: {' '.join(make_flags)})...")

            proc = subprocess.Popen(
                ["cmake", "--build", ".", "--", *make_flags],
                cwd=build_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=build_env,
            )

            output_lines = []
            timed_out = False
            last_output_time = time.time()

            # Read stdout with idle timeout protection (P2 fix from AI review)
            while True:
                ready, _, _ = select.select([proc.stdout], [], [], 10)
                if ready:
                    line = proc.stdout.readline()
                    if not line:
                        break  # EOF — process exited
                    print(line, end='')
                    output_lines.append(line)
                    last_output_time = time.time()
                else:
                    # No output — check if process is done
                    if proc.poll() is not None:
                        # Process exited, drain any remaining output
                        remaining = proc.stdout.read()
                        if remaining:
                            print(remaining, end='')
                            output_lines.append(remaining)
                        break
                    # Check for idle timeout (process alive but no output)
                    if time.time() - last_output_time > idle_timeout:
                        proc.kill()
                        proc.wait()
                        timed_out = True
                        self.output.info(
                            f"Build idle timeout on attempt {attempt+1} "
                            f"(no output for {idle_timeout}s)"
                        )
                        break

            if not timed_out:
                proc.wait(timeout=3600)

            if timed_out:
                self._sign_all_executables(build_dir, failed_sign_bins, already_signed)
                continue

            if proc.returncode == 0:
                self.output.info("Build completed successfully")
                return

            # Check for unsigned binary execution failures.
            # Filter out "make: jobserver mkfifo" false positives — those are
            # file permission issues with the jobserver fifo, not unsigned binaries.
            combined_output = ''.join(output_lines)
            has_unsigned_binary = any(
                "Operation not permitted" in line and "/bin/sh:" in line
                for line in output_lines
            )
            if has_unsigned_binary:
                self.output.info(f"Unsigned binaries detected, batch signing...")
                signed_count = self._sign_all_executables(
                    build_dir, failed_sign_bins, already_signed
                )
                if signed_count == 0:
                    raise ConanException(
                        f"Cannot sign binaries (all failed): {failed_sign_bins}. "
                        f"Already signed: {already_signed}."
                    )
                continue

            self.output.error(f"Build failed (attempt {attempt+1}, return code {proc.returncode})")
            raise ConanException(f"Build failed: {proc.returncode}")

        raise ConanException(f"Build failed after {max_retries} retries (binary signing loop)")

    def _sign_all_executables(self, build_dir, failed_bins, already_signed=None):
        """Scan build directory for ELF executables and sign them all at once.

        Always re-signs all executables to ensure valid signatures.
        Returns the number of newly signed binaries.
        """
        if already_signed is None:
            already_signed = set()

        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            return 0

        signed_count = 0
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                fpath = os.path.join(root, f)
                # Skip binaries that previously failed signing
                if fpath in failed_bins:
                    continue
                if f.endswith(".dwarf"):
                    continue
                if not os.access(fpath, os.X_OK):
                    continue
                # Check if it's an ELF file (skip scripts and AR archives)
                try:
                    with open(fpath, 'rb') as fp:
                        magic = fp.read(4)
                        if magic != b'\x7fELF':
                            continue
                        # Check ELF type: only sign executables (ET_EXEC=2) and
                        # shared objects (ET_DYN=3), skip relocatable (ET_REL=1)
                        fp.seek(16)  # e_type is at ELF header offset 16 (0x10)
                        elf_type = fp.read(2)
                        elf_type_val = int.from_bytes(elf_type, 'little')
                        if elf_type_val == 1:  # ET_REL (object files)
                            continue
                except (IOError, OSError):
                    continue
                # Always re-sign: previous signing may have been invalidated
                # by a rebuild or may have produced an invalid signature.
                if self._sign_single_binary(fpath):
                    signed_count += 1
                    already_signed.add(fpath)
                else:
                    failed_bins.add(fpath)
        return signed_count

    def _sign_single_binary(self, bin_path):
        """Sign a single ELF binary on HarmonyOS. Returns True on success, False on failure."""
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            return False
        try:
            # Preserve original timestamp to prevent make from rebuilding
            # the binary after signing (which would create a new unsigned binary)
            stat = os.stat(bin_path)
            orig_atime, orig_mtime = stat.st_atime, stat.st_mtime

            # Remove existing .codesign section if present.
            r = subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                              capture_output=True, timeout=10)
            # Sign the binary (adds .codesign section with valid signature)
            subprocess.run([sign_tool, "sign", "-inFile", bin_path,
                           "-outFile", bin_path, "-selfSign", "1"],
                          capture_output=True, timeout=30, check=True)
            os.chmod(bin_path, 0o755)
            # Restore original timestamp so make doesn't rebuild the binary
            os.utime(bin_path, (orig_atime, orig_mtime))
            self.output.info(f"Signed: {os.path.basename(bin_path)}")
            return True
        except subprocess.CalledProcessError as e:
            self.output.warning(f"Signing tool failed for {bin_path}: {e.stderr.decode() if e.stderr else e}")
            return False
        except Exception as e:
            self.output.warning(f"Failed to sign {bin_path}: {e}")
            return False

    def _sign_binaries(self):
        """Sign ELF binaries on HarmonyOS to allow execution."""
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            return  # Not on HarmonyOS or tools not found

        build_dir = self.build_folder
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                if f.endswith(".dwarf"):
                    continue
                fpath = os.path.join(root, f)
                if not os.access(fpath, os.X_OK):
                    continue
                # Check if it's an ELF file (skip scripts)
                try:
                    with open(fpath, 'rb') as fp:
                        magic = fp.read(4)
                        if magic != b'\x7fELF':
                            continue
                        # Skip relocatable files (ET_REL=1), consistent with
                        # _sign_all_executables
                        fp.seek(16)  # e_type is at ELF header offset 16 (0x10)
                        elf_type = fp.read(2)
                        elf_type_val = int.from_bytes(elf_type, 'little')
                        if elf_type_val == 1:  # ET_REL (object files)
                            continue
                except (IOError, OSError):
                    continue
                try:
                    # Preserve timestamp to prevent make rebuilds
                    stat = os.stat(fpath)
                    # Remove existing .codesign section if present
                    subprocess.run([objcopy, "--remove-section", ".codesign", fpath],
                                  capture_output=True, timeout=10)
                    subprocess.run([sign_tool, "sign", "-inFile", fpath,
                                   "-outFile", fpath, "-selfSign", "1"],
                                  capture_output=True, timeout=30, check=True)
                    os.chmod(fpath, 0o755)
                    os.utime(fpath, (stat.st_atime, stat.st_mtime))
                except subprocess.CalledProcessError as e:
                    self.output.warning(f"Signing tool failed for {fpath}: {e.stderr.decode() if e.stderr else e}")
                except Exception as e:
                    self.output.warning(f"Failed to sign {fpath}: {e}")

    def _find_tool(self, name):
        """Find a tool in common paths."""
        for path in ["/data/service/hnp/bin", "/usr/bin", "/usr/local/bin"]:
            full = os.path.join(path, name)
            if os.path.exists(full):
                return full
        return shutil.which(name)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy all static libraries needed for downstream linking.
        # Slang's CMakeLists.txt only installs some libs; the embedded
        # submodule libs (cmark, miniz, lz4, glslang, SPIRV-Tools) are
        # required by libslang-compiler.a and libcore.a but not installed.
        pkg_lib = os.path.join(self.package_folder, "lib")
        build_type = str(self.settings.build_type) if self.settings.build_type else "Release"
        candidate_dirs = [
            os.path.join(self.build_folder, build_type, "lib"),
            os.path.join(self.build_folder, "lib"),
        ]
        # Main libs + external submodule deps
        libs_to_copy = [
            "libcore.a", "libcompiler-core.a", "libslang-cpp-parser.a",
            "libslang-compiler.a", "libslang-rt.a",
            "libcmark-gfm.a", "libminiz.a", "liblz4.a",
            "libglslang.a", "libSPIRV.a",
            "libSPIRV-Tools.a", "libSPIRV-Tools-opt.a", "libSPIRV-Tools-link.a",
        ]
        for lib in libs_to_copy:
            found = False
            # Check candidate_dirs first, then search build tree
            for build_lib in candidate_dirs:
                src = os.path.join(build_lib, lib)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(pkg_lib, lib))
                    found = True
                    break
            if not found:
                for root, dirs, files in os.walk(self.build_folder):
                    if lib in files:
                        src = os.path.join(root, lib)
                        shutil.copy2(src, os.path.join(pkg_lib, lib))
                        found = True
                        break
            if not found:
                raise ConanException(
                    f"Required library {lib} not found in build tree; "
                    f"downstream linking will fail"
                )

        # Copy runtime .so modules to bin/ (slangc loads them by basename
        # from its own directory at runtime via dlopen)
        pkg_bin = os.path.join(self.package_folder, "bin")
        for so_name in ["libslang-glslang-2026.14.so", "libslang-glsl-module-2026.14.so"]:
            so_src = os.path.join(pkg_lib, so_name)
            if os.path.exists(so_src):
                shutil.copy2(so_src, os.path.join(pkg_bin, so_name))
                # Also create a copy without 'lib' prefix — slangc's dlopen()
                # looks for "slang-glslang-2026.14.so" not "libslang-...so"
                short_name = so_name[3:]  # Strip "lib" prefix
                shutil.copy2(so_src, os.path.join(pkg_bin, short_name))

    def package_info(self):
        # Link order: dependents first, dependencies last
        self.cpp_info.libs = [
            "slang-compiler", "slang-cpp-parser", "compiler-core", "core", "slang-rt",
            "cmark-gfm", "miniz", "lz4",
            "glslang", "SPIRV",
            "SPIRV-Tools", "SPIRV-Tools-opt", "SPIRV-Tools-link",
        ]
        self.cpp_info.bindirs = ["bin"]
        # Include bin/ in libdirs so conanrun sets LD_LIBRARY_PATH to find
        # the runtime .so modules (slang-glslang, slang-glsl-module) there
        self.cpp_info.libdirs = ["lib", "bin", "lib/slang-standard-module-2026.14"]
        # Explicitly set LD_LIBRARY_PATH for conanrun (slangc uses dlopen to
        # load runtime .so modules; some Conan versions don't auto-generate
        # LD_LIBRARY_PATH from libdirs)
        self.runenv.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "bin"))
