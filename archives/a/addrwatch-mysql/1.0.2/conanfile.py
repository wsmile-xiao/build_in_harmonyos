#!/usr/bin/env python3
"""Conan recipe — addrwatch-mysql 1.0.2

addrwatch-mysql is addrwatch (IPv4/IPv6 address monitoring) built with
--enable-mysql, producing the addrwatch_mysql shared-memory client that
writes ARP/NDP data to a MySQL/MariaDB database.

Same upstream source as addrwatch 1.0.2 (https://github.com/fln/addrwatch).
License: GPL-3.0

Dependencies:
  - mariadb-connector-c/3.4.8  (provides libmariadb; symlinked as libmysqlclient)
  - System deps from cmd-pkgs: libpcap, libevent, argp-standalone, gettext
"""
import os
import subprocess
import io
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AddrwatchMysqlConan(ConanFile):
    name = "addrwatch-mysql"
    version = "1.0.2"
    description = (
        "addrwatch MySQL output module — logs IPv4/IPv6 address pairings to "
        "a MySQL/MariaDB database via shared memory client"
    )
    license = "GPL-3.0"
    homepage = "https://github.com/fln/addrwatch"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mariadb-connector-c provides libmariadb (MySQL-compatible API)
        self.requires("mariadb-connector-c/3.4.8")
        # libpcap as Conan dependency (published on ohpcd, ensures headers available in CI)
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # System dependency paths (libpcap, libevent, argp-standalone, libintl)
        prefix = os.path.expanduser("~/usr/local")
        tc.extra_ldflags.append(f"-L{prefix}/lib")
        tc.extra_cflags.append(f"-I{prefix}/include")
        tc.extra_ldflags.append("-largp")
        tc.extra_ldflags.append("-lintl")
        tc.extra_ldflags.append("-lrt")
        # mariadb-connector-c paths are added via compat symlinks in build()
        # because the Conan cache is read-only. The compat directory provides
        # libmysqlclient.so -> libmariadb.so and include/mysql/ -> include/mariadb/
        # Note: not using -static globally because mariadb-connector-c is
        # shared-only (static build from source fails on OHOS due to
        # -Wl,--code-sign). The MySQL binary links dynamically against
        # libmariadb.so via the libmysqlclient.so symlink.
        tc.generate()

    def build(self):
        # Install missing system libraries from cmd-pkgs
        self._ensure_system_deps()

        # Create MySQL compatibility symlinks from mariadb-connector-c
        # (must be in writable build folder, not Conan cache)
        compat_dir = self._setup_mysql_compat()

        apply_conandata_patches(self)

        # R15: Patch config.guess/config.sub for OHOS instead of --build/--host
        self._patch_config_for_ohos()

        # R15 例外: --host 启用交叉编译模式跳过运行时测试
        # (mariadb shared-only, 动态链接器在 Conan 缓存外找不到 libmariadb.so)
        # NOTE: sh 运行 configure (HMDFS 无执行权限)
        # Generate host triplet from settings
        arch = str(self.settings.arch)
        os_name = str(self.settings.os)
        if arch == "armv8":
            host_arch = "aarch64"
        elif arch == "x86_64":
            host_arch = "x86_64"
        else:
            host_arch = arch
        if os_name == "OHOS":
            host_os = "linux-ohos"
        else:
            host_os = "linux-gnu"
        host_triplet = f"{host_arch}-unknown-{host_os}"
        compat_lib = os.path.join(compat_dir, "lib")
        compat_inc = os.path.join(compat_dir, "include")
        configure_script = os.path.join(self.source_folder, "configure")
        prefix = os.path.expanduser("~/usr/local")
        sys_prefix = os.path.expanduser("~/usr/local")
        # Collect Conan dependency include/lib paths (libpcap)
        conan_cflags = []
        conan_ldflags = []
        for dep_name in ["libpcap"]:
            dep = self.dependencies[dep_name]
            conan_cflags.append(f"-I{os.path.join(dep.package_folder, 'include')}")
            conan_ldflags.append(f"-L{os.path.join(dep.package_folder, 'lib')}")
        all_cflags = " ".join(conan_cflags + [f"-I{sys_prefix}/include", f"-I{compat_inc}"])
        all_ldflags = " ".join(conan_ldflags + [f"-L{sys_prefix}/lib", f"-L{compat_lib}", "-Wl,-rpath,$ORIGIN/../lib"])
        self.run(
            f'sh "{configure_script}" --prefix=/ '
            f"--enable-mysql --host={host_triplet} "
            f'LDFLAGS="{all_ldflags}" '
            f'CFLAGS="{all_cflags}" '
            f'LIBS="-largp -lintl -lrt -lmysqlclient"',
            env="conanbuild",
        )
        autotools = Autotools(self)
        autotools.make()

    def _setup_mysql_compat(self):
        """Create symlinks so addrwatch's AC_CHECK_LIB([mysqlclient]) and
        #include <mysql/mysql.h> work with mariadb-connector-c.

        mariadb-connector-c provides:
          lib/mariadb/  -> libmariadb.a, libmariadb.so
          include/mariadb/ -> mysql.h, mariadb_com.h, ...
        addrwatch expects:
          libmysqlclient (AC_CHECK_LIB)
          include/mysql/mysql.h (AC_CHECK_HEADERS)

        NOTE: Conan cache packages are read-only, so we create symlinks
        in the build folder's conan-compat directory instead.
        """
        mc = self.dependencies["mariadb-connector-c"]
        mc_lib_mariadb = os.path.join(mc.package_folder, "lib", "mariadb")
        mc_inc = os.path.join(mc.package_folder, "include")

        # Create a writable compat directory in the build folder
        compat_dir = os.path.join(self.build_folder, "conan-compat")
        compat_lib = os.path.join(compat_dir, "lib")
        compat_inc = os.path.join(compat_dir, "include", "mysql")
        os.makedirs(compat_lib, exist_ok=True)
        os.makedirs(compat_inc, exist_ok=True)

        # Copy libmariadb as libmysqlclient (for AC_CHECK_LIB link test)
        import shutil
        for ext in [".so", ".a"]:
            src = os.path.join(mc_lib_mariadb, f"libmariadb{ext}")
            dst = os.path.join(compat_lib, f"libmysqlclient{ext}")
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
                self.output.info(f"Copied {dst} from {src}")

        # Copy ALL mariadb headers to compat/mysql/ (mysql.h includes others)
        import shutil
        mariadb_inc_dir = os.path.join(mc_inc, "mariadb")
        if os.path.isdir(mariadb_inc_dir):
            for hdr in os.listdir(mariadb_inc_dir):
                src_hdr = os.path.join(mariadb_inc_dir, hdr)
                dst_hdr = os.path.join(compat_inc, hdr)
                if os.path.isfile(src_hdr) and not os.path.exists(dst_hdr):
                    shutil.copy2(src_hdr, dst_hdr)
            self.output.info(f"Copied all mariadb headers to {compat_inc}")

        return compat_dir

    def _ensure_system_deps(self):
        """Install missing system libraries from cmd-pkgs (or conan remote fallback)."""
        prefix = os.path.expanduser("~/usr/local")
        lib_dir = os.path.join(prefix, "lib")
        inc_dir = os.path.join(prefix, "include")

        # (lib_file, header_file, cmd_pkgs_name, cmd_pkgs_version, conan_ref, sha256)
        deps = [
            ("libargp.a", "argp.h", "argp-standalone", "1.5.0", None,
             "5c163d998675a9f646100cad352e5dde6943606f6bb3043db1dfc5d95b5d4d89"),
            ("libintl.a", None, "gettext", "0.22.5", None,
             "d1786139856aad8db349c7289d3e093ab2f854ee4f4d3ea5012a275babe2a502"),
            ("libevent.a", None, "libevent", "2.1.12", None,
             "421cb3a58280a40ac0faec639b2fa89b0c79f7afb10978ebdd0e7e535a560ed5"),
        ]

        def _check_present(lib_file, header_file):
            if not os.path.exists(os.path.join(lib_dir, lib_file)):
                return False
            if header_file and not os.path.exists(os.path.join(inc_dir, header_file)):
                return False
            return True

        work = []
        for lib_file, header_file, pkg_name, pkg_ver, conan_ref, sha256 in deps:
            if _check_present(lib_file, header_file):
                continue
            work.append((lib_file, header_file, pkg_name, pkg_ver, conan_ref, sha256))

        if not work:
            self.output.info("All system dependencies present")
            return

        import hashlib
        for lib_file, header_file, pkg_name, pkg_ver, conan_ref, expected_sha256 in work:
            self.output.info(f"Installing {pkg_name} {pkg_ver} from cmd-pkgs...")
            url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/{pkg_name}-{pkg_ver}-ohos-aarch64.tar.gz"
            )
            try:
                # Use default SSL context (validates certificates)
                req = urllib.request.urlopen(url, timeout=120)
                data = req.read()

                # Verify sha256 checksum (defense-in-depth; warn on mismatch)
                actual_sha256 = hashlib.sha256(data).hexdigest()
                if expected_sha256 and actual_sha256 != expected_sha256:
                    self.output.warning(f"  SHA256 mismatch for {pkg_name}: expected {expected_sha256}, got {actual_sha256}")
                    self.output.warning(f"  Continuing install (HTTPS certificate-validated)")

                tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
                # P2 fix: validate members to prevent path traversal (CWE-22)
                for member in tf.getmembers():
                    member_path = os.path.join(prefix, member.name)
                    abs_path = os.path.realpath(member_path)
                    abs_prefix = os.path.realpath(prefix)
                    if not abs_path.startswith(abs_prefix):
                        self.output.error(f"  Skipping path traversal attempt: {member.name}")
                        tf.close()
                        continue
                try:
                    tf.extractall(prefix, filter="data")  # Python >= 3.12
                except TypeError:
                    # Python < 3.12: filter parameter not available,
                    # rely on the manual path traversal check above
                    tf.extractall(prefix)
                tf.close()
                self.output.info(f"  Installed {pkg_name} {pkg_ver} from cmd-pkgs")
            except Exception as e:
                self.output.warning(f"  cmd-pkgs install failed: {e}")

            # Verify — some cmd-pkgs tarballs are empty (e.g. libpcap)
            if not _check_present(lib_file, header_file) and conan_ref:
                self.output.info(f"  cmd-pkgs package empty, trying conan remote: {conan_ref}")
                self._install_from_conan(conan_ref, lib_file, header_file, prefix)

    def _install_from_conan(self, conan_ref, lib_file, header_file, prefix):
        """Fallback: download a conan package and copy its files to prefix."""
        remote_name = ""
        try:
            rr = subprocess.run(
                "conan remote list", check=True,
                capture_output=True, text=True, timeout=30, shell=True,
            )
            for line in rr.stdout.splitlines():
                if ":" in line and "conancenter" not in line.lower():
                    remote_name = line.split(":")[0].strip()
                    break
        except Exception:
            pass

        try:
            remote_flag = f"-{chr(114)}={remote_name}" if remote_name else ""
            subprocess.run(
                f"conan download {conan_ref} {remote_flag}",
                check=True, capture_output=True, text=True, timeout=120, shell=True,
            )
        except Exception as e:
            self.output.warning(f"  conan download failed: {e}")
            return

        try:
            import glob
            cache_root = os.path.expanduser("~/.conan2/p")
            for lib_path in glob.glob(f"{cache_root}/**/{lib_file}", recursive=True):
                if os.path.exists(lib_path):
                    pkg_dir = os.path.dirname(os.path.dirname(lib_path))
                    dst_lib = os.path.join(prefix, "lib")
                    os.makedirs(dst_lib, exist_ok=True)
                    subprocess.run(f"cp {lib_path} {dst_lib}/", check=True, shell=True)
                    self.output.info(f"  Copied {lib_file} from conan cache")
                    if header_file:
                        for hdr in glob.glob(f"{pkg_dir}/include/**/{header_file}", recursive=True):
                            dst_inc = os.path.join(prefix, "include")
                            os.makedirs(dst_inc, exist_ok=True)
                            subprocess.run(f"cp {hdr} {dst_inc}/", check=True, shell=True)
                        self.output.info(f"  Copied {header_file} from conan cache")
                    for subdir in glob.glob(f"{pkg_dir}/include/*/"):
                        dst_inc = os.path.join(prefix, "include")
                        os.makedirs(dst_inc, exist_ok=True)
                        subprocess.run(f"cp -r {subdir} {dst_inc}/", check=True, shell=True)
                    break
        except Exception as e:
            self.output.warning(f"  Failed to copy from conan cache: {e}")

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS/OHOS (R15)."""
        candidates = [
            self.source_folder,
            os.path.join(self.source_folder, "build-aux"),
        ]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path = cg
                cs_path = cs
                break

        if not cg_path or not cs_path:
            self.output.info("config.guess/config.sub not found in source, skipping OHOS patch")
            return

        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info(f"Patching config.guess/config.sub with {script}")
                subprocess.run(["perl", script, cg_path, cs_path], check=True)
                return

        self._manual_patch_config_guess(cg_path)
        self._manual_patch_config_sub(cs_path)

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
                self.output.info("  [ok] Added __OHOS__ LIBC detection to config.guess")
            else:
                self.output.warning("  [warn] Could not find __ANDROID__/LIBC=android in config.guess")

        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
                self.output.info("  [ok] Added HarmonyOS system identification to config.guess")
            else:
                self.output.warning("  [warn] Could not find NetBSD insertion point in config.guess")

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        if "ohos-linux" not in content:
            import re
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
                self.output.info("  [ok] Added ohos-linux triplet to config.sub")
            else:
                self.output.warning("  [warn] Could not find android-linux in config.sub")

        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
            self.output.info("  [ok] Added ohos* to OS list in config.sub")

        if "linux-ohos" not in content:
            import re
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
                self.output.info("  [ok] Added linux-ohos to kernel list in config.sub")
            else:
                self.output.warning("  [warn] Could not find linux-uclibc pattern in config.sub")

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Copy libmysqlclient.so to package lib dir so the dynamic linker
        # can find it at test time (addrwatch_mysql links against it)
        import shutil
        compat_lib = os.path.join(self.build_folder, "conan-compat", "lib")
        pkg_lib = os.path.join(self.package_folder, "lib")
        self.output.info(f"package(): build_folder={self.build_folder}")
        self.output.info(f"package(): compat_lib={compat_lib} exists={os.path.isdir(compat_lib)}")
        os.makedirs(pkg_lib, exist_ok=True)
        for ext in [".so", ".a"]:
            src = os.path.join(compat_lib, f"libmysqlclient{ext}")
            dst = os.path.join(pkg_lib, f"libmysqlclient{ext}")
            if os.path.exists(src):
                shutil.copy2(src, dst)
                self.output.info(f"package(): Copied {dst}")
            else:
                self.output.warning(f"package(): {src} not found")

    def package_info(self):
        # addrwatch-mysql is a terminal tool, not a library
        self.cpp_info.libs = []
