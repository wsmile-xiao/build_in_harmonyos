# iortcw 1.51.c 适配笔记

## 基本信息

- **三方库名称**：iortcw
- **上游版本**：1.51.c
- **上游仓库地址**：https://github.com/iortcw/iortcw
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（iortcw 用 make 构建，走 OHOS 工具链 clang 直接编）

## 构建方案

iortcw 是 Return to Castle Wolfenstein 游戏引擎（基于 ioquake3 + GPL 源码），使用 `make` 编译产出 iowolfsp/iowolfmp/iowolfded 二进制 + main/ 游戏 .so。

### 构建命令

```bash
make ARCH=arm64 PLATFORM=ohos CC=clang CXX=clang++ BUILD_CLIENT=1 BUILD_SERVER=1 BUILD_GAME_SO=1
```

### 交叉编译目标

`ARCH=arm64` 指定架构，`PLATFORM=ohos` 指定平台，CC/CXX 注入 Conan 解析的 clang（非宿主 gcc）。

### 依赖注入

iortcw 的 Makefile 不走 pkg-config，需手动注入依赖包的 include/lib 路径到 CFLAGS/LDFLAGS：
- SDL2/2.30.0（Simple DirectMedia Layer）
- openal/1.25.2（OpenAL 音频 API）
- opus/1.4 + opusfile/0.12（Opus 编解码）
- libogg/1.3.5 + libvorbis/1.3.7（Ogg Vorbis 编解码）
- libjpeg/10（JPEG 库）
- freetype/2.14.3（FreeType 字体引擎）
- curl/8.15.0（libcurl HTTP 下载）
- zlib/1.3.1.1.1（zlib 压缩）

## 上游测试说明

### 上游测试用例

- iortcw 上游无独立 tests/ 目录（游戏引擎非库，无单元测试框架）
- freetype-2.9/src/tools/ 含 test_afm.c/test_bbox.c/test_trig.c 但属内部库非 iortcw 本体测试
- 上游真测试靠运行时游戏验证（需 RTCW 游戏数据 pak0.pk3 等），CI worker 无游戏数据跳过

### 跳过原因

iortcw 是游戏引擎非库，无单元测试框架；运行时游戏验证需 RTCW 游戏数据（pak0.pk3 等），CI worker 无游戏数据 → 跳过上游测试。

## 适配后测试

### test_package

- `test_package/conanfile.py test()` 验证 `iowolfsp` 二进制存在 + ELF header sanity
- 交叉编译场景（arm64 OHOS binary on x86_64 CI worker）：跳过 runtime，只验 ELF header `\x7fELF`
- native 场景：跑 `iowolfsp --version` 退出码 0

### 测试用例对比

| 测试类型 | 上游用例数 | 适配后用例数 | 说明 |
|----------|-----------|-------------|------|
| 单元测试 | 0 | 0 | iortcw 无单元测试框架 |
| 鸿蒙特有测试 | 0 | 1 | test_package 验证二进制 + ELF header |
| **合计** | **0** | **1** | |

## 依赖

全依赖已合入 main：
- SDL2/2.30.0 ✅
- openal/1.25.2 ✅
- opus/1.4 ✅
- opusfile/0.12 ✅
- libogg/1.3.5 ✅
- libvorbis/1.3.7 ✅
- libjpeg/10 ✅
- freetype/2.14.3 ✅
- curl/8.15.0 ✅
- zlib/1.3.1.1.1 ✅

## 验证结果

- 编译状态：通过（CI worker 需 clang 工具链 + 全依赖 Conan 包可用）
- 上游测试用例通过率：0/0（上游无单元测试）
- 新增测试用例通过率：1/1（100%，交叉编译场景诚实跳过 runtime 只验 ELF header）
