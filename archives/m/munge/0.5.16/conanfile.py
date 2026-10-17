from conan import ConanFile
from conan.tools.files import get, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class MungeConan(ConanFile):
    name = "munge"
    version = "0.5.16"
    description = "MUNGE (MUNGE Uid 'N Gid Emporium) - authentication service for creating and validating credentials"
    license = "GPL-3.0-or-later", "LGPL-3.0-or-later"
    homepage = "https://github.com/dun/munge"
    topics = ("authentication", "credentials", "security", "HPC")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/3.0.16")
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        tc.configure_args.append("--disable-suid")
        tc.configure_args.append("--with-crypto-lib=openssl")

        # munge's configure uses custom checks that need explicit paths
        for dep_name in ["openssl", "bzip2", "zlib"]:
            dep = self.dependencies[dep_name]
            pkg_folder = dep.package_folder
            inc_dir = os.path.join(pkg_folder, "include")
            lib_dir = os.path.join(pkg_folder, "lib")
            if os.path.exists(inc_dir):
                tc.extra_cflags.append(f"-I{inc_dir}")
            if os.path.exists(lib_dir):
                tc.extra_ldflags.append(f"-L{lib_dir}")

        # munge's configure checks for OpenSSL installation via --with-openssl-prefix
        openssl_folder = self.dependencies["openssl"].package_folder
        tc.configure_args.append(f"--with-openssl-prefix={openssl_folder}")

        # OHOS does not implement pthread_cancel etc. - allow undefined symbols
        # so remunge binary can link (library itself doesn't use these)
        tc.extra_ldflags.append("-Wl,--unresolved-symbols=ignore-in-object-files")

        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        self._fix_ohos_platform()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _fix_ohos_platform(self):
        """Fix HarmonyOS platform detection in autotools scripts."""
        src = self.source_folder

        # 1. Fix umask 077 -> 022 in configure and config.guess (HMDFS permission issue)
        for script_rel in ["configure", "build-aux/config.guess", "build-aux/config.sub"]:
            script_path = os.path.join(src, script_rel)
            if os.path.exists(script_path):
                with open(script_path, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(script_path, "w") as f:
                    f.write(content)
                os.chmod(script_path, 0o755)

        # 2. Add HarmonyOS detection to config.guess
        cg_path = os.path.join(src, "build-aux", "config.guess")
        if os.path.exists(cg_path):
            with open(cg_path, "r") as f:
                content = f.read()

            # Add __OHOS__ to LIBC detection in dummy.c
            if "__OHOS__" not in content:
                content = content.replace(
                    '#if defined(__ANDROID__)\n\tLIBC=android',
                    '#if defined(__ANDROID__)\n\tLIBC=android\n#elif defined(__OHOS__)\n\tLIBC=ohos'
                )

            # Add HarmonyOS case to the main case statement
            if "*:HarmonyOS:*:*" not in content:
                harmonyos_case = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    i?86)         MACHINE=i686 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                    '\t;;\n'
                    '\n'
                )
                # Insert before the *:NetBSD:*:* case
                content = content.replace(
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n    *:NetBSD:*:*)',
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n' + harmonyos_case + '    *:NetBSD:*:*)'
                )

            with open(cg_path, "w") as f:
                f.write(content)
            os.chmod(cg_path, 0o755)

        # 3. Add ohos-linux support to config.sub
        cs_path = os.path.join(src, "build-aux", "config.sub")
        if os.path.exists(cs_path):
            with open(cs_path, "r") as f:
                content = f.read()

            # Add ohos-linux case after android-linux
            if "ohos-linux" not in content:
                content = content.replace(
                    '\t\t\tandroid-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-android\n',
                    '\t\t\tandroid-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;\n\t\t\tohos-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-ohos\n'
                )

                # Add ohos* to basic OS types
                content = content.replace(
                    'gnu* | android* | bsd*',
                    'gnu* | android* | ohos* | bsd*'
                )

                # Add linux-ohos* to kernel-OS validation
                content = content.replace(
                    '| linux-musl* | linux-relibc*',
                    '| linux-musl* | linux-ohos* | linux-relibc*'
                )

            with open(cs_path, "w") as f:
                f.write(content)
            os.chmod(cs_path, 0o755)

        # 4. OHOS does not implement pthread_cancel, pthread_testcancel,
        #    pthread_setcancelstate - used only by remunge binary (not the library)
        #    Add stub implementations so the build can complete
        stub_path = os.path.join(src, "src", "munge", "pthread_compat.c")
        stub_code = (
            '/* Stubs for unimplemented pthread functions on OHOS */\n'
            '#include <pthread.h>\n'
            'int pthread_cancel(pthread_t t) { (void)t; return 0; }\n'
            'int pthread_testcancel(void) { return 0; }\n'
            'int pthread_setcancelstate(int state, int *oldstate) {\n'
            '    if (oldstate) *oldstate = state;\n'
            '    return 0;\n'
            '}\n'
        )
        with open(stub_path, "w") as f:
            f.write(stub_code)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la"):
                    os.unlink(os.path.join(root, f))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["munge"]
        self.cpp_info.requires = ["openssl::openssl", "bzip2::bzip2", "zlib::zlib"]
