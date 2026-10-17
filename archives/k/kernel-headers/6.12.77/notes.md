# kernel-headers 6.12.77 编译笔记

## 任务背景

- **任务**：积分赛 #12807 — kernel-headers 6.12.77 适配（纯头文件包）
- **认领人**：calbee21
- **平台分支**：feat/kernel-headers-6.12.77（平台 taskBranch 原值，逐字核对）
- **上游来源**：kernel.org 官方 linux-6.12.77.tar.xz（平台任务 url 字段为 null，
  按 Linux 内核官方发布渠道确定；sha256 取自 kernel.org 官方 sha256sums.asc：
  358836ebe5caef41e7ae9492e7fbcdf5be6e53ee43c99752aebda81e1b2cff67，
  TUNA 镜像 sha256sums.asc 实测与官方一致）
- **开始时间**：2026-09-18

## 开工前侦察（W0，2026-09-18 实测）

1. **制品仓**：仓内无 kernel-headers 归档（`git ls-tree origin/main archives/k/`
   无 kernel-headers）；libevdev/libcap-ng/acpi_call 等以 `type: system` 引用
   "OHOS SDK sysroot 的内核头"——本包以 conan 包形态提供独立可控版本
2. **上游 tag**：kernel.org v6.x 目录 linux-6.12.77.tar.xz 实存（HEAD 200，
   Content-Length 148218636 ≈ 141.5MB）
3. **平台任务**：GET /api/contrib/tasks?q=kernel-headers → id=12807，
   claimer=calbee21，taskBranch=feat/kernel-headers-6.12.77，activity=
   开源鸿蒙PC专项积分赛 → PR 前缀【积分赛】
4. **镜像实测**：cdn.kernel.org 200 可用；TUNA 200 可用（7.6s 下载 141.5MB）；
   mirrors.huaweicloud.com 返回 WAF HTML 拦截页（非 xz 流）**不可用**；
   gh-proxy 404 不适用 → conandata url 列表 = [kernel.org, TUNA]

## 库特性与形态选型

Linux 内核 UAPI（userspace API）头文件——纯头文件包：

- **零依赖**：无 requirements（W0 依赖检查天然通过）
- **形态**：package_type="header-library" + no_copy_source + package_id 清空
  （参照 compile-time-regular 3.11.0 先例）
- **导出管线**：`make ARCH=arm64 HOSTCC=clang O=<build> headers`
  （headers_install 的 HDRINST 阶段），产物落 build 树 usr/include/，
  package() 用 `conan copy("*.h")` 拷贝

## 关键踩坑与解决（含实测数据）

### 1. kbuild headers_install 末步 rsync 依赖

- 内核 Makefile:1299 `cmd_headers_install` 末步 `rsync -mrl --include='*.h'`
  拷贝产物——OHOS worker **无 rsync**（`which rsync` 空），首次手测
  Error 127
- **解法**：配方 build() 只跑 `make ... headers` 目标（HDRINST 全阶段，
  产物已在 build 树 usr/include/），rsync 拷贝由 package() 的
  `copy(self, "*.h", ...)` 等价替代

### 2. HOSTCC 默认 gcc 不可用

- worker 只有 OHOS SDK clang（`/data/service/hnp/bin/clang`，无 gcc），
  kbuild 宿主工具（scripts/basic/fixdep、scripts/unifdef）需宿主编译器
- **解法**：`HOSTCC=clang` 实测通过（fixdep/unifdef 正常编译，
  HDRINST 全程 rc=0）
- 注：`make[1]: gcc: No such file or directory` 仍会出现——这是 sub-make
  版本探测的 warning，**不致命**（整体 rc=0，dry-run 实证）

### 3. O= out-of-tree 必须从干净源码跑

- 曾跑过 in-tree 构建的源码树，`make clean` **不会清 usr/include/**，
  二次 O= 构建产物头文件数与干净源码不一致（实测 944 vs 963，
  asm wrapper 20 vs 38）
- conan create 每次从 conandata 下载干净 tarball 解压，天然规避；
  手工复现时务必用全新解压的源码

### 4. arm64 导出语义（asm wrapper + no-export-headers）

- `arch/arm64/include/uapi/asm/Kbuild`：`generic-y += kvm_para.h` +
  `syscall-y += unistd_64.h` → asm/ 下生成 `#include <asm-generic/xxx.h>`
  wrapper 与 unistd_64.h（arm64 syscall 表：__NR_io_setup=0、
  __NR_openat=56）
- `include/uapi/Kbuild:10-12`：arch 有 generated asm wrapper 时
  `no-export-headers += linux/kvm_para.h`（linux/kvm_para.h 不导出属
  arm64 正确语义）
- 大写 netfilter 头（xt_CONNMARK.h/xt_MARK.h 等）与同名小写是**不同
  文件**（iptables target vs match 传统命名），均在 include/uapi 源内

### 5. 测试断言的 arm64 语义修正

- 初版 test_package 断言 `__NR_io_setup > 0` 失败——arm64 syscall 表
  io_setup 编号是 **0**（表首项）；改为 `__NR_io_setup == 0 &&
  __NR_openat == 56` 后通过

## 上游 N 核验（rule4：以实际构建系统注册为准）

- Linux kernel 6.12 顶层 Makefile 无 headers_check 目标（grep 实证——
  该目标已随 5.x kbuild 演进移除），仅 headers_install/headers 导出目标，
  无 add_test/ctest 等价注册 → **N=0 如实申报**
- 导出管线自带校验：scripts/headers_install.sh 逐头 sed 清洗
  （__KERNEL__ 段剔除）+ Kbuild no-export-headers 排除，随 make headers
  一体执行，无失败即通过
- 消费者验证（R34）由 test_package 承担：编译期 #error 断言（版本一致性
  LINUX_VERSION_CODE == KERNEL_VERSION(6,12,77) + 宏存在性）+ 运行期
  断言（struct input_id/__u16/BUS_USB/KEY_A/ETH_P_IP/_IOC 宏/syscall
  编号，退出码 0）

## 构建耗时参考（CI 预算）

- 本机（20 并发）：make headers 全程约 4-5 分钟（大 tarball 下载另计
  ~8s-2min 视网络）
- CI build_timeouts 默认 3600s 足够，无需覆盖

## 交付形态

- archives/k/kernel-headers/6.12.77/：conanfile.py + conandata.yml +
  test_package/（CMakeLists.txt + conanfile.py + test_kernel_headers.c +
  MANIFEST.yml）+ manifest.yaml + notes.md（本文件）+ reports/test-report.md
- 软件级：archives/k/kernel-headers/{manifest.yaml, README.md}
- 包产物：include/ 963 头文件 + licenses/
