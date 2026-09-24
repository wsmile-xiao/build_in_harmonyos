# byobu 6.13 编译笔记

## 编译信息
- 软件名称: byobu
- 版本: 6.13
- 构建系统: custom (纯 shell/Python 脚本项目，conan 配方手动处理 .in 模板)
- 编译时间: 2026-05-25（手工验证）/ 2026-08-06（conan 适配）

## 源码获取
- 来源: GitHub (dustinkirkland/byobu tag 6.13)
- conandata URL: https://github.com/dustinkirkland/byobu/archive/refs/tags/6.13.tar.gz
- sha256: 9690c629588e8f95d16b2461950d39934faaf8005dd2a283886d4e3bd6c86df6

## 历史手工验证流程（2026-05-25，非 conan 流程，仅作参考）

```bash
aclocal
automake --add-missing --copy
autoconf
./configure --prefix=$HOME/usr/local
make -j1
make install
```

**平台适配**（手工验证时）:
- 修复 config.status 中临时目录创建逻辑
- 将 `mktemp -d "./confXXXXXX"` 改为 `mktemp -d "$TMPDIR/confXXXXXX"`
- 原因: 鸿蒙平台当前目录可能无写权限

## Conan 适配流程（2026-08-06，当前配方实际做法）

conan 配方不运行 configure/make（避免修改 autotools 生成文件，R6）：
1. `source()`: 下载官方 tag 6.13 tarball
2. `build()`: `apply_conandata_patches()` 应用 E058 补丁；`rglob("*.in")` 遍历模板（跳过 debian/），
   将 `@prefix@` 替换为 `self.package_folder`，写出同名无后缀文件
3. `package()`: 拷贝 `usr/bin` → `bin/`、`usr/lib/byobu` → `lib/byobu`、
   `usr/share/{byobu,man,doc,sounds,dbus-1}` → `share/`、`etc` → `etc/`（排除 *.in/*.am/Makefile*）；
   重建 `byobu-screen`/`byobu-tmux` 相对符号链接（与上游设计一致，依赖 argv[0] 检测）
4. `package_info()`: bindirs/libdirs/resdirs + `BYOBU_PREFIX` 运行环境变量

## 平台适配问题

### E058: HOME 目录所有权检查
**现象**: byobu 检查 `[ ! -O "$HOME" ]` 失败，因为鸿蒙平台用户 UID 与 HOME 目录 owner UID 不匹配。

**原因**: 鸿蒙平台的多用户隔离机制，用户目录由 file_manager (UID 20001006) 创建，但实际用户 UID 为 20020088。

**解决方案**: 通过 `uname -s` 运行时检测 HarmonyOS 平台，跳过 HOME 目录所有权检查（补丁中禁用 `__OHOS__` 宏，遵循 R8 口径）：
```bash
if [ ! -O "$HOME" ] && [ "$(uname -s 2>/dev/null)" != "HarmonyOS" ]; then
```

**补丁**: 0001-usr-bin-byobu.in.patch

## 依赖说明
- 运行时依赖: tmux >= 1.5 或 screen（后端，需用户自备，未随 conan 包提供）
- 可选依赖: python-newt (配置界面), gsed

## 上游测试清点（R51）
- 上游 byobu 6.13 无测试套件：无 tests/ 目录；根/子目录 Makefile.am 均无 TESTS 或 check 目标
  （`make check` 仅为 automake 空默认目标；usr/share/byobu/tests 下仅 byobu-time-notifications 通知脚本，非测试）
- test_package 自有 18 项断言：脚本存在性/可执行性、E058 补丁存在性、col1 功能执行、
  库脚本/资源/符号链接/man page 存在性、BYOBU_PREFIX 运行环境

## 上游已知问题
- 上游 tag 6.13 源码内嵌 `VERSION=6.12`（usr/bin/byobu.in 第 21 行），`byobu --version` 输出
  "byobu version 6.12"。属上游发版疏漏，非适配问题，保持上游原样不改。

## 产物
- （历史手工验证产物: byobu-6.13-ohos-aarch64.tar.gz 468KB — 2026-05 手工阶段产物，未入库，非 conan 流程交付物）
- conan 交付: byobu/6.13 包（108 个文件：bin/ 脚本 + lib/byobu + share/{byobu,man,doc} + etc/byobu）

---
**编译结束**: 2026-05-25 21:52
**最终状态**: built

---
**编译结束**: 2026-08-06
**最终状态**: built (conan adapted)

---
**复验记录**: 2026-09-20（第 4 次尝试，接续修复模式）
- 本地 `conan create`（ohos-aarch64 profile）复验通过（exit 0），test_package 18 项断言全过
- 分支与远端 feat/byobu-6.13 一致，配方/补丁/测试无改动；此前 CI #50106 对配方态已通过，
  本次推送仅为刷新 PR head 的元数据提交（本条记录），并重新触发 CI 与 AI 检视闭环
