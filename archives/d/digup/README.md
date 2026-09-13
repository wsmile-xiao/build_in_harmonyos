# digup

digup 是一个命令行工具，用来**读取、校验并更新 md5sum / shasum 摘要文件**。
它读取目录中已有的摘要文件，重新扫描目录树，把文件的 new / changed /
renamed / deleted 状态汇总出来，确认后写回摘要文件；摘要文件本身用 CRC32
校验，格式与 coreutils 的 `md5sum` 等工具兼容。

## 功能

- 支持 MD5、SHA1、SHA256、SHA512 四种摘要算法，摘要文件带 CRC32 尾部校验。
- 默认按修改时间只重算“被触碰过”的文件，`--check` 可强制全量校验。
- 支持 `--restrict=PAT` 限定扫描范围、`--exclude-marker=FILE` 跳过目录、
  `--modify-window=NUM`（FAT 等文件系统的 mtime 窗口）、`--links` 处理符号链接。
- 批量模式：`-b` 非交互、`-u` 自动写回，适合 crontab 例行校验。
- 文件表使用自带的内侵式红黑树，可在大规模目录上快速工作。

## HarmonyOS 适配

- 上游 release tarball 自带 `configure` / `Makefile.in`，按标准 autotools 流程构建，
  不引入 automake/libtool 自举依赖。
- 设备 `uname -s` 返回 `HarmonyOS`，上游 2020-01-01 版 `config.guess` /
  `config.sub` 不认识该系统；三个可移植性补丁让两个脚本认识
  `aarch64-unknown-linux-ohos` 原生三元组，并修掉 HMDFS 上 `umask 077`
  造成的 `config.status` 临时目录不可写问题。
- `config.guess` 与 `config.sub` 必须成对补齐：只补 `config.guess` 时 configure
  不会报错，但三元组会被静默规范化成 `aarch64-unknown-linux-gnu-ohos`
  （自检命令 `config.sub "$(config.guess)"` 必须原样返回）。
- 配方不改写 `AutotoolsToolchain.configure_args`：本仓库 CI 用同一 profile 传给
  `-pr:h`/`-pr:b`，`cross_building()` 为 False，Conan 不注入三元组，configure 会
  自行调用打了补丁的 `config.guess`；异构 profile 下保留注入并由补丁 `0002`
  接受 Conan 的 `aarch64-linux-ohos` 形态，避免剪枝导致在构建机上误判平台。
- 上游 `make check` 的三条测试程序在设备上全部通过。

## 依赖

无外部依赖：摘要算法、CRC32 与红黑树都在上游源码内实现，只需要 C 库。

## 参考

- https://panthema.net/2009/digup/
- https://github.com/bingmann/digup
