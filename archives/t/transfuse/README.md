# transfuse

## 是什么

transfuse 把带嵌套内联格式的文档（HTML / HTML-fragment / ODT / DOCX / PPTX / TXT）
送进转换或翻译流程：先把内联格式抽成可处理的 span，把纯文本流交给转换处理器
（`apertium` 或 `visl`），再把转换后的流注回原文档并恢复原有格式。

## 功能概述

- `transfuse extract`：抽取模式，输出带 `[tf-block:N-<hash>]` 块标记与
  `[[t:b:...]]` 内联标记的可翻译文本流
- `transfuse inject` / `transfuse clean`：回注 / 清洗模式，把转换后的流写回文档
- `tf-extract` / `tf-inject` / `tf-clean`：上游为上面三个模式创建的别名
- 支持的转换处理器：`apertium`（`-s apertium`）、`visl`（`-s visl`）

## OHOS 适配

- 交叉编译目标 `aarch64-linux-ohos`，`package_type = "application"`，静态链接
  （R26），产物为单个 `transfuse` 可执行文件加三个别名
- 上游用 `pkg_search_module()` 找 libxml2 与 sqlite3、用 `find_package(ICU)` 找
  ICU、用 `find_*` 找 libzip 与 xxhash；配方侧生成 `PkgConfigDeps` 的 .pc 文件，
  并通过 CMake 适配钩子补回 CMake 拆分出去的 `-L` 搜索路径、补回 ICU 数据归档
- OHOS profile 的 `compiler.cppstd=17` 会覆盖上游探测到的 C++20，配方通过
  `CMAKE_PROJECT_INCLUDE` 钩子纠正（详见版本级 `notes.md`）
- `libzip` 依赖 `arc4random`/`arc4random_buf`；OHOS libc 提供这两个符号，
  musl 1.2 之前的运行时没有（详见版本级 `notes.md` 的已知限制）

## 依赖关系

编译依赖（均为制品仓已发布包）：

- icu/76.1
- libxml2/2.15.3.1
- libzip/1.11.4
- sqlite3/3.53.4
- xxhash/0.8.4

运行依赖：OHOS libc（musl）。

## 参考资料

- 上游仓库：https://github.com/TinoDidriksen/transfuse
- 发布页：https://github.com/TinoDidriksen/transfuse/releases/tag/v0.7.6