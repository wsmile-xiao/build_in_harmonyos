#!/usr/bin/env python3
"""Conan recipe — kore 4.2.3 (Makefile)"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KoreConan(ConanFile):
    name = "kore"
    version = "4.2.3"
    description = "Secure web application framework for writing web APIs in C (kore + kodev)"
    license = "ISC"
    homepage = "https://kore.io"
    url = "https://github.com/jorisvink/kore"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Default flavor links -lssl -lcrypto (TLS_BACKEND=openssl).
        self.requires("openssl/3.5.8.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        # The profile's compiler_executables point at the CI worker layout
        # (/data/service/hnp/bin); on runners where that path does not exist
        # fall back to resolving the compiler from PATH (the profile also
        # prepends the real toolchain bin/ to PATH). Keeps CI semantics when
        # the conf path exists.
        if not os.path.isfile(cc):
            cc = shutil.which("clang") or cc
        openssl = self.dependencies["openssl"].package_folder
        return cc, openssl

    def _sign_elf(self, path):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(sign_tool) and os.path.isfile(path):
            oc = objcopy if os.path.isfile(objcopy) else (shutil.which("llvm-objcopy") or "llvm-objcopy")
            self.run(f'{oc} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _downgrade_deprecated_werror(self):
        # kore 4.2.3 predates OpenSSL 3.x (openssl/3.5.8.1):
        #  (1) src/tls_openssl.c uses RSA_meth_*/EVP_PKEY_get1_RSA,
        #      deprecated in OpenSSL 3 -> -Wdeprecated-declarations.
        #  (2) src/keymgr_openssl.c assigns the OpenSSL 3 const-qualified
        #      getters to non-const locals:
        #        rsa = EVP_PKEY_get0_RSA(key->pkey);      (~line 695)
        #        ec  = EVP_PKEY_get0_EC_KEY(key->pkey);   (~line 719)
        #      OpenSSL 3 returns `const RSA *` / `const EC_KEY *`, so
        #      clang raises -Wincompatible-pointer-types-discards-qualifiers.
        # Upstream CFLAGS hard-codes -Werror, which promotes both to hard
        # errors. Previous cycle used a conandata patch file; the hunk
        # context proved fragile in preflight (patch failed to apply).
        # Different route: deterministic in-recipe Makefile edit — append
        # the downgrades AFTER the existing CFLAGS block so they take
        # precedence over the earlier -Werror (gcc/clang: later
        # -Wno-error=foo wins). Keeps -Werror for everything else.
        # The const-discard downgrade is runtime-safe: the underlying
        # EVP_PKEY object is mutable; OpenSSL 3 only changed the getter
        # contract to const. No source semantics are altered.
        mk = os.path.join(self.source_folder, "Makefile")
        with open(mk, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        flags = [
            "-Wno-error=deprecated-declarations",
            "-Wno-error=incompatible-pointer-types-discards-qualifiers",
        ]
        missing = [fl for fl in flags if fl not in content]
        if not missing:
            return
        extra = "\n".join("CFLAGS+=" + fl for fl in missing)
        anchor = "CFLAGS+=-DPREFIX="
        if anchor in content:
            # Insert after the -fstack-protector-all line which follows
            # the -DPREFIX line in kore 4.2.3's Makefile.
            needle = "CFLAGS+=-DPREFIX='\"$(PREFIX)\"' -fstack-protector-all"
            insertion = (
                needle + "\n"
                "# OHOS/OpenSSL>=3: kore 4.2.3 uses pre-3.0 RSA/EC APIs;\n"
                "# keep -Werror but do not fail on deprecated-declarations\n"
                "# (src/tls_openssl.c) or const-discard from\n"
                "# EVP_PKEY_get0_RSA/EC_KEY (src/keymgr_openssl.c).\n"
                + extra
            )
            if needle in content:
                content = content.replace(needle, insertion, 1)
            else:
                content += "\n" + extra + "\n"
        else:
            content += "\n" + extra + "\n"
        with open(mk, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def _fix_kodev_openssl_path(self):
        # kodev/Makefile (4.2.3) never references OPENSSL_PATH: it only
        # handles darwin via pkg-config and adds no -I/-L on linux, so the
        # kodev sub-make (make -C kodev, OPENSSL_PATH propagates as a
        # command-line make variable but is ignored) fails at
        # ../src/cli.c:26 openssl/err.h not found in the isolated Conan
        # layout where headers/libs live only under the openssl package
        # folder. Mirror the top-level Makefile idiom deterministically:
        # honor OPENSSL_PATH for both headers and the -lcrypto link.
        # kodev has its own CFLAGS with -Werror, and the top-level
        # -Wno-error=* lines do NOT propagate to this sub-make (they are
        # file-local, not command-line vars), so the OpenSSL 3
        # deprecated-API uses in src/cli.c (SHA256_Init/Update/Final,
        # RSA_new, RSA_generate_key_ex, EVP_PKEY_assign_RSA) need the same
        # targeted downgrade here. Keeps -Werror for everything else.
        mk = os.path.join(self.source_folder, "kodev", "Makefile")
        with open(mk, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        if "OPENSSL_PATH" in content and \
                "-Wno-error=deprecated-declarations" in content:
            return
        if "OPENSSL_PATH" not in content:
            needle = "LDFLAGS=-lcrypto"
            insertion = (
                needle + "\n"
                "# OHOS/Conan: honor OPENSSL_PATH like the top-level Makefile.\n"
                "# (command-line OPENSSL_PATH propagates to this sub-make.)\n"
                "ifneq (\"$(OPENSSL_PATH)\", \"\")\n"
                "CFLAGS+=-I$(OPENSSL_PATH)/include\n"
                "LDFLAGS+=-L$(OPENSSL_PATH)/lib\n"
                "endif"
            )
            if needle in content:
                content = content.replace(needle, insertion, 1)
            else:
                content += "\n" + insertion + "\n"
        if "-Wno-error=deprecated-declarations" not in content:
            content += (
                "\n"
                "# OHOS/OpenSSL>=3: kodev src/cli.c uses pre-3.0 SHA256_*/\n"
                "# RSA_* APIs; keep -Werror but do not fail on\n"
                "# deprecated-declarations (nor on const-discard, for\n"
                "# symmetry with the top-level Makefile).\n"
                "CFLAGS+=-Wno-error=deprecated-declarations\n"
                "CFLAGS+=-Wno-error=incompatible-pointer-types-discards-qualifiers\n"
            )
        with open(mk, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._downgrade_deprecated_werror()
        self._fix_kodev_openssl_path()
        cc, openssl = self._toolchain()
        # Ensure sibling toolchain tools resolve when conf path was replaced
        # by the PATH fallback above.
        toolchain_bin = os.path.dirname(cc)
        if toolchain_bin:
            os.environ["PATH"] = toolchain_bin + os.pathsep + os.environ.get("PATH", "")
        # R33: compiler and OpenSSL paths come from Conan conf/deps, never
        # from bare shell variables. Default flavor only (no PYTHON/LUA/CURL/
        # PGSQL/ACME/TASKS/JSONRPC) to keep the dependency closure at openssl.
        # PREFIX=/ keeps install paths package-relative under DESTDIR.
        # OHOS uname -s reports "HarmonyOS" (cf. librecast precedent), so the
        # upstream OSNAME probe (uname -s | sed | tr) yields "harmonyos" and
        # falls into the else/bsd.c branch without -D_GNU_SOURCE. OHOS is
        # Linux-like (HongMeng kernel + musl): force the linux branch so the
        # build uses src/linux.c+seccomp.c and gains -D_GNU_SOURCE=1, which
        # exposes the BSD u_int*_t aliases from <sys/types.h> (already
        # included by kore.h) even under -std=c99. Command-line OSNAME
        # overrides the Makefile assignment and propagates to kodev sub-make.
        self.run(
            f'make -j1 CC="{cc}" OPENSSL_PATH="{openssl}" PREFIX=/ OSNAME=linux',
            cwd=self.source_folder,
        )
        if self.settings.os == "OHOS":
            for name in ("kore", os.path.join("kodev", "kodev")):
                self._sign_elf(os.path.join(self.source_folder, name))

    def package(self):
        cc, openssl = self._toolchain()
        self.run(
            f'make install DESTDIR="{self.package_folder}" PREFIX=/ '
            f'CC="{cc}" OPENSSL_PATH="{openssl}" OSNAME=linux',
            cwd=self.source_folder,
        )
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            for name in ("kore", "kodev"):
                self._sign_elf(os.path.join(self.package_folder, "bin", name))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
