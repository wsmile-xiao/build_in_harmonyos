# stuntman 1.2.16 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，非 autotools）
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载发布版本源码包: `https://www.stunprotocol.org/stunserver-1.2.16.tgz`
2. 修改 `common.inc` 添加 LDFLAGS（绕过 lld/libxml2 问题）
3. `make -j1`（编译静态库 + 二进制）
4. 手动安装到 DESTDIR: `cp stunserver stunclient stuntestcode $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
5. 手动安装 man pages 和文档
6. 运行测试: `./stuntestcode` — 全部 PASS
7. ELF 签名并验证二进制运行
8. `ohc-run.py package` 制作预编译包
9. `make install`（不带 DESTDIR）到 DEFAULT_PREFIX
10. 用户验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 链接器无法执行（需要 libxml2.so.16） | OHOS SDK 的 lld 二进制依赖 libxml2.so.16，系统中不可用 | 使用 GNU ld (/data/service/hnp/bin/ld) 替代，添加 `-fuse-ld=/data/service/hnp/bin/ld` 到 LDFLAGS |
| 2 | GNU ld 找不到 -lcrypto | GNU ld 默认不搜索 ~/usr/local/lib | 添加 `-L/storage/Users/currentUser/usr/local/lib` 到 LDFLAGS |
| 3 | 没有 make install 目标 | 自定义 Makefile 项目没有标准 install 目标 | 手动安装二进制、man pages 和文档 |
| 4 | HMDFS 文件系统不允许执行新文件 | OHOS ELF 签名机制要求二进制签名后才能执行 | 使用 `ohc-run.py sign-elf` 签名后运行 |

## 源码修改

- `common.inc`: 添加 `LDFLAGS := -fuse-ld=/data/service/hnp/bin/ld -L/storage/Users/currentUser/usr/local/lib`
- 补丁文件: `0001-common.inc.patch`（+4/-1 行）

## 依赖版本

- openssl/1.1.1w（预编译包，提供 libcrypto.so）

## 验证结果

```bash
# 测试
./stuntestcode
Result of CTestDataStream: PASS
Result of CTestReader: PASS
Result of CTestBuilder: PASS
Result of CTestIntegrity: PASS
Result of CTestMessageHandler: PASS
Result of CTestCmdLineParser: PASS
Result of CTestClientLogic: PASS
Result of CTestRecvFromEx(IPV4): PASS
Result of CTestRecvFromEx(IPV6): PASS
Result of CTestFastHash: PASS
Result of CTestPolling: PASS
Result of CTestAtomicHelpers: PASS
Result of CTestRateLimiter: PASS

# 用户验证
$DEFAULT_PREFIX/bin/stunserver --help → 正常输出帮助信息
$DEFAULT_PREFIX/bin/stunclient --help → 正常输出帮助信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| stuntman-1.2.16-ohos-aarch64.tar.gz | 3396KB | 预编译包（3个二进制+man pages+文档） |
| stuntman-1.2.16-ohos-aarch64-debug.tar.gz | 838KB | 调试符号包 |

## 注意事项

- stuntman 使用自定义 Makefile，没有 configure 和 install 目标
- lld 链接器在 OHOS 上不可用（依赖 libxml2.so.16），必须使用 GNU ld 作为替代
- 二进制需要 ELF 签名才能在 HMDFS 上执行
- stunserver/stunclient 没有 --version 选项，只有 --help
---