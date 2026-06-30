# drafter 5.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-29
- 编译器: clang/clang++ (Clang 15.0.4, aarch64)
- 平台: HarmonyOS (aarch64)
- 状态: published

## 编译步骤

### 1. 源码获取

由于 GitHub release tarball 下载在 HarmonyOS 环境 SSL 证书验证失败（CERTIFICATE_VERIFY_FAILED），使用 git clone 替代：

```bash
cd $TMPDIR/builds
git clone --depth 1 --branch v5.1.0 https://github.com/apiaryio/drafter.git drafter-5.1.0.work
cd drafter-5.1.0.work
git submodule update --init --recursive
git config --global --add safe.directory "*"
```

### 2. CMake 配置

```bash
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

### 3. 编译

```bash
make -j2
```

全部目标构建成功（100%），包含 sundown、apib、drafter-lib、drafter-so、drafter-cli 及测试套件。

### 4. 测试

```bash
ctest --verbose
```

4/4 测试全部通过，共 7651 个断言、1358 个测试用例。

### 5. 安装

```bash
make install DESTDIR=$TEST_PREFIX
```

### 6. Staging 验证

```bash
readelf -d "$TEST_PREFIX$DEFAULT_PREFIX/bin/drafter" | grep NEEDED
"$TEST_PREFIX$DEFAULT_PREFIX/bin/drafter" --version
```

### 7. Conan 配方生成与验证

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init drafter 5.1.0
# 手动将 conanfile.py 从 Autotools 模板改写为 CMake 模板
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify drafter 5.1.0
```

conan-verify 8 道门禁全部通过 (G0-G4 + L2/L4/L5)。

### 8. 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish drafter 5.1.0 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub release tarball 下载失败 (CERTIFICATE_VERIFY_FAILED) | HarmonyOS 环境 SSL 证书验证不通过 | 使用 `git clone --depth 1 --branch v5.1.0` 获取源码，打包为本地 tarball，conandata.yml 使用 file:// URL |
| 2 | CMake 配置报 deprecation warning | drafter 子模块（sundown, cmdline）使用 cmake_minimum_required < 3.5，CMake 4.x 不兼容 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | conan-init 生成 Autotools 模板 | ohc-run.py conan-init 未正确识别 CMake 构建系统 | 手动将 conanfile.py 改写为 CMake 模板（conan.tools.cmake） |
| 4 | conandata.yml SHA256 为占位符 | 无法下载 GitHub release tarball 获取原始 SHA256 | 使用 git clone 创建本地 tarball，计算 SHA256 (447ce171e4dbb68b650a10e8bd988b40922230e76d3d030ea2e7ecf096486440) |
| 5 | "System is unknown to cmake" 警告 | CMake 不识别 HarmonyOS 平台 | 非阻塞警告，不影响编译 |

## 源码修改

无补丁。所有子模块通过 git clone --recursive 获取，未修改任何源文件。
CMAKE_POLICY_VERSION_MINIMUM=3.5 通过 Conan 工具链传递，不修改源码。

## 依赖版本

无外部依赖。drafter 将所有依赖作为 git 子模块内嵌在 packages/ 目录中：
- sundown (Markdown 解析)
- cmdline (命令行解析)
- snowcrash (API Blueprint 解析核心)
- carcass (代码生成模板)
- peg-markdown (Markdown 解析)

## 验证结果

```bash
# ctest 结果
100% tests passed, 0 tests failed out of 4
Total Test time (real) =   4.04 sec

# smoke test
$ drafter --version
v5.0.0

# 动态依赖
readelf -d bin/drafter | grep NEEDED
  (NEEDED) Shared library: [libc++_shared.so]
  (NEEDED) Shared library: [libc.so]

# conan-verify 结果
G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS
L2: PASS | L4: PASS | L5: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/drafter | 1,841,664 bytes | 命令行可执行文件 (ELF 64-bit arm64, PIE) |
| lib/libdrafter.a | 3,120,502 bytes | 静态库 (ar archive) |
| lib/libdrafter.so | 2,197,952 bytes | 共享库 |
| include/drafter/drafter.h | - | C/C++ 头文件 |
| lib/cmake/drafter/ (4个文件) | - | CMake 配置文件 |

## 注意事项

1. **版本号不一致**: `drafter --version` 输出 v5.0.0 而非 v5.1.0，因为版本号来自 CMakeLists.txt 中的硬编码而非 git tag，这是上游项目的行为
2. **共享库仍被安装**: 虽然 BUILD_SHARED_LIBS=OFF，drafter 项目默认同时构建和安装静态库和共享库。BUILD_SHARED_LIBS=OFF 主要在 Conan 配方中控制链接选择
3. **本地 tarball**: conandata.yml 中的 URL 使用 file:// 协议指向本地 tarball，因为 GitHub SSL 下载在当前环境不可用。生产环境应替换为原始 GitHub URL 和 SHA256

---

**编译结束**: 2026-06-29 23:43
**最终状态**: published
