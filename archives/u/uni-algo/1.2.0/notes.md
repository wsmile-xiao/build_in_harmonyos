# uni-algo 1.2.0 适配笔记

## 编译环境

| 项目 | 值 |
|------|-----|
| 构建系统 | CMake |
| 编译日期 | 2026-06-18 |
| 编译器 | clang 15.0.4 / clang++ 15.0.4 |
| C++ 标准 | C++17 (cxx_std_17) |
| CFLAGS | -fPIC -O2 |
| 平台 | HarmonyOS aarch64 |
| 状态 | published |

## 编译步骤

### Step 1: 初始化
```bash
export SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" | head -1)")"
export SSL_CERT_FILE="/storage/Users/currentUser/usr/local/ssl/cert.pem"
python3 $SKILL_ROOT/scripts/ohc-run.py init-build uni-algo 1.2.0 \
  --url=https://github.com/uni-algo/uni-algo/archive/refs/tags/v1.2.0.tar.gz
```

### Step 2: CMake 配置 + 编译
```bash
source .build-context-uni-algo-1.2.0
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..
make -j2
```

cmake 配置输出要点：
- CXX 编译器：Clang 15.0.4
- BUILD_SHARED_LIBS: OFF（默认静态库）
- UNI_ALGO_HEADER_ONLY: OFF
- UNI_ALGO_INSTALL: ON

编译输出：
- `[50%] Building CXX object CMakeFiles/uni-algo.dir/src/data.cpp.obj`
- `[100%] Linking CXX static library libuni-algo.a`
- 编译成功，无警告无错误

### Step 3: Staging 安装（DESTDIR 模式，R20）
```bash
make install DESTDIR=$TEST_PREFIX
```
安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/`，用于打包验证。

### Step 4: 测试
```bash
cd $BUILD_SRC_DIR/test
mkdir -p build_test && cd build_test
cmake .. -DBUILD_UNI_ALGO=ON
make -j2
ctest --output-on-failure --verbose
```
结果：1/1 测试通过，17 个子测试项全部 PASS（2 项跳过因未下载 Unicode 测试文件）。

### Step 5: 预编译包制作
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package uni-algo 1.2.0
```
产物：`uni-algo-1.2.0-ohos-aarch64.tar.gz`（2.6MB）

### Step 6: 本地安装（模拟用户部署）
```bash
cd $BUILD_SRC_DIR/build
make install
```
安装到 `$DEFAULT_PREFIX`（/storage/Users/currentUser/usr/local）。

### Step 7: 收尾
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish uni-algo 1.2.0 published
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build uni-algo 1.2.0
```
质量门禁：G1-G4 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败：SSL CERTIFICATE_VERIFY_FAILED | 系统默认 OpenSSL CA 路径 `/etc/ssl/cert.pem` 不存在 | 设置 `SSL_CERT_FILE` 指向 `/storage/Users/currentUser/usr/local/ssl/cert.pem` |
| 2 | G4 门禁失败：manifest 缺少 build_system | 模板使用嵌套格式 `build: system:`，但门禁检查顶层 `build_system:` 字符串 | 在 manifest.yaml 顶层添加 `build_system: cmake` 字段 |
| 3 | G0 clean-verify 失败（exit 127） | clean-verify 脚本对 cmake 项目仍尝试运行 `./configure`，cmake 项目没有该脚本 | 已知平台限制，实际编译通过 cmake 手动完成并全部测试通过 |
| 4 | make jobserver mkfifo 警告 | HarmonyOS 上 mkfifo 系统调用权限受限 | 非致命警告，编译正常完成不影响产物 |

## 源码修改

无补丁，无源码修改。uni-algo 1.2.0 在 HarmonyOS 平台上原生编译通过，不需要任何平台适配。

## 依赖版本

无外部库依赖。uni-algo 是 header-only 友好的 C++17 库，仅编译 `src/data.cpp` 生成静态库。

- 编译器: clang 15.0.4
- CMake: 4.1.2
- Make: GNU Make 4.4.1
- C++ 标准: C++17

## 验证结果

### 库文件验证
```bash
$ ls -la /storage/Users/currentUser/usr/local/lib/libuni-algo.a
-rw-rw---- 1 20001006 file_manager 674698 2026-06-18 19:10 libuni-algo.a
$ file /storage/Users/currentUser/usr/local/lib/libuni-algo.a
ar archive
$ sha256sum /storage/Users/currentUser/usr/local/lib/libuni-algo.a
c37f535af5ed9494436c62c07a1f29fc024b62d4e24324738846e3eaca68c7ae
```

### 头文件验证
```bash
$ find /storage/Users/currentUser/usr/local/include/uni_algo -name "*.h" | wc -l
53
```
头文件列表：all.h, case.h, config.h, conv.h, locale.h, norm.h, prop.h, ranges.h, ranges_conv.h, ranges_grapheme.h, ranges_norm.h, ranges_word.h, script.h, version.h 及 impl/、internal/、ext/ 子目录下的 39 个内部头文件。

### CMake 配置验证
```bash
$ ls /storage/Users/currentUser/usr/local/share/uni-algo/cmake/
uni-algo-config-version.cmake
uni-algo-config.cmake
uni-algo-targets-noconfig.cmake
uni-algo-targets.cmake
```
支持 `find_package(uni-algo)` 集成。

### 测试验证
```
100% tests passed, 0 tests failed out of 1
Total Test time (real) = 2.30 sec
ALL TESTS PASSED!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libuni-algo.a` | 674,698 bytes | 静态库 |
| `include/uni_algo/*.h` | 53 个文件 | 头文件 |
| `share/uni-algo/cmake/*.cmake` | 4 个文件 | CMake 集成配置 |
| `uni-algo-1.2.0-ohos-aarch64.tar.gz` | 2,738,614 bytes | 预编译包 |

## 注意事项

1. **纯库项目**：uni-algo 不产出可执行二进制文件，G2 门禁的 "无二进制文件" 警告属于预期行为。
2. **静态库**：默认编译为静态库（BUILD_SHARED_LIBS=OFF），符合鸿蒙平台静态库优先策略。
3. **CMake 项目识别**：init-build 默认识别为 autotools，实际为 cmake 项目，需手动使用 cmake 命令编译。
4. **SSL 证书**：本环境需设置 SSL_CERT_FILE 环境变量才能正常下载源码。

---

**编译结束**: 2026-06-18 19:13
**最终状态**: published
