# oystr 0.2.0 — exact OHOS Conan evidence

Command completed with exit 0 on 2026-09-04:

```sh
conan create archives/o/oystr/0.2.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build='oystr/*' \
  -s:h=compiler.cppstd=17 -s:b=compiler.cppstd=17 \
  -s:h=compiler.libcxx=libc++ -s:b=compiler.libcxx=libc++ \
  -s:h=os.version=6.0 -s:b=os.version=6.0 \
  -c tools.build:jobs=1
```

Input host/build settings printed by Conan were `os=OHOS`, `os.version=6.0`, `arch=armv8`, `compiler=clang`, `compiler.version=15`, `compiler.cppstd=17`, `compiler.libcxx=libc++`, `build_type=Release`. The package was forced from source; recipe/package identity was `oystr/0.2.0#d583ebcee2fe67894601e253d7a61554:fe3ea609c6e189df769b5dd0a2ac118e48e41c37#305b8c25071b070a0404d32a3f8601f5`. All four portability patches applied. The build enabled upstream developer mode/CTest and passed `oystr_test`; `test_package` then passed both PTY file-search and stdin-search assertions. Exit code was 0.
