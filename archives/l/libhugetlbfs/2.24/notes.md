# libhugetlbfs 2.24 — 适配笔记

> 档案创建时间: 2026-09-19
> 状态: 前置适配（W0/W1 完成），判定**可适配**，待真机 W3 编译 + 大页功能验证
> ⚠️ 重要更正：初版曾误判为"平台不可适配（无大页后端）"，经核实 OHOS musl 完整支持大页，已纠正。

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libhugetlbfs |
| 版本 | 2.24 |
| 构建系统 | autotools（configure.ac + Makefile.in，tag 归档需 autogen.sh 引导） |
| 上游仓库 | https://github.com/libhugetlbfs/libhugetlbfs |
| 源码归档 | https://github.com/libhugetlbfs/libhugetlbfs/archive/refs/tags/2.24.tar.gz |
| SHA256 | e6731ce521cf3d9da4c55af005d5a14cddd0e4a25d7fe6fd13543cef39b2a704 |
| 许可证 | LGPL-2.1-or-later |

## 二、W0 依赖检查结论

```
依赖数量：0 个 Conan 制品仓依赖
构建依赖（系统级，非 Conan）：
  - autoconf/automake/libtool（tag 归档无预生成 configure，需 autoreconf 引导）
  - libdl（Makefile.in 已内置 -ldl；OHOS 需要，见 E013）、libpthread
运行时功能依赖（平台能力，已确认 OHOS 具备）：
  - MAP_HUGETLB / MAP_HUGE_* / MADV_HUGEPAGE / MFD_HUGETLB —— OpenHarmony musl 已定义
  - hugetlbfs 内核特性 —— OpenHarmony kernel 有 SYS_SUPPORTS_HUGETLBFS，musl 有"文件大页"特性
测试依赖：tests/run_tests.py 需 Python；完整测试需 root + 真实 hugetlbfs 挂载
是否需要拆分依赖适配：否
下一步：真机 W3 编译 + 大页功能验证（见第六节）
```

## 三、W1 源码/构建系统分析结论（更正版）

1. **构建系统**：autotools。`configure.ac` 只做 `AC_PROG_CC/INSTALL/LN_S/MAKE_SET` +
   `AC_CHECK_LIB([dl],[pthread])` + `__morecore` 探测，**不含 AC_CANONICAL_HOST**，
   因此不会触发 config.sub/config.guess 识别 OHOS 的经典问题（E072/E160）。
2. **架构**：Makefile.in 有显式 `aarch64` 分支（`ELF64=aarch64elf`、`TMPLIB64=lib64`、
   `sys-aarch64elf.S`）。交叉编译需 `make ARCH=aarch64`（默认 `uname -m` 探测）。
3. **逐项核对 musl/OHOS 兼容性（均已核实）**：
   | 依赖 | 初版误判 | 实际情况 |
   |---|---|---|
   | `<features.h>` | 无 | OHOS musl **有**（mman.h 首行即 include） |
   | `<link.h>` + `dl_iterate_phdr` | glibc 专属 | OHOS musl **完整提供**（dl_phdr_info/link_map/dl_iterate_phdr） |
   | `<malloc.h>` | 无 | musl 有 |
   | `__morecore` | 致命 | configure.ac 已做 HAS_MORECORE 降级检测（musl 自动跳过） |
   | `MAP_HUGETLB`/`MADV_HUGEPAGE` | 无 | OHOS musl **完整定义** |
   | `<mntent.h>`/setmntent/getmntent_r | 无 | musl 有（运行时挂载表可能为空，需降级） |
   | `-ldl` | 障碍 | Makefile.in 已内置，且 OHOS 正好需要（E013） |
4. **残余编译风险点（需真机确认）**：
   - tests/ 用 `<linux/falloc.h>` 的 `FALLOC_FL_*` 常量，OHOS 内核头可能缺失（E115 有补丁先例，仅影响测试）。
   - `ld.hugetlbfs` 链接脚本 wrapper 与 `--version-script=version.lds` 需 ld.lld 支持验证。
5. **功能降级预期（诚实声明）**：
   - `get_huge_pages()`/`get_hugepage_region()`（直接 `mmap(MAP_HUGETLB)`）——预期可用。
   - malloc 堆大页化（`hugetlbfs_setup_morecore` 写 `__morecore`）——**musl 无 __morecore，
     天然降级**，只能走 mmap 大页路径，不经过 brk 堆。
   - `hugectl`/`hugeedit`（ELF 段重映射）——依赖 `dl_iterate_phdr`（musl 支持），需真机验证。

## 四、本机前置验证（如实记录）

- [x] 源码归档下载 + SHA256 复核一致（e6731ce5…2a704）
- [x] W0/W1 分析（含 musl/OHOS 兼容性逐项核实）
- [x] 配方静态检查：conanfile.py 语法通过，validate() 仅拦 Linux/OHOS 之外平台
- [x] YAML 解析、`git diff --check` 通过
- [ ] `conan create` 编译验证：**未执行**（本机无 Conan / OHOS 工具链）
- [ ] 上游 `make check`：**未执行**（需真实 hugetlbfs 挂载 + root）

## 五、交付物说明

| 文件 | 说明 |
|------|------|
| conandata.yml | 官方 tag 归档 URL + 已验证 SHA256，无补丁 |
| conanfile.py | 完整配方（autoreconf→configure→make ARCH=aarch64），validate() 允许 Linux/OHOS |
| manifest.yaml | 前置阶段快照，knowledge_gained 记录更正后的结论 |
| test_package/ | 消费者契约测试（链接 libhugetlbfs，调 gethugepagesize/getpagesizes） |
| notes.md | 本文档 |

## 六、下一步：真机验证（关键实证点）

本机无 OHOS 工具链，以下必须在真机 shadow CI 完成：

**1. 内核大页能力探测（决定功能成败，一条命令）**
```sh
# 是否启用 hugetlbfs / 大页
cat /proc/meminfo | grep -i huge
ls -la /dev/hugepages 2>/dev/null || echo "no /dev/hugepages"
grep -i hugetlb /proc/filesystems
# 试分配一个 2MB 大页（返回地址即支持）
python3 -c "import ctypes,mmap; print(mmap.mmap(-1, 2*1024*1024, flags=mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS|mmap.MAP_HUGETLB) and 'MAP_HUGETLB OK' or '')"
```

**2. shadow CI 编译验证**
```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job libhugetlbfs-2.24-<ts> \
  --package archives/l/libhugetlbfs/2.24 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

**3. 判据**
- 若 `/proc/meminfo` 无 `HugePages_*` 且 `MAP_HUGETLB` mmap 失败 → 内核未启大页，
  降级为 `env_unsupported`（但此时是**内核配置问题**，不是库不可适配）。
- 若 `MAP_HUGETLB` 成功 → 继续修编译微调（fallocate 常量等）→ 跑 `get_huge_pages` 功能测试。

## 七、注意事项

- 上游项目多年停更（2.24 为 2022 版，仅接受邮件列表补丁），适配需自维护补丁。
- 编译通过 ≠ 功能可用（R40）：必须验证 mmap(MAP_HUGETLB) 真正返回大页，而非仅编译过。
- malloc 堆大页化在 musl 上**预期降级**，交付时应明确说明，避免夸大功能。

## 八、真机 shadow CI 验证记录（2026-09-19）

- 设备连通性 OK；环境：conan/python3/make/zsh 有，**git/bash 缺失**（用 --repo-source 复用已有 repo）。
- prepare 隔离 job 成功：`libhugetlbfs-2.24-shadow-20260919-r1`，repo 复用 klibc job。
- 配方 8 文件 scp 到设备 job repo 的 `archives/l/libhugetlbfs/2.24/`，清单核对齐全。
- conan create 链路实测：L0 质量门禁全过（test_package 结构/MANIFEST/L0j 版本碰撞/L0k commands.json），
  源码经 gh-proxy 镜像下载成功，依赖图计算成功，profile=ohos-aarch64(armv8/OHOS/clang15/libc++)。
- 已修复的构建问题（迭代中）：
  1. `./autogen.sh: Permission denied`（Error 126）→ 源码 tarball 内 autogen.sh 无执行位；改为 `sh ./autogen.sh`。
  2. `autoreconf: inaccessible or not found`（Error 127）→ autoreconf/autoconf/m4 在 `/data/service/hnp/bin`
     （不在 PATH，automake/aclocal/libtoolize 在 /usr/local/bin）；build() 前置 PATH 加入 toolchain bin。
- **最终结果（成功）**：shadow CI exit=0，`conan create` 通过，L0/L1/L2/L4/L5 全 pass。
  - L2 smoke：`hugeadm --help`/`hugectl --help`/`hugeedit --help` OK（`pagesize --help` 非阻塞告警）。
  - L1e 破坏性反向验证通过（test 实质依赖 libhugetlbfs，非空壳）。
- **实证（已纠正）**：`gethugepagesize=-1, getpagesizes=-1` 的根因是 CI 普通用户无 root——`/proc/sys/vm/nr_overcommit_hugepages: Permission denied`（E031）。
  经真机核查，**OHOS 内核已启用 hugetlbfs**：`/proc/meminfo` 显示 `HugePages_Total=2`、`Hugepagesize=2048 kB`、`Hugetlb=4096 kB`；
  `mmap(MAP_HUGETLB)` 返回 `ENOMEM`（因 `HugePages_Free=0`，2 个大页被占满）而非 `EINVAL`，证明机制工作。
  结论：编译/打包/消费链路可用；大页分配需 root 写 `/proc/sys/vm/nr_overcommit_hugepages`，属权限边界（待 root 环境验证），非平台功能缺失。
- 迭代修复（musl + HMDFS 兼容，共 10 处，详见 manifest.yaml knowledge_gained）：
  autoconf 直代 autoreconf、PATH 加 toolchain bin、umask 077→022(E011)、
  `_SC_LEVEL2_CACHE_LINESIZE`→64、`__THROW`/`__nonnull` 删除、`addmntent`→no-op、
  `ln`→`cp`(E018/E073)、跳过 install-man、`PREFIX=/ LIB64=lib`、静态链接删 .so。
- 待办：finish 阶段用 `refresh-patch --auto` 把 build() 内的 sed 固化为 patches/*.patch；
  当前 status=built（未 upload 制品仓）。
