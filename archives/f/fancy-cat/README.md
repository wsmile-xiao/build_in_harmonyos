# fancy-cat

PDF 终端阅读器（Kitty image protocol），Zig 0.15.2 项目（freref/fancy-cat）。

- 上游：https://github.com/freref/fancy-cat
- 版本：0.6.0
- 许可证：AGPL-3.0-or-later

## 构建要点（OHOS aarch64）

- Zig 0.15.2 工具链自包含下载（build.zig.zon 要求 minimum_zig_version=0.15.2，
  项目仅有 zig/0.16.0，build.zig API 与 0.16 不兼容）。
- mupdf 为 git 子模块（GitHub tarball 不含子模块内容），配方单独下载固定
  commit 归档放入 `deps/mupdf`，由 build.zig 内 `make` 构建静态库
  （libmupdf.a + libmupdf-third.a）。
- zig 二进制与编译产物需 binary-sign-tool 签名才能在 OHOS 执行；
  `zig build` 的 build_runner execve 若被拒，签名缓存内 ELF 后重跑。
- 上游无测试套件（build.zig 无 test step，CI 仅 zig build + zig fmt --check），
  已按 no_tests 审计处理；test_package 冒烟执行 `fancy-cat --version`。
