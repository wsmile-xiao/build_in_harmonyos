# afmize 2.0.2 — exact OHOS Conan evidence

Command completed with exit 0 on 2026-09-04:

```sh
conan create archives/a/afmize/2.0.2 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build='afmize/*' \
  -s:h=compiler.cppstd=17 -s:b=compiler.cppstd=17 \
  -s:h=compiler.libcxx=libc++ -s:b=compiler.libcxx=libc++ \
  -s:h=os.version=6.0 -s:b=os.version=6.0 \
  -c tools.build:jobs=1
```

Input host/build settings printed by Conan were `os=OHOS`, `os.version=6.0`, `arch=armv8`, `compiler=clang`, `compiler.version=15`, `compiler.cppstd=17`, `compiler.libcxx=libc++`, `build_type=Release`. The package was forced from source. Recipe revision/package identity was `afmize/2.0.2#6a8a63c6403dea1b46e9518ecb03a5bb:2c35088b11588a6c5653e994e5a51d7e9ca78475#fd7455e9f30d05cde7ed80ef42ecc904`. CMake built afmize and ran the three upstream CTest cases, all passing. The Conan test_package then executed `afmize config.toml` through the OHOS bash and verified non-empty PPM/TSV/JSON outputs; it exited 0.
