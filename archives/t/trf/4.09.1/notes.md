# trf 4.09.1 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag v4.09.1 自带 2020 年预生成 configure）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（OHOS aarch64 交叉，clang 15.0.4）
- 状态: built

## 编译步骤

1. `conan create` 驱动：`source()` 下载 GitHub tag v4.09.1 tarball（官方 URL，sha256 校验）。
2. `build()`：
   - 构建期正则移除 configure 中两处 `(umask 077 && …)` 临时目录包裹（E114，HMDFS setgid 目录导致 config.status 临时文件不可写）；
   - 聚合 env 脚本（generators_folder/**/*.sh）内 `/data/service/hnp/bin/bash` 文本替换为 `/bin/sh`（E386/经验汇总 §12.70①）；
   - `configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --prefix=<package_folder>`（2020 config.guess/sub 不识别 ohos triplet；显式 gnu 双 triplet 使 config.guess 探测不运行——本包 host 判定仅用于 TARGET_NAME=linux64 符号链接后缀，无功能影响）；
   - `make -j1`（上游无测试套件，无 make check 可执行）。
3. `package()`：`make install` → `bin/trf` + install-exec-hook 符号链接 `trf<上游版本串>.linux64.exe`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/sub（1992-2020）不识别 OHOS，`-linux-ohos` triplet 可能被 config.sub 拒绝 | 归档早于 ohos triplet 支持 | 显式传 `--build/--host=aarch64-unknown-linux-gnu`，configure 不运行 config.guess 探测（零依赖单文件程序，无自举需求） |
| 2 | configure 含 2 处 `umask 077` 临时目录包裹 | E114：HMDFS 强制 setgid | 构建期正则移除（toppred 1.10 同款通用修法） |
| 3 | 上游 tag 版本串不一致 | tag v4.09.1 的 configure.ac 自报 `4.10.0-rc.2` | 配方/conandata/任务版本统一 4.09.1（以平台任务版本为准）；install-hook 符号链接名内嵌上游串，仅命名差异 |

## 源码修改

无补丁文件（patches 为空）。仅构建期对生成物 configure 做 E114 替换（不进源码树 diff）。

## 依赖版本

无外部依赖（单 C 源文件 + 生成的 tr30dat.c 数据表，纯 libc）。

## 验证结果

### 上游测试五维账本（R51/§10.1 口径）

- `N_static` = 0：上游无自动化测试（Makefile.am 仅 `SUBDIRS=src` 与 `dist_doc_DATA`；无 TESTS/check_PROGRAMS/ctest；仓库内 test_seqs.fasta 与 test_seqs.txt 为手工样例输入与期望输出，非可执行套件）
- `N_registered` = 0
- `N_executed` = 0（如实申报；上游确无测试）
- 未执行 = 0
- `N_consumer` = 1（test_package/test.sh：对齐上游手工样例的端到端行为测试，断言 5 处）

```bash
# conan create 内真实执行 test_package：
# ALL CONSUMER TESTS PASSED（日志见 .ci_logs/）
```

### 消费者测试

test_package/test.sh（conanrun 环境）：打包后 `trf sample.fasta 2 7 7 80 10 50 500 -d`（默认参数 + `-d` 数据表，对齐上游 test_seqs 手工样例口径）
- 断言 1：trf 退出码非崩溃（<128；上游行为：退出码=处理序列条数，本样例双序列返回 2）
- 断言 2：`.dat` 数据表生成且非空
- 断言 3/4：两条样例重复模式 TCATCGG、ACCCCTCAGGGT 出现在数据表中
- 断言 5：s1 文本报告含 "Period size: 7" 重复表头

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/trf | ~200KB | 串联重复检测 CLI |
| bin/trf*.exe | 符号链接 | install-exec-hook 生成的版本别名 |

## 注意事项

- 上游无 make check 目标，N_static=0 属实申报；以消费者端到端测试补位（审查口径：0 执行不可交付的前提是 N_static>0）。
- commands.json（软件级）声明 trf 为 tool 类型。
---

**编译结束**: 2026-09-19 04:14
**最终状态**: built
