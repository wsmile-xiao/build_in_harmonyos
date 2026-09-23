# Overdrive

Overdrive 是一个单文件 Bash 命令行工具，用于处理图书馆借出的 OverDrive `.odm`
借阅文件：向 OverDrive 服务申请 license（按官方 OverDrive Media Console 的
`SHA-1(ClientID|OMC|OS|"ELOSNOC*AIDEM*EVIRDREVO")` 规则生成 Hash），下载无 DRM 的
MP3 分段与封面，并可解析/打印书籍元数据。

- 上游：<https://github.com/chbrown/overdrive>（MIT，作者 Christopher Brown）
- 上游命令：`overdrive {download|return|info|metadata} book.odm [...]`
  选项 `-h|--help`、`--version`、`-v|--verbose`、`--insecure`、`-o|--output DIR_FORMAT`

## 本仓库适配（OHOS aarch64）

| 版本 | 形态 | 说明 |
|---|---|---|
| 2.4.1 | `overdrive/2.4.1`（application，零 conan requires） | 打包动作等价 Homebrew core 的 `bin.install "overdrive.sh" => "overdrive"`，无源码修改、无补丁 |

运行时依赖为 PATH 上的可执行文件（上游 `overdrive.sh:87` 的 PREREQ 清单）：
`curl`、`uuidgen`、`xmllint`、`iconv`、`openssl`、`base64`，
外加 `bash`（`#!/usr/bin/env bash`）与 `sed/awk/tr/seq/cat/head/mkdir/rm`。
OHOS 上前者由 `/usr/bin`（toybox 0.8.12 / curl / openssl）提供，
`bash` 与 `xmllint` 由 `/data/service/hnp/bin` 提供，已在设备与 CI worker 的系统 PATH
及 Conan profile buildenv 中，因此无需引入 conan 依赖链。

## 验证摘要（2.4.1）

- 上游自动化测试：**无**（发布归档仅 `README.md` + `overdrive.sh`，无 Makefile/configure/tests/.github）
- 上游唯一可执行测试入口（Homebrew `test do` 声明）：
  `overdrive download fake_file.odm` → `Specified media file does not exist`，rc=2 —— 源码目录、
  staging 前缀、安装包三处实跑一致
- `test_package/test_overdrive.py`：11 用例，11 通过 / 0 失败 / 0 跳过
- `conan create`（profile `ohos-aarch64`）rc=0，产物 `bin/overdrive`(0755) + `share/doc/overdrive/README.md`

## 已知上游行为（与平台无关）

- 书名含 `&` 时 `info` 会输出 `-amp-`：`xmllint --xpath '//Title/text()'` 重新转义 `&amp;`
  后再被 `tr` 替换，Linux 上表现相同。
- `download`/`return` 需访问 OverDrive 在线服务；离线只能验证 ENOENT、`info`、`metadata`
  与许可证哈希管线。

详见 `2.4.1/notes.md` 与 `2.4.1/reports/test-report.md`。
