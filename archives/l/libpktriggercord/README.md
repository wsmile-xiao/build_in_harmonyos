# libpktriggercord

pkTriggerCord（https://github.com/asalamon74/pktriggercord）的库本体：Pentax 单反相机
遥控 / tethering 库 `pslr`，通过 SCSI-generic（`/dev/sg*` + `ioctl(SG_IO)`）与相机
通信，读取状态与设置、触发拍照并从相机缓冲取图。

## 上游特征

- 构建系统：裸 `Makefile`（无 configure / CMake / meson）
- 上游不产出任何库文件：`cli` 与 `gui` 两个可执行目标直接把对象链接成程序
- 内嵌依赖：`src/external/js0n`（JSON 解析，树内 vendored）
- 无自动化测试（无 `tests/`、无 `test`/`check` 目标）；`.travis.yml` 唯一功能入口是
  `./pktriggercord-cli --version`

## 本包交付物

| 路径 | 说明 |
|------|------|
| `lib/libpktriggercord.so` | 由上游 `pslr*` 对象自建（117 个导出 `pslr_*` 符号，`NEEDED` 仅 `libc.so`） |
| `include/*.h` | 8 个公共头（`pslr.h` 为总入口） |
| `share/pktriggercord/pentax_settings.json` | 未知机型的运行期设置表（编译期以 `PKTDATADIR` 烤入路径） |
| `licenses/COPYING` | LGPL-3.0-or-later |

不含可执行文件：GUI 依赖已 EOL 的 GTK+ 2（制品仓无 gtk2），CLI 只在构建期承载上游冒烟测试。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.85.1-20221221181244 | built | 上游 commit `c1177a48`（`VERSION=0.85.01`） |
