# ytnef

`ytnef` 是 Yerase's TNEF Stream Reader：解码 Microsoft Outlook / Exchange 的
TNEF（Transport Neutral Encapsulation Format，俗称 `winmail.dat`）流，提取附件、
联系人卡片与日历项。上游同时提供 `libytnef` 解码库与 `ytnef` / `ytnefprint` /
`ytnefprocess` 命令行工具。

## OHOS 适配

- **构建系统**: autotools（上游 tag 快照为 git-archive，不含 `configure`，用 `autoreconf -fi` 引导）
- **依赖**: 无第三方库（仅 libc + libtool）
- **tool_requires**: `automake/1.18`、`libtool/2.5.4`
- **平台适配**: 补齐 `config.guess` 的 HarmonyOS 分支（E007，不使用 `--build/--host`）、
  处理 HMDFS 下 `umask 077 && mktemp -d` 目录不可写（E114）、`make -j1`（E074）
- **产物**: `lib/libytnef.a`、`lib/pkgconfig/libytnef.pc`、6 个头文件、`bin/{ytnef,ytnefprint,ytnefprocess}`
- **上游测试**: `test-data/test.sh` 8 组断言全部通过，并已集成进 `conanfile.py` 的 `build()`

## Versions

| Version | Status | 说明 |
| --- | --- | --- |
| 2.1.2 | published | 首次适配（上游 tag v2.1.2，commit d9f089144414d3b0912c29ab96f8f1c591d00319） |

## 命令行工具

| 工具 | 说明 |
| --- | --- |
| `ytnef` | 解析 TNEF 流并按需提取附件 / 正文（RTF、HTML） |
| `ytnefprint` | 打印 TNEF 流中的 MAPI 属性 |
| `ytnefprocess` | 上游 perl 脚本，从邮件中抽取 TNEF 部分（依赖 CPAN 模块，本仓库不执行） |

Homepage: https://github.com/Yeraze/ytnef
