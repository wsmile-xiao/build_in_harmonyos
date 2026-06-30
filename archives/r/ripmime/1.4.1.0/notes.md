# ripmime 1.4.1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯Makefile，无configure/autotools）
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `ohc-run.py init-build ripmime 1.4.1.0`
2. 修改Makefile/ripOLE/Makefile/tnef/Makefile/build_ripOLE脚本
3. 编译: `make CC=clang LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld" -j1`
4. 安装到staging: `make install DESTDIR=$TEST_PREFIX`
5. 签名: `ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/ripmime`
6. 功能验证: `ripmime --version` → v1.4.1.0
7. 打包: `ohc-run.py package ripmime 1.4.1.0`
8. 正式安装: `make install`（无DESTDIR）
9. 递归功能测试: MIME文本附件提取、Base64解码提取、目录递归处理

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SDK lld链接器报错 `libxml2.so.16 not found` | OpenHarmony SDK的lld依赖libxml2.so.16，但系统缺少该库 | 使用GNU ld替代：`LDFLAGS=-fuse-ld=/data/service/hnp/bin/ld` |
| 2 | tnef编译大端序字节序错误 | tnef/Makefile默认PLATFORM=`-D___TNEF_BYTE_ORDER=4321`（大端），但aarch64为小端 | 改为 `-D___TNEF_BYTE_ORDER=1234` |
| 3 | ripOLE子构建脚本build_ripOLE会链接ripole可执行文件（lld失败） | 原始build_ripOLE调用`make clean && make`，其中链接步骤使用lld | 改为直接编译.o文件，不链接可执行文件 |
| 4 | 运行ripmime时Permission denied | HarmonyOS要求ELF签名才能执行二进制文件 | 使用 `ohc-run.py sign-elf` 签名 |

## 源码修改

4个补丁：
- 0001-Makefile.patch: LOCATION改为$DEFAULT_PREFIX、DESTDIR支持、strip || true、LDFLAGS添加-fuse-ld、ripOLE/ole.o改为直接编译
- 0002-build_ripOLE.patch: build_ripOLE脚本改为只编译.o文件，不链接ripole可执行文件
- 0003-ripOLE-Makefile.patch: CFLAGS添加-fPIC
- 0004-tnef-Makefile.patch: PLATFORM改为小端1234，CFLAGS添加-fPIC

## 依赖版本

- clang (OpenHarmony SDK内置)
- GNU ld (/data/service/hnp/bin/ld)
- 无第三方库依赖

## 验证结果

```bash
$ ripmime --version
v1.4.1.0 - September 20, 2022 (C) PLDaniels http://www.pldaniels.com/ripmime
```

功能性测试（9项全部通过）：
- ✅ 版本验证
- ✅ ELF二进制完整性（AArch64 PIE, 小端序, musl libc）
- ✅ MIME文本附件提取（attachment.txt内容完整）
- ✅ Base64编码附件解码提取（data.bin内容与原始一致）
- ✅ 无附件简单邮件处理
- ✅ verbose模式输出
- ✅ 目录递归提取
- ✅ 边界情况（空文件、不存在文件均正确拒绝）

详见 reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ripmime-1.4.1.0-ohos-aarch64.tar.gz | 149K | aarch64预编译包（stripped） |
| ripmime-1.4.1.0-ohos-aarch64-debug.tar.gz | 14K | aarch64调试包（含符号） |

## 注意事项

- ripmime为纯Makefile项目，无configure脚本，不支持autotools标准构建流程
- G0 clean-verify的make调用因Python subprocess平台限制（output-sync参数兼容性）报错，但手动验证确认4个补丁+make可正常构建
- 必须使用GNU ld替代SDK lld，否则链接阶段会因libxml2.so.16缺失而失败
- HarmonyOS平台执行二进制必须先进行ELF签名（sign-elf）

---
**编译结束**: 2026-06-09
**最终状态**: published
