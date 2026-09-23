# libgd2 2.3.3 OpenHarmony PC 适配说明

## 范围

- 路径 A（基础适配）：上游 libgd 2.3.3（https://github.com/libgd/libgd）的核心内存图像 C API。
- 本配方以 conan 包名 `libgd2` 发布，与仓库既有 `gd` / `libgd` 配方指向同一上游、互不干扰，供独立评审。
- 构建系统：CMake；默认静态库（`libgd.a`），`shared=True` 可切动态。
- 零外部依赖：PNG/JPEG/TIFF/WebP/AVIF/HEIF/XPM/Freetype/Fontconfig/Raqm/LIQ/Iconv/C++ API/GD_FORMATS 全部关闭，
  因此 `requires` 为空，不存在依赖链断裂风险。
- 不打包 CLI helper（`GD_PROGRAMS` 已清空、`bdftogd` 安装已移除，首轮均未经验证）与 docs。

## 上游测试盘点（源码审计，2026-09-19）

审计对象：官方 `libgd-2.3.3.tar.gz`（sha256 已校验 `dd3f1f0b…b1ed2`），`tests/` 共 77 个 `CMakeLists.txt`：

- 无条件测试条目 81 个，其中 2 个引用缺失源码（`tests/gdimagecopyrotated` 的 `bug00320.c`、
  `tests/gif` 的 `bug00415.c`），另有 `tests/CMakeLists.txt` 的 `TESTS_DIRS` 列出不存在的 `gdmatrix/` 目录
  （会导致 configure 直接失败）。配方在 `source()` 中仅注释这 3 行列表项，不改任何上游测试源码。
  修复后可运行 **79 个 ctest 用例**，且已逐个确认其余 79 个的 `.c` 均不含可选编解码头（`png.h`/`jpeglib.h`/`tiffio.h` 等），
  可在全关闭配置下编译。
- 条件测试条目 138 个，需要 PNG/JPEG/TIFF/WebP/AVIF/HEIF/XPM/freetype/fontconfig 等可选栈，首轮关闭故不运行。
- `examples/` 16 个 `.c` 为示例程序（非 ctest 用例，部分需要已关闭的编解码栈），`docs/` 需要文档工具链；
  两个子目录在配置前禁用，不参与构建。

## 关键适配点

1. **静态测试目标重定向**：纯静态构建只生成 `gd_static`（`OUTPUT_NAME` 为 `gd`，产出 `libgd.a`），
   而 `tests/gdtest` 的辅助库链接未定义的共享目标名 `${GD_LIB}`。配方在该标记后追加条件块，
   把 `GD_LIB` 指向已存在的 `gd_static`，保留 CMake 依赖边。实现带存在性校验：上游改动导致标记消失时直接抛错，
   要求重新审计，而不是静默跳过。
2. **工具链映射**：不手动覆盖 `CMAKE_SYSTEM_NAME`，依赖 OHOS 适配版 Conan 按
   `ci/conan/profiles/ohos-aarch64` 注释自动映射（`os=OHOS` → `aarch64-linux-ohos` / `HarmonyOS`）。
3. **上游测试常开**：`BUILD_TEST=ON` 写死在配方中；`build()` 末尾在 `can_run` 为真时执行
   `ctest --output-on-failure`。CI 交叉构建只编译测试程序，不执行。
4. **机器证据防造假**：
   - 逐行解析 ctest 的 `Test #N:` 结果行分别计数 Passed/Failed/Skipped，不只看退出码；
   - 与 `N% tests passed, M tests failed out of K` 汇总行交叉核对，不一致记 warning 并以逐行计数为准；
   - 发现数低于 10 直接抛错（审计预期约 79），杜绝空跑报通过；
   - 通过才输出 `HMBS_UPSTREAM_TEST_RESULT`，失败先输出标记再抛异常，日志里永远留数；
   - 同一 JSON 落盘 `build_folder/hmbs_upstream.json` 并随包发布到 `res/`，`test_package` 在缓存命中时也能复发标记。

## 真机执行

```bash
conan create archives/l/libgd2/2.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

- 预期：`ctest` 发现约 79 项；`test_package` 的 `test_libgd2` 输出 6 行 `CHECK-OK`（含 GIF 魔数与非空断言）。
- 若设备对未签名二进制拒绝执行（`ctest` 报 exec 失败），下一轮在运行前加自签名流程（`test_package` 已有签名实现可复用），
  不要把失败改成跳过。
- test_package 的 GIF 编解码断言只覆盖内置格式；PNG 等需可选栈的能力闭环留待后续版本。

## 与既有配方的差异

- `archives/g/gd/2.3.3.2`：上游测试靠 `with_upstream_tests` 选项（默认关），本配方常开并带解析与落盘；
  其 source 裁剪在 `build()` 中做且重定向块不可重入，本配方移到 `source()` 并加幂等 guard。
- `archives/l/libgd/2.3.3`：autotools 路线且 requires zlib/libpng，本配方 CMake 路线零依赖；其上游测试标注 N/A，
  本配方在真机完整执行 79 项。
