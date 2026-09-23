# afmize 2.0.2 — native build/test evidence

- Date: 2026-09-04
- Verification source commit: `5b07352db33d2b037efb97e73752ad04bfeb989e`
- Functional input files were unchanged by the subsequent evidence-only edits; the binding check is:
  `git diff --quiet 5b07352db33d2b037efb97e73752ad04bfeb989e HEAD -- archives/a/afmize/2.0.2/conanfile.py archives/a/afmize/2.0.2/conandata.yml archives/a/afmize/2.0.2/patches archives/a/afmize/2.0.2/test_package`
- Final Conan package folder observed and independently verified in the local cache: `/storage/Users/currentUser/.conan2/p/b/afmiz77034af3633bd/p`
- Conan package identity: `afmize/2.0.2#6a8a63c6403dea1b46e9518ecb03a5bb:2c35088b11588a6c5653e994e5a51d7e9ca78475#fd7455e9f30d05cde7ed80ef42ecc904`
- Compiler: `/data/service/hnp/bin/clang++` (clang 15.0.4), libc++
- CMake mode: `CMAKE_SYSTEM_NAME=Linux`, `CMAKE_SYSTEM_PROCESSOR=aarch64`, Release
- Exact functional input SHA-256: `conanfile.py=83682cc44b847e41f4aad275574960a7a8080f3df6ea01d8b178b4237c150913`, `conandata.yml=e0bee0732da5f81cbf0c909fc6aa659d404d7e3c38eba8ba91938f63cb2636d4`, `patch=9a4c66eeeb07403a9bf3ff275b92cfe3872b4a3c03e08c1dc22835e8b3408ead`, `test_package/conanfile.py=a5dce35d4194796c95d284fd81822093583049dc7228fe60e76a511e85e12017`, `test_package/test.sh=c9ccfa239a9140b195bbf0eeace9c682f5b0df9e81e6a22c31ba9d037c31c6a4`.

The device command that produced this evidence was:

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

The recipe applied the portability patch, configured CMake with the OHOS-compatible Linux/aarch64 variables, built with `--parallel 1 -- -j1 -j1`, and ran the upstream CTest target with the same serial flags. CTest discovered three tests and all passed: `TOTAL=3 PASS=3 FAIL=0 SKIP=0 NOT_RUN=0` (`test_collision`, `test_read_as_angstrom`, `test_aabb`). The Conan `test_package` separately executed `afmize config.toml` through the OHOS bash and checked three non-empty generated output files; the command exited 0.
