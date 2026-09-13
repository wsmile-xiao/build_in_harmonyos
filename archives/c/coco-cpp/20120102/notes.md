# coco-cpp 20120102 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile 仅一行 `g++ *.cpp -o Coco`，g++ 硬编码）
- 编译日期: 2026-09-08
- 编译器: clang++（profile tools.build:compiler_executables 提供）
- 状态: built

## 编译步骤

```bash
clang++ Action.cpp ArrayList.cpp …（全部 *.cpp） -o Coco
```

与上游 `make all`/`build.sh` 语义一致，仅 g++ 换为 profile 的 clang++（Makefile 将
g++ 写死在规则内，命令行变量无法覆盖，故 conanfile build() 直接调用编译器）。

## 源码 URL 决策（重要）

- 上游官方站 `https://ssw.jku.at/Research/Projects/Coco/CPP/CocoSourcesCPP.zip`
  经 `openssl s_client -showcerts` 实测只下发 leaf 证书（Let's Encrypt YE2 中间证书
  不在链内），设备 curl/Python 均报 unable to get local issuer certificate，
  conan source() 与同构 CI 均无法下载。
- 且 JKU 当前 zip 与 20120102 快照存在 4 文件差异（Coco.cpp/Scanner.cpp/Scanner.frame/
  Scanner.h，逐文件 md5 比对），不能充当任务版本源。
- 故采用 Ubuntu 官方归档的 pristine 上游包
  `https://archive.ubuntu.com/ubuntu/pool/universe/c/coco-cpp/coco-cpp_20120102.orig.tar.gz`
  （.orig 即未打 Debian 补丁的上游原始源码；其 sha256 与 Debian dsc 声明的
  67c85f19... 完全一致；PF7 黑名单仅含 deb.debian.org 等 4 域，不含 archive.ubuntu.com）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 探索运行 `./Coco Coco.atg` 覆盖了源码树自带的 Parser.cpp/Scanner.cpp 等 4 文件 | Coco 默认把生成物写到 CWD（即源码根） | 已从 pristine 提取恢复 4 文件；消费者测试改在临时目录运行 |

## 上游测试清点（R51）

- 上游无自动化测试套件：Makefile 仅 all/clean/install，build.sh/coc.sh 为编译脚本，
  无 check/test 目标，无测试目录；上游静态用例数 N_static = 0。
- 消费者测试（test_package）：内嵌最小属性文法 Sample.atg（含 CHARACTERS/TOKENS/
  PRODUCTIONS），运行打包后的 cococpp 生成 Scanner.cpp/Parser.cpp，断言两文件生成且
  内容正确（扫描器含 Scanner 类、解析器含文法名 Sample），conan test() 1/1 passed。
- 补充实测（探索构建）：对上游自带 Coco.atg（Coco/R 自身文法，自举）运行
  `./Coco Coco.atg` → "parser + scanner generated, 0 errors detected"，RC=0。

## 注意事项

- frame 文件（Scanner.frame/Parser.frame/Copyright.frame）是生成期的运行时输入，
  已打包到 res/；Coco 按文法文件所在目录查找 frame，消费者测试将 frame 复制到临时目录。
- 二进制按上游 install 惯例命名 cococpp（上游 Makefile install 段用 /usr/bin/cococpp 符号
  链接指向 Coco；HMDFS 符号链接受限，直接以单一可执行交付）。

## 编译结束

- 最终状态: built（conan-verify 全过、W3 本地 CI 通过、W4 审计 P0=0 P1=0）
- 结束标记: 2026-09-09
---

**编译结束**: 2026-09-09 02:24
**最终状态**: built
