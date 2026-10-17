# vbrfix (vbrfixc)

命令行 MP3 VBR 头修复工具：扫描 MP3 文件，剔除无法识别的数据并重建一个正确的
VBR 头（Xing/Info），从而修正错误的比特率、时长与 seek 信息。

## 功能

- 重建 MP3 的 VBR 头（Xing/Info），使时长/比特率/seek 信息正确
- 识别并处理既有 Xing 头，保留 LAME 扩展信息（`-lameinfo`）
- 可选移除 ID3v1 / ID3v2 标签（`-ri1` / `-ri2`），或原样保留并写回输出
- 支持强制写出（`-allways`）与强制生成 VBR 头（`-makevbr`）

## 命令行

```
vbrfixc [-flags] input.mp3 output.mp3

-flags:
  -ri1        remove Id3v1 tag
  -ri2        remove Id3v2 tag
  -skiplame   if tag made by lame don't fix it
  -allways    always write even if not vbr
  -makevbr    make it vbr (need -allways also)
  -log        write a log file
  -lameinfo   keep the lame info
```

## 安装

```bash
conan install --requires=vbrfix/0.24 -r=ohpcd
# 产物：<package>/bin/vbrfixc
```

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 编译依赖 | 无（仅 C++ 标准库 + autotools/libtool） |
| 运行依赖 | 无（动态链接 OHOS 系统 musl 运行时） |

## OHOS 适配要点

- 上游 `admin/config.guess` / `admin/config.sub` 为 2002 年版，不认识 HarmonyOS 与
  aarch64 / `-linux-ohos`，需补丁补齐三元组识别（补丁 0001、0002）
- `configure` 自建临时目录用 `(umask 077 && mktemp -d)`，HMDFS 上目录权限落为
  `drwx--S---` 导致自身不可写，需改 `umask 022`（补丁 0003，知识库 E011）
- clang 15 + libc++ 下两处老式 C++ 写法不可编译：隐式 `ostream → bool`、非标准类型
  `uint`（补丁 0004、0005）
- 上游 tarball 内含 32 位 x86 预编译二进制 `vbrfixc/vbrfixc`（Debian 已用 `+dfsg`
  重打包剔除）；构建时被 `make` 覆盖，不参与打包

## 测试

- 上游 0.24 无自动化测试（无 `tests/` 目录、`Makefile.am` 无 `TESTS` 声明），
  `make check` 为空套件；无上游样例数据。
- 消费者侧测试见 `0.24/test_package/test_vbrfixc.sh`：9 项用例，其中 1 项为
  鸿蒙平台专有（产物 AArch64 ELF 目标 + 本机可执行性）。

## 参考资料

- 上游源码（Debian 官方镜像）：https://salsa.debian.org/debian/vbrfix
- 原始上游主页（已失效）：http://www.willwap.co.uk/Programs/vbrfix.php
- 许可证：GPL-2.0-or-later
