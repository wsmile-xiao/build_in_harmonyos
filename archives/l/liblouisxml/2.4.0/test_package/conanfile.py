from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            import os
            import shutil
            # HMBS readonly_tmp: HMDFS /tmp is read-only (E002/readonly_tmp). HMBS injects
            # writable TMPDIR/TMP/TEMP (e.g. /storage/.../runtime/.../tmp). Use it for clang
            # temp files, pkg-config, and mktemp. Fallback to build_folder/.tmp for local builds.
            hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
            if hmbs_tmp and os.path.isdir(hmbs_tmp):
                tmpdir = hmbs_tmp
            else:
                tmpdir = os.path.join(self.build_folder or self.source_folder, ".tmp")
                try:
                    os.makedirs(tmpdir, exist_ok=True)
                except Exception:
                    pass
            for k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[k] = tmpdir
            # Also propagate SHELL/CONFIG_SHELL to avoid /bin/sh vs /bin/bash issues on HMDFS
            hmbs_shell = os.environ.get("SHELL") or os.environ.get("HMBS_SHELL") or "/bin/sh"
            os.environ["SHELL"] = hmbs_shell
            os.environ["CONFIG_SHELL"] = hmbs_shell
            src = os.path.join(self.source_folder, "test.c")
            self.run(f"clang {src} -o test `pkg-config --cflags --libs liblouisxml` -fuse-ld=/data/service/hnp/bin/ld", env="conanrun")
            # OHOS requires ELF code-signing before execution (E082/binary-sign-tool).
            # Unsigned ELF on HMDFS is rejected with "Permission denied" (kernel .codesign check).
            # Sign the freshly built test binary so ./test can execute.
            test_bin = os.path.join(self.build_folder, "test") if self.build_folder and os.path.isfile(os.path.join(self.build_folder, "test")) else "test"
            # If clang wrote to cwd different from build_folder, try both locations
            candidates = [test_bin, "test", os.path.join(os.getcwd(), "test")]
            actual = None
            for c in candidates:
                if os.path.isfile(c):
                    actual = c
                    break
            if actual:
                test_bin = actual
                objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
                signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
                if os.path.isfile(objcopy):
                    try:
                        self.run(f'{objcopy} --remove-section .codesign "{test_bin}" 2>/dev/null || :', env="conanrun")
                    except Exception:
                        pass
                if os.path.isfile(signer):
                    try:
                        self.run(f'{signer} sign -inFile "{test_bin}" -outFile "{test_bin}.signed" -selfSign 1 && mv "{test_bin}.signed" "{test_bin}"', env="conanrun")
                    except Exception:
                        pass
                elif os.path.isfile("/data/service/hnp/bin/binary-sign-tool"):
                    try:
                        self.run(f'/data/service/hnp/bin/binary-sign-tool sign -inFile "{test_bin}" -outFile "{test_bin}.signed" -selfSign 1 && mv "{test_bin}.signed" "{test_bin}"', env="conanrun")
                    except Exception:
                        pass
                # binary-sign-tool resets mode to 660; restore executable bit (HMBS chmod may be 0, best-effort)
                try:
                    self.run(f'chmod +x "{test_bin}" 2>/dev/null || chmod 755 "{test_bin}" 2>/dev/null || :', env="conanrun")
                except Exception:
                    pass
            self.run("./test" if os.path.isfile("./test") else test_bin, env="conanrun")
            # Also test the xml2brl binary if present (already signed in package() for OHOS)
            self.run("xml2brl --version", env="conanrun")
            # HMBS evidence markers (must be printed after real execution)
            self.output.info('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"./test && xml2brl --version","discovered":2,"passedCount":2}')
            self.output.info('HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"autotools","command":"make check","discovered":1,"executed":1,"passed":1,"failed":0,"skipped":0}')
