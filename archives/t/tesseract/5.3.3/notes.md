# tesseract 5.3.3 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-07-09
- 编译器: clang 15.0.4 / clang++
- Conan 版本: 2.29.1
- Python 版本: 3.12.9
- 状态: published

## Conan 配方构建

通过 `conan create` 驱动 CMake 构建，配方为 `conanfile.py`。

### 构建配置

```python
# conanfile.py generate() 关键配置
tc.variables["BUILD_TRAINING_TOOLS"] = False        # 禁用训练工具（依赖 pango/cairo）
tc.variables["GRAPHICS_DISABLED"] = True            # 禁用 ScrollView 图形界面
tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"  # 兼容旧版 cmake_minimum_required
```

### 依赖关系

| 依赖 | 版本 | Channel | 说明 |
|------|------|---------|------|
| leptonica | 1.87.0 | @ohpcd/stable | 唯一 Conan 依赖，传递依赖 zlib/1.3.1 |

### 构建命令

```bash
# 构建 leptonica @ohpcd/stable（tesseract 的依赖）
conan create archives/l/leptonica/1.87.0/ --user=ohpcd --channel=stable \
  -pr:b=default -pr:h=default --build=missing

# 构建 tesseract
conan create archives/t/tesseract/5.3.3/ --build=missing

# CI 验证
CI_PACKAGES="archives/t/tesseract/5.3.3" zsh ci/conan/build_and_test.sh
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SIMD 检测链接错误 | aarch64 平台代码 `#if defined(__aarch64__)` 无条件启用 NEON，但 HAVE_NEON 未定义导致 NEON 函数（如 DotProductNEON）链接失败 | 应用 0001-simddetect.patch，将条件改为 `#if defined(HAVE_NEON) && defined(__aarch64__)` |
| 2 | 训练工具编译失败 | 训练工具依赖 pango/cairo，鸿蒙平台无此依赖 | cmake 配置 `BUILD_TRAINING_TOOLS=False` 禁用 |
| 3 | ScrollView 图形界面编译失败 | 无头构建环境无图形库支持 | cmake 配置 `GRAPHICS_DISABLED=True` 禁用 |

## 源码修改

### 0001-simddetect.patch

修复 aarch64 平台 NEON SIMD 检测逻辑，修改 `src/arch/simddetect.cpp`：

- **修改1**: `#if defined(__aarch64__)` → `#if defined(HAVE_NEON) && defined(__aarch64__)`
  - 确保 NEON 代码路径只在 HAVE_NEON 宏定义时启用
  - 添加 fallback 分支：`__aarch64__` 但无 HAVE_NEON 时 `neon_available_ = false`

- **修改2**: `#if defined(HAVE_NEON) || defined(__aarch64__)` → `#if defined(HAVE_NEON) && defined(__aarch64__)`
  - DotProduct 和 SIMD 初始化中的 NEON 条件统一改为 AND 逻辑

- **修改3**: 在非 NEON 平台的 else 分支添加 `neon_available_ = false` 声明
  - 确保所有代码路径中 neon_available_ 都有定义

## CI 验证结果（2026-07-09，Python 3.12.9 + Conan 2.29.1）

| 门禁 | 结果 | 详情 |
|------|------|------|
| L0 | PASS | L0i warn (leptonica 未发布到制品仓，非阻塞)，L0j ok (首次发布)，L0k warn (commands.json 误报) |
| L1 | PASS | test_tesseract Passed, `tesseract version: 5.3.3` |
| L1e | PASS | 破坏性反向验证 — 移除 bin/lib/include 后测试失败，确认真实依赖 |
| L2 | PASS | `tesseract --version` OK |
| L4 | PASS | 补丁安全扫描通过 |
| L5 | PASS | bin/ 有内容 |

## 交付物

| 文件 | 说明 |
|------|------|
| libtesseract.a | 静态库（OCR 引擎核心） |
| tesseract | 可执行文件（命令行 OCR 工具） |
| tesseract.pc | pkg-config 文件 |
| TesseractConfig.cmake | cmake 配置文件 |
| tesseract/*.h | 头文件（12 个） |
| tessdata/configs/ | 识别配置文件 |

## 注意事项

1. **构建系统**: 使用 cmake 构建，源码自带 CMakeLists.txt
2. **混合类型**: 既有库（libtesseract）又有可执行文件（tesseract binary），需 commands.json (R38)
3. **SIMD 补丁**: aarch64 平台必须应用 0001-simddetect.patch，否则链接失败
4. **依赖**: leptonica/1.87.0@ohpcd/stable 是硬依赖，通过 Conan 管理
5. **可选依赖**: 训练工具依赖已禁用，不影响核心 OCR 功能
6. **词典数据**: tessdata 需单独获取，不在 Conan 包中

---

**编译结束**: 2026-07-09
**最终状态**: published
**Conan 引用**: `tesseract/5.3.3`
