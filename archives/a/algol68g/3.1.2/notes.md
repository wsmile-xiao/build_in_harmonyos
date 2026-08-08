# algol68g 3.1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. init-build（源码来自官方站 algol68genie.nl）
python3 scripts/ohc-run.py init-build algol68g 3.1.2 --url=https://algol68genie.nl/algol68g-3.1.2.tar.gz

# 2. 手动编译（探索阶段）
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check   # 24 个测试全部通过

# 3. 配方生成与验证
python3 scripts/ohc-run.py conan-init algol68g 3.1.2
python3 scripts/ohc-run.py conan-verify algol68g 3.1.2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess (2018-02-24) 无 HarmonyOS 检测分支，uname -s=HarmonyOS 无法匹配 | 升级 config.guess/config.sub 至 2023 版（含 aarch64-unknown-linux-ohos 三元组，E007） |
| 2 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | configure 用 `umask 077` 创建临时目录（0700），HMDFS 上 owner 映射为 20001006 而进程 uid=20020093 不可写；且 chmod 被 SELinux 限制（E046） | configure 两处 `umask 077` → `umask 002`（group 可写），已验证可行 |
| 3 | GSL 缺失警告 | configure 检测 gsl-config 未找到（可选依赖） | 非致命，GSL/MPFR/curses/PostgreSQL 均为可选特性，默认不启用 |

## 源码修改

| 补丁 | 内容 | 知识条目 |
|------|------|----------|
| 0001-config.guess.patch | config.guess 升级 2023 版 + HarmonyOS 检测 | E007 |
| 0002-config.sub.patch | config.sub 升级 2023 版 + linux-ohos 三元组 | E007 |
| 0003-configure.patch | 临时目录 umask 077→002 (HMDFS 平台限制) | E046 |

> 注：a68g-config.h 为 configure 生成文件（R6），不纳入补丁。

## 依赖版本

无第三方库依赖（纯 C 实现）。

## 验证结果

```bash
# 上游测试（make check）：24/24 通过
All 24 tests passed

# test_package（conan create L1 测试）
a68g --execute 'print((1+1))'  → 输出 +2 ✅

# conan-verify 门禁
G1-G4 全部 PASS，配方验证通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方 |
| patches/0001-0003 | 3 个 OHOS 适配补丁 |
| test_package/ | L1 实质测试（执行 a68g 验证） |
| packaging/algol68g-3.1.2-ohos-aarch64.tar.gz | release 打包产物 |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- algol68g 为命令行工具（a68g 可执行文件），`package_type=application`，`cpp_info.bindirs=["bin"]`，无库文件
- 编译时 `configure` 需 CONFIG_SHELL bash 包装执行（OHOS mksh 无法执行 ELF）
- 版本号 3.1.2 为上游首次适配，无后缀
---

**编译结束**: 2026-08-06 19:36
**最终状态**: published
