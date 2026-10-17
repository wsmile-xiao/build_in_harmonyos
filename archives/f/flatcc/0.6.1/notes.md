# flatcc 0.6.1 适配笔记

## 编译环境
- 平台: HarmonyOS (aarch64, musl libc, ld-musl-aarch64.so.1)
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4
- CMake: 4.1.2
- GNU Make: 4.4.1
- 状态: published

## 编译步骤（完整命令）

```bash
# Step 1: 初始化
source .build-context-flatcc-0.6.1
cd $BUILD_SRC_DIR

# Step 2: cmake 配置
mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DFLATCC_ALLOW_WERROR=OFF \
  -DFLATCC_INSTALL=ON

# Step 3: 编译
make -j2

# Step 4: 安装到 staging（DESTDIR 模式）
make install DESTDIR=$TEST_PREFIX

# Step 5: 测试
ctest --test-action=test

# Step 6: 安装到本地
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律 |
|---|------|------|----------|------|
| 1 | SSL 下载失败 | 鸿蒙环境 HTTPS 证书验证失败，Python urllib 无法建立 SSL 连接 | 手动 `curl -kL` 下载 tarball，`init-build --no-download` 初始化 | R10 |
| 2 | cmake_minimum_required 报错 | CMake 4.1.2 移除了对 `cmake_minimum_required < 3.5` 的兼容性支持 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数 | R6/R23 |
| 3 | 编译错误: variable 'present_id' set but not used | CMakeLists.txt 中 `-Werror` 将 clang 15 的 `-Wunused-but-set-variable` 警告提升为编译错误 | 添加 `-DFLATCC_ALLOW_WERROR=OFF` 禁用 -Werror | R6 |
| 4 | make install 报 No rule to make target 'install' | flatcc 的 `FLATCC_INSTALL` 选项默认为 OFF，不生成 install 目标 | 添加 `-DFLATCC_INSTALL=ON` 启用安装目标 | R20 |
| 5 | init-build 检测为 autotools | init-build 默认检测为 autotools，但 flatcc 使用 cmake | 手动修正 manifest.yaml 中 build_system 为 cmake | R15 |
| 6 | G0 干净构建验证失败 | clean_verify.py 脚本硬编码 `bash ./configure`，不支持 cmake 项目 | 手动 G0 验证通过（脚本限制，不影响编译结果） | - |

## 源码修改

**无源码修改**。所有问题均通过 cmake 配置选项解决，遵守 R6 铁律（只改配置不改源文件）。

## cmake 配置参数详解

| 参数 | 说明 |
|------|------|
| `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX` | 安装前缀（R20: DESTDIR 模式，prefix=~/usr/local） |
| `-DCMAKE_BUILD_TYPE=Release` | Release 构建 |
| `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` | CMake 4.x 兼容旧项目（解决 cmake_minimum_required < 3.5） |
| `-DFLATCC_ALLOW_WERROR=OFF` | 禁用 -Werror（解决 clang 15 编译警告变错误） |
| `-DFLATCC_INSTALL=ON` | 启用 cmake install 目标（flatcc 默认 OFF） |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| cmake | 4.1.2 | 构建系统 |
| clang | 15.0.4 | C/C++ 编译器 |
| make | GNU Make 4.4.1 | 构建工具 |
| llvm-ar | LLVM | 静态库归档工具 |

## 编译产物清单

| 文件 | 路径 | 大小 | 类型 |
|------|------|------|------|
| flatcc | ~/usr/local/bin/ | 326K | ELF 共享对象, arm64, 链接 ld-musl-aarch64.so.1 |
| libflatcc.a | ~/usr/local/lib/ | 479K | ar 静态库（编译器核心） |
| libflatccrt.a | ~/usr/local/lib/ | 196K | ar 静态库（运行时库） |
| flatcc 头文件 | ~/usr/local/include/flatcc/ | 63 个 .h | 头文件（含 portable/reflection/support 子目录） |
| **总安装文件** | | 71 个 | DESTDIR staging 验证 |

## 验证结果

### ctest 测试
```
100% tests passed, 0 tests failed out of 22
Total Test time (real) =   1.11 sec
```

### 二进制验证
```
$ flatcc --version
flatcc FlatBuffers schema compiler for C by dvide.com
version: 0.6.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| flatcc-0.6.1-ohos-aarch64.tar.gz | 1.5M (1,657,617 bytes) | 预编译包（含 bin/lib/include，ELF 已签名） |
| flatcc-0.6.1-ohos-aarch64-debug.tar.gz | 51K (51,740 bytes) | 调试符号包 |

## G0 干净构建验证（手动执行）

G0 脚本（clean_verify.py）硬编码 `bash ./configure`，不支持 cmake 项目。手动从原始 tarball 解压后重新编译验证通过：

```
解压 flatcc-0.6.1.tar.gz → cmake configure → make → make install DESTDIR
→ flatcc --version: 0.6.1 ✅
```

## 注意事项

1. flatcc 使用 cmake 而非 autotools，构建系统为 cmake
2. FLATCC_INSTALL 默认 OFF，需要手动开启
3. FLATCC_ALLOW_WERROR 默认 ON，clang 15 编译需关闭
4. 无外部库依赖（纯 C 项目，自带 hash/external 子模块）
5. 生成的二进制为静态库模式（libflatcc.a + libflatccrt.a），无共享库

---

**编译开始**: 2026-06-17 03:51 (init-build)
**编译结束**: 2026-06-17 06:54 (finish published)
**最终状态**: built (conan-verify G0-G4 通过, W3 本地 CI 模拟通过)
---

**编译结束**: 2026-07-16 20:44
**最终状态**: built
