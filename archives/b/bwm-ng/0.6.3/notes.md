# bwm-ng 0.6.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.in + Makefile.am）
- 编译日期: 2026-08-21
- 编译器: clang
- 状态: built

## 编译步骤

1. 下载 GitHub tag `v0.6.3` 源码包（sha256 见 conandata.yml）
2. 将 `configure.in` 复制为 `configure.ac`（autoreconf ≥ 2.70 不接受 `.in`）
3. `tool_requires`：automake/1.18、libtool/2.5.4（设备仅有 autoconf）
4. `autoreconf -v -i -f`
5. E007：对生成的 `config.guess`/`config.sub` 打 HarmonyOS 识别补丁（不传 `--build`/`--host`）
6. E114：将生成 `configure` 中的 `umask 077` 改为 `umask 022`
7. `./configure --prefix=/ --without-curses --without-ncurses --with-proc-netdev`，并加 `-static`
8. `make`；`make check`（上游无 TESTS，automake 默认 no-op）
9. `make install` 打包 `bin/bwm-ng`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | GNU config.guess 无 HarmonyOS 分支（E007） | autoreconf 后补丁 config.guess/sub，禁止 `--build`/`--host`（R15） |
| 2 | autoreconf 找不到 aclocal/automake | 系统仅有 autoconf（E178） | `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")` |
| 3 | config.status 写临时目录 Permission denied | umask 077 + HMDFS UID remap（E114） | 生成 configure 中 `umask 077` → `umask 022` |
| 4 | 上游无测试套件 | 无 `tests/`、无 `TESTS=` | `build()` 仍调用 `make check`；`test_package/` 补 6 条消费者断言 |

## 源码修改

无静态补丁文件（`patches_applied: []`）。config.guess/sub 在 autoreconf 之后由配方运行时修补（源码包不含这两份脚本）。

## 依赖版本

无外部 Conan 依赖。curses/ncurses 已禁用。

## 验证结果

```bash
# test_package/test.sh：6 条断言
bwm-ng --version
bwm-ng --help
bwm-ng -o plain -d 1 -c 1
bwm-ng -o csv -d 1 -c 1
readelf -h bwm-ng   # Type: EXEC 或 DYN
readelf -d bwm-ng   # 无 NEEDED（静态链接）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/bwm-ng | 静态链接 CLI |
| share/man/man1/bwm-ng.1 | man 手册 |
| commands.json | R38 命令行工具声明 |

## 注意事项

- 本包是 CLI 工具，`package_type=application`，必须有软件级 `commands.json`（L0k / R38）。
- OHOS 可能无可用网卡统计；plain/csv 采样允许空输出或退出码 1/2。
- 构建工具走制品仓 `automake/1.18`、`libtool/2.5.4`，不硬编码 `/storage/Users/currentUser/...`。
