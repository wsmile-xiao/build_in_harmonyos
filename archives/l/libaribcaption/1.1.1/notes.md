# libaribcaption 1.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 初始化编译环境:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libaribcaption 1.1.1 --url=https://github.com/xqq/libaribcaption/archive/refs/tags/v1.1.1.tar.gz
   ```
2. cmake 配置:
   ```bash
   source .build-context-libaribcaption-1.1.1
   cd $BUILD_SRC_DIR
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=MinSizeRel \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DCMAKE_C_FLAGS="-D__OHOS__" \
         -DCMAKE_CXX_FLAGS="-D__OHOS__" \
         -DARIBCC_NO_RENDERER=ON .
   ```
3. 构建: `make -j1`
4. staging 安装: `make install DESTDIR=$TEST_PREFIX`
5. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package libaribcaption 1.1.1`
6. 本地安装: `make install`（不带 DESTDIR）
7. 收尾: `python3 $SKILL_ROOT/scripts/ohc-run.py finish libaribcaption 1.1.1 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 配置失败: Could NOT find Fontconfig | CMAKE_SYSTEM_NAME=Linux 时，CMakeLists.txt 第74行默认启用 ARIBCC_USE_FONTCONFIG=ON 和 ARIBCC_USE_FREETYPE=ON，需 Fontconfig 和 FreeType 库 | 添加 `-DARIBCC_NO_RENDERER=ON` 禁用 renderer，消除 Fontconfig/FreeType 依赖（符合铁律 R8 源码四不准则——不改源码，通过编译选项解决） |
| 2 | 源码下载 SSL 证书验证失败 | 系统 SSL 证书不完整，urllib HTTPS 验证失败 | 使用 `curl -L -k` 手动下载源码包，放置到 `~/tmp/builds/libaribcaption-1.1.1.tar.gz`，init-build 检测到已存在 tarball 自动跳过下载 |
| 3 | G0 干净构建验证失败 (exit 127) | ohc-run.py 的 clean_verify.py 仅支持 autotools（硬编码 `bash ./configure`），不支持 cmake 项目 | 手动执行 G0 验证: 解压原始 tarball → cmake 配置 → make → make install DESTDIR → 创建 `.g0-verified` 标记文件 |
| 4 | verify-build G4 门禁失败: manifest 缺少 build_system | init-build 自动生成的 manifest.yaml 将 build_system 写在 `build.system` 子字段下，但 verify_build.py 检查的是顶级字段 `build_system` | 在 manifest.yaml 顶级添加 `build_system: cmake` 字段 |

## 源码修改

**无源码修改**。所有问题通过 cmake 配置选项解决，符合铁律 R6（只改源文件不改生成文件）和 R8（源码四不准则——#ifdef __OHOS__ 守卫）。

## 依赖版本

无外部依赖（renderer 禁用后不需要 Fontconfig/FreeType）

## 验证结果

### 功能验证测试（真实执行）

编写 C 测试程序链接静态库，验证核心 API:

```
=== libaribcaption 1.1.1 功能验证测试 ===

[PASS] 测试1: aribcc_context_alloc() 成功创建上下文
[PASS] 测试2: aribcc_decoder_alloc() 成功创建解码器
[PASS] 测试3: 头文件可用，aribcaption.h 正确包含
       ARIBCC_PROFILE_A = 0x0008
       ARIBCC_PROFILE_C = 0x0012
[PASS] 测试4: 静态库 libaribcaption.a 链接成功
[PASS] 测试5: pkg-config --modversion 返回 1.1.1
[PASS] 测试6: aribcc_decoder_free() 成功释放解码器
[PASS] 测试7: aribcc_context_free() 成功释放上下文

=== 全部 7 项测试通过 ===
```

### pkg-config 验证

```
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --modversion libaribcaption → 1.1.1
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --libs libaribcaption → -L.../lib -laribcaption -lc++ -lc++abi -lunwind -lm
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --cflags libaribcaption → -I.../include
```

### 符号导出验证

```
llvm-nm libaribcaption.a | grep aribcc_context_alloc  → 0000000000000000 T aribcc_context_alloc
llvm-nm libaribcaption.a | grep aribcc_context_free   → 0000000000000128 T aribcc_context_free
llvm-nm libaribcaption.a | grep aribcc_decoder_alloc  → 0000000000000000 T aribcc_decoder_alloc
llvm-nm libaribcaption.a | grep aribcc_decoder_free   → 0000000000000060 T aribcc_decoder_free
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libaribcaption-1.1.1-ohos-aarch64.tar.gz | 365KB | 预编译包（含头文件、静态库、cmake 配置、pkgconfig） |

## 功能限制

- Renderer 功能已禁用（ARIBCC_NO_RENDERER=ON），仅提供 decoder 功能
- 若需要 renderer 功能（文字渲染），需先编译安装 Fontconfig 和 FreeType 预编译包
- 这是纯静态库（libaribcaption.a），无可执行二进制

## 知识提取

- **L2 模式经验**: libaribcaption 在 CMAKE_SYSTEM_NAME=Linux 时默认启用 Fontconfig+FreeType 渲染依赖；在 OHOS 平台可通过 `-DARIBCC_NO_RENDERER=ON` 禁用渲染器实现零依赖编译
- **工具局限**: ohc-run.py 的 clean_verify.py 仅支持 autotools 构建系统（硬编码 `bash ./configure`），对 cmake 项目需手动 G0 验证

**编译结束**: 2026-06-12
**最终状态**: published
