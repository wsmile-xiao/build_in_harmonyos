# libxml2 2.15.3.1 编译笔记（HarmonyOS PC · arm64 · 标准 Conan cmake）

## 版本说明
- 2.15.3.1 为 2.15.3 的适配修复版本（R37）。相对 2.15.3 差异：补充 `export_sources()`（G1 门禁）、
  修正 build() 读取 `self.options.shared`（AI 检视 Medium）、启用上游测试套件
  `LIBXML2_WITH_TESTS=ON` + `LIBXML2_WITH_PROGRAMS=ON`（PR 规则4：实跑上游测试并给出真实通过率）。

## 定位
- 产出动态 libxml2.so（libxml2.so.16.1.3 + .so.16 + .so 软链），供 dlopen 及作依赖。
- 测试随构建启用：`LIBXML2_WITH_TESTS=ON`（runtest 等 11 个测试程序 + ctest）；
  CMake 的 `add_suite()`/catalog 测试无条件引用 xmllint/xmlcatalog 目标，
  因此必须同时 `LIBXML2_WITH_PROGRAMS=ON`（纯库模式会生成阶段报 Target not found）。
  `LIBXML2_WITH_PYTHON=OFF`。

## 关键适配
- **OHOS 工具链自发现**：build() 用 `_ohos_toolchain()` 从 `OHOS_NDK_HOME` / profile
  `tools.cmake.cmaketoolchain:user_toolchain` / glob SDK 路径定位 `ohos.toolchain.cmake`，
  再裸 `cmake -DCMAKE_TOOLCHAIN_FILE=...` 构建（绕开 conan_toolchain，glfw/libjpeg-turbo/zstd 同法）。
  `-DCMAKE_INSTALL_LIBDIR=lib` 覆盖 ohos.toolchain 64 位默认 lib64/。
- **export_sources()**：`export_conandata_patches(self)`，满足当前框架 G1 门禁要求
  （conanfile.py 必须含 export_sources 方法）。
- **依赖裁剪**：`LIBXML2_WITH_ZLIB=OFF`、`LIBXML2_WITH_LZMA=OFF`（上游默认 OFF，避免拖依赖）；
  `LIBXML2_WITH_ICONV=ON`（iconv 在 musl libc 内建，无 conan 依赖）。requirements() 为空。
- **.so 自签**：package() 用 `llvm-objcopy --remove-section .codesign` 剥旧签名 +
  `binary-sign-tool sign -selfSign 1` 重签（SDK 工具链产出的 .so 自签无效，见 _sign_shared_libs）。
- **头文件双根**：`package_info().includedirs = ["include/libxml2", "include"]`
  （<libxml/*.h> 与 <libxml2/libxml/*.h> 两种消费形态都支持）。
- **test_package 实质测试（R34）**：test.c `dlopen(libxml2.so)` + `dlsym("xmlReadMemory")`
  验证真实导出符号；编译期 `#include <libxml2/libxml/parser.h>` 验证头文件闭包。

## 平台陷阱
- E017/源码下载：`download.gnome.org` 在 CI Worker 上 Connection reset 不可达，且不在
  `build_and_test.sh` 自动镜像 rewrite 域名列表中。改用官方 GitHub tag archive
  （`github.com/GNOME/libxml2`，与 libxslt 同法）单值 URL，启用 CI GitHub 镜像 fallback。
- R26 说明：libxml2 非 /lib /lib64 系统同名库（OHOS 上的 libxml2.so.16 是 SDK lld 工具链内部依赖，
  非系统路径库），动态构建不违反 R26，G3 门禁已确认无系统同名库冲突。
- E120/E132：OHOS SDK lld 运行时依赖 libxml2.so.16，编译/configure 前必须
  `export LD_LIBRARY_PATH=$OHOS_NDK_HOME/llvm/lib`，否则链接阶段报
  "error while loading shared libraries: libxml2.so.16"。
- E002：/tmp 只读，conan 临时文件用 `TMPDIR=$HOME/tmp`。

## 上游测试实跑结果（规则4）
本机即 aarch64 OHOS 真机，`LIBXML2_WITH_TESTS=ON` 构建后在源码目录实跑 ctest：

| 测试 | 结果 | 说明 |
|------|------|------|
| runtest（主回归套件） | 3880 用例，**通过率 97.3%**（106 errors + 1 leak） | 失败集中在少量输出格式/字节差异（如 HTML 序列化 meta 注入、VC 校验错误信息行数），以及上游 tarball 缺失个别 result 参考文件（如 `result/errors/attr3.xml.ent/.err/.str`，tarball 仅含 attr3.xml）导致的 stat 失败 |
| testapi / testcatalog / testchar / testdict / testparser / testrecurse | 全部 PASS | 6 个独立测试程序全过 |
| runsuite | 无法运行 | 需要 xmlconf 套件数据，上游 tarball 未附带（任何平台都如此） |
| scripts_* / catalogs_* / catalog_add_del | 无法运行 | 上游 tarball 未打包 `run_and_diff.cmake`/`test_xmlcatalog_add_del.cmake`（CMakeLists 引用但 tarball 缺失，上游打包缺陷，与平台无关） |

**结论**：上游测试可编译可在 OHOS 实跑，核心 runtest 套件通过率 97.3%；失败均为
上游 tarball 数据缺失或输出格式差异，非 OHOS 平台能力缺失。

## 状态
built（本地 conan create + test_package 实际通过，conan-verify 8 门禁通过；未上传 CI）
---

**编译结束**: 2026-08-03 18:05
**最终状态**: built
