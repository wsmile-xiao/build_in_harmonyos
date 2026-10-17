# cddlib-tools 0.94m 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. `./configure --prefix=/storage/Users/currentUser/usr/local`（CC=clang, CFLAGS=-O2）
2. `make -j1`
3. `make install DESTDIR=<test-install>`
4. `make check`（上游无实际测试目标，RC=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 cannot guess build type | config.guess(2020) 无 HarmonyOS/__OHOS__ 检测分支 | scripts/patch-autotools-ohos.pl 打补丁（config.guess 2 处 + config.sub 2 处） |
| 2 | config.sub 报 Kernel 'linux' not known to work with OS 'ohos' | config.sub kernel-os 白名单缺 linux-ohos*-（补丁脚本误判已存在而跳过第 3 处） | 手动在 `case $kernel-$os-$obj` 的 linux-mlibc*- 后追加 `| linux-ohos*- )` |
| 3 | config.status 报 can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS 上 umask 077 创建的临时目录对当前进程不可写（E011） | perl -pi 's/umask 077/umask 022/g' configure config.status |
| 4 | /tmp 只读且已满 | /tmp 为只读文件系统 | 全程 TMPDIR=$HOME/tmp |
| 5 | W3 junk_check full 模式拦其他库历史 junk | 分支相对 origin/main 无提交 diff 时回退 full 模式扫全仓 | 生成 pr.diff 使 junk_check 走 prdiff 模式（CI 同款），W3 100% 通过后删除恢复 |

## 源码修改

补丁（3 个）：
- 0001-config.guess.patch：更新至 2023-08-22 版 + HarmonyOS 识别（LIBC 检测 + 系统 case 分支）
- 0002-config.sub.patch：ohos-linux triplet + OS 白名单 ohos* + kernel-os 白名单 linux-ohos*-
- 0003-configure.patch：umask 077→022（2 处，HMDFS 临时目录兼容）

## 依赖版本

无外部依赖（GMP 可选，本包未启用 GMP 变体工具）。

## 验证结果

```bash
# 真实计算断言：6 维超立方体 H→V 变换 = 64 顶点
cddexec --rep < cube6.ine   # V-representation 64 7 real
# W3 本地 CI 模拟
zsh ci/conan/build_and_test.sh archives/c/cddlib-tools/0.94m
#   1/1, pass rate 100% (L0/L1/L5 PASS)
# conan-verify 8 道门禁
python3 scripts/ohc-run.py conan-verify cddlib-tools 0.94m
#   G1/G0/G2/G3/G4/L2/L4/L5 全 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 类型，14 个 bin 工具 + libcdd/libcddgmp） |
| conandata.yml | 官方 GitHub release URL + sha256 + 3 个补丁声明 |
| test_package/conanfile.py | 消费者测试：cddexec --rep 断言 64 顶点 |
| commands.json | 命令行工具集声明（R38） |

## 注意事项

- 本包为工具集（application），同时随包装入 libcdd/libcddgmp（工具运行时依赖）
- 上游 make check 无实际测试目标，测试以 test_package 真实计算断言 + W3 本地 CI 模拟为准
- conandata.yml 的 sources.url 必须保持官方 GitHub URL（build_and_test.sh 预下载改写本地路径后需还原，R39）
---

**编译结束**: 2026-09-06 20:18
**最终状态**: published
