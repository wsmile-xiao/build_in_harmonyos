#!/usr/bin/env python3
"""Conan recipe for acme-client 0.1.15-portable."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class AcmeClientConan(ConanFile):
    name = "acme-client"
    version = "0.1.15-portable"
    description = "Portable ACME client for certificate management"
    license = "ISC"
    homepage = "https://github.com/kristapsdz/acme-client-portable"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("libressl/3.9.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self._patch_sources()
        compat_dir = os.path.join(self.build_folder, "compat")
        os.makedirs(compat_dir, exist_ok=True)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = (
            compilers.get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )
        prefix = os.environ.get("DEFAULT_PREFIX", os.path.join(os.path.expanduser("~"), "usr", "local"))
        libressl_pkg = self.dependencies["libressl"].package_folder
        libressl_include = os.path.join(libressl_pkg, "include")
        libressl_lib = os.path.join(libressl_pkg, "lib")
        include_flags = [
            f"-I{compat_dir}",
            f"-I{libressl_include}",
            f"-I{os.path.join(prefix, 'include')}",
        ]
        lib_flags = f"-L{libressl_lib} -L{os.path.join(prefix, 'lib')}"
        cflags = " ".join(["-fPIC", "-O2", "-DHAVE_CONFIG_H", "-DMUSL_LIBC"] + include_flags)
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{lib_flags}" '
            'LIBADD="-ltls -lssl -lcrypto -ldl -lpthread" -j1',
            cwd=self.source_folder,
        )

    def _patch_sources(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "GNUmakefile"),
            "$(CC) -o $@ $(OBJS) $(LDFLAGS) -ltls -lssl -lcrypto $(LIBADD)",
            "$(CC) -o $@ $(OBJS) $(LDFLAGS) $(LIBADD)",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "GNUmakefile"),
            "# If you need to change anything below here, it's a bug.",
            """# Add portable privilege and null-sandbox objects when the host uname
# does not match any upstream platform branch, as happens in OHOS CI.
ifeq ($(filter util-portable.o util-pledge.o,$(OBJS)),)
OBJS	+= util-portable.o
endif
ifeq ($(filter sandbox-null.o sandbox-darwin.o sandbox-pledge.o sandbox-capsicum.o sandbox-seccomp.o,$(OBJS)),)
OBJS	+= sandbox-null.o
endif

# If you need to change anything below here, it's a bug.""",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.h"),
            "#  define getprogname() (program_invocation_short_name)",
            "static inline const char *getprogname(void) { return \"acme-client\"; }",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "extern.h"),
            "int\t\t verbose;",
            "extern int\t verbose;",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "extern.h"),
            "enum comp\t proccomp;",
            "extern enum comp\t proccomp;",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "main.c"),
            "static\tconst char *const subps[COMP__MAX] = {",
            "int\t\t verbose;\nenum comp\t proccomp;\n\nstatic\tconst char *const subps[COMP__MAX] = {",
            strict=False,
        )
        for rel in ("acctproc.c", "keyproc.c", "rsa.c"):
            replace_in_file(
                self,
                os.path.join(self.source_folder, rel),
                "EVP_PKEY_type(pkey->type)",
                "EVP_PKEY_type(EVP_PKEY_id(pkey))",
                strict=False,
            )
        for rel in ("acctproc.c",):
            path = os.path.join(self.source_folder, rel)
            replace_in_file(self, path, "EVP_MD_CTX_create()", "EVP_MD_CTX_new()", strict=False)
            replace_in_file(self, path, "EVP_MD_CTX_destroy(ctx)", "EVP_MD_CTX_free(ctx)", strict=False)
            replace_in_file(self, path, "ERR_load_crypto_strings()", "ERR_load_CRYPTO_strings()", strict=False)
            replace_in_file(self, path, "ERR_free_strings()", "(void)0", strict=False)
            replace_in_file(self, path, "RSA\t*r;", "RSA\t*r;\n\tconst BIGNUM *n = NULL, *e = NULL;", strict=False)
            replace_in_file(
                self,
                path,
                "if (NULL == (r = EVP_PKEY_get1_RSA(pkey)))\n\t\twarnx(\"EVP_PKEY_get1_RSA\");",
                "if (NULL == (r = EVP_PKEY_get1_RSA(pkey)))\n\t\twarnx(\"EVP_PKEY_get1_RSA\");",
                strict=False,
            )
            replace_in_file(
                self,
                path,
                "if (NULL == (r = EVP_PKEY_get1_RSA(pkey)))\n\t\twarnx(\"EVP_PKEY_get1_RSA\");\n\telse if (NULL == (mod = bn2string(r->n)))\n\t\twarnx(\"bn2string\");\n\telse if (NULL == (exp = bn2string(r->e)))\n\t\twarnx(\"bn2string\");\n\telse if (NULL == (json = json_fmt_thumb_rsa(exp, mod)))\n\t\twarnx(\"json_fmt_thumb_rsa\");",
                "if (NULL == (r = EVP_PKEY_get1_RSA(pkey)))\n\t\twarnx(\"EVP_PKEY_get1_RSA\");\n\telse {\n\t\tRSA_get0_key(r, &n, &e, NULL);\n\t\tif (NULL == (mod = bn2string(n)))\n\t\t\twarnx(\"bn2string\");\n\t\telse if (NULL == (exp = bn2string(e)))\n\t\t\twarnx(\"bn2string\");\n\t\telse if (NULL == (json = json_fmt_thumb_rsa(exp, mod)))\n\t\t\twarnx(\"json_fmt_thumb_rsa\");\n\t}",
                strict=False,
            )
            replace_in_file(
                self,
                path,
                "if (NULL == (r = EVP_PKEY_get1_RSA(pkey)))\n\t\twarnx(\"EVP_PKEY_get1_RSA\");\n\telse if (NULL == (mod = bn2string(r->n)))\n\t\twarnx(\"bn2string\");\n\telse if (NULL == (exp = bn2string(r->e)))\n\t\twarnx(\"bn2string\");\n\telse if (NULL == (*head = json_fmt_header_rsa(exp, mod)))\n\t\twarnx(\"json_fmt_header_rsa\");\n\telse if (NULL == (*prot = json_fmt_protected_rsa(exp, mod, nonce)))\n\t\twarnx(\"json_fmt_protected_rsa\");\n\telse\n\t\trc = 1;",
                "if (NULL == (r = EVP_PKEY_get1_RSA(pkey)))\n\t\twarnx(\"EVP_PKEY_get1_RSA\");\n\telse {\n\t\tRSA_get0_key(r, &n, &e, NULL);\n\t\tif (NULL == (mod = bn2string(n)))\n\t\t\twarnx(\"bn2string\");\n\t\telse if (NULL == (exp = bn2string(e)))\n\t\t\twarnx(\"bn2string\");\n\t\telse if (NULL == (*head = json_fmt_header_rsa(exp, mod)))\n\t\t\twarnx(\"json_fmt_header_rsa\");\n\t\telse if (NULL == (*prot = json_fmt_protected_rsa(exp, mod, nonce)))\n\t\t\twarnx(\"json_fmt_protected_rsa\");\n\t\telse\n\t\t\trc = 1;\n\t}",
                strict=False,
            )
        for rel in ("certproc.c", "keyproc.c", "revokeproc.c"):
            path = os.path.join(self.source_folder, rel)
            replace_in_file(self, path, "ERR_load_crypto_strings()", "ERR_load_CRYPTO_strings()", strict=False)
            replace_in_file(self, path, "ERR_free_strings()", "(void)0", strict=False)
            replace_in_file(self, path, "bio->num_write", "BIO_number_written(bio)", strict=False)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "keyproc.c"),
            "OBJ_cleanup();",
            "(void)0;",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "revokeproc.c"),
            "x->cert_info->extensions",
            "X509_get0_extensions(x)",
            strict=False,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "acme-client", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "acme-client.1", src=self.source_folder, dst=mandir, keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bin_path = os.path.join(bindir, "acme-client")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
        if os.path.exists(bin_path) and str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true")
            self.run(
                f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1",
                quiet=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
