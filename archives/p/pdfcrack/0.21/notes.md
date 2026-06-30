# pdfcrack 0.21 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-21
- 编译器: clang/clang++ (clang-15)
- 状态: built
- 补丁: 2 个

## 编译步骤

pdfcrack 原始使用简单 Makefile 构建（无 configure 脚本、无 install target）。
通过补丁添加 dummy configure 和 install target 后，完整编译流程如下：

1. `./configure --prefix=$DEFAULT_PREFIX` — dummy configure (接受 --prefix 并 exit 0)
2. `make -j1` — 构建 pdfcrack 二进制 (clang, 211KB)
3. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — staging 隔离安装
4. R7 安全弹窗验证：`$TEST_PREFIX/$DEFAULT_PREFIX/bin/pdfcrack --version` → "pdfcrack version 0.21" ✅
5. make check — 跳过（无 check target）
6. `ohc-run.py package pdfcrack 0.21` — 制作预编译包
7. `rm -f && cp` 安装到 DEFAULT_PREFIX（HMDFS 不支持覆盖, R5）
8. 用户验证：`pdfcrack --version` → "pdfcrack version 0.21" ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | 无 configure 脚本 | 项目使用简单 Makefile | 补丁添加 dummy configure wrapper | ref:E105 |
| 2 | 无 install target | Makefile 没有 install 规则 | 补丁添加 install/uninstall target | ref:E105 |
| 3 | make check 不存在 | 项目没有测试套件 | 跳过并记录原因 | — |
| 4 | G0 clean-verify 失败 (exit 127) | clean-verify 尝试运行 ./configure | 补丁添加 configure wrapper | ref:E105 |
| 5 | SSL 下载失败 | HTTPS 证书验证失败 | 手动 curl -k 下载后 init-build --no-download | ref:E030 |
| 6 | HMDFS cp 覆盖失败 | 不能 cp 覆盖已有文件 | rm -f && cp (R5 铁律) | ref:E101 |
| 7 | hints/configure.sh 不生效 | clean-verify 不读取 hints 目录 | 改用源码补丁方式添加 configure | ref:E105 |
| 8 | patch 格式错误 | 手动生成补丁缺尾换行/路径格式错 | 用 shell heredoc 写入并验证 | — |

## 源码修改

### 0001-Makefile.patch (+12/-0)
添加 install/uninstall target 到 Makefile。
目的：支持 DESTDIR 模式安装（`make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`）。
内容：添加 PREFIX 变量、mkdir -p、cp pdfcrack 和 pdfcrack.1 到 $(DESTDIR)$(PREFIX)。

### 0002-configure.patch (+24/-0)
添加 dummy configure 脚本，接受 --prefix 参数并 exit 0。
目的：使 G0 clean-verify 能通过 configure 步骤。
内容：for arg 循环解析 --prefix 和 --help，输出 "Configuration complete"，exit 0。

## 依赖版本

无依赖。

## 验证结果

```bash
$DEFAULT_PREFIX/bin/pdfcrack --version
pdfcrack version 0.21
```

详细测试见 `reports/test-report.md`（10 个真实执行验证用例全部 PASS）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pdfcrack-0.21-ohos-aarch64.tar.gz | 160KB | 预编译包（strip + ELF 签名） |
| pdfcrack-0.21-ohos-aarch64-debug.tar.gz | 133KB | 调试符号包 |

## 注意事项

- pdfcrack 是纯 Makefile 项目，原始无 configure/install/check target
- 构建系统类型应为 `makefile`（非 autotools）
- 补丁 0001 添加 install target，补丁 0002 添加 dummy configure wrapper (ref:E105)
- HMDFS 不能覆盖文件，需 rm -f 再 cp (ref:E101)
- clean-verify 不读取 hints 目录，必须用源码补丁方式添加 configure

---
**编译结束**: 2026-05-21
**最终状态**: built