# bifrost — OpenHarmony 编译档案

## 软件简介
Bifrost 是高度并行的彩色压缩 de Bruijn 图（CCDBG）构建与索引工具（C++，BSD-2-Clause），
由 Páll Melsted 与 Guillaume Holley 开发，用于基因组序列组装、k-mer 查询与图可视化导出。

## OHOS 适配要点
- CMake 构建（`add_subdirectory(src)`，产物：`Bifrost` CLI、`bifrost_static`、`bifrost_dynamic`）
- 上游默认 `COMPILATION_ARCH=native` + `ENABLE_AVX2=ON` 为 x86-64 取向，
  OHOS arm64 目标必须在 recipe 中显式置 `OFF`，否则工具链生成不支持的指令
- 必需依赖 zlib（`find_package(ZLIB REQUIRED)`），经 conan 制品仓提供（zlib/1.3.1）

## 参考资料
- [bifrost GitHub](https://github.com/pmelsted/bifrost)