- **三方库名称**：mhddfs
- **上游版本**：0.1.39.0
- **上游仓库地址**：http://mhddfs.uvw.ru/（上游官网已失效；本 PR 使用 Debian 归档 pristine orig 包，取证见「补充说明」）
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新，见「路径 B 知识贡献说明」）
- **使用知识库**：E051（OHOS libc 未实现函数：pthread_cancel / pthread_setcancelstate）、知识图谱原则 P014；本 PR 新增 2 条知识草稿（见下）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 手动 helper（`tests/`） | 7 | access.pl、seek.pl、statvfs.pl、utimes.sh、xattrs.sh、rename.c、plocks.c；全部要求真实 FUSE 挂载 |
| Makefile 挂载类目标 | 10 | test-mount、test-umount、test、btest、tests、ptest、rename、symlinks_test、rename-test、dirtree-test（`tests` 循环调用 `test`；`rename` 仅编译 helper）；均以真实挂载为运行前提 |
| **合计** | **17** | 上游无自动化断言框架；全部以 live mount 为前提 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游测试（Linux+FUSE 参考环境，同源补丁构建） | **16/17 真实执行** | 新增执行 | 13 项退出码 0（含 `test-mount`、`btest`（65 MiB 经 union 写入回读 md5 一致）、`rename-test`、`dirtree-test`、`symlinks_test`、`access.pl`、`seek.pl`、`statvfs.pl`）；`plocks/ptest`、`tests` 为上游无限循环压测按有界时间运行完成；唯一未执行 `xattrs.sh`（缺 attr/mkfs.xfs/sudo 且构建按 `WITHOUT_XATTR`）。摘要：`reports/upstream-suite-linux-reference.md` |
| 上游测试（OHOS 设备逐项尝试） | 4 项设备真机执行通过 | 平台边界 | `access.pl`/`seek.pl`/`rename`/`plocks` 设备执行通过；`statvfs.pl` 缺设备 Perl 模块；其余挂载类目标 `/dev/fuse` EACCES(13)。原始输出：`reports/ohos-device-upstream-attempts.md` |
| 鸿蒙特有测试（test_package） | **10** | 新增 | 真实执行打包后的 `bin/mhddfs`：版本输出、usage 退出码、目录校验 ×2、重复目录消除、mlimit 解析、启动信息、有界挂载尝试；`mhddfs functional tests: 10/10 passed` |
| **合计** | **16（上游参考执行）+ 10（鸿蒙消费者）** | — | 设备端另完成 4 项上游 helper 真机执行 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无自动化测试套件（7 个手动 helper + 10 个 Makefile 挂载类目标，共 17 项，均以真实挂载为运行前提；已在具备 FUSE 的参考环境以同源补丁构建真实执行 16/17，设备端另做逐项尝试），适配后补全消费者测试

> 补全的测试范围：10 项消费者断言（启动契约 + 有界挂载判定），覆盖参数解析、目录校验、聚合选项与 FUSE 启动边界。
> 补全原因：上游测试以 live FUSE 挂载为前提，OHOS PC 普通进程挂载不可用（平台边界，见补充说明）；按 R34/R51 以真实执行被测二进制的消费者测试补位，不写空壳、不伪造挂载。
> 新增测试文件清单：
> 1. `test_package/test_mhddfs.py` — 10 项断言：T1–T2 版本、T3–T4 usage 非零退出、T5–T6 目录校验诊断、T7 重复目录消除、T8 mlimit 解析、T9 启动信息、T10 有界真实挂载尝试（超时=已挂载则尽力卸载；快速非零且含 fuse 诊断=干净边界失败，两者都如实记录）。

## 验证结果

- 编译状态：通过（conan-verify G0–G4 全 PASS；conan create 干净构建成功）
- 上游测试用例通过率：**16/17 真实执行**（Linux+FUSE 参考环境，同源补丁构建：13 项退出码 0，`plocks/ptest`、`tests` 按有界时间运行完成；`xattrs.sh` 因缺 attr/mkfs.xfs/sudo 未执行）——摘要与原始节选见 `reports/upstream-suite-linux-reference.md`
- 目标平台（OHOS PC）上游测试尝试：4 项独立 helper 设备真机执行通过（`access.pl`/`seek.pl`/`rename`/`plocks`），其余受 `/dev/fuse` EACCES(13) 平台边界阻塞——原始输出见 `reports/ohos-device-upstream-attempts.md`
- 新增测试用例通过率：10/10（100%）

## 补充说明

### 路径 B 知识贡献说明

本 PR 按路径 A+B 申报，携带 2 条「一类问题」级知识草稿（`knowledge/drafts/` 下 kv + md 成对，字段完整）：

1. **`DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary.{kv,md}`**
   **OHOS PC 用户态 FUSE 消费端挂载可用性边界**：`/dev/fuse` 的 stat/open 全部 EACCES(13)、
   系统无 `fusermount`（libfuse 自带 fusermount 一执行即 SIGSYS 终止）、`mount(2)` 被沙箱以
   SIGSYS(31) 杀死；内核 FUSE 能力存在但仅供系统服务（媒体服务挂载
   `/data/storage/el2/media/Photo`）。给出三层探针命令与"普通进程能否挂载"判定树。
   **触发实例**：mhddfs 打包后二进制实跑输出 `fuse: failed to open /dev/fuse: Permission denied`
   （rc=1）；`CapEff=0x2a` 无 CAP_SYS_ADMIN。**适用范围**：全部 libfuse 消费端
   （mhddfs/tmfs/mtpfs/securefs/kio-fuse 等同簇）。
2. **`DRAFT-mhddfs-0.1.39.0-fuse-consumer-test-construction.{kv,md}`**
   **挂载不可用平台上的 FUSE 消费端测试构造**：可确定启动行为硬断言（版本/usage 退出码/
   目录校验/去重/mlimit）＋ 有界挂载双向判定（超时=已挂载则清理并记录；快速非零且含 fuse
   诊断=干净边界失败）＋ 上游测试逐项 BLOCKED 申报（R51），禁止空壳/伪造/skip 美化。
   **触发实例**：本 PR 的 10/10 消费者测试、16/17 上游测试参考环境执行与设备侧逐项尝试记录。

**查重结论与新增价值**：现有条目中 `DRAFT-composefs-1.0.8-hmfs-fsverity-ioctl-eacces` 与
`…-security-xattr-skip` 讲 HMFS/fsverity/xattr 的 ioctl 语义边界，
`DRAFT-ohos-syscall-capability-matrix-fork-probe` 讲进程/syscall 能力矩阵；
本 PR 两条均属空白面：一条聚焦 **FUSE 挂载链本身**（设备节点/辅助程序/mount(2)），
一条聚焦 **测试工程构造**。`draft-review` 预审：条目 1 最相似为 E303（score 0.34，hostfs
opendir 路径搜索）及 E008/E031（SELinux 对非普通文件/procfs 的限制）——资源与调用链均不同；
条目 2 预审建议 `create`（无高相似条目）。预审输出收录于两条草稿的 md 文件。

### 上游测试执行方式与证据（2026-10-03 打回修复）

上一轮审查（rule4）要求真实执行上游测试用例。本 PR 已完成并留档：

1. **参考环境完整执行（Linux+FUSE，同源补丁构建）**：上游 17 项中 **16 项真实执行**——
   13 项退出码 0（含 `test-mount` 挂载态 `df`/`ls`、`btest` 65 MiB 经 union 写入回读
   **md5 一致**、`rename-test`/`dirtree-test`/`symlinks_test` 输出 `PASSED`、`access.pl`/
   `seek.pl`/`statvfs.pl` 经挂载点通过），`plocks/ptest`、`tests` 为上游无限循环压测按
  15s/20s 有界运行完成；唯一未执行 `xattrs.sh`（缺 `attr`/`mkfs.xfs`/`sudo`，且构建按
  `WITHOUT_XATTR` 未启用 xattr）。摘要与原始节选：`reports/upstream-suite-linux-reference.md`。
2. **OHOS 设备真机逐项尝试**：`access.pl`、`seek.pl`、`rename`、`plocks` 4 项独立 helper
   真机执行通过；`statvfs.pl` 因设备 Perl 缺 `Filesys::Statvfs` 未执行；其余挂载类目标受
  `/dev/fuse` EACCES(13) 平台边界阻塞并附原始错误。原始输出：
  `reports/ohos-device-upstream-attempts.md`。
3. 参考环境为具备 FUSE 的 Linux 主机，使用与本 PR **完全相同的源码包与 3 个补丁**构建
   （`make mhddfs WITHOUT_XATTR=1`）；参考环境结果与目标平台结果分别标注，不混用不冒充。

### 源码 URL 取证（R39 例外登记）

- 上游官网 `http://mhddfs.uvw.ru/` 已失效：http 拒连（curl exit 7）、https 证书 hostname
  不匹配（curl exit 60），svn.uvw.ru 同步消失（2026-09-27 实测）。
- 唯一权威可得源为 Debian 归档 **pristine orig** 包（`.orig.tar.xz` 即上游原包；Debian 补丁在
  单独的 `.debian.tar.xz`）：`https://deb.debian.org/debian/pool/main/m/mhddfs/mhddfs_0.1.39.0.orig.tar.xz`，
  sha256 `8bae7d3820b472cf87cd6d1fecf5d2d7965a0fe6c020b121c08c98b2c2231863`（下载件重算一致）。
- CI 的镜像回退不覆盖该主机；本地 preflight PF7 按主机名机械拦截（无法区分 orig 与下游
  重打包）。提交时以 `OHC_PREFLIGHT=0` 显式跳过，并在此登记例外说明。

### 关键适配点

1. **Makefile 硬编码 gcc** → `$(CC)`（补丁 0001，2 行规则），使用 Conan 注入的 OHOS clang。
2. **OHOS libc 缺 pthread_cancel / pthread_setcancelstate（E051）** → 新增消费者侧
   `src/pthread_stubs.c`（补丁 0002，与 libfuse 2.9.9 test_package 同型，ENOSYS 语义，
   glibc/musl 守卫下不生效）；默认单线程 `fuse_main()` 不触达这两个调用点。
3. **VERSION 宏滞后（0.1.39）** → 对齐发行/包版本 0.1.39.0（补丁 0003，与 Debian 构建
   经 changelog 注入的行为一致）；`mhddfs --version` 输出 `mhddfs version: 0.1.39.0`。
4. **xattr**：OHOS sysroot 无 legacy `<attr/xattr.h>`，按上游 `WITHOUT_XATTR` 编译开关构建。
5. **make 目标直达**：显式 `make mhddfs`，避开原包无 `debian/changelog` 时 `update_version`
   分支覆写 version.h 的行为。

### 构建环境与验证方式

- 设备真机 OpenHarmony PC aarch64；clang 15.0.4（OHOS SDK）；Conan 2.29.1；
  profile `ohos-aarch64-device`（与 `ci/conan/profiles/ohos-aarch64` 同构）
- `conan-verify` G0–G4 全 PASS；`reports/conan-verify-report.md`、`reports/conan-create.log`

### 产物验证

| 产物 | 验证方式 | 结果 |
|------|----------|------|
| `bin/mhddfs` | 打包后实跑（版本/usage/目录校验/选项解析） | 通过 |
| `share/man/man1/mhddfs.1` | 包内清单检查 | 通过 |
| `licenses/`（GPL-3.0） | 包内清单检查 | 通过 |
| 真实 FUSE 挂载 | 设备尝试（`/dev/fuse` EACCES） | BLOCKED（平台边界，如实记录，不含伪造） |

### preflight 逃生口说明（PF7/PF9 机械误报，提交时 OHC_PREFLIGHT=0）

本地 preflight 对本 PR 报 3 条，均为规则可识别的机械误报；提交时以 `OHC_PREFLIGHT=0` 跳过并在此登记：

1. **PF7 ×2**（`conandata.yml` 与版本级 `manifest.yaml` 的源 URL 命中 `deb.debian.org`）：
   PF7 按主机名拦截，无法区分 `.orig.tar.xz`（上游原包）与 Debian 下游重打包；本 PR 的 URL
   是 pristine orig（见上节取证），规则原文亦允许"确属官方托管例外须 PR 说明并 --no-preflight 跳过"。
2. **PF9 ×1**（软件级 `README.md` / `commands.json` / 软件级 `manifest.yaml` 不在版本目录层）：
   ARCHIVE-SPEC v3.0 与 CI L0k 均要求这两个文件位于软件级目录，PF9 的"路径须含版本层"为误报；
   按仓库既有约定保留在软件级。

### Issue / 评审口径

按当前仓库实践（#9670 标注 Issue 机制已废弃；近期合并的路径 B PR 均未单独开 issue），
本 PR 不单独开 issue，路径 B 部分由评审委员会在 PR 复审。
