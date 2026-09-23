# fdk-aac-encoder 1.0.9 适配笔记

## 基本信息
- 上游项目: fdkaac（nu774 的 FDK-AAC 命令行编码器前端）
- 构建系统: **CMake（首选，已验证）** + autotools 双构建系统
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（OHOS 原生工具链，build=host）
- 状态: published
- 语言: C（lang-preflight 判定 c，任务 cpp，c↔cpp 兼容族通过 R47）

## ⚠️ 关键坑（供后续复用）

### 1. 源码来源：GitHub 官方仓库 tag 归档
- fdkaac 的官方源是上游作者 nu774 的 GitHub 仓库
  `https://github.com/nu774/fdkaac`（上游 COPYING 中 Source 字段即指向此仓库）
- **正确源**: `https://github.com/nu774/fdkaac/archive/refs/tags/v1.0.9.tar.gz`（v1.0.9 tag 归档）
- SHA256 经本地缓存与 gh-proxy 镜像重新下载双重核验一致，满足 R39 官方源要求

### 2. init-build 误判构建系统为 autotools —— 忽略之
- 源码同时含 `configure.ac`/`Makefile.am`（autotools）与 `CMakeLists.txt`（CMake）
- init-build 优先检测到 configure.ac 误判为 autotools（`.build-context` 中 BUILD_SYSTEM=autotools）
- **实际用 CMake 构建**（上游 CMakeLists.txt 为官方主构建系统，2015 年起由作者维护）
- CMake 通过 `pkg_check_modules(FDK_AAC REQUIRED fdk-aac)` 找依赖，无需改源码

### 3. Conan 包名规范：fdk-aac-encoder 而非 fdkaac
- 上游二进制名是 `fdkaac`，但制品仓/归档规范用描述性名 `fdk-aac-encoder`
- 与已发布依赖 `fdk-aac/2.0.3`（库）区分：本包是 encoder CLI 工具
- Conan recipe 中 `name = "fdk-aac-encoder"`

## 编译步骤（CMake 路径）

依赖注入方式（R49：build_folder 私有 prefix，禁共享 /usr/local）：

```bash
# 1. 生成依赖注入文件（PkgConfigDeps 供上游 pkg-config 探测，CMakeToolchain 供工具链）
mkdir -p $HOME/tmp/fdkaac-cmake-deps && cd $HOME/tmp/fdkaac-cmake-deps
conan install --requires fdk-aac/2.0.3 --requires libsndfile/1.2.2 \
  -r ohpcd -pr:a ohos-aarch64 -g PkgConfigDeps -g CMakeToolchain -g VirtualBuildEnv

# 2. 配置 + 编译（参数最少化 R1：仅 CMAKE_INSTALL_PREFIX）
source conanbuild.sh
export PKG_CONFIG_PATH=$HOME/tmp/fdkaac-cmake-deps:$PKG_CONFIG_PATH
cmake $BUILD_SRC_DIR -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build . -j2

# 3. staging 安装（$TEST_PREFIX 隔离）
cmake --install .   # CMAKE_INSTALL_PREFIX 已指向 staging
# 4. 正式安装：重新 cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX 后 cmake --install
```

注：上游 CMakeLists.txt 用 `pkg_check_modules(FDK_AAC REQUIRED fdk-aac)` 探测依赖，
故 Conan 侧需 PkgConfigDeps 生成 fdk-aac.pc（fdk-aac 库包的 cpp_info 无 pkg_config 自定义名，
默认 .pc 名与包名一致，直接可用）。libsndfile 非链接依赖（wav 解析为源码内置实现），
仅作为工具链同族依赖声明，实际不进入链接。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码 URL 选择 | 无独立官网，官方源即 GitHub 仓库 | 使用 GitHub 官方仓库 nu774/fdkaac tag v1.0.9 归档（上游 COPYING Source 字段） |
| 2 | init-build 判 BUILD_SYSTEM=autotools | 源码含 configure.ac 双构建系统 | 忽略误判，用 CMake 构建（官方主构建系统） |
| 3 | `fdkaac --version` 报 unrecognized option | 上游 CLI 无 --version 选项（只有 -h/--help，首行打印版本） | 验证用 `fdkaac --help | head -1` 或编码实测 |
| 4 | Iconv 未找到（CMake WARNING，非致命） | OHOS 无独立 libiconv（musl libc 内置） | 无需处理，HAVE_ICONV 未定义时上游走兼容路径 |
| 5 | cmake 4.1.2 警告 "System is unknown to cmake, create Platform/HarmonyOS" | OHOS 适配 conan 的 CMAKE_SYSTEM_NAME=HarmonyOS 尚未进 CMake 官方平台表 | 警告非错误，编译正常，忽略 |
| 6 | 上游测试 verify_smart_padding.py 需要 ffmpeg | 测试脚本用 ffmpeg 解码交叉验证 gapless 边界 | 用制品仓 ffmpeg/5.1.10（conan install + conanrun.sh 提供 PATH） |

## 源码修改
无（零补丁，源码原样编译）

## 依赖版本
- fdk-aac/2.0.3（ohpcd 已发布，shared，R36 预检通过）
- libsndfile/1.2.2（ohpcd 已发布；上游 CMakeLists 不链接它——wav 读取为内置实现，声明为工具族依赖）
- ffmpeg/5.1.10（仅测试期使用，非构建依赖）

## 上游测试清点（R51）
- `tests/` 目录 1 个文件：`verify_smart_padding.py`（smart-padding/LPC pre/post-roll 回归测试）
- 无 ctest 注册（CMakeLists.txt 无 enable_testing/add_test）
- 实测：30 项全部 PASS（profiles 2/5/29/23/39 × empty/tiny/one frame/exact multiple/short tail/general），ffmpeg 5.1.10 作解码器

## 验证结果

```bash
# staging 验证
$TEST_PREFIX/bin/fdkaac --help | head -1   # → fdkaac 1.0.9
# 编码实测（440Hz 双声道 1s 正弦波 WAV → M4A）
$TEST_PREFIX/bin/fdkaac -b 128000 -o test_tone.m4a test_tone.wav
# → 44100/44100 samples processed，输出 M4A 头 ftyp M4A 有效
# 上游回归测试
python3 tests/verify_smart_padding.py --fdkaac $TEST_PREFIX/bin/fdkaac
# → 30 passed, 0 failed
# 用户级验证（$DEFAULT_PREFIX 安装后）
/storage/Users/currentUser/usr/local/bin/fdkaac -b 128000 --silent -o t2.m4a test_tone.wav  # OK
```

## Conan 配方要点
- `name = "fdk-aac-encoder"`（区别于库包 fdk-aac）
- package_type = "application"（产物为 CLI 可执行文件）
- requirements: fdk-aac/2.0.3, libsndfile/1.2.2
- generate(): PkgConfigDeps（上游用 pkg_check_modules）+ CMakeToolchain
- R38: 软件级 commands.json 必须创建（产物含 bin/fdkaac）
- build 不需要 CXX（fdk-aac 预编译库已含 C++ runtime 符号解析，纯 C 链接即可）
---

**编译结束**: 2026-09-04 11:35
**最终状态**: published
