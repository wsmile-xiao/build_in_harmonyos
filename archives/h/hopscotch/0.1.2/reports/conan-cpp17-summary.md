# hopscotch 0.1.2 — exact OHOS Conan evidence

Command completed with exit 0 on 2026-09-04 against implementation commit `ba8c707601e8871127c6c52a3c9c32100e8257bf` (later evidence-only commits do not change recipe or test code):

```sh
conan create archives/h/hopscotch/0.1.2 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build='hopscotch/*' \
  -s:h=compiler.cppstd=17 -s:b=compiler.cppstd=17 \
  -s:h=compiler.libcxx=libc++ -s:b=compiler.libcxx=libc++ \
  -s:h=os.version=6.0 -s:b=os.version=6.0 \
  -c tools.build:jobs=1
```

Input host/build settings printed by Conan were `os=OHOS`, `os.version=6.0`, `arch=armv8`, `compiler=clang`, `compiler.version=15`, `compiler.cppstd=17`, `compiler.libcxx=libc++`, `build_type=Release`. The package was forced from source; `apply_conandata_patches()` reported no patches. Recipe/package identity was `hopscotch/0.1.2#024373a3acad4717e9d05c3a8481b938:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#abd606aa97e22d2389d79768d7efb73a`. Raw Makefile build used `make -j1`. The static library, header and CLI were packaged. The test package compiled the consumer and explicitly executed it through `self.run` on the native OHOS host; all five API calls passed and exited 0: `TOTAL=1 PASS=1 FAIL=0 SKIP=0 NOT_RUN=0`.
