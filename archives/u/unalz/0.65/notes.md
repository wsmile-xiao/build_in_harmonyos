# unalz 0.65 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure，无测试套件）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（conan conf `tools.build:compiler_executables` 注入，make 命令行变量覆盖）
- 状态: built

## 源码来源说明

官方源站 `www.kipple.pe.kr` 不可达（HTTPS 无响应、HTTP 403 WAF、设备侧 DNS 假解析
198.18.0.0/15 保留网段），采用 `deb.debian.org` 的 pristine orig tarball
（`unalz_0.65.orig.tar.gz`，Debian 未重打包），与仓库既有 140+ 先例一致
（如 `archives/a/a52dec/0.7.4`）。sha256 实测
`4c26699eb7545072de2ef7de79b4fff1f01c4db09cebff2d8d50ec03d5d74db0`。

## 编译步骤

```bash
# 上游 Makefile 目标之一：linux-utf8 = -D_UNALZ_ICONV -D_UNALZ_UTF8，不带 -liconv
# （OHOS musl 内置 iconv，支持 CP949/EUC-KR 别名，实测探针通过）
make -j1 linux-utf8 CC=clang CXX=clang++ CPP=clang++
```

- `CC` 编译捆绑的 zlib/bzip2 子集（.c），`CPP`（上游把 C++ 编译器命名为 CPP）
  编译 UnAlz.cpp/UnAlzUtils.cpp/main.cpp 并链接。
- 捆绑子集：zlib（adler32/crc32/infback/inffast/inflate/inftrees/zutil，无 deflate）
  与 bzip2（blocksort/compress/crctable/huffman/randtable + UnAlzbzlib.c 改造版），
  故包无外部 requirements。
- 上游 `make install` 硬编码 `cp unalz /usr/local/bin/`（R49 禁注入共享前缀），
  配方 `package()` 手工 `copy()` 到 `bin/`，不调用上游 install 目标。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方源站不可达 | kipple.pe.kr 失效（2026-09 实测 403/DNS 假解析） | Debian pristine orig tarball + sha256 实测 |
| 2 | CLI 无 --version/--help，L2 冒烟无法应答 | 2009 年代码仅无参打印横幅 | 补丁 0001 加 -v/--version 与 -h/--help（aa3d 先例） |
| 3 | 错误路径恒 return 0 | 上游设计：打印错误文本继续跑 | test_package 断言打输出文本而非退出码 |
| 4 | Makefile 硬编码 gcc/g++ | conan 环境变量被文件内赋值覆盖 | make 命令行变量优先级高于文件内赋值 |

## 源码修改

- `patches/0001-UnAlz.cpp.patch`：`CRC32()` 里 `get_crc_table()` 返回值强转
  `const unsigned long *`——OHOS SDK sysroot 的现代 zlib 头把返回类型声明为
  `const z_crc_t *`（unsigned int 表项），而实际链接的是捆绑 zlib 1.2.3 实现
  （LP64 上 unsigned long 表项），不改索引语义、只消编译期类型冲突。
- `patches/0002-main.cpp.patch`：main.cpp 参数循环在 `-l`
  分支前插入 `-v/--version`（打印 Copyright 横幅后退出 0）与 `-h/--help`（打印
  Usage 后退出 0）。命名从 refresh-patch 的 `NNNN-<源文件名>.patch` 惯例
  （aa3d 先例）。两补丁上下文均避开 EUC-KR 非字节安全区域，行保持 CRLF。

## 依赖版本

无外部依赖（zlib/bzip2 为源码内捆绑子集）。

## 验证结果

```bash
# conan create（采信轮）+ test_package 9 用例/28 断言
# 详细数字见 reports/ 与 PR 正文（由最终设备日志复算）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/unalz | 待构建后填写 | ALZ 解压 CLI（静态链接捆绑 zlib/bzip2 子集，musl iconv） |

## 注意事项

- 上游错误路径恒 return 0（missing file/corrupt file 均打印后退出 0）——自动化
  断言勿用退出码判错。
- ALZ 夹具在 test_package 运行时用 python3 生成（无归档入库）；布局：
  `ALZ\x01` 全局头 → `BLZ\x01` 本地头（fileDescriptor 0x40=4 字节长度字段，
  压缩方法 0=stored，CRC32 由 zlib.crc32 计算，解压路径强校验）→ `CLZ\x01`
  中央目录（12B）→ `CLZ\x02` 结尾。
- EUC-KR 文件名转换依赖 musl iconv 的 CP949 别名（探针实测 ok）。
---

**编译结束**: 2026-09-21 13:06
**最终状态**: built
