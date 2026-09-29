# libextractor

GNU libextractor 是一个通用元数据提取库：给定任意文件，它按插件（`src/plugins/*.c` →
`libextractor_<name>.so`）解析并输出该文件中可提取的元数据（EXIF、 Vorbis 注释、ZIP 条目、
ELF 头、PDF 文档信息、HTML 标题等），命令行入口为 `extract`。

- 上游：https://ftp.gnu.org/gnu/libextractor/ （主页 https://www.gnu.org/software/libextractor/）
- 许可证：GPL-3.0-or-later（插件含 LGPL 组件）
- 插件在运行期由 libltdl（GNU libtool）`dlopen`，因此本包**必须 shared 构建**，
  静态构建不产出可加载的插件。

## 已归档版本

| 版本 | 说明 |
|------|------|
| [1.13](1.13/notes.md) | HarmonyOS PC（aarch64）首次适配；上游 `make -C src check` **执行项 30/30** 通过（main 7/7 + plugins 23/23，0 失败 0 跳过；PASS 名单原文 `1.13/reports/w3-local-ci.log:1166-1172` 与 `:1317-1347`）。上游静态全集 `N_static=40`，未执行 10 项逐项原因见 `1.13/notes.md` 五维账本 |

## 平台适配要点（详见各版本 `notes.md`）

- `configure` 的临时目录 `umask 077` 在 HMDFS 上会让 `config.status` 建不出 `subs1.awk`（E011）。
- profile 的 `[buildenv]` 把 `SHELL/CONFIG_SHELL` 指向 hnp bash，configure re-exec 时
  `getcwd` 失败（E386），需路由到 `/bin/sh`。
- 设备无 texinfo：`doc/` 段 `makeinfo` 缺失，用构建期 fake `makeinfo` 跳过，测试只在
  `src/main` 与 `src/plugins` 两棵子树执行。
- 插件 `.so` 的依赖在 musl 上不受 `DT_RUNPATH` 驱动，需 `LD_LIBRARY_PATH` 指向依赖 libdir。
- 依赖 `-I/-L` 必须显式进 `CPPFLAGS/LDFLAGS`（本包未使用 `AutotoolsDeps`），否则
  configure 探不到 `ltdl.h`。

## 命令行工具

见 [commands.json](commands.json)（`extract`）。
