# maxflow

maxflow（gerddie/maxflow）是 Kolmogorov 与 Boykov 的 BK max-flow/min-cut
图割算法库，出自论文 "An Experimental Comparison of Min-Cut/Max-Flow
Algorithms for Energy Minimization in Vision"（IEEE TPAMI 2004），是视觉
能量最小化 / graph cut 分割类应用的常用底库。Debian（libmaxflow-dev）、
Ubuntu、Mageia、Guix、MSYS2 均以该仓库为上游打包。

## OHOS adaptation

- Builds the upstream `3.0.5` tag with its own CMake build; the library is
  compiled as the shared `libmaxflow.so` exactly as upstream hardcodes
  (`ADD_LIBRARY(maxflow SHARED ...)`), with the four explicit template
  instantiations (int / short / float / double caps).
- The single patch (`0001-bump-cmake-minimum-version-to-3.5.patch`) bumps
  `cmake_minimum_required` from 2.8.5 to 3.5 so CMake 4.x can configure it
  (knowledge error-pattern E103).
- Consumers include `<maxflow.h>` with include dir `<prefix>/include/maxflow-3.0`
  (upstream's versioned layout) and link through the CMakeDeps-generated
  `maxflow::maxflow` target (upstream ships no CMake package config).
- The upstream test binary (`test_maxflow.cpp`, 3 test functions / 10
  assertions) runs via ctest inside `conan build`; the recipe injects the
  build dir into `LD_LIBRARY_PATH` because HarmonyOS emits no usable RPATH.

## Dependencies

None — the library needs only CMake >= 3.5 and a C++ toolchain.

## References

- https://github.com/gerddie/maxflow (upstream)
- `archives/m/maxflow/3.0.5/notes.md` (adaptation notes)
