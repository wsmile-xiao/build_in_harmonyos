# sqlite3 OpenHarmony 编译记录

该目录包含 SQLite 3.49.1（历史已发布版本）和本次新增的 3.53.4 适配。
3.53.4 从官方 `sqlite-autoconf-3530400.tar.gz` 构建，提供静态 C 库、
`sqlite3` 命令行工具及手册，避免覆盖平台可能提供的同名库。

OHOS HMDFS 上不调用 autosetup 的 jimsh0 生成器；配方直接编译官方
amalgamation，并从 Conan 工具闭包解析目标 clang 与 llvm-ar。
