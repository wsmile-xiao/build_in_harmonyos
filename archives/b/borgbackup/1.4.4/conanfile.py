"""Conan recipe for borgbackup 1.4.4 - deduplicating backup with Cython C extensions."""
import os
import sys
import sysconfig
import tarfile
import hashlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save, mkdir
from conan.tools.layout import basic_layout


class BorgbackupConan(ConanFile):
    name = "borgbackup"
    version = "1.4.4"
    package_type = "application"
    description = "Deduplicating backup program with compression and authenticated encryption"
    license = "BSD-3-Clause"
    homepage = "https://github.com/borgbackup/borg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("backup", "encryption", "compression", "python", "cython")

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("zstd/1.5.6")
        self.requires("lz4/1.10.0")
        self.requires("xxhash/0.8.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"borgbackup is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"borgbackup/1.4.4 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        src_entries = self.conan_data["sources"][self.version]
        expected_sha256 = src_entries[0]["sha256"]
        # Collect all URLs from conandata entries for fallback
        urls = [entry["url"] for entry in src_entries if "url" in entry]

        # Check for a local cached copy (development convenience)
        local_tarball = os.path.join(os.path.expanduser("~"), "tmp",
                                    "borgbackup-src", "borgbackup-1.4.4.tar.gz")
        download_ok = False

        if os.path.exists(local_tarball):
            with open(local_tarball, "rb") as f:
                actual_sha256 = hashlib.sha256(f.read()).hexdigest()
            if actual_sha256 == expected_sha256:
                download_ok = True

        if download_ok:
            with tarfile.open(local_tarball, "r:gz") as tar:
                members = tar.getmembers()
                root_prefix = os.path.commonprefix([m.name for m in members])
                if "/" in root_prefix:
                    root_prefix = root_prefix.split("/")[0]
                for member in members:
                    member.name = member.name[len(root_prefix) + 1:]
                    if member.name:
                        tar.extract(member, self.source_folder)
            self.output.info(f"Extracted source from local cache: {local_tarball}")
        else:
            get(self, url=urls, sha256=expected_sha256, strip_root=True)

        # Apply patches from recipe folder
        recipe_dir = self.recipe_folder
        patches_dir = os.path.join(recipe_dir, "patches")
        if os.path.isdir(patches_dir):
            patch_files = sorted(os.listdir(patches_dir))
            for pf in patch_files:
                if pf.endswith(".patch"):
                    patch_path = os.path.join(patches_dir, pf)
                    self.run(f'cd "{self.source_folder}" && '
                             f'patch -p1 < "{patch_path}"')

    def build(self):
        src = self.source_folder
        cc = self._get_cc()
        # Fix for CI: lld (LLVM linker) requires libxml2.so.16
        # Add SDK lib directories to LD_LIBRARY_PATH so lld can find its dependencies
        import glob as _glob
        for _pattern in [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/lib",
            "/data/service/hnp/lib",
            "/storage/Users/currentUser/usr/local/lib",
        ]:
            for _path in _glob.glob(_pattern):
                _existing = os.environ.get("LD_LIBRARY_PATH", "")
                if _path not in _existing:
                    os.environ["LD_LIBRARY_PATH"] = f"{_path}:{_existing}" if _existing else _path
        py_inc = self._get_py_include()
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
        cflags = "-Wall -Wextra -Wpointer-arith -Wno-unreachable-code-fallthrough"

        # Create stub ACL headers (OpenHarmony has no libacl)
        stub_dir = os.path.join(src, "src", "borg", "stub_acl")
        mkdir(self, os.path.join(stub_dir, "sys"))
        mkdir(self, os.path.join(stub_dir, "acl"))
        save(self, os.path.join(stub_dir, "sys", "acl.h"),
             "#ifndef _SYS_ACL_H\n#define _SYS_ACL_H\n"
             "typedef void* acl_t;\ntypedef int acl_type_t;\n"
             "#define ACL_TYPE_ACCESS 0\n#define ACL_TYPE_DEFAULT 1\n"
             "#endif\n")
        save(self, os.path.join(stub_dir, "acl", "libacl.h"),
             "#ifndef _ACL_LIBACL_H\n#define _ACL_LIBACL_H\n"
             "#include <sys/acl.h>\n"
             "static inline int acl_free(void* obj) { (void)obj; return 0; }\n"
             "static inline acl_t acl_from_text(const char* s) { (void)s; return NULL; }\n"
             "static inline int acl_set_fd(int fd, acl_t acl) { (void)fd; (void)acl; return -1; }\n"
             "static inline int acl_set_file(const char* p, acl_type_t t, acl_t acl) { (void)p; (void)t; (void)acl; return -1; }\n"
             "static inline acl_t acl_get_fd(int fd) { (void)fd; return NULL; }\n"
             "static inline acl_t acl_get_file(const char* p, acl_type_t t) { (void)p; (void)t; return NULL; }\n"
             "static inline char* acl_to_text(acl_t acl, ssize_t* len) { (void)acl; (void)len; return NULL; }\n"
             "static inline int acl_extended_fd(int fd) { (void)fd; return 0; }\n"
             "static inline int acl_extended_file_nofollow(const char* p) { (void)p; return 0; }\n"
             "#endif\n")

        # Dependency paths
        dep_info = self._gather_dep_paths()
        stub_inc = f"-I{stub_dir}"

        # Extension definitions: (source, module_name, extra_inc, extra_lib, undef_ndebug)
        extensions = [
            ("src/borg/chunker.c", "borg.chunker", "", "", True),
            ("src/borg/hashindex.c", "borg.hashindex", "", "", True),
            ("src/borg/item.c", "borg.item", "", "", False),
            ("src/borg/crypto/low_level.c", "borg.crypto.low_level",
             dep_info["openssl_inc"], dep_info["openssl_link"], False),
            ("src/borg/compress.c", "borg.compress",
             dep_info["lz4_zstd_inc"], dep_info["lz4_zstd_link"], False),
            ("src/borg/algorithms/checksums.c", "borg.algorithms.checksums",
             dep_info["xxhash_inc"], dep_info["xxhash_link"], False),
            ("src/borg/platform/posix.c", "borg.platform.posix",
             stub_inc, "", False),
            ("src/borg/platform/linux.c", "borg.platform.linux",
             stub_inc, "", False),
            ("src/borg/platform/syncfilerange.c", "borg.platform.syncfilerange",
             "", "", False),
        ]

        build_dir = os.path.join(self.build_folder, "extensions")
        mkdir(self, build_dir)

        for src_file, mod_name, extra_inc, extra_link, undef_ndebug in extensions:
            src_path = os.path.join(src, src_file)
            mod_path = mod_name.replace(".", "/")
            out_dir = os.path.join(build_dir, os.path.dirname(mod_path))
            mkdir(self, out_dir)
            mod_basename = os.path.basename(mod_path)
            out_path = os.path.join(out_dir, mod_basename + ext_suffix)

            undef_flag = " -UNDEBUG" if undef_ndebug else ""
            acl_flag = " -DBORG_NO_ACL" if "linux" in mod_name or "posix" in mod_name else ""

            cmd = (
                f'"{cc}" -shared -fPIC -O2 {cflags}{undef_flag}{acl_flag} '
                f'-I"{py_inc}" {extra_inc} '
                f'-I"{src}/src/borg" '
                f'"{src_path}" '
                f'{extra_link} '
                f'-o "{out_path}"'
            )
            self.run(cmd)

    def package(self):
        # Copy compiled .so extensions
        ext_dir = os.path.join(self.build_folder, "extensions")
        copy(self, "*.so", ext_dir, os.path.join(self.package_folder, "lib", "site-packages"))

        # Copy Python source files
        src = self.source_folder
        borg_src = os.path.join(src, "src", "borg")
        copy(self, "*.py", borg_src, os.path.join(self.package_folder, "lib", "site-packages", "borg"))
        copy(self, "*.html", borg_src, os.path.join(self.package_folder, "lib", "site-packages", "borg"))

        # Copy subdirectories with Python files
        for subdir in ["algorithms", "crypto", "platform", "helpers", "cache_sync", "testsuite"]:
            subdir_path = os.path.join(borg_src, subdir)
            if os.path.isdir(subdir_path):
                copy(self, "*.py", subdir_path,
                     os.path.join(self.package_folder, "lib", "site-packages", "borg", subdir))

        # Create borg entry point script
        bin_dir = os.path.join(self.package_folder, "bin")
        mkdir(self, bin_dir)
        save(self, os.path.join(bin_dir, "borg"),
             "#!/usr/bin/env python3\n"
             "import sys\n"
             "from borg.archiver import main\n"
             "if __name__ == '__main__':\n"
             "    sys.exit(main())\n")
        os.chmod(os.path.join(bin_dir, "borg"), 0o755)

    def package_info(self):
        self.cpp_info.libdirs = ["lib/site-packages"]
        self.cpp_info.bindirs = ["bin"]

    def _get_cc(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compiler_executables.get("c") or "clang"

    def _get_py_include(self):
        return sysconfig.get_path("include")

    def _gather_dep_paths(self):
        result = {}
        deps = self.dependencies

        def extract(cpp_info):
            inc_dirs = [str(d) for d in cpp_info.includedirs] if cpp_info.includedirs else []
            lib_dirs = [str(d) for d in cpp_info.libdirs] if cpp_info.libdirs else []
            libs = list(cpp_info.libs) if cpp_info.libs else []
            return inc_dirs, lib_dirs, libs

        # OpenSSL
        oi, ol, olf = extract(deps["openssl"].cpp_info)
        result["openssl_inc"] = " ".join(f'-I"{d}"' for d in oi)
        result["openssl_link"] = " ".join(f'-L"{d}"' for d in ol) + " " + \
                                " ".join(f"-l{lib}" for lib in olf)

        # lz4 + zstd
        li, ll, llf = extract(deps["lz4"].cpp_info)
        zi, zl, zlf = extract(deps["zstd"].cpp_info)
        all_inc = li + zi
        all_lib_dirs = ll + zl
        all_libs = llf + zlf
        result["lz4_zstd_inc"] = " ".join(f'-I"{d}"' for d in all_inc)
        result["lz4_zstd_link"] = " ".join(f'-L"{d}"' for d in all_lib_dirs) + " " + \
                                   " ".join(f"-l{lib}" for lib in all_libs)

        # xxhash
        xi, xl, xlf = extract(deps["xxhash"].cpp_info)
        result["xxhash_inc"] = " ".join(f'-I"{d}"' for d in xi)
        result["xxhash_link"] = " ".join(f'-L"{d}"' for d in xl) + " " + \
                                " ".join(f"-l{lib}" for lib in xlf)

        return result
