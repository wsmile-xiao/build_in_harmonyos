# libisofs 1.5.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 (aarch64, HarmonyOS)
- 状态: built

## 编译步骤

```bash
# 官方源核验
# URL: https://files.libburnia-project.org/releases/libisofs-1.5.6.tar.gz
# sha256: 0152d66a9d340b659fe9c880eb9190f3570fb477ac07cf52e8bcd134a1d30d70
# 上游版本: configure.ac AC_INIT([libisofs], [1.5.6]) — 与任务版本一致

# configure（需 --build/--host 显式三元组；config.sub 需补 OHOS 支持）
# 修补 config.sub: linux-ohos* 加入内核-OS 组合与有效 OS 列表
./configure --prefix=$DEFAULT_PREFIX --build=aarch64-linux-ohos --host=aarch64-linux-ohos

make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 2012 版无法识别 HarmonyOS，configure 报 cannot guess build type | 上游 config.guess 过旧，无 HarmonyOS 分支 | 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`，绕过 config.guess 猜测 |
| 2 | config.sub 不识别 aarch64-linux-ohos | config.sub 无 ohos 系统条目 | patches 中在 config.sub 的 KERNEL-OS 组合列表与有效 OS 列表各加 `linux-ohos*`（POSIX 兼容方式，R8 允许 config.sub 修改） |
| 3 | config.status 报 can't create ./confXXXXXX/subs1.awk: Permission denied | config.status 用 `umask 077` 建临时目录为 owner-only(2700)，本机进程 uid 非目录 owner，组内成员无写权限（HMDFS） | patches 中 configure 的临时目录创建 `umask 077` 改为 `umask 002`，目录组可写 |
| 4 | make 触发 aclocal-1.14 重建 aclocal.m4 失败 | 恢复 configure.ac 后时间戳变新，automake 版本缺失 | touch aclocal.m4/configure 等生成文件，跳过 autotools 重生成（生成文件不作为补丁内容） |

## 上游测试申报表（R51 三步法）

1. **清点**：上游 tarball 无 `test/`、`tests/` 目录；`Makefile.am` 中单元测试（`check_PROGRAMS = test/test` 等）被上游注释禁用（ticket 147: "The test code does not use the API"）；无 ctest/pytest 注册；`make check` 无注册目标（Nothing to be done for 'check'）。
2. **实测**：`make check` 实际运行，exit 0（无测试目标，无失败项）。
3. **结论**：上游未提供可运行测试；以 demo 编译链接成功 + 后续 conan test_package 作为适配验证。

## 源码修改

- `config.sub`：加 `linux-ohos*` 支持（两处：maybe_os 组合列表、有效 OS 列表）
- `configure`：临时目录创建 umask 077 → 002（HMDFS 组写兼容）

## 依赖版本

- zlib: 系统提供（zlib.h + libz 已探测，configure 检测 compressBound in -lz 通过）
- libjte: 未安装（configure 探测 no，禁用对应功能）
- libacl: 未安装（禁用 ACL 本地处理，非必需）
- xattr: 系统支持（sys/xattr.h + listxattr in -lc，启用 Linux style xattr）

## 验证结果

```bash
# configure exit 0，生成 Makefile/version.h/libisofs-1.pc
# make exit 0（libisofs 库 + demo 链接成功，仅 4 个上游 -Wstrict-prototypes 警告）
# make install DESTDIR exit 0（staging 隔离：include/lib/pkgconfig 已安装）
# make check exit 0（上游无注册测试目标）
```

## 注意事项

- 本库为纯库（libisofs.so/.a + 头文件），无命令行工具产物，不需要 commands.json（R38）
- 构建需显式 --build/--host 三元组，conanfile.py 的 settings 判断需兼容 OHOS（R32）
- demo/ 仅为示例程序，不作为交付产物
---

**编译结束**: 2026-09-07 01:31
**最终状态**: built
