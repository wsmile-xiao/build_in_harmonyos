# libsgutils 1.46 适配笔记

## 编译环境
- 构建系统: autotools (GNU Autoconf 2.70 + libtool)
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（ohos-aarch64 profile）
- 状态: built

## 编译步骤

```bash
# 1. 官方源码（github.com/hreinecke/sg3_utils tag v1.46，SHA-256
#    6e048db9b48f78a29ad17ee948897bd6c0d71257df515a95c63e376ad8aacce9）
# 2. autotools 鸿蒙补丁（E007 方案）
perl scripts/patch-autotools-ohos.pl config.guess config.sub
# 3. 临时目录 HMDFS 适配（config.guess/config.status/configure：
#    mktemp -d 0700 在 HMDFS 上创建进程不可写 → mkdir+chmod 2770）
# 4. configure
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
# 5. 上游测试（testing/ 目录）单独构建
cd testing && make
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess: cannot guess build type | config.guess 无 HarmonyOS 分支（E007） | patch-autotools-ohos.pl + config.sub 补 ohos-linux/linux-ohos* |
| 2 | config.guess/config.status/configure 报 can't create .../confXXXXXX/...: Permission denied | HMDFS 上 mktemp -d 创建的 0700 tmp 目录对创建进程（UID 错位）不可写（E011/E052） | 临时目录创建改 mkdir+chmod 2770 组可写 |
| 3 | sg_dd.c 等编译失败: struct drand48_data incomplete / mrand48_r undeclared | OHOS libc（musl 系）无 glibc 可重入随机函数族（DRAFT-libsgutils-1.46-ohos-missing-drand48-r） | 单线程降级 srand48/mrand48；多线程 per-rep xorshift64 |
| 4 | 链接失败: unable to find library -latomic | OHOS aarch64 无 libatomic.a（原子操作走 clang 内建指令） | testing/Makefile 移除 -latomic |
| 5 | W3 JC full 模式被其他库基线空状态文件（cloog .build-closed/.staging-verified）连坐 | 本库 pr.diff 为空时回退整仓扫描（E538/DRAFT-libpopcnt） | JUNK_PR_DIFF 限定 prdiff 只检本库 + 基线隔离审计（pre==post SHA-256） |

## 源码修改

- 0001-config.guess.patch: HarmonyOS 检测 + HMDFS tmpdir 组可写
- 0002-config.sub.patch: ohos-linux 三元组 + linux-ohos* 校验
- 0003-configure.patch: config.status tmpdir HMDFS 适配
- 0004-src-sg_dd.c.patch: drand48_r → srand48/mrand48
- 0005-testing-Makefile.patch: 移除 -latomic
- 0006-testing-sg_mrq_dd.cpp.patch: drand48_data → per-rep xorshift64
- 0007-testing-sgh_dd.cpp.patch: drand48_data → per-rep xorshift64

## 依赖版本

- 无运行时依赖（libsgutils2 纯系统 API：linux/nvme_ioctl.h、sys/random.h 等已按
  configure 检测启用）
- 工具链: clang 15.0.4 / GNU make 4.4.1 / autoconf 2.72 / pkg-config 0.29.2

## 验证结果

```bash
# 上游测试台账（双口径，17 个独立用例，详见 reports/upstream-test-ledger.md）
#   全量通过率 3/17=17.6%（3 个无硬件自测通过，13 个需真实 SCSI/bsg/NVMe 硬件，
#   sg_chk_asc 执行并检出 t10.org 表差异）
# 鸿蒙专项测试（test_package/ohos_test.c）: ALL PASS（5/5 断言，RUN_RC=0）
# 消费者用例（test_package/test.c）: ALL PASS（3/3 断言，RUN_RC=0）
# conan-verify: G0-G4 + L2/L4/L5 全 PASS
# W3 本地 CI: build_and_test.sh RC=0（JC prdiff 基线隔离复验通过）
```

## 交付物

- libsgutils2.a / libsgutils2.so（lib/）
- 79 个 sg_* CLI 工具 + scsi_* 脚本（bin/）
- 公开头文件 scsi/sg_lib.h 等（include/scsi/）

## 注意事项

- 上游 testing/ 多数用例依赖真实 SCSI 通用（sg）/bsg/NVMe/块设备，目标机无对应
  硬件时属真实外部硬件阻塞，恢复条件为在具备 sg/bsg/NVMe 硬件的设备上运行。
- test_package 消费者用例仅经公开头文件 scsi/sg_lib.h 与公开 API 使用库。
- 知识路径判定: new_draft（K4 drand48_r 缺族，DRAFT-libsgutils-1.46-ohos-missing-drand48-r.kv/.md），
  与 K1/K2/K3/K5 既有条目复用关系见 reports/knowledge-candidate-ledger.md。

## 结束

**最终状态**: built（本地门禁全通过、conan-verify PASS、W2/W3 通过、W4 审计 pass，
制品未 upload，符合 built 语义；待 PR 合入后由 CI 发布为 published）
---

**编译结束**: 2026-09-17 10:56
**最终状态**: built
