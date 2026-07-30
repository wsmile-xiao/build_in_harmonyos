#!/usr/bin/env python3
"""Conan recipe for bpytop 1.0.68 (Python CLI application)."""
import glob
import os
import shutil
import stat
import subprocess
import sys
import sysconfig
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class BpytopConan(ConanFile):
    name = "bpytop"
    version = "1.0.68"
    description = "Python terminal resource monitor"
    license = "Apache-2.0"
    homepage = "https://github.com/aristocratos/bpytop"
    url = "https://github.com/aristocratos/bpytop"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        psutil = self.conan_data["resources"]["psutil"]
        download(
            self,
            url=psutil["url"],
            filename="psutil-5.9.8.tar.gz",
            sha256=psutil["sha256"],
        )

    def build(self):
        apply_conandata_patches(self)
        psutil_archive = os.path.join(self.source_folder, "psutil-5.9.8.tar.gz")
        psutil_src = os.path.join(self.build_folder, "psutil-5.9.8")
        stage_dir = os.path.join(self.build_folder, "psutil-stage")
        shutil.rmtree(psutil_src, ignore_errors=True)
        shutil.rmtree(stage_dir, ignore_errors=True)

        with tarfile.open(psutil_archive, "r:gz") as archive:
            self._safe_extract(archive, self.build_folder)

        self._patch_psutil(psutil_src)
        staged_package = os.path.join(stage_dir, "psutil")
        os.makedirs(staged_package, exist_ok=True)
        for source in glob.glob(os.path.join(psutil_src, "psutil", "*.py")):
            shutil.copy2(source, staged_package)

        common_sources = [
            "psutil/_psutil_common.c",
            "psutil/_psutil_posix.c",
        ]
        linux_sources = common_sources + [
            "psutil/_psutil_linux.c",
            "psutil/arch/linux/disk.c",
            "psutil/arch/linux/mem.c",
            "psutil/arch/linux/net.c",
            "psutil/arch/linux/proc.c",
            "psutil/arch/linux/users.c",
        ]
        self._compile_extension(
            psutil_src,
            "_psutil_linux.so",
            linux_sources,
            staged_package,
        )
        self._compile_extension(
            psutil_src,
            "_psutil_posix.so",
            common_sources,
            staged_package,
        )

    def _safe_extract(self, archive, destination):
        destination = os.path.abspath(destination)
        for member in archive.getmembers():
            target = os.path.abspath(os.path.join(destination, member.name))
            if target != destination and not target.startswith(destination + os.sep):
                raise RuntimeError(f"Refusing to extract unsafe path: {member.name}")
            if member.islnk() or member.issym():
                link_target = os.path.abspath(os.path.join(os.path.dirname(target), member.linkname))
                if not link_target.startswith(destination + os.sep):
                    raise RuntimeError(f"Refusing to extract unsafe link: {member.name}")
        archive.extractall(destination)

    def _patch_psutil(self, psutil_src):
        common_py = os.path.join(psutil_src, "psutil", "_common.py")
        with open(common_py, "r", encoding="utf-8") as handle:
            content = handle.read()
        linux_marker = 'LINUX = sys.platform.startswith("linux")'
        if linux_marker not in content:
            raise RuntimeError("Unable to patch psutil platform detection for OHOS")
        content = content.replace(
            linux_marker,
            'LINUX = sys.platform.startswith(("linux", "ohos"))',
        )
        with open(common_py, "w", encoding="utf-8") as handle:
            handle.write(content)

        net_c = os.path.join(psutil_src, "psutil", "arch", "linux", "net.c")
        with open(net_c, "r", encoding="utf-8") as handle:
            content = handle.read()
        linux_header = "#include <linux/if.h>"
        if linux_header not in content:
            raise RuntimeError("Unable to patch psutil network headers for OHOS")
        with open(net_c, "w", encoding="utf-8") as handle:
            handle.write(content.replace(linux_header, "#include <net/if.h>"))

    def _compile_extension(self, psutil_src, output_name, sources, stage_dir):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        default_cc = "gcc" if str(self.settings.compiler) == "gcc" else "clang"
        cc = compilers.get("c", default_cc)
        python_include = sysconfig.get_paths()["include"]
        build_type_flags = {
            "Debug": ["-O0", "-g"],
            "Release": ["-O3", "-DNDEBUG"],
            "RelWithDebInfo": ["-O2", "-g", "-DNDEBUG"],
            "MinSizeRel": ["-Os", "-DNDEBUG"],
        }
        cflags = list(
            self.conf.get("tools.build:cflags", default=[], check_type=list) or []
        )
        cflags.extend(build_type_flags.get(str(self.settings.build_type), []))
        macros = [
            "-DPSUTIL_POSIX=1",
            "-DPSUTIL_LINUX=1",
            "-DPSUTIL_SIZEOF_PID_T=4",
            "-DPSUTIL_VERSION=598",
        ]
        object_dir = os.path.join(
            self.build_folder,
            "objects",
            output_name.replace(".", "_"),
        )
        os.makedirs(object_dir, exist_ok=True)
        objects = []

        for index, source in enumerate(sources):
            source_path = os.path.join(psutil_src, source)
            object_path = os.path.join(
                object_dir,
                f"{index}-{os.path.basename(source)}.o",
            )
            command = [
                cc,
                "-fPIC",
                *cflags,
                *macros,
                f"-I{python_include}",
                f"-I{os.path.join(psutil_src, 'psutil')}",
                "-c",
                source_path,
                "-o",
                object_path,
            ]
            self.output.info("Compiling " + source)
            subprocess.run(command, check=True)
            objects.append(object_path)

        output_path = os.path.join(stage_dir, output_name)
        link_flags = list(
            self.conf.get(
                "tools.build:sharedlinkflags", default=[], check_type=list
            ) or []
        )
        self.output.info("Linking " + output_name)
        subprocess.run(
            [cc, "-shared", *objects, *link_flags, "-o", output_path],
            check=True,
        )
        os.chmod(output_path, 0o755)

    def package(self):
        libexec_dir = os.path.join(self.package_folder, "libexec", "bpytop")
        bin_dir = os.path.join(self.package_folder, "bin")
        themes_dir = os.path.join(self.package_folder, "share", "bpytop", "themes")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(libexec_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        copy(self, "bpytop.py", src=self.source_folder, dst=libexec_dir)
        copy(self, "*", src=os.path.join(self.source_folder, "themes"), dst=themes_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        shutil.copy2(
            os.path.join(self.build_folder, "psutil-5.9.8", "LICENSE"),
            os.path.join(self.package_folder, "licenses", "psutil-LICENSE"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "psutil-stage"),
            dst=site_packages,
        )
        self._prepare_psutil_extensions(site_packages)

        wrapper = """#!/usr/bin/env sh
set -e
script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix=$(CDPATH= cd "$script_dir/.." && pwd)
python_bin=${BPYTOP_PYTHON:-python3}
pyver=$("$python_bin" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)
site="$prefix/lib/python$pyver/site-packages"
if [ -d "$site" ]; then
    if [ -d "$site/psutil" ]; then
        runtime_parent=${BPYTOP_RUNTIME_DIR:-}
    fi
    if [ -n "${runtime_parent:-}" ]; then
        runtime_site="$runtime_parent/bpytop-python$pyver"
        if mkdir -p "$runtime_site" 2>/dev/null; then
            rm -rf "$runtime_site/psutil"
            if cp -R "$site/psutil" "$runtime_site/psutil" 2>/dev/null; then
                chmod -R u+rwX,go+rX "$runtime_site/psutil" 2>/dev/null || true
                site="$runtime_site"
            fi
        fi
    fi
    if [ -n "${PYTHONPATH:-}" ]; then
        export PYTHONPATH="$site:$PYTHONPATH"
    else
        export PYTHONPATH="$site"
    fi
fi
exec "$python_bin" "$prefix/libexec/bpytop/bpytop.py" "$@"
"""
        wrapper_path = os.path.join(bin_dir, "bpytop")
        save(self, wrapper_path, wrapper)
        os.chmod(
            wrapper_path,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
            stat.S_IRGRP | stat.S_IXGRP |
            stat.S_IROTH | stat.S_IXOTH,
        )

    def _prepare_psutil_extensions(self, site_packages):
        extensions = sorted(
            glob.glob(os.path.join(site_packages, "psutil", "*.so"))
        )
        if not extensions:
            raise RuntimeError("Packaged psutil native extensions are missing")

        for extension in extensions:
            os.chmod(extension, 0o755)

        if str(self.settings.os) != "OHOS":
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        objdump = "/data/service/hnp/bin/llvm-objdump"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for extension in extensions:
            sections = subprocess.run(
                [objdump, "-h", extension],
                capture_output=True,
                timeout=15,
            )
            if sections.returncode != 0:
                detail = (sections.stdout + sections.stderr).decode(
                    errors="replace"
                )
                raise RuntimeError(
                    f"Unable to inspect {os.path.basename(extension)} "
                    f"before signing: {detail[-1000:]}"
                )

            if b".codesign" in sections.stdout:
                stripped = subprocess.run(
                    [objcopy, "--remove-section", ".codesign", extension],
                    capture_output=True,
                    timeout=15,
                )
                if stripped.returncode != 0:
                    detail = (stripped.stdout + stripped.stderr).decode(
                        errors="replace"
                    )
                    raise RuntimeError(
                        f"Unable to prepare {os.path.basename(extension)} "
                        f"for signing: {detail[-1000:]}"
                    )

            signed = extension + ".signed"
            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    extension,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0 or not os.path.isfile(signed):
                detail = (result.stdout + result.stderr).decode(
                    errors="replace"
                )
                raise RuntimeError(
                    f"Unable to sign {os.path.basename(extension)}: "
                    f"{detail[-1000:]}"
                )
            os.replace(signed, extension)
            os.chmod(extension, 0o755)

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libs = []

        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, site_packages))
