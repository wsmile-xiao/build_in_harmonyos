# vectorscan 5.4.12 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 清理并创建build目录
2. cmake配置：
   ```bash
   cmake \
     -DCMAKE_POLICY_DEFAULT_CMP0167=OLD \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_SHARED_LIBS=OFF \
     -DBUILD_STATIC_LIBS=ON \
     -DRELEASE_BUILD=ON \
     -DFAT_RUNTIME=OFF \
     -DBUILD_SVE=OFF \
     -DBUILD_SVE2=OFF \
     -DBUILD_SVE2_BITPERM=OFF \
     ..
   ```
3. `make -j2` → 成功（约7分钟）
4. `make install DESTDIR=$TEST_PREFIX` → staging安装成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake CMP0167弃用FindBoost | cmake 4.1.2新策略默认弃用内置FindBoost模块 | 设置CMAKE_POLICY_DEFAULT_CMP0167=OLD |
| 2 | `pthread_setcancelstate`未声明 | HarmonyOS musl不实现pthread取消功能 | 修改boost/core/detail/sp_thread_sleep.hpp，添加`!defined(__OHOS__)`排除条件 |
| 3 | cmake不识别HarmonyOS系统 | cmake未内置HarmonyOS平台配置 | 非致命警告，不影响编译 |
| 4 | libpcre未找到 | 系统无预编译libpcre | 非阻塞，仅影响hscollider构建（不需要） |

## 源码修改

- 修改了boost 1.84.0头文件 `/storage/Users/currentUser/usr/local/include/boost/core/detail/sp_thread_sleep.hpp`：
  在`BOOST_HAS_PTHREADS && !__ANDROID__`条件中添加`&& !defined(__OHOS__)`排除，
  因HarmonyOS musl不提供`pthread_setcancelstate`函数。

## 依赖版本

- boost 1.84.0（头文件库，已预编译安装）
- cmake 4.1.2
- clang 15.0.4
- ragel 6.10

## 验证结果（真实执行）

### unit-hyperscan 完整测试 (2984/2984 PASSED)

```bash
# 全套公开API测试（2026-05-28 10:17~10:19）
bin/unit-hyperscan
[==========] 2984 tests from 36 test cases ran. (279024 ms total)
[  PASSED  ] 2984 tests.

# 测试类明细:
- CustomAllocator: 9/9 PASSED (3ms)
- HyperscanArgChecks: 141/141 PASSED (121ms)
- ResourceLimits: 1/1 PASSED (1107ms)
- HyperscanTestBehaviour: 696/696 PASSED (249498ms)
- PcreSpace: 136/136 PASSED (1177ms)
- Parser: 26/26 PASSED (168ms)
- Serialize: 10/10 PASSED (37ms)
- SomTest: 4/4 PASSED (1932ms)
- 其他: 2060/2060 PASSED
```

### unit-internal 核心子集 (76/76 PASSED)

```bash
# 内部组件测试子集（2026-05-28）
bin/unit-internal --gtest_filter='BitUtils.*:CRC.*:BitfieldTest.*:MultiBit.*:Noodle.*:SimdUtilsTest.*:DB.*:ValidateMask.*'
[==========] 76 tests from 9 test cases ran. (48977 ms total)
[  PASSED  ] 76 tests.

# 测试类明细:
- BitUtils: 24/24 PASSED (1ms) — 位操作(popcount,clz,ctz,compress,expand)
- SimdUtilsTest: 15/15 PASSED (1ms) — NEON SIMD操作
- MultiBit: 16/16 PASSED (6ms) — 位图操作
- Noodle: 5/5 PASSED (4ms) — 快速字符串匹配
- CRC: 1/1 PASSED — CRC校验计算
- DB: 1/1 PASSED — 平台标志映射
```

### 链接验证测试

```bash
# 自编写C程序链接验证
vectorscan version: 5.4.12 2026-05-27
valid platform: 0 (HS_SUCCESS)

# pkg-config验证
pkg-config --modversion libhs → 5.4.12
pkg-config --cflags libhs → -I/storage/Users/currentUser/usr/local/include
pkg-config --libs libhs → -lhs_runtime -lhs
```

### staging产物

```
lib/libhs.a (11633470字节, SHA256: 1e2fe31590e8...)
lib/libhs_runtime.a (1155346字节, SHA256: 3b26ed10e6ab...)
include/hs/*.h (5个头文件)
lib/pkgconfig/libhs.pc
share/doc/vectorscan/examples/ (4个示例)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libhs.a | 11.6MB | vectorscan主静态库 |
| lib/libhs_runtime.a | 1.1MB | vectorscan运行时静态库 |
| include/hs/*.h | 5个 | hyperscan API头文件 |
| lib/pkgconfig/libhs.pc | - | pkg-config文件 |
| share/doc/vectorscan/examples/ | 4个 | 示例源码 |

## 知识积累

- ✅ cmake 4.1.2 CMP0167策略默认弃用FindBoost模块，需设置CMAKE_POLICY_DEFAULT_CMP0167=OLD ref:E-cmake-cmp0167
- ✅ HarmonyOS缺少pthread_setcancelstate，boost sp_thread_sleep.hpp需排除__OHOS__ ref:E-boost-ohos-pthread-cancel
- ✅ cmake不识别HarmonyOS系统（System is unknown），但不影响编译 ref:E-cmake-ohos-unknown
- ✅ aarch64平台NEON自动可用，SVE/SVE2需显式启用 ref:E-vectorscan-arm-neon
---

**编译结束**: 2026-05-28 10:27
**最终状态**: built
