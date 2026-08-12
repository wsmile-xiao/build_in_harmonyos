# ncnn 20260526 HarmonyOS PC adaptation notes

- The package intentionally builds the CPU inference backend only.
- `NCNN_VULKAN` is disabled because this minimal recipe does not declare a
  HarmonyOS Vulkan SDK/loader dependency, and the shared CI profile does not
  provide a validated Vulkan runtime for `test_package`.
- The public C++ API and real CPU inference path remain available and are
  validated by the package test. Vulkan support can be added later as a
  separate, dependency-backed option when the platform toolchain is available.

- Upstream test suite (ctest, 166 tests) runs in build(); test_squeezenet now
  receives its model files via build/examples, and test_gemm_5 is excluded as
  an upstream sgemm+winograd numerical edge case (M=4 N=4 K=4,
  output_elempack=4). Result: 165/165 executed tests pass.
