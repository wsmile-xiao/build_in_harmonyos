#!/usr/bin/env python3
"""Conan recipe — cryptokit 1.21.1 (OCaml crypto library, C stubs layer)"""

import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import VirtualBuildEnv

class CryptokitConan(ConanFile):
    name = "cryptokit"
    version = "1.21.1"
    license = "LGPL-2.0-or-later WITH OCaml-LGPL-linking-exception"
    url = "https://github.com/xavierleroy/cryptokit"
    description = "A library of cryptographic primitives including AES, ChaCha20, SHA-256, SHA-3, Blake2, Blake3, RSA, ECDSA for OCaml with C stubs"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    package_type = "library"

    def validate(self):
        if self.options.shared and not self.options.fPIC:
            raise ConanException("shared=True requires fPIC=True (arm64 link failure otherwise)")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib/1.3.1 是 cryptokit OCaml 完整构建的依赖（conf-zlib）
        # C stubs 层不需要 zlib，留注释供后续 OCaml 构建参考
        pass
        # OCaml runtime (zarith, ocaml) not available as conan packages for OHOS
        # Full OCaml compilation requires: ocaml >= 4.13.0, dune >= 2.5, zarith >= 1.13
        # Here we compile only the C stubs layer for OHOS

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R33: Use Conan build env, not shell env vars
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)

        src_dir = os.path.join(self.source_folder, "src")
        build_dir = os.path.join(self.build_folder, "build_cstubs")
        self.run(f"mkdir -p {build_dir}")

        # Create OCaml header stubs for C stubs that include <caml/ headers
        caml_dir = os.path.join(src_dir, "caml")
        self.run(f"mkdir -p {caml_dir}")
        self.run(f"cat > {caml_dir}/config.h << 'HEADER_EOF'\n"
                 "#ifndef CAML_CONFIG_H\n#define CAML_CONFIG_H\n"
                 "#define ARCH_ALIGN_INT64 1\n#define SIZEOF_LONG 8\n#endif\n"
                 "HEADER_EOF")
        self.run(f"cat > {caml_dir}/mlvalues.h << 'HEADER_EOF'\n"
                 "#ifndef CAML_MLVALUES_H\n#define CAML_MLVALUES_H\n"
                 "typedef long value;\ntypedef unsigned char tag_t;\n#define Val_long(x) ((value)(x))\n"
                 "#define Long_val(x) ((long)(x))\n#define Val_int(x) ((value)(((x)<<1)+1))\n"
                 "#define Int_val(x) (((int)(x))>>1)\n#define Is_block(x) (((value)(x)&1)==0)\n"
                 "#define Field(x,n) (((value*)(x))[n])\n#endif\n"
                 "HEADER_EOF")
        self.run(f"cat > {caml_dir}/alloc.h << 'HEADER_EOF'\n"
                 "#ifndef CAML_ALLOC_H\n#define CAML_ALLOC_H\n"
                 "#include \"mlvalues.h\"\nvalue caml_alloc(tag_t,int);\n"
                 "value caml_copy_string(const char*);\n#endif\n"
                 "HEADER_EOF")
        self.run(f"cat > {caml_dir}/memory.h << 'HEADER_EOF'\n"
                 "#ifndef CAML_MEMORY_H\n#define CAML_MEMORY_H\n"
                 "#include \"alloc.h\"\n#define CAMLparam1(x)\n#define CAMLreturn(x) return(x)\n"
                 "#define CAMLlocal1(x)\n#endif\n"
                 "HEADER_EOF")
        self.run(f"cat > {caml_dir}/fail.h << 'HEADER_EOF'\n"
                 "#ifndef CAML_FAIL_H\n#define CAML_FAIL_H\n"
                 "#define caml_failwith(s)\n#define caml_invalid_argument(s)\n#endif\n"
                 "HEADER_EOF")
        self.run(f"cat > {caml_dir}/callback.h << 'HEADER_EOF'\n"
                 "#ifndef CAML_CALLBACK_H\n#define CAML_CALLBACK_H\n"
                 "#define caml_callback(r,v) (0)\n#endif\n"
                 "HEADER_EOF")

        # R33: Get compiler from Conan conf (not hardcoded)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "")
        if not cc:
            # Fallback: try OHOS SDK clang, then bare clang
            candidates = ["/data/service/hnp/bin/clang", "clang"]
            for c in candidates:
                if os.path.exists(c) or "/" not in c:
                    cc = c
                    break
        if not cc:
            raise ConanException("C compiler not found: set tools.build:compiler_executables in profile")

        c_sources = [
            "arcfour.c", "aesni.c", "blake2.c", "blake3.c",
            "blake3_dispatch.c", "blake3_portable.c", "blowfish.c",
            "chacha20.c", "d3des.c", "ghash.c", "keccak.c",
            "pclmul.c", "poly1305-donna.c", "rijndael-alg-fst.c",
            "ripemd160.c", "sha1.c", "sha256.c", "sha512.c", "siphash.c",
        ]
        cflags = "-DEXPORT= -DCAML_NAME_SPACE -DBLAKE3_NO_SSE2 " \
                 "-DBLAKE3_NO_SSE41 -DBLAKE3_NO_AVX2 -DBLAKE3_NO_AVX512 -DBLAKE3_USE_NEON=1"
        # Respect fPIC option (P2: fPIC=True must add -fPIC flag)
        if self.options.fPIC:
            cflags += " -fPIC"
        # Respect build_type setting (P2: Release/Debug optimization flags)
        if self.settings.build_type == "Release":
            cflags += " -O2 -DNDEBUG"
        elif self.settings.build_type == "Debug":
            cflags += " -O0 -g"
        elif self.settings.build_type == "RelWithDebInfo":
            cflags += " -O2 -g"
        elif self.settings.build_type == "MinSizeRel":
            cflags += " -Os -DNDEBUG"
        else:
            cflags += " -O2"

        for src in c_sources:
            obj = src.replace(".c", ".o")
            # R33: Pass compiler explicitly from Conan toolchain
            self.run(f"{cc} -c {cflags} -I{src_dir} -o {build_dir}/{obj} {src_dir}/{src}",
                     env="conanbuild")

        # Create library archive based on shared option
        obj_files = [os.path.join(build_dir, s.replace(".c", ".o")) for s in c_sources]
        objs_str = " ".join(obj_files)
        if self.options.shared:
            # Create shared library (.so)
            self.run(f"{cc} -shared -o {build_dir}/libcryptokit.so {objs_str}",
                     env="conanbuild")
        else:
            # Create static library (.a) — get ar from same dict as cc
            ar = compilers.get("ar")
            if not ar and cc:
                # Derive llvm-ar from cc's directory (OHOS CI only gives c/cpp)
                ar = os.path.join(os.path.dirname(cc), "llvm-ar")
            if not ar:
                # OHOS CI profile only provides c/cpp, no ar
                ar = "llvm-ar"
            self.run(f"{ar} rcs {build_dir}/libcryptokit.a {objs_str}",
                     env="conanbuild")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        build_dir = os.path.join(self.build_folder, "build_cstubs")
        # Package library archive
        if self.options.shared:
            copy(self, "*.so", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "*.a", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        # Package algorithm header files (only src/*.h, exclude caml/ stubs)
        import glob as _glob
        for h_file in _glob.glob(os.path.join(src_dir, "*.h")):
            if os.path.isfile(h_file):
                copy(self, os.path.basename(h_file), src=src_dir,
                     dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["cryptokit"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "cryptokit")
