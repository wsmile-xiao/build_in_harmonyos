#!/usr/bin/env python3
"""Conan recipe for the spidev 3.8 CPython extension."""
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


class SpidevConan(ConanFile):
    name = "spidev"
    version = "3.8"
    description = "Python bindings for Linux SPI access through the spidev kernel driver"
    license = "MIT"
    homepage = "https://github.com/doceme/py-spidev"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "spidev requires Linux/OHOS spidev headers and SPI_IOC ioctl support"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        cc = self._compiler_c()
        cflags = self._profile_list("tools.build:cflags")
        shared_flags = self._profile_list("tools.build:sharedlinkflags")

        env = Environment()
        env.define("CC", cc)
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        if cflags:
            env.define("CFLAGS", " ".join(cflags))
        python_link_flags = []
        if str(self.settings.os) != "OHOS":
            python_link_flags = self._python_link_flags()
        env.define(
            "LDSHARED",
            " ".join([cc, "-shared"] + cflags + shared_flags + python_link_flags),
        )
        env.vars(self).save_script("spidev_profile")

    def build(self):
        apply_conandata_patches(self)
        stage = self._stage_folder()
        os.makedirs(stage, exist_ok=True)
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--break-system-packages",
            "--no-deps",
            f"--prefix={stage}",
            self.source_folder,
        ]
        self.run(
            " ".join(shlex.quote(str(part)) for part in cmd),
            env=["conanbuild", "spidev_profile"],
        )

    def package(self):
        copy(self, "*", src=self._stage_folder(), dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self._sign_python_extensions()

    def package_info(self):
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", pyver, "site-packages")
        pythonpath = os.path.join(self.package_folder, site_packages)

        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.buildenv_info.append_path("PYTHONPATH", pythonpath)
        self.runenv_info.append_path("PYTHONPATH", pythonpath)

    def _stage_folder(self):
        return os.path.join(self.build_folder, "stage")

    def _compiler_c(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return compilers.get("c") or os.environ.get("CC") or "cc"

    def _profile_list(self, name):
        return self.conf.get(name, default=[], check_type=list) or []

    def _python_link_flags(self):
        active_libpython = self._active_libpython()
        if active_libpython:
            return [active_libpython]

        for libdir in self._python_library_dirs():
            for name in self._python_library_names():
                path = os.path.join(libdir, name)
                if os.path.isfile(path):
                    return [path]
        return []

    def _active_libpython(self):
        maps = "/proc/self/maps"
        if not os.path.isfile(maps):
            return ""

        try:
            with open(maps, encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    fields = line.split()
                    if not fields:
                        continue
                    path = fields[-1]
                    if "libpython" in os.path.basename(path) and os.path.isfile(path):
                        return path
        except OSError:
            return ""
        return ""

    def _python_library_dirs(self):
        dirs = [
            sysconfig.get_config_var("LIBDIR"),
            sysconfig.get_config_var("LIBPL"),
        ]
        includepy = sysconfig.get_config_var("INCLUDEPY")
        if includepy:
            dirs.append(os.path.join(os.path.dirname(os.path.dirname(includepy)), "lib"))
        return list(dict.fromkeys(path for path in dirs if path))

    def _python_library_names(self):
        names = []
        for key in ("LDLIBRARY", "INSTSONAME"):
            value = sysconfig.get_config_var(key)
            if (
                value
                and value.startswith("libpython")
                and (".so" in value or value.endswith(".dylib"))
            ):
                names.append(value)

        stem = self._python_library_stem(sysconfig.get_config_var("LDLIBRARY") or "")
        if stem:
            names.extend([f"lib{stem}.so", f"lib{stem}.dylib"])
        return list(dict.fromkeys(names))

    def _python_library_stem(self, library):
        if not library.startswith("lib"):
            return ""
        name = library[3:]
        for marker in (".so", ".dylib", ".a"):
            index = name.find(marker)
            if index != -1:
                return name[:index]
        return name

    def _sign_python_extensions(self):
        if str(self.settings.os) != "OHOS":
            return

        for path in self._python_extension_files():
            self._sign_elf(path)

    def _python_extension_files(self):
        pattern = os.path.join(self.package_folder, "lib", "python*", "site-packages", "**", "*.so")
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
            raise RuntimeError(
                "OHOS ELF signing tools not found: {}; cannot sign Python extension".format(
                    ", ".join(missing)
                )
            )

        os.chmod(path, 0o755)
        errors = []
        original = path + ".unsigned.orig"
        unsigned = path + ".unsigned.tmp"
        signed = path + ".signed.tmp"
        self._remove_if_exists(original)
        shutil.copy2(path, original)
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
                except subprocess.TimeoutExpired:
                    errors.append("{}: objcopy timed out after 30s".format(objcopy))
                    self._remove_if_exists(unsigned)
                    continue
                except OSError as exc:
                    errors.append("{}: objcopy failed: {}".format(objcopy, exc))
                    self._remove_if_exists(unsigned)
                    continue
                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired:
                    errors.append("{} ({}): signing timed out after 60s".format(signer, label))
                    continue
                except OSError as exc:
                    errors.append("{} ({}): signing failed to start: {}".format(signer, label, exc))
                    continue
                finally:
                    self._remove_if_exists(unsigned)

                if result.returncode != 0 or not os.path.exists(signed):
                    errors.append(
                        "{} ({}): {}".format(
                            signer, label, (result.stderr or result.stdout).strip()
                        )
                    )
                    self._remove_if_exists(signed)
                    continue

                os.replace(signed, path)
                os.chmod(path, 0o755)
                self._remove_if_exists(original)
                self.output.info(
                    "Signed OHOS Python extension with {} ({}): {}".format(
                        signer, label, os.path.relpath(path, self.package_folder)
                    )
                )
                return

        if os.path.exists(original):
            os.replace(original, path)
            os.chmod(path, 0o755)
        self._remove_if_exists(unsigned)
        self._remove_if_exists(signed)

        raise RuntimeError(
            "OHOS ELF signing failed for Python extension {}: {}".format(
                os.path.basename(path), " | ".join(errors)
            )
        )

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
        candidates = []
        home = os.path.expanduser("~")
        if home:
            candidates.append(os.path.join(home, "usr", "local", "bin", name))
        if os.path.dirname(cc):
            candidates.append(os.path.join(os.path.dirname(cc), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/storage/Users/currentUser/usr/local/bin", name))
        candidates.append(os.path.join("/data/service/hnp/bin", name))

        found_tools = []
        seen = set()
        for candidate in candidates:
            if candidate and candidate not in seen and os.path.isfile(candidate):
                found_tools.append(candidate)
                seen.add(candidate)
        return found_tools
