# libdng

Interface library between libtiff and the world to make sure the output is valid DNG (Adobe Digital Negative).

## 功能概述

- 按 DNG 1.4 规范生成 TIFF 文件（写 DNG、缩略图、 raw 数据 stride 支持）
- DCP 标定文件解析（color matrix / forward matrix / tone curve / HueSatMap）
- 基础 DNG 读取支持（供 `dngmerge` 工具合并标定数据）
- 附带 `makedng`（raw 转 DNG）与 `dumpdng`（抽取 raw tiff 数据）两个小工具

## OHOS 适配

- 构建系统选用上游 Meson（`meson.build` 为 0.2.2 主构建定义；`CMakeLists.txt` 仍停留在 0.1 版本号，已废弃不用）
- `man-pages` 特性固定 `disabled`：OHOS/CI 无 `scdoc`，避免 `dependency('scdoc')` 失败
- 唯一运行时依赖 `libtiff/4.7.2`，经 `PkgConfigDeps` 生成 `libtiff-4.pc` 供给 `dependency('libtiff-4')`
- `shared_library('dng', ...)` 改为 `library('dng', ...)`（构建期字符串替换，仅为让 `default_library` 控制静态/动态，不改源码逻辑），默认动态由 Conan 管理依赖链
- 上游 4 个 greatest 测试（`check_mode`/`check_dng`/`check_dcp`/`check_repack`，共 8 个 TEST）在 `build()` 经 `meson.test()` 完整运行；`dng_validate` 为可选外部程序，未找到时上游自动跳过
- 产物为 `libdng.so.1.2.0`（symlink `libdng.so.1`/`libdng.so`）+ 头文件 `libdng.h` + `makedng`/`dumpdng` 可执行文件；`.so` 按本仓惯例自签（工具缺失时告警跳过，不阻断打包）

## 依赖关系

- 编译依赖：`libtiff/4.7.2`
- 运行依赖：同上（`libtiff.so` 经 NEEDED 传递）

## 参考资料

- 上游仓库：https://gitlab.com/megapixels-org/libdng
- 文档：https://libdng.me.gapixels.me/
- 许可证：MIT
