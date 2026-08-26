# notes.md — dialog 1.3-20240307

## 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools |
| 状态 | built |
| 编译日期 | 2026-08-24 |

## 编译步骤

1. 下载源码: `wget https://invisible-mirror.net/archives/dialog/dialog-1.3-20240307.tgz`
2. 应用补丁: config.guess (HarmonyOS 检测) + config.sub (linux-ohos 模式)
3. 配置: `./configure --prefix=/ --disable-shared --enable-static --with-ncurses --with-curses-dir=<ncurses_pkg>`
4. 编译: `make -j1`
5. 测试: `make check` (5 个 rc 回归测试全部通过)
6. 安装: `make DESTDIR=<stage> install-full`

## 依赖

- ncurses/6.6 (Conan 制品仓已发布)

## 关键适配点

1. **config.guess**: 添加 `aarch64:HarmonyOS` 检测分支，映射为 `aarch64-unknown-linux-gnu`
   (OHOS 在 API 层面兼容 Linux，使用 linux-gnu triplet 即可通过 configure)
2. **config.sub**: 添加 `linux-ohos*-` 到 OS 识别模式
3. **ncurses 库链接**: dialog 的 configure 查找 `-lncurses`，但 ncurses 包提供 `libncursesw.a`
   (wide-char)。创建符号链接 `libncurses.a -> libncursesw.a` 解决链接问题
4. **headers-sh 失败**: dialog 的 install-full 通过 headers-sh 脚本安装头文件，
   但该脚本在 HMDFS 上创建临时文件失败。改为手动复制头文件到 include 目录
5. **TMPDIR**: configure/config.status 需要可写临时目录，HMDFS 的 /tmp 只读，
   使用 `/data/storage/el2/base/.conan-build-dialog-*` 作为 TMPDIR
6. **CONFIG_SHELL**: 使用 `/data/service/hnp/bin/bash` 作为 CONFIG_SHELL

## 验证

- `dialog --version` → Version: 1.3-20240307
- `make check` → 5/5 rc 测试通过
- conan create + test_package → PASS

## 最终状态
status: closed
COMPLETED
