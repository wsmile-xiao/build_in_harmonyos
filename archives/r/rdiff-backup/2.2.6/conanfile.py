#!/usr/bin/env python3
"""Conan recipe for rdiff-backup 2.2.6."""

import glob
import os
import shlex
import shutil
import subprocess
import sys
import sysconfig

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RdiffBackupConan(ConanFile):
    name = "rdiff-backup"
    version = "2.2.6"
    description = "Reverse incremental backup and restore utility"
    license = "GPL-2.0-or-later"
    homepage = "https://rdiff-backup.net/"
    url = "https://github.com/rdiff-backup/rdiff-backup"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("librsync/2.3.4")
        self.requires("pyyaml/6.0.2", run=True)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rdiff-backup supports POSIX-like Linux/OHOS builds")
        if sys.version_info < (3, 6):
            raise ConanInvalidConfiguration("rdiff-backup 2.2.6 requires Python 3.6 or newer")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        cc = self._compiler_c()
        cflags = self._profile_list("tools.build:cflags")
        shared_flags = self._profile_list("tools.build:sharedlinkflags")
        python_link_flags = self._python_link_flags()

        env = Environment()
        env.define("CC", cc)
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.define("TEMP", os.path.join(self.build_folder, "tmp"))
        env.define("TMP", os.path.join(self.build_folder, "tmp"))
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.define("SETUPTOOLS_SCM_PRETEND_VERSION", self.version)
        if cflags:
            env.define("CFLAGS", " ".join(cflags))
        env.define("LDSHARED", " ".join([cc, "-shared"] + cflags + shared_flags + python_link_flags))
        env.vars(self).save_script("rdiff_backup_build")

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)

        build_deps = os.path.join(self.build_folder, "_build_deps")
        self.run(
            f'"{sys.executable}" -m pip install --disable-pip-version-check '
            f'--no-compile --prefer-binary --target "{build_deps}" '
            '"setuptools>=68" "wheel" "setuptools_scm>=8"'
        )

        stage = self._stage_folder()
        os.makedirs(stage, exist_ok=True)
        record = os.path.join(self.build_folder, "install-record.txt")
        librsync_dir = self.dependencies["librsync"].package_folder

        build_env = Environment()
        build_env.prepend_path("PYTHONPATH", build_deps)
        build_env.prepend_path("PYTHONPATH", self._dependency_site_packages("pyyaml"))
        with build_env.vars(self).apply():
            cmd = [
                sys.executable,
                "setup.py",
                f"--librsync-dir={librsync_dir}",
                "install",
                f"--prefix={stage}",
                "--single-version-externally-managed",
                f"--record={record}",
            ]
            self.run(
                " ".join(shlex.quote(str(part)) for part in cmd),
                cwd=self.source_folder,
                env=["conanbuild", "rdiff_backup_build"],
            )

        self._sign_python_extensions(stage)
        if str(self.settings.os) == "OHOS":
            self._verify_ohos_stage_artifacts(stage)
            if self._python_link_flags():
                self._run_upstream_subset(stage)
            else:
                self.output.warning(
                    "OHOS Python shared library was not found; keeping signed-artifact "
                    "validation and skipping cache-path upstream subset imports."
                )
        else:
            self._run_upstream_subset(stage)

    def package(self):
        copy(self, "*", src=self._stage_folder(), dst=self.package_folder)
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self._sign_python_extensions(self.package_folder)

    def package_info(self):
        site_packages = self._package_site_packages(self.package_folder)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        python_libdir = self._python_library_dir()
        if python_libdir and os.path.isdir(python_libdir):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", python_libdir)
        self.buildenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _run_upstream_subset(self, stage):
        site_packages = self._package_site_packages(stage)
        test_env = Environment()
        test_env.prepend_path("PATH", os.path.join(stage, "bin"))
        test_env.prepend_path(
            "PATH",
            os.path.join(self.dependencies["librsync"].package_folder, "bin"),
        )
        for path in ("/bin", "/usr/bin", "/sbin", "/usr/sbin"):
            test_env.append_path("PATH", path)
        test_env.prepend_path("PYTHONPATH", site_packages)
        test_env.prepend_path("PYTHONPATH", self._dependency_site_packages("pyyaml"))
        test_env.prepend_path("PYTHONPATH", os.path.join(self.source_folder, "testing"))
        test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.dependencies["librsync"].package_folder, "lib"))
        python_libdir = self._python_library_dir()
        if python_libdir and os.path.isdir(python_libdir):
            test_env.prepend_path("LD_LIBRARY_PATH", python_libdir)
        test_env.define("TOX_ENV_DIR", os.path.join(self.build_folder, "upstream-test-env"))
        test_env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        test_env.define("TEMP", os.path.join(self.build_folder, "tmp"))
        test_env.define("TMP", os.path.join(self.build_folder, "tmp"))
        test_env.define("PYTHONDONTWRITEBYTECODE", "1")
        os.makedirs(os.path.join(self.build_folder, "upstream-test-env"), exist_ok=True)

        scripts = [
            "testing/commontest.py",
            "testing/api_test.py",
            "testing/setconnectionstest.py",
            "testing/timetest.py",
            "testing/iterfiletest.py",
            "testing/hashtest.py",
            "testing/utils_simpleps_test.py",
            "testing/ctest.py",
            "testing/librsynctest.py",
            "testing/action_complete_test.py",
            "testing/location_lock_test.py",
            "testing/action_compare_test.py",
            "testing/action_list_test.py",
            "testing/action_remove_test.py",
            "testing/action_verify_test.py",
            "testing/readonly_actions_test.py",
            "testing/rdb_arguments.py",
        ]
        with test_env.vars(self).apply():
            self.run('"rdiff-backup" --version', cwd=self.source_folder)
            for script in scripts:
                self._run_upstream_test_script(script)

    def _run_upstream_test_script(self, script):
        script_path = os.path.join(self.source_folder, script)
        if str(self.settings.os) == "OHOS" and script == "testing/librsynctest.py":
            runner = (
                "import subprocess, runpy, sys; "
                "subprocess._USE_POSIX_SPAWN = False; "
                "script = sys.argv[1]; "
                "sys.argv = sys.argv[1:]; "
                'runpy.run_path(script, run_name="__main__")'
            )
            cmd = [
                sys.executable,
                "-c",
                runner,
                script_path,
                "--verbose",
                "--buffer",
            ]
        else:
            cmd = [sys.executable, script_path, "--verbose", "--buffer"]
        self.run(" ".join(shlex.quote(str(part)) for part in cmd), cwd=self.source_folder)

    def _stage_folder(self):
        return os.path.join(self.build_folder, "stage")

    def _package_site_packages(self, root):
        candidates = glob.glob(os.path.join(root, "lib", "python*", "site-packages"))
        candidates += glob.glob(os.path.join(root, "lib", "python", "site-packages"))
        for path in candidates:
            if os.path.isdir(os.path.join(path, "rdiff_backup")):
                return path
        raise RuntimeError("rdiff_backup site-packages directory was not found")

    def _dependency_site_packages(self, dep_name):
        package_folder = self.dependencies[dep_name].package_folder
        candidates = glob.glob(os.path.join(package_folder, "lib", "python*", "site-packages"))
        candidates += glob.glob(os.path.join(package_folder, "lib", "python", "site-packages"))
        for path in candidates:
            if os.path.isdir(path):
                return path
        raise RuntimeError(f"{dep_name} site-packages directory was not found")

    def _verify_ohos_stage_artifacts(self, stage):
        self.output.warning(
            "OHOS HNP Python can reject dlopen from Conan/HMDFS user paths; "
            "verifying signed Python extension artifacts instead of importing from stage."
        )
        self._verify_ohos_cli_script(stage)
        self._verify_ohos_extension_artifacts(stage)

    def _verify_ohos_cli_script(self, root):
        script = os.path.join(root, "bin", "rdiff-backup")
        if not os.path.isfile(script):
            raise RuntimeError("rdiff-backup console script was not installed")
        with open(script, "rb") as handle:
            content = handle.read()
        if b"console_scripts" not in content or b"rdiff-backup" not in content:
            raise RuntimeError("rdiff-backup console script does not reference the console entry point")

        site_packages = self._package_site_packages(root)
        entry_points = glob.glob(os.path.join(site_packages, "rdiff_backup*.egg-info", "entry_points.txt"))
        entry_points += glob.glob(os.path.join(site_packages, "rdiff_backup*.dist-info", "entry_points.txt"))
        if len(entry_points) != 1:
            raise RuntimeError(f"expected one rdiff-backup entry_points.txt, found {len(entry_points)}")
        with open(entry_points[0], "rb") as handle:
            entry_data = handle.read()
        if b"rdiff-backup = rdiffbackup.run:main" not in entry_data:
            raise RuntimeError("rdiff-backup entry_points.txt does not map to rdiffbackup.run:main")

    def _verify_ohos_extension_artifacts(self, root):
        site_packages = self._package_site_packages(root)
        expected = {
            "C": b"PyInit_C",
            "_librsync": b"PyInit__librsync",
        }
        for module, symbol in expected.items():
            matches = glob.glob(
                os.path.join(
                    site_packages,
                    "rdiff_backup",
                    f"{module}.cpython-*-aarch64-linux-ohos.so",
                )
            )
            if len(matches) != 1:
                raise RuntimeError(f"expected one rdiff_backup.{module} extension, found {len(matches)}")
            path = matches[0]
            with open(path, "rb") as handle:
                data = handle.read()
            if not data.startswith(b"\x7fELF"):
                raise RuntimeError(f"extension is not ELF: {path}")
            if b".codesign" not in data:
                raise RuntimeError(f"extension is missing OHOS .codesign section: {path}")
            if symbol not in data:
                raise RuntimeError(f"extension is missing expected init symbol {symbol!r}: {path}")
        self.output.info("OHOS signed Python extension artifact checks passed")

    def _compiler_c(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return compilers.get("c") or os.environ.get("CC") or "cc"

    def _profile_list(self, name):
        return self.conf.get(name, default=[], check_type=list) or []

    def _python_link_flags(self):
        libdir = self._python_library_dir()
        ldlibrary = sysconfig.get_config_var("LDLIBRARY") or ""
        libname = os.path.basename(ldlibrary)
        flags = []
        libpath = os.path.join(libdir, libname) if libdir and libname else ""
        if libdir and os.path.isfile(libpath) and libname.startswith("lib") and ".so" in libname:
            flags.append(f"-L{libdir}")
            flags.append("-l" + libname[3:].split(".so", 1)[0])
        return flags

    def _python_library_dir(self):
        return sysconfig.get_config_var("LIBDIR") or os.path.join(sys.prefix, "lib")

    def _sign_python_extensions(self, root):
        if str(self.settings.os) != "OHOS":
            return
        for path in self._python_extension_files(root):
            self._sign_elf(path)

    def _python_extension_files(self, root):
        pattern = os.path.join(root, "lib", "python*", "site-packages", "**", "*.so")
        return [
            path
            for path in glob.glob(pattern, recursive=True)
            if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path)
        ]

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf(self, path):
        objcopies = self._tool_candidates("llvm-objcopy")
        signers = self._tool_candidates("binary-sign-tool")
        if not objcopies or not signers:
            missing = []
            if not objcopies:
                missing.append("llvm-objcopy")
            if not signers:
                missing.append("binary-sign-tool")
            raise RuntimeError("OHOS ELF signing tools not found: {}".format(", ".join(missing)))

        os.chmod(path, 0o755)
        original = path + ".unsigned.orig"
        unsigned = path + ".unsigned.tmp"
        signed = path + ".signed.tmp"
        self._remove_if_exists(original)
        shutil.copy2(path, original)
        errors = []
        try:
            for signer in signers:
                objcopy = objcopies[0]
                paired_objcopy = os.path.join(os.path.dirname(signer), "llvm-objcopy")
                if os.path.isfile(paired_objcopy):
                    objcopy = paired_objcopy
                for label, command in self._sign_command_variants(signer, unsigned, signed):
                    self._remove_if_exists(unsigned)
                    self._remove_if_exists(signed)
                    shutil.copy2(original, unsigned)
                    try:
                        subprocess.run(
                            [objcopy, "--remove-section", ".codesign", unsigned],
                            capture_output=True,
                            text=True,
                            timeout=30,
                            check=False,
                        )
                        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        errors.append(f"{signer} ({label}): {exc}")
                        continue
                    finally:
                        self._remove_if_exists(unsigned)

                    if result.returncode != 0 or not os.path.exists(signed):
                        errors.append(f"{signer} ({label}): {(result.stderr or result.stdout).strip()}")
                        self._remove_if_exists(signed)
                        continue

                    os.replace(signed, path)
                    os.chmod(path, 0o755)
                    self._remove_if_exists(original)
                    self.output.info("Signed OHOS Python extension: {}".format(os.path.basename(path)))
                    return
        finally:
            self._remove_if_exists(unsigned)
            self._remove_if_exists(signed)

        if os.path.exists(original):
            os.replace(original, path)
            os.chmod(path, 0o755)
        raise RuntimeError("OHOS ELF signing failed for {}: {}".format(path, " | ".join(errors)))

    def _sign_command_variants(self, signer, infile, outfile):
        base = [signer, "sign", "-inFile", infile, "-outFile", outfile, "-selfSign", "1"]
        return [
            ("selfSign SHA256withECDSA", base + ["-signAlg", "SHA256withECDSA"]),
            ("selfSign default", base),
        ]

    def _remove_if_exists(self, path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def _tool_candidates(self, name):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, "usr", "local", "bin", name),
            os.path.join(os.path.dirname(cc), name) if os.path.dirname(cc) else "",
            shutil.which(name) or "",
            os.path.join("/storage/Users/currentUser/usr/local/bin", name),
            os.path.join("/data/service/hnp/bin", name),
        ]
        found = []
        seen = set()
        for candidate in candidates:
            if candidate and candidate not in seen and os.path.isfile(candidate):
                found.append(candidate)
                seen.add(candidate)
        return found
