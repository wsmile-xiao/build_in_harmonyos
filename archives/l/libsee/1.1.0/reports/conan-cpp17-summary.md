# libsee 1.1.0 — exact OHOS Conan evidence

Command completed with exit 0 on 2026-09-04:

```sh
conan create archives/l/libsee/1.1.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build='libsee/*' \
  -s:h=compiler.cppstd=17 -s:b=compiler.cppstd=17 \
  -s:h=compiler.libcxx=libc++ -s:b=compiler.libcxx=libc++ \
  -s:h=os.version=6.0 -s:b=os.version=6.0 \
  -c tools.build:jobs=1
```

Input host/build settings printed by Conan were `os=OHOS`, `os.version=6.0`, `arch=armv8`, `compiler=clang`, `compiler.version=15`, `compiler.cppstd=17`, `compiler.libcxx=libc++`, `build_type=Release`. The package was forced from source; recipe/package identity was `libsee/1.1.0#64c9f79726dab69089aaf98568fe9fb1:01d92cf349a0dd98ff915f4bd99a04430171517f#a560b789e77385e524d5707702efc49b`. The OHOS portability patch applied. CMake built `libsee.so`, and the Conan consumer compiled/ran and reported `libsee_print_size -> 1,234,567`. The final test_package result was exit 0; its five dlopen/dlsym/length/exact-output/preload assertions passed. The preload assertion used the package's own patched `libsee.so` with `/data/service/hnp/bin/bash -c true` and exit 0.
