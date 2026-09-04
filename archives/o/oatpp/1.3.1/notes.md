# oatpp 1.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `init-build oatpp 1.3.1 --url=https://github.com/oatpp/oatpp/archive/refs/tags/1.3.1.tar.gz`（官方 tag tarball，sha256=9dd31f005ab0b3e8895a478d750d7dbce99e42750a147a3c42a9daecbddedd64）
2. `lang-preflight` → cpp 匹配（cmake + 414 cpp 源，主体占比 100%）
3. 手动交叉编译（CMake + OHOS clang）：
   ```bash
   cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
     -DOATPP_BUILD_TESTS=ON -DOATPP_COMPAT_BUILD_NO_SET_AFFINITY=ON \
     -DOATPP_LINK_ATOMIC=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
   make -j4   # oatpp + oatpp-test + oatppAllTests 全部链接成功
   ```
4. 上游测试：`./test/oatppAllTests`（52 个独立用例实际运行全部通过；全量通过率 52/53=98.1%，1 个千迭代用例因单次执行预算中断，非失败）
5. 鸿蒙专项：`test_oatpp_ohos.cpp` HTTP 回环（127.0.0.1:18091 服务端+客户端，status=200、body 校验一致、`OHOS_TEST_PASS` exit 0）
6. `conan-init` + 修正配方（CMake 模板、package_info 版本子目录声明）→ `conan-verify` G0-G4+L2/L4/L5 全过（含 test_package ctest 1/1）
7. `finish` → W2 原子性 8 文件仅配方 / W3 本地 CI（setup+build_and_test RC=0、Junk 0、通过率 100%）/ submit 就绪

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake Error: Compatibility with CMake < 3.5 has been removed | CMake 4.1.2 移除对 cmake_minimum_required(<3.5) 的兼容；oatpp 声明 3.5 | configure 时传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（toolchain 变量加载时机过晚无效，须走 configure 命令行） |
| 2 | `use of undeclared identifier 'pthread_setaffinity_np'` (Thread.cpp:57) | OHOS musl 未实现 pthread_setaffinity_np（glibc GNU 扩展） | 上游自带选项 `OATPP_COMPAT_BUILD_NO_SET_AFFINITY=ON`（CMakeLists.txt:44/86），不改源码 |
| 3 | `ld.lld: error: unable to find library -latomic` | OHOS sysroot 无 libatomic.a；上游 OATPP_LINK_ATOMIC 默认 ON | `OATPP_LINK_ATOMIC=OFF`（aarch64 原子操作由 clang 内建实现） |
| 4 | conan create: `Library 'oatpp' not found in package` / 头文件 not found | oatpp 安装到版本子目录 `lib/oatpp-1.3.0`、`include/oatpp-1.3.0/oatpp`（module-install.cmake） | conanfile `package_info()` 显式声明 `libdirs=["lib/oatpp-1.3.0"]`、`includedirs=["include/oatpp-1.3.0/oatpp"]` |

## 源码修改

无（平台差异全部通过上游 CMake 选项解决，无补丁）。

## 依赖版本

- 无 Conan 外部依赖（oatpp 1.3.1 核心为纯 C++ 库）
- 工具链：clang 15.0.4 / CMake 4.1.2 / OHOS 6.0 (aarch64)

## 验证结果

```bash
# 上游测试（适配期全量运行）
./test/oatppAllTests  # 52/53 = 98.1% 全量通过率（52 个独立用例实过，1 个长迭代用例因预算中断）
# 鸿蒙专项回环测试
./test_oatpp_ohos    # OHOS status=200 body='Hello from OHOS oatpp 1.3.1' → OHOS_TEST_PASS (exit 0)
# Conan 验证
conan-verify oatpp 1.3.1   # G0-G4 + L2/L4/L5 全过
# W3 本地 CI
setup.sh + build_and_test.sh  # RC=0, Junk 0, Pass rate 100% (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 静态库配方（上游 compat 选项 + package_info 版本子目录声明） |
| conandata.yml | 官方 tag tarball + sha256 |
| test_package/ | 真实 HTTP 回环消费者测试（R34）+ MANIFEST.yml |
| packaging/oatpp-1.3.1-ohos-aarch64.tar.gz | 安装产物打包 |
| reports/ | test-report / upstream-test-inventory / knowledge-candidate-ledger / audit-result |

## 注意事项

- 版本子目录为 `oatpp-1.3.0`（非 1.3.1）：tag 1.3.1 的 Environment.hpp 定义 `OATPP_VERSION "1.3.0"`，module-install.cmake 据此生成子目录名，配方已对应声明。
- 上游全量测试含 1000 迭代 web 压测（FullTest 等），单次执行预算内可能无法跑完；按 SKILL "make check 超时跳过并记录原因" 处理，不阻塞交付。
---
**编译结束**: 2026-09-03 01:19
**最终状态**: built
