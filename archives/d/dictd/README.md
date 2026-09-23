# dictd 1.13.3

DICT 协议（RFC 2229）服务器 `dictd`，以及客户端与工具集：`dict`（客户端）、
`dictzip`/`dictunzip`（dictzip 压缩格式）、`dictfmt`（词典格式化）、
`dictunformat`、`dictl`、`colorit`、`dictfmt_index2word`、`dictfmt_index2suffix`。

- 上游：https://www.dict.org/ （发布渠道：SourceForge 项目 `dict`）
- License：GPL-2.0-or-later（`parse.c` 另有 LGPL-2.0-or-later 授权）
- 构建系统：autotools（tarball 自带 configure，无需 autoreconf；构建期需 flex/bison/awk）
- 包类型：application（全部产物为可执行文件）

## OHOS 移植要点

1. `patches/0001-config.guess.patch`、`patches/0002-config.sub.patch`：
   让 2021 版 config.guess/config.sub 识别 `HarmonyOS`/`linux-ohos`（dialog 同款全仓通用模式）。
2. libmaa 依赖：仓内无 libmaa Conan recipe，经批准在本 recipe 内 vendored 静态构建
   libmaa 1.4.7（官方 SourceForge 归档，SHA256 固定于 conandata.yml）。dictd 仅使用
   `maa_init`/`maa_shutdown` 两个符号。构建细节见 notes.md。
3. zlib 通过 Conan 依赖（zlib/1.3.2，静态链接）。
4. 上游测试：`make test`（`test/dictd_test` + `test/dictzip_test`），在 build() 内执行；
   test_package 另做无 socket 冒烟（版本输出、dictzip 往返、dictfmt+dictd 管道协议应答）。
