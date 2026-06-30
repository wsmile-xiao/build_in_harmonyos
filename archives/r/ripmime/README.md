# ripmime

从 MIME 编码的电子邮件中提取附件的工具。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.4.1.0 | published | makefile |

## 注意事项

- ripmime 使用纯 Makefile 构建系统（无 configure/autotools/cmake）
- OpenHarmony SDK 的 lld 链接器依赖 libxml2.so.16（系统缺失），需使用 GNU ld 替代（`-fuse-ld=/data/service/hnp/bin/ld`）
- HarmonyOS 平台要求二进制文件进行 ELF 签名后才可执行（`sign-elf`）
- aarch64 为小端序架构，tnef 子模块的 PLATFORM 需改为 `1234`（原默认 `4321` 为大端）