import io
import os
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, download, get, replace_in_file, save
from conan.tools.layout import basic_layout


class YkushControlConan(ConanFile):
    name = "ykush-control"
    version = "1.3.0"
    description = "Command-line controller for Yepkit YKUSH switchable USB hub boards"
    license = "Apache-2.0"
    homepage = "https://github.com/Yepkit/ykush"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    _ohos_libusb_cmd_pkgs = {
        "armv8": {
            "label": "aarch64",
            "filename": "libusb-1.0.27-ohos-aarch64.tar.gz",
            "url": (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                "download/pkgs/libusb-1.0.27-ohos-aarch64.tar.gz"
            ),
            "sha256": "52cc022e2a7e1be81f993689c8f326aaca8b97f51e232995d5cc366b860271a3",
        }
    }

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ykush-control is supported for Linux/OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _target(self):
        targets = {
            "armv8": "aarch64-linux-ohos",
            "x86_64": "x86_64-linux-ohos",
        }
        arch = str(self.settings.arch)
        if arch not in targets:
            raise ConanInvalidConfiguration(f"unsupported OHOS architecture: {arch}")
        return targets[arch]

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if compilers and compilers.get("cpp"):
            return compilers["cpp"]
        return os.environ.get("CXX") or "g++"

    def _sysroot_flag(self, compiler):
        native_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(compiler)))
        )
        sysroot = os.path.join(native_dir, "sysroot")
        return [f"--sysroot={sysroot}"] if os.path.isdir(sysroot) else []

    def _ensure_ohos_libusb(self):
        if str(self.settings.arch) == "x86_64":
            return self._build_ohos_x86_64_libusb()

        root = os.path.join(self.build_folder, "cmd-pkgs", "libusb-package")
        header = os.path.join(root, "include", "libusb-1.0", "libusb.h")
        library = os.path.join(root, "lib", "libusb-1.0.a")
        if os.path.isfile(header) and os.path.isfile(library):
            return root

        pkg = self._ohos_libusb_cmd_pkgs.get(str(self.settings.arch))
        if pkg is None:
            raise ConanInvalidConfiguration(
                f"OHOS {self.settings.arch} needs a matching libusb cmd-pkgs archive"
            )

        os.makedirs(os.path.dirname(root), exist_ok=True)
        self.output.info(f"Installing libusb 1.0.27 from cmd-pkgs for OHOS {pkg['label']}")
        archive_path = os.path.join(self.build_folder, pkg["filename"])
        download(
            self,
            pkg["url"],
            archive_path,
            retry=3,
            retry_wait=5,
            sha256=pkg["sha256"],
        )
        with open(archive_path, "rb") as archive_file:
            data = archive_file.read()

        prefix = os.path.dirname(root)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                target = os.path.abspath(os.path.join(prefix, member.name))
                if not target.startswith(os.path.abspath(prefix) + os.sep):
                    raise ConanInvalidConfiguration(
                        f"unsafe path in libusb cmd-pkgs archive: {member.name}"
                    )
                if member.isdir():
                    os.makedirs(target, exist_ok=True)
                elif member.isfile():
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    src = archive.extractfile(member)
                    if src is None:
                        continue
                    with src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        if not (os.path.isfile(header) and os.path.isfile(library)):
            raise ConanInvalidConfiguration(
                "libusb cmd-pkgs archive did not provide libusb.h and libusb-1.0.a"
            )
        return root

    def _build_ohos_x86_64_libusb(self):
        root = os.path.join(self.build_folder, "cmd-pkgs", "libusb-x86_64-built")
        header = os.path.join(root, "include", "libusb-1.0", "libusb.h")
        library = os.path.join(root, "lib", "libusb-1.0.a")
        if os.path.isfile(header) and os.path.isfile(library):
            return root

        source_dir = os.path.join(self.build_folder, "libusb-1.0.27-src")
        get(self, **self.conan_data["libusb_sources"], destination=source_dir, strip_root=True)

        config_dir = os.path.join(self.build_folder, "libusb-1.0.27-ohos-x86_64-config")
        save(
            self,
            os.path.join(config_dir, "config.h"),
            """#define DEFAULT_VISIBILITY __attribute__((visibility("default")))
#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#define ENABLE_LOGGING 1
#define HAVE_CLOCK_GETTIME 1
#define HAVE_DECL_EFD_CLOEXEC 1
#define HAVE_DECL_EFD_NONBLOCK 1
#define HAVE_DECL_TFD_CLOEXEC 1
#define HAVE_DECL_TFD_NONBLOCK 1
#define HAVE_EVENTFD 1
#define HAVE_GETTIMEOFDAY 1
#define HAVE_PIPE2 1
#define HAVE_POLL_H 1
#define HAVE_PTHREAD_CONDATTR_SETCLOCK 1
#define HAVE_PTHREAD_SETNAME_NP 1
#define HAVE_SIGNAL_H 1
#define HAVE_STRINGS_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_TIMERFD 1
#define HAVE_UNISTD_H 1
#define OS_LINUX 1
#define PACKAGE "libusb"
#define PACKAGE_BUGREPORT "libusb-devel@lists.sourceforge.net"
#define PACKAGE_NAME "libusb"
#define PACKAGE_STRING "libusb 1.0.27"
#define PACKAGE_TARNAME "libusb"
#define PACKAGE_URL "https://libusb.info"
#define PACKAGE_VERSION "1.0.27"
#define PLATFORM_POSIX 1
#define POLL_NFDS_TYPE nfds_t
#define PRINTF_FORMAT(a, b) __attribute__((format(printf, a, b)))
#define THREADS_POSIX 1
#define TIMESPEC_TO_TIMEVAL(tv, ts) do { (tv)->tv_sec = (ts)->tv_sec; (tv)->tv_usec = (ts)->tv_nsec / 1000; } while (0)
#define USBI_TIMERFD_AVAILABLE 1
#define VERSION "1.0.27"
""",
        )

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c") or os.environ.get("CC") or "cc"
        llvm_ar = os.path.join(os.path.dirname(compiler), "llvm-ar.exe")
        ar = llvm_ar if os.path.isfile(llvm_ar) else "ar"
        obj_dir = os.path.join(self.build_folder, "libusb-1.0.27-x86_64-obj")
        os.makedirs(obj_dir, exist_ok=True)

        flags = [
            "--target=x86_64-linux-ohos",
            *self._sysroot_flag(compiler),
            "-D__MUSL__",
            "-DHAVE_CONFIG_H",
            "-I" + config_dir,
            "-I" + os.path.join(source_dir, "libusb"),
            "-I" + os.path.join(source_dir, "libusb", "os"),
            "-O2",
            "-DNDEBUG",
            "-fPIC",
            "-pthread",
        ]
        sources = [
            "libusb/core.c",
            "libusb/descriptor.c",
            "libusb/hotplug.c",
            "libusb/io.c",
            "libusb/strerror.c",
            "libusb/sync.c",
            "libusb/os/events_posix.c",
            "libusb/os/threads_posix.c",
            "libusb/os/linux_usbfs.c",
            "libusb/os/linux_netlink.c",
        ]
        objects = []
        for source in sources:
            obj = os.path.join(obj_dir, source.replace("/", "_") + ".o")
            self._run([compiler, *flags, "-c", os.path.join(source_dir, source), "-o", obj])
            objects.append(obj)

        os.makedirs(os.path.dirname(library), exist_ok=True)
        self._run([ar, "rcs", library, *objects])
        os.makedirs(os.path.dirname(header), exist_ok=True)
        shutil.copyfile(os.path.join(source_dir, "libusb", "libusb.h"), header)
        return root

    def _libusb_flags(self):
        if str(self.settings.os) == "OHOS":
            root = self._ensure_ohos_libusb()
            return (
                ["-I" + os.path.join(root, "include", "libusb-1.0")],
                [os.path.join(root, "lib", "libusb-1.0.a")],
            )

        cflags = ["-I" + os.path.join(self.source_folder, "libusb")]
        libs = ["-lusb-1.0"]
        try:
            pc_cflags = subprocess.check_output(
                ["pkg-config", "--cflags", "libusb-1.0"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).split()
            pc_libs = subprocess.check_output(
                ["pkg-config", "--libs", "libusb-1.0"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).split()
            if pc_cflags:
                cflags = pc_cflags + cflags
            if pc_libs:
                libs = pc_libs
        except (OSError, subprocess.CalledProcessError):
            pass
        return cflags, libs

    def _common_flags(self):
        compiler = self._cxx()
        flags = ["-std=c++11", "-D_LINUX_", "-D_LIBUSB_"]
        if str(self.settings.os) == "OHOS":
            flags.extend([f"--target={self._target()}", "-D__MUSL__"])
            flags.extend(self._sysroot_flag(compiler))
        if str(self.settings.build_type) == "Debug":
            flags.extend(["-O0", "-g"])
        else:
            flags.extend(["-O2", "-DNDEBUG"])
        include_dirs = [
            "src",
            "src/ykushxs",
            "src/ykush",
            "src/ykush2",
            "src/ykush3",
            "src/help",
            "src/utils",
            "src/usbhid",
        ]
        flags.extend("-I" + os.path.join(self.source_folder, path) for path in include_dirs)
        libusb_cflags, _ = self._libusb_flags()
        flags.extend(libusb_cflags)
        return compiler, flags

    def _link_flags(self):
        compiler = self._cxx()
        flags = []
        if str(self.settings.os) == "OHOS":
            flags.extend([f"--target={self._target()}"])
            flags.extend(self._sysroot_flag(compiler))
        _, libusb_libs = self._libusb_flags()
        flags.extend(libusb_libs)
        return flags

    def _run(self, command):
        self.output.info(" ".join(command))
        subprocess.run(command, check=True)

    def _compile(self, sources, output):
        compiler, flags = self._common_flags()
        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []
        for source in sources:
            obj = os.path.join(obj_dir, source.replace("/", "_") + ".o")
            self._run(
                [
                    compiler,
                    *flags,
                    "-c",
                    os.path.join(self.source_folder, source),
                    "-o",
                    obj,
                ]
            )
            objects.append(obj)
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        self._run([compiler, *objects, *self._link_flags(), "-o", output])

    def build(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "help", "ykush_help.cpp"),
            "YKUSHCMD Version 1.2.5",
            f"YKUSHCMD Version {self.version}",
        )

        main_sources = [
            "src/yktrl.cpp",
            "src/commandParser.cpp",
            "src/ykushxs/ykushxs.cpp",
            "src/ykush/ykush.cpp",
            "src/ykush2/ykush2.cpp",
            "src/ykush3/ykush3.cpp",
            "src/yk_usb_device.cpp",
            "src/help/ykush_help.cpp",
            "src/utils/command_parser.cpp",
            "src/utils/string2val.cpp",
            "src/usbhid/usbhid.cpp",
        ]
        bin_dir = os.path.join(self.build_folder, "bin")
        self._compile(main_sources, os.path.join(bin_dir, "ykushcmd"))

        upstream_test_sources = [
            "src/tests/test_usbhid.cpp",
            "src/usbhid/usbhid.cpp",
        ]
        self._compile(upstream_test_sources, os.path.join(bin_dir, "test_usbhid"))
        if can_run(self):
            self.run(os.path.join(bin_dir, "test_usbhid"))
            self.output.info("Upstream usbhid test passed: 1/1")
        else:
            self.output.info("Upstream usbhid test built; execution skipped for cross build context")

    def package(self):
        copy(self, "ykushcmd*", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "doc", "ykush-control"))
        copy(self, "*.txt", os.path.join(self.source_folder, "doc"), os.path.join(self.package_folder, "share", "doc", "ykush-control"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["usb-1.0"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
