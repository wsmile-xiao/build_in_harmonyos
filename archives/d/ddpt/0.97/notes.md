# ddpt 0.97 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure，无需 autoreconf 自举）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（OHOS SDK llvm）
- 状态: built

## 编译步骤

探索阶段（设备真机，R1 探索模式）：

```bash
cd ~/builds/ddpt-0.97.work
# 1. E007/E072: config.guess/config.sub 打 OHOS 补丁
perl ~/qzy/GLM-9-ddpt-0.97/scripts/patch-autotools-ohos.pl config.guess config.sub
# 2. E122: config.sub 的 kernel-os 校验分支补 linux-ohos*（自动脚本未覆盖，见问题 2）
sed -i 's/linux-uclibc\* )/linux-uclibc* | linux-ohos* )/' config.sub
# 3. E011: configure 的 umask 077 → umask 022（HMDFS 临时目录权限）
sed -i 's/umask 077/umask 022/g' configure
# 4. 显式三元组 configure + make
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos --prefix=$HOME/tmp/ddpt-explore
make -j1
src/ddpt -V          # → version: 0.97 20210421 [svn: r388]
```

配方固化（conan create 路径）：三个补丁经 `refresh-patch --auto` 固化为 patches/000{1,2,3}（strip:1），
build() 用 AutotoolsToolchain + 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `unable to guess system type`（config.guess 临时 dummy.c 写不进 TMPDIR） | HMDFS 权限组合 + 老 config.guess（2020-11-19）无 HarmonyOS 分支 | patch-autotools-ohos.pl（E007），配方中以显式三元组绕过 guess |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | patch-autotools-ohos.pl 未覆盖 config.sub 的 kernel-os 校验分支（本版结构为 `case $kernel-$os in`，E122） | 在 linux-uclibc* 分支补 `| linux-ohos*`（E122），固化为 0002 补丁的一部分 |
| 3 | `config.status: can't create ./confXXXX/subs1.awk: Permission denied` | configure 以 umask 077 创建临时目录，HMDFS UID 映射（目录属主 20001006 vs 进程 uid 20020083）导致不可写（E011） | configure 内 umask 077 → umask 022（E011 受控方案，保留真实临时目录创建），固化为 0003 补丁 |
| 4 | conan create 内 configure 报 `working directory cannot be determined`（bash shell-init getcwd EPERM 连环报错），同一目录手动执行同一命令则正常 | ohos-aarch64 profile buildenv 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`，autoconf 按 CONFIG_SHELL 重执行 configure；hnp bash 的 getcwd() 在 HMDFS 上被拒（EPERM），autoconf 取 cwd 失败即中止（知识库同域条目 E386：getcwd/CONFIG_SHELL/HMDFS） | configure 命令前 `unset CONFIG_SHELL`，让 configure 在 /bin/sh 下运行（E386 的"能力测试合格 shell"思路在 conan 环境的等价落地）；CC/CFLAGS/LDFLAGS 仍由 AutotoolsToolchain env 提供 |

## 源码修改（补丁清单）

| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-config.guess.patch | 新增 `*:HarmonyOS:*` uname 分支，GUESS 输出 `-unknown-linux-ohos` | portability（E007） |
| 0002-config.sub.patch | ohos-linux basic_os 映射 + OS 白名单 `ohos*` + kernel-os 白名单 `linux-ohos*` | portability（E072+E122） |
| 0003-configure.patch | 2 处 `umask 077` → `umask 022` | portability（E011） |

三个补丁均不含平台宏（`__OHOS__` 等，PF5 合规）。

## 上游测试清点（R51）

- 上游无自动化测试套件：顶层 Makefile.am 仅有 `SUBDIRS = src doc` 与 distclean-local，无 check/test 目标，
  无 deja-gnu/ctest/autotest 注册；N_static = 0（如实申报）。
- `testing/` 目录为 2 个手动脚本（prepare.sh、test_sgl.sh）+ 8 个 .jf 作业/数据文件：
  依赖真实 Linux SCSI/ram 块设备（/dev/sg*、/dev/ram*、/dev/sd*）且写入 /tmp（OHOS 只读，E002），
  OHOS 环境不可执行，未执行数 2（环境限制，如实申报）。
- 消费者测试：test_ddpt.c（1 个程序，N_consumer=1）驱动安装后的 ddpt 二进制：
  ① `-V` 版本横幅（含 0.97、退出码 0）；② 常规文件→文件拷贝（确定性伪随机 100000 字节，bs=4096，
  断言退出码 0 + 输出字节一致 + 大小不变）；③ `/dev/zero` count=2 拷贝（断言 8192 字节全零）；
  ④ 坏输入文件（断言非零退出码 + unable to access 提示）。共 10 项断言。
  四条路径均已在设备真机探索阶段实证。

## 依赖版本

无第三方依赖（仅 libc）。

## 验证结果

conan-verify（2026-09-11 设备真机，8 道门禁全过，报告 `reports/conan-verify-report.md`）：
- G2 conan create 成功（日志 `reports/conan-create.log`）。
- test_package 实际执行，10/10 断言通过（日志同上，`PASS: ... × 10` + `all ddpt behaviour checks passed`）：
  1. `ddpt -V` 退出 0 且版本横幅含 0.97；
  2. 常规文件对拷（100000 字节确定性输入，bs=4096）退出 0、大小一致、逐字节相同；
  3. `/dev/zero` bs=4096 count=2 退出 0、恰 8192 全零字节；
  4. 缺失输入文件非零退出（rc=15）且提示 `unable to access`。
- 测试账本：N_static=0（上游无自动化测试套件，如实申报）；testing/ 手动脚本 2 个未执行（环境限制）；
  N_consumer=1（test_ddpt 程序），N_assertion=10（括注）。
- finish/W3 本地 CI 模拟 100% 通过（`reports/w3-local-ci.log`），conandata.yml 官方 URL 还原确认。

## 路径 A/B 判断（§6.2，2026-09-11）

**结论：纯路径 A，不走路径 B。** 判断依据：

1. **证据门槛核对**：三个补丁均为知识库既有条目（E007/E072/E122/E011）在本包的直接应用；第 4 个问题（CONFIG_SHELL→hnp bash getcwd EPERM）被 conan-verify 引擎命中既有条目 E386（同域：getcwd/CONFIG_SHELL/HMDFS），本包按其"能力测试合格 shell"思路以 unset 落地，无新错误签名、无"已穷尽方案的部分适配分析"。
2. **拟沉淀知识主题核对**：E122 的"patch-autotools-ohos.pl 未覆盖 kernel-os 分支"缺口在本包实证，已回填版本级 manifest 的 knowledge_gained 供知识库核对，但 E122 条目本身已存在（本包是其实例化验证，非新知识增量）。
3. **知识库查重结论**：conan-verify G0/知识引擎按既有 E 条目（含 E386 命中）解决全部四个问题，本次无新增草稿。
4. **真实验证证据**：设备真机 10/10 消费者断言通过（见下），仅支撑路径 A 交付。

## 注意事项

- 安装产物为 bin/ 下 3 个程序（ddpt、ddptctl、ddpt_sgl）+ 3 个 man 页；cpp_info.bindirs=["bin"]。
- testing/ 脚本与 .jf 文件不参与构建（不在 SUBDIRS 中），不进入安装产物。
