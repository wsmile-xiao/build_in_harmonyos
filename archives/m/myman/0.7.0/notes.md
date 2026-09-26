# myman 0.7.0 适配笔记

## 上游版本与来源

- 任务：myman/0.7.0（依赖活动任务 #6298，分支 `feat/myman-0.7.0`）。
- 上游：MyMan 0.7.0，作者 Benjamin C. Wiley Sittler；SourceForge 官方发布包。
- 源码地址：`https://sourceforge.net/projects/myman/files/myman/myman-0.7.0/myman-0.7.0.tar.gz/download`
- SHA-256：`31a94b2c8949a35d18eed35e8f685801fbfeb71418a3c01eafbf710ce95a292b`（与 SourceForge 文件页公布值一致）。
- 该归档的 `VERSION` 文件内容为 `0.7.0`，不是 0.7.1 的 2009-10-30 CVS 快照。

## 构建和依赖

- 上游构建系统：手写 `configure` 生成 GNUmakefile，再用 GNU Make 构建。
- 输出后端：ncursesw；依赖已发布的 `ncurses/6.6`。
- 0.7.0 的 Makefile 直接使用 `-lncursesw`，没有 0.7.1 所用的 `NCURSESW_CONFIG`。Conan 的 ncurses/6.6 将宽字符头文件放在 `include/curses.h`，而上游包含 `<ncursesw/curses.h>`；配方在非 HMDFS build tree 生成仅转包含 `<curses.h>` 的兼容头，并用 `EXTRACINCLUDES`/`CURSESLIBS` 注入依赖路径。
- 显式传入 `make install DESTDIR=...`，将程序、man page 与文档装入 stage。
- Makefile 默认将 maze、tile、sprite 数据编译进可执行文件。
- `configure`/`make` 在 `/data/storage/el2/base` 下构建，避开 HMDFS 执行位和目录权限问题；HarmonyOS 的 `install`、`rmdir`、`sed` 帮助自检由 wrapper 满足，实际操作交给 toybox。
- 打包阶段按 OHOS 要求为 `bin/myman` 加签，并恢复执行权限。

## 上游测试

上游包没有 `tests/` 或其他功能测试套件。Makefile 的 `check` 目标明确输出 `target check not implemented`，并以失败状态退出；它不是上游测试。MANIFEST 将上游用例数记为 0。消费者测试运行安装后的 `myman --version` 和 `myman --help`，覆盖 CLI 启动、版本输出和帮助输出。

## 验证结果

真机验证（HarmonyOS PC aarch64，2026-09-23）：

- `conan create archives/m/myman/0.7.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：`CREATE_EXIT:0`；解析并安装 `ncurses/6.6`。
- Conan `test_package` 在设备上实际执行 `myman --version` 与 `myman --help`，两项均退出 0；共 2/2 消费者测试通过。构建结束后再次直接运行两个命令，也均退出 0。
- 包内产物：`bin/myman`、`share/man/man6/myman.6` 与上游文本文档。ELF 为 arm64，包含 `.codesign`（OHOS 签名）及 `.note.ohos.ident`。
- 上游无测试套件；`make check` 是上游明示的未实现占位目标，因此不计为测试。生成 `.txt/.ps/.dvi/.html` 手册依赖的可选文档目标在设备上不可用，Makefile 将其标为 ignored；主程序、man6 手册、文本文档、Conan 打包及消费者测试均成功。
