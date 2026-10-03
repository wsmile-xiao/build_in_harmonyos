# nlopt 2.11.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: built

## 编译步骤

1. init-build 下载源码（tag v2.11.0）并校验 sha256
2. CMake 配置（关闭可选绑定，保留 C++ 接口与测试）：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=${DEFAULT_PREFIX} -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_SHARED_LIBS=ON -DNLOPT_CXX=ON \
     -DNLOPT_PYTHON=OFF -DNLOPT_OCTAVE=OFF -DNLOPT_MATLAB=OFF \
     -DNLOPT_GUILE=OFF -DNLOPT_SWIG=OFF -DNLOPT_TESTS=ON
   ```
3. make -j 编译（100% 完成）
4. ctest 全部 77 项通过（100%），为上游注册清单中 OHOS 可运行的 C++/testopt 部分（上游完整注册 94 项，其余 17 项为语言绑定测试，OHOS 无对应运行时未运行）
5. conan-verify 8 门禁通过（G0-G4 + L2/L4/L5），标记 built
6. finish 收尾（补丁 0 个，无源码修改）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 Autotools 配方 | 版本级 manifest 模板残留 build.system=autotools，_detect_build_system 优先读 manifest 而非源码扫描 | 修正 manifest.yaml build.system=cmake 后重新 conan-init 生成 CMake 配方 |
| 2 | 本机 cmake/ctest Error relocating 符号找不到 | /data/service/hnp 下 cmake 依赖 libc++_shared.so（SDK llvm/lib/aarch64-linux-ohos/），LD_LIBRARY_PATH 未包含 | 运行前 export LD_LIBRARY_PATH=$SDK/lib/aarch64-linux-ohos:$SDK/lib:$LD_LIBRARY_PATH |
| 3 | test_package 链接 ld.lld undefined symbol（operator delete 等） | NLOPT_CXX=ON 使 libnlopt.a 含 C++ 符号，但 test_package 用 project(... C) 纯 C 链接器缺少 libc++ 运行时 | test_package 改 project(test_nlopt CXX)，test.c → test.cpp |
| 4 | CTest 注册 94 项（上游完整清单，含语言绑定测试）；OHOS 实测运行 77 项全部参数化（testopt 等 6 个二进制） | 上游测试设计如此 | ctest 直接全量运行可运行部分，77/77 通过，无需逐一映射 |

## 源码修改

无（0 补丁，源码无改动）。

## 依赖版本

- 无外部依赖（纯数学库，所有可选绑定已关闭）
- 工具链：cmake 4.1.2、clang 15.0.4、make 4.4.1

## 验证结果

```bash
# 上游测试（build 目录内）
ctest --output-on-failure
# => 100% tests passed, 0 tests failed out of 77

# 消费者测试（conan create 自动执行 test_package）
# => 1/1 Test #1: test_nlopt ... Passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| libnlopt.a / libnlopt.so | 优化库本体（NLOPT_CXX=ON，含 C++ API） |
| include/nlopt.h, include/nlopt.hpp | C/C++ 头文件 |
| lib/cmake/nlopt/ | CMake 包配置文件 |
| lib/pkgconfig/nlopt.pc | pkg-config 元数据 |

## 注意事项

- NLopt 顶层 CMake 默认开启 Python/Octave/Matlab/Guile/SWIG 可选绑定（find_package），OHOS 无对应工具链，配方 generate() 中显式关闭（方案 A），功能损失面：仅语言绑定，核心 C/C++ 优化 API 完整保留，PrusaSlicer 依赖的 nlopt_cxx API 不受影响。
- 本机 ctest 若报 Error relocating 符号错误，须前置 SDK `llvm/lib/aarch64-linux-ohos` 到 LD_LIBRARY_PATH（libc++_shared.so）。

---

**编译结束**: 2026-09-29 22:20
**最终状态**: built
