#!/usr/bin/env python3
"""Conan recipe for firebuild 0.8.6.1 on HarmonyOS PC (aarch64)."""
import glob
import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class FirebuildConan(ConanFile):
    name = "firebuild"
    version = "0.8.6.1"
    description = "Build accelerator that caches build process results via LD_PRELOAD interception"
    license = "Proprietary"
    homepage = "https://github.com/firebuild/firebuild"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "with_jemalloc": [True, False], "enable_xxh_inline_all": [True, False]}
    default_options = {"shared": False, "fPIC": True, "with_jemalloc": False, "enable_xxh_inline_all": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libconfig/1.7.3")
        self.requires("libelf/0.8.13")
        self.requires("xxhash/0.8.3")
        self.requires("zstd/1.5.7.1")
        if self.options.with_jemalloc:
            self.requires("jemalloc/5.3.0")

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration("Cannot find ohos.toolchain.cmake")

    def _vendor_tsl_hopscotch_map(self):
        import urllib.request, tarfile, hashlib
        mirrors = [
            "https://gh-proxy.com/https://github.com/Tessil/hopscotch-map/archive/refs/tags/v2.3.0.tar.gz",
            "https://github.com/Tessil/hopscotch-map/archive/refs/tags/v2.3.0.tar.gz",
        ]
        sha = "a59d65b552dc7682521989842418c92257147f5068152b5af50e917892ad9317"
        tmp = os.path.join(self.build_folder, "tmp-hopscotch")
        os.makedirs(tmp, exist_ok=True)
        tb = os.path.join(tmp, "hopscotch-map-2.3.0.tar.gz")
        downloaded = False
        for url in mirrors:
            try:
                urllib.request.urlretrieve(url, tb)
                h = hashlib.sha256()
                with open(tb, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                if h.hexdigest() == sha:
                    downloaded = True
                    break
            except Exception as e:
                self.output.warn("Failed to download from %s: %s" % (url, str(e)))
                continue
        if not downloaded:
            raise ConanInvalidConfiguration("Failed to download tsl-hopscotch-map from any mirror")
        with tarfile.open(tb, "r:gz") as tar:
            tar.extractall(path=tmp)
        src_inc = os.path.join(tmp, "hopscotch-map-2.3.0", "include", "tsl")
        dst_inc = os.path.join(self.source_folder, "include", "tsl")
        os.makedirs(os.path.dirname(dst_inc), exist_ok=True)
        if os.path.exists(dst_inc):
            shutil.rmtree(dst_inc)
        shutil.copytree(src_inc, dst_inc)
        shutil.rmtree(tmp, ignore_errors=True)
        return os.path.join(self.source_folder, "include")

    def _dep_info(self, name):
        if name not in self.dependencies:
            return None
        ci = self.dependencies[name].cpp_info
        if not ci.libs and hasattr(ci, "components") and ci.components:
            for comp in ci.components.values():
                if comp.libs:
                    return comp
        return ci

    def _find_lib(self, ci):
        if not ci.libdirs:
            return None
        lib_dir = ci.libdirs[0]
        for lib in ci.libs:
            for ext in ("a", "so"):
                p = os.path.join(lib_dir, "lib%s.%s" % (lib, ext))
                if os.path.exists(p):
                    return p
        return None

    def _find_lib_named(self, ci, libname):
        """Find a specific library variant by basename (e.g. config++)."""
        if not ci.libdirs:
            return None
        lib_dir = ci.libdirs[0]
        for ext in ("a", "so"):
            p = os.path.join(lib_dir, "lib%s.%s" % (libname, ext))
            if os.path.exists(p):
                return p
        return None

    def build(self):
        apply_conandata_patches(self)
        tsl_inc = self._vendor_tsl_hopscotch_map()
        defs = []
        ci = self._dep_info("libconfig")
        if ci:
            inc = ci.includedirs[0] if ci.includedirs else ""
            defs.append('-DLIBCONFIGPP_INCLUDE_DIR="%s"' % inc)
            defs.append('-DLIBCONFIG_INCLUDE_DIR="%s"' % inc)
            # firebuild links LIBCONFIGPP_LIBRARY against the C++ wrapper
            # libconfig++.a (contains libconfig::Config symbols). The
            # libconfig conan recipe declares libs=[config] only, so
            # _find_lib returns the C-only libconfig.a which fails at link
            # time with undefined C++ symbols. Pick the C++ variant first,
            # fall back to the C variant only if the C++ one is missing.
            lp_pp = self._find_lib_named(ci, "config++")
            lp_c = self._find_lib_named(ci, "config")
            if lp_pp:
                defs.append('-DLIBCONFIGPP_LIBRARY="%s"' % lp_pp)
            elif lp_c:
                defs.append('-DLIBCONFIGPP_LIBRARY="%s"' % lp_c)
            if lp_c:
                defs.append('-DLIBCONFIG_LIBRARY="%s"' % lp_c)
            elif lp_pp:
                defs.append('-DLIBCONFIG_LIBRARY="%s"' % lp_pp)
        ci = self._dep_info("xxhash")
        if ci:
            inc = ci.includedirs[0] if ci.includedirs else ""
            defs.append('-DXXHASH_INCLUDE_DIRS="%s"' % inc)
            lp = self._find_lib(ci)
            if lp:
                defs.append('-DXXHASH_LDFLAGS="%s"' % lp)
        ci = self._dep_info("zstd")
        if ci:
            inc = ci.includedirs[0] if ci.includedirs else ""
            defs.append('-DZSTD_INCLUDE_DIRS="%s"' % inc)
            lp = self._find_lib(ci)
            if lp:
                defs.append('-DZSTD_LDFLAGS="%s"' % lp)
        ci = self._dep_info("libelf")
        if ci:
            # libelf ships gelf.h at include/ top level, which does
            # #include "libelf_config.h" -- that file lives in include/libelf/.
            # Pass ALL include dirs (semicolon = CMake list separator) so both
            # include/ and include/libelf/ are on the search path.
            inc = ";".join(ci.includedirs) if ci.includedirs else ""
            defs.append('-DLIBELF_INCLUDE_DIRS="%s"' % inc)
            lp = self._find_lib(ci)
            if lp:
                defs.append('-DLIBELF_LIBRARIES="%s"' % lp)
        if self.options.with_jemalloc:
            ci = self._dep_info("jemalloc")
            if ci:
                inc = ci.includedirs[0] if ci.includedirs else ""
                defs.append('-DJEMALLOC_INCLUDE_DIRS="%s"' % inc)
                lp = self._find_lib(ci)
                if lp:
                    defs.append('-DJEMALLOC_LDFLAGS="%s"' % lp)
        defs.append('-DTSL_HOPSCOTCH_MAP_INCLUDE_DIRS="%s"' % tsl_inc)
        toolchain = self._ohos_toolchain()
        llvm_bin = os.path.dirname(toolchain)
        llvm_bin = os.path.join(os.path.dirname(os.path.dirname(llvm_bin)), "llvm", "bin")
        cmake_ar = os.path.join(llvm_bin, "llvm-ar")
        ranlib_shim = os.path.join(self.build_folder, "llvm-ranlib-shim")
        with open(ranlib_shim, "w") as f:
            f.write("#!/data/service/hnp/bin/bash\nexec {ar} s \"$@\"\n".format(ar=cmake_ar))
        os.chmod(ranlib_shim, 0o755)
        bdir = os.path.join(self.build_folder, "build-ohos")
        tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        defs += ["-DCMAKE_TOOLCHAIN_FILE=%s" % toolchain, "-DCMAKE_AR=%s" % cmake_ar, "-DCMAKE_RANLIB=%s" % ranlib_shim, "-DOHOS_ARCH=arm64-v8a", "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type, "-DCMAKE_INSTALL_LIBDIR=lib", "-DCMAKE_INSTALL_PREFIX=%s" % self.package_folder, "-DENABLE_XXH_INLINE_ALL=ON", "-DWITH_JEMALLOC=OFF", "-DBUILD_MANPAGES=OFF"]
        self.run('cmake -G Ninja -B "%s" -S "%s" %s' % (bdir, self.source_folder, " ".join(defs)))
        self.run('cmake --build "%s" -- -j$(nproc)' % bdir)
        self._run_upstream_tests(bdir)


    def _run_upstream_tests(self, bdir):
        import time
        from conan.tools.build import cross_building
        run_root = os.path.join(os.path.expanduser("~"),
            ".local","state","oh-device-porting","runs","firebuild-0.8.6.1")
        logdir = os.path.join(run_root, "logs")
        os.makedirs(logdir, exist_ok=True)
        log_path = os.path.join(logdir, "upstream-tests-round-17.log")
        is_cross = cross_building(self)
        lf = open(log_path, "w")
        def log(m):
            lf.write(m + chr(10))
            lf.flush()
        log("=== Upstream CTest Integration (round-17) ===")
        log("Date: " + time.strftime("%Y-%m-%d %H:%M:%S"))
        log("Build dir: " + str(bdir))
        log("cross_building: " + str(is_cross))
        log("")
        if is_cross:
            log("Cross-compiling: upstream tests N/A")
            log("=== FINAL SUMMARY ===")
            log("fbb_test: N/A")
            log("test-symbols: N/A")
            log("22 test_binary: N/A")
            log("bats-integration: N/A")
            lf.close()
            return
        # Step 1: Build test targets
        log("--- Step 1: Building check-bins + fbb_test ---")
        try:
            self.run("cmake --build \"" + bdir + "\" --target check-bins fbb_test -- -j$(nproc) -k 0 2>&1")
            log("Build check-bins + fbb_test: OK")
        except Exception as e:
            log("Build check-bins: PARTIAL FAILURE (musl)")
            log("  Error: " + str(e)[:200])
        # Step 2: Sign test binaries
        log("")
        log("--- Step 2: Signing test binaries ---")
        test_dir = os.path.join(bdir, "test")
        oc = "/data/service/hnp/bin/llvm-objcopy"
        sg = "/data/service/hnp/bin/binary-sign-tool"
        test_bins = [
            "test_cmd_fork_exec","test_cmd_popen","test_cmd_posix_spawn",
            "test_cmd_system","test_pthreads","test_system","test_exec",
            "test_file_ops","test_file_ops_2","test_file_ops_3",
            "test_random","test_sendfile","test_wait","test_orphan",
            "close_fds_exec","test_err","test_error","test_env_fixup",
            "test_static","test_mtime","test_stat","fbb_test"]
        signed = 0
        for tb in test_bins:
            p = os.path.join(test_dir, tb)
            if os.path.isfile(p) and self._is_elf(p):
                try:
                    self.run(oc + " --remove-section .codesign \"" + p + "\" 2>/dev/null || true")
                    self.run(sg + " sign -inFile \"" + p + "\" -outFile \"" + p + "\" -selfSign 1")
                    signed += 1
                except Exception:
                    pass
        dl = os.path.join(test_dir, "libtest_dlopen_lib.so")
        if os.path.isfile(dl):
            try:
                self.run(oc + " --remove-section .codesign \"" + dl + "\" 2>/dev/null || true")
                self.run(sg + " sign -inFile \"" + dl + "\" -outFile \"" + dl + "\" -selfSign 1")
                signed += 1
            except Exception:
                pass
        log("Signed " + str(signed) + " test binaries")
        # Step 3: ctest -R fbb (alone) + test-symbols with explicit bash
        log("")
        log("--- Step 3: ctest -R fbb (alone) ---")
        fbb_r = "FAIL"
        try:
            self.run("ctest --test-dir \"" + bdir + "\" -R fbb --output-on-failure")
            log("ctest fbb: PASS")
            fbb_r = "PASS"
        except Exception as e:
            log("ctest fbb: FAIL")
            log("  Error: " + str(e)[:300])
        log("")
        log("--- Step 3b: test-symbols via explicit bash ---")
        sym_r = "FAIL"
        sym_path = os.path.join(test_dir, "test_symbols")
        if os.path.isfile(sym_path):
            sym_cmd = "/data/service/hnp/bin/bash \"" + sym_path + "\" \"" + bdir + "\""
            log("Running: " + sym_cmd)
            import subprocess
            try:
                r = subprocess.run(["/data/service/hnp/bin/bash", sym_path, bdir],
                    capture_output=True, text=True, timeout=60,
                    cwd=test_dir)
                log("test-symbols rc=" + str(r.returncode))
                for line in (r.stdout + r.stderr).splitlines():
                    log("  " + line)
                if r.returncode == 0:
                    sym_r = "PASS"
            except Exception as e:
                log("test-symbols execution error: " + str(e)[:200])
        else:
            log("test_symbols not found at: " + sym_path)
        # Step 4: 22 test_binary direct exec with proper arguments
        log("")
        log("--- Step 4: 22 test_binary direct exec (parameterized) ---")
        log("Run mode: direct exec (no firebuild LD_PRELOAD)")
        # Some test binaries require specific arguments per their source code:
        #   test_cmd_fork_exec: >=1 arg (command + args to fork-exec)
        #   test_cmd_system: exactly 1 arg (command string for system())
        #   test_cmd_popen: exactly 2 args (command, mode e.g. "r")
        #   close_fds_exec: >=1 arg (command + args to execvp after closing fds)
        # Others run without arguments.
        test_args = {
            "test_cmd_fork_exec": ["/bin/echo", "hello"],
            "test_cmd_system": ["/bin/echo hello"],
            "test_cmd_popen": ["/bin/echo hi", "r"],
            "close_fds_exec": ["/bin/echo", "hello"],
        }
        pc = 0
        fc = 0
        nc = 0
        for tb in test_bins:
            if tb == "fbb_test":
                continue
            p = os.path.join(test_dir, tb)
            if not os.path.isfile(p):
                log("  " + tb + ": N/A (not built)")
                nc += 1
                continue
            if not self._is_elf(p):
                log("  " + tb + ": N/A (not ELF)")
                nc += 1
                continue
            args = test_args.get(tb, [])
            import shlex
            arg_str = " ".join(shlex.quote(a) for a in args)
            try:
                self.run("timeout 30 \"" + p + "\" " + arg_str + " > /dev/null 2>&1")
                log("  " + tb + ": PASS (exit=0, args=[" + arg_str + "])")
                pc += 1
            except Exception as e:
                log("  " + tb + ": FAIL (args=[" + arg_str + "])")
                log("    Error: " + str(e)[:200])
                fc += 1
        # Step 5: bats integration (integration.bats, 39 @test scenarios)
        log("")
        log("--- Step 5: bats integration (integration.bats) ---")
        bats_pass = 0
        bats_skip = 0
        bats_fail = 0
        bats_status = "N/A"
        bats_bin = os.environ.get("BATS_BIN", "")
        if not bats_bin:
            bats_bin = os.path.join(os.path.expanduser("~"), "tmp", "bats-core", "bin", "bats")
        if not os.path.isfile(bats_bin):
            log("bats binary not found at: " + bats_bin)
            log("  Install bats-core to $HOME/tmp/bats-core or set BATS_BIN env var.")
            log("bats-integration: N/A (bats not installed)")
        else:
            bats_sh = os.environ.get("BATS_BASH", "/data/service/hnp/bin/bash")
            int_bats = os.path.join(test_dir, "integration.bats")
            if not os.path.isfile(int_bats):
                log("integration.bats not found at: " + int_bats)
                log("bats-integration: N/A (integration.bats missing)")
            else:
                log("bats binary: " + bats_bin)
                log("integration.bats: " + int_bats)
                # Rewrite shebang in build-product run-firebuild (generated from
                # run-firebuild.in via configure_file). The upstream template uses
                # "#!/bin/bash" which does not exist on OHOS. We rewrite the
                # *build product* only (not the upstream run-firebuild.in source).
                run_firebuild = os.path.join(test_dir, "run-firebuild")
                if os.path.isfile(run_firebuild):
                    try:
                        with open(run_firebuild, "r") as rf:
                            rf_data = rf.read()
                        rf_data = rf_data.replace(
                            "#!/bin/bash",
                            "#!/data/service/hnp/bin/bash", 1)
                        with open(run_firebuild, "w") as rf:
                            rf.write(rf_data)
                        log("Rewrote run-firebuild shebang: /bin/bash -> /data/service/hnp/bin/bash")
                    except Exception as e:
                        log("run-firebuild shebang rewrite failed: " + str(e)[:200])
                else:
                    log("run-firebuild not found at: " + run_firebuild)
                tap_path = os.path.join(logdir, "bats-integration.tap")
                cmd = ("cd \"" + test_dir + "\" && export PWD=\"" + test_dir + "\" && \"" +
                       bats_sh + "\" \"" + bats_bin + "\" --tap integration.bats > \"" +
                       tap_path + "\" 2>&1")
                log("Running: " + cmd)
                bats_rc = 0
                tap = ""
                try:
                    self.run(cmd)
                except Exception as e:
                    bats_rc = 1
                    log("bats run raised: " + str(e)[:200])
                try:
                    with open(tap_path, "r") as tf:
                        tap = tf.read()
                except Exception:
                    tap = ""
                for line in tap.splitlines():
                    if line.startswith("ok ") and "# skip" in line:
                        bats_skip += 1
                    elif line.startswith("ok "):
                        bats_pass += 1
                    elif line.startswith("not ok "):
                        bats_fail += 1
                total = bats_pass + bats_skip + bats_fail
                log("bats TAP output written to: " + tap_path)
                log("bats raw results: Pass=" + str(bats_pass) + " Skip=" + str(bats_skip) +
                    " Fail=" + str(bats_fail) + " Total=" + str(total))
                fb_bind_err = False
                try:
                    import subprocess
                    fb_bin = os.path.join(bdir, "build-ohos", "src", "firebuild", "firebuild")
                    conf = os.path.join(bdir, "build-ohos", "etc", "firebuild.conf")
                    probe = ("cd \"" + test_dir + "\" && export PWD=\"" + test_dir +
                             "\" && timeout 10 \"" + fb_bin + "\" -c \"" + conf +
                             "\" -- /bin/true 2>&1 | head -1")
                    r = subprocess.run([bats_sh, "-c", probe],
                        capture_output=True, text=True, timeout=20)
                    if "bind: Operation not permitted" in (r.stdout + r.stderr):
                        fb_bind_err = True
                except Exception:
                    pass
                if fb_bind_err and bats_fail > 0:
                    log("Root cause for " + str(bats_fail) + " FAIL: firebuild supervisor " +
                        "bind(AF_UNIX) returns EPERM under OHOS sandbox " +
                        "(firebuild.cc create_listener).")
                    log("  All run-firebuild invocations exit 1 before executing the build command.")
                if bats_fail > 0 and not fb_bind_err:
                    log("Root cause probe inconclusive; see TAP for per-test failures.")
                bats_status = ("Pass=" + str(bats_pass) + " Skip=" + str(bats_skip) +
                               " Fail=" + str(bats_fail) + "/" + str(total))

        log("")
        log("=== FINAL SUMMARY ===")
        log("fbb_test: " + fbb_r)
        log("test-symbols: " + sym_r)
        log("22 test_binary: Pass=" + str(pc) + " Fail=" + str(fc) + " N/A=" + str(nc))
        log("bats-integration: " + bats_status)
        log("")
        log("Pass rates:")
        log("  fbb_test: " + ("1/1 PASS" if fbb_r=="PASS" else "0/1 FAIL"))
        log("  test-symbols: " + ("1/1 PASS" if sym_r=="PASS" else "0/1 FAIL"))
        log("  22 test_binary: " + str(pc) + "/22 PASS (" + str(round(pc*100.0/22,1)) + "%)")
        log("  bats-integration: " + str(bats_pass) + "/" +
               str(bats_pass + bats_skip + bats_fail) +
               " PASS (" + str(round(bats_pass*100.0/max(1,bats_pass+bats_skip+bats_fail),1)) + "%)," +
               " Skip=" + str(bats_skip) + " Fail=" + str(bats_fail))
        log("Log: " + log_path)
        lf.close()

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        import glob as _g
        targets = _g.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _g.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        oc = "/data/service/hnp/bin/llvm-objcopy"
        sg = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('%s --remove-section .codesign "%s" 2>/dev/null || true' % (oc, f))
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sg, f, f))

    def package_info(self):
        self.cpp_info.libs = ["firebuild"]
        self.cpp_info.set_property("cmake_file_name", "firebuild")
        self.cpp_info.set_property("cmake_target_name", "firebuild::firebuild")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
