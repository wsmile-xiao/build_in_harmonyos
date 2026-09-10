# cowdancer 0.90 测试报告

## 上游测试清点（R51 三步法第 1 步）

上游 `make check` 注册用例清单（26 项）：

- **FAST_TESTS（6）**：test_cowbuilder test_cowbuilder_util test_file
  test_forkexec test_ilistcreate test_parameter
- **QEMUBUILDER 条件（2）**：test_qemuarch test_qemuipsanitize
  （configure host_os=linux 时启用，OHOS arm64 触发）
- **SLOW_TESTS（18）**：tests/000_test_basic.sh tests/001_test_symlink.sh
  tests/002_test_open.sh tests/003_test_fopen.sh tests/004_test_fopen64.sh
  tests/010_test_noilistfile.sh tests/012_test_chown.sh tests/013_test_chmod.sh
  tests/014_ilistdump_test.sh tests/015_test_ilistdelete.sh
  tests/017_tempfilecheck.sh tests/018_testcxx.sh
  tests/019_test_filename_with_space.sh tests/020_test_lchown.sh
  tests/021_test_open.sh tests/022_kernel_waitpid.sh
  tests/101_test_qemubuilder_dumpconfig.sh
  tests/102_test_cowbuilder_debbuildopts.sh

合计 **26 项**。另注册 `tests/016_memleakcheck` 仅进 `check_PROGRAMS`
（编译构建）但不在 SLOW_TESTS 运行列表（上游注释列为 fragile）；且该测试
依赖 glibc 专用 `mcheck.h`，musl 缺失 → 已从 check_PROGRAMS 移除（补丁 0001）。

## OHOS 实测运行（R51 第 2 步，本机 aarch64）

**结果：PASS 21 / SKIP 2 / FAIL 3（共 26）**

- PASS：test_cowbuilder_util test_forkexec test_ilistcreate test_parameter
  test_qemuarch test_qemuipsanitize tests/000 002 003 004 013 014 015 017 018 019 022
  101 102（19 shell/C 用例）
- PASS（经 TMPDIR 可移植补丁修复）：test_cowbuilder test_file
  （3 个 C 测试原硬编码 /tmp 模板，OHOS /tmp 只读 erofs；补丁 0026-0028 改为
  读取 $TMPDIR 环境变量，POSIX 可移植，fallback /tmp，语义不变）
- SKIP：tests/012(chown) tests/020(lchown)（权限判定分支跳过）

## 失败项根因（R51 第 3 步如实申报，余 3 项）

| 用例 | 根因 | 类别 |
|------|------|------|
| tests/001 / 021 | `cp -al` 对符号链接创建硬链接被 OHOS 文件系统拒绝（Operation not permitted），实测 tmpfs/HMDFS 均不允许对符号链接 link() | 平台限制（文件系统） |
| tests/010 | `/bin/dd` 为系统预编译二进制，OHOS 对其整体禁用 LD_PRELOAD 拦截（决定性对照实验：无条件拒绝所有 open 的中立拦截库 LD_PRELOAD 到 dd 完全无效、无打印、dd 正常成功；同库对用户程序实测拦截生效）。cowdancer 的 open/openat 拦截对经 PLT 调用的用户程序实测生效（wr_open_test 无 ILIST 时 openat 写返回 -1；000/002/003/004 等 COW 测试全部通过） | 平台限制（系统二进制 LD_PRELOAD 不可达） |

**结论**：剩余 3 项失败全部为平台级硬限制（文件系统禁止符号链接硬链接、
musl 对系统二进制的 LD_PRELOAD 不可达），无软件自身逻辑缺陷。
核心功能（COW 拦截、ilist 生成/转储、cow-shell）由通过用例 + test_package
自研断言完整覆盖。通过率 21/26（80.8%）。

## test_package 自研测试（新增，6 断言）

test_package/test.sh 实质调用被测包二进制：
1. cowdancer-ilistcreate 无参调用 → 打印用法 banner 且返回非 0
2. cowdancer-ilistcreate 端到端生成 .ilist（find 扫描 → dev/ino 清单）
3. cowdancer-ilistdump 回读 .ilist 非空、无 error
4. cow-shell 经 COWDANCER_ILISTFILE 驱动 COW 语义执行命令
（assertion_count: 6）

## conan-verify

**G0-G4 + L2/L4/L5 全部 PASS**（2026-09-08，profile ohos-aarch64）。
详见 reports/conan-verify-report.md。