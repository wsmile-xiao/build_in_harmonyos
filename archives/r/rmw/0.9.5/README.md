# rmw 0.9.5 — 鸿蒙PC适配

命令行回收站/垃圾箱工具 rmw（ReMove to Waste）的 OpenHarmony PC (aarch64) Conan 配方。

- 上游：https://github.com/theimpossibleastronaut/rmw
- 语言：C（meson 构建，`package_type = "application"`）
- 产物：`bin/rmw` 可执行文件 + 文档；静态链入 ncursesw/menuw（conan 包）与
  vendored musl-fts 1.2.7（BSD-3-Clause），动态链 libcanfigger.so.0
- 依赖：canfigger/0.3.2、ncurses/6.6（均仓内已适配）
- 验证：conan create rc=0；test_package 端到端消费者用例 11/11 通过
  （版本/帮助/配置解析/移入 waste/trashinfo/恢复）

详见 `notes.md`（踩坑与解决方案）与 `manifest.yaml`（构建/测试元数据）。
