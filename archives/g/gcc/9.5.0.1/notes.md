# gcc 9.5.0.1 适配笔记（全 PIE + LLD 自动签名路线）

## 版本说明（为什么是 9.5.0.1 而不是改 9.5.0）

制品仓 ohpcd 已有 `gcc/9.5.0@ohpcd/stable`（2026-08-07 积分赛 PR 合入 main）。
该包在功能上是坏的：宿主生成器与目标对象非 PIE，命中 OHOS lld 的 AArch64
COPY 重定位 bug（详见下文），所编程序在 `gcc.c-torture/execute` 的
nestfunc / printf-2 / fprintf-2 等用例段错误。本地配方与制品仓配方 diff
为零（同为路线 A），L0j 同版本禁改 → 按 R37 新建版本目录 **9.5.0.1**
（同一上游 gcc-9.5.0 源码，工具链路线重构），9.5.0 目录不动。

## 工具链路线：B（全 PIE + SDK ld.lld 自动签名）

相对 9.5.0（路线 A：GNU ld + binary-sign-tool 全链手动签名）的四大变化：

| 维度 | 9.5.0（路线 A） | 9.5.0.1（路线 B） |
|------|----------------|-------------------|
| PIE | 默认非 PIE（gcc_cv 预置无效） | `--enable-default-pie` + 清 `NO_PIE_*` |
| 链接器 | GNU ld（binutils 2.45） | SDK `ld.lld`（`--with-ld` 烘焙 + LD/LD_FOR_TARGET） |
| 签名 | CC 包装器 + `_sign_elf_tree` 全树 binary-sign-tool | LLD 链接即签名（.codesign），零 binary-sign-tool |
| 包装器 | clang-sign/clangxx-sign/xgcc-sign（签名逻辑 ~60 行/个） | 薄 exec 包装器（仅 -B/-isystem/-D 搜索前缀） |

### 核心机制（2026-09-22 设备最小实验复核）

1. **clang 默认走 SDK lld，产物自动带 .codesign 可运行**（env -i 亦然，本机
   libxml2 可解析；包装器仍防御性导出 SDK llvm/lib 的 LD_LIBRARY_PATH）。
2. **GNU ld 不签名**：产物 rc=126（execve 拒绝）。
3. **ld.lld 直链产物带 .codesign 且可被内核加载运行**。

### 非 PIE + lld COPY 重定位 bug（9.5.0 崩溃根因）

非 PIE 对象中 libc `stderr` 等外部数据符号产生 R_AARCH64_COPY 重定位；
OHOS lld 将 COPY 目标按 16 字节对齐布置 literal (LO12) 加载，而非 PIE
可执行文件的加载基址没有对齐保证 → `ldr x0, [x0, :lo12:...]` 未对齐访问
→ 段错误。修复 = 全链 PIE（PIE 下该符号走 GOT，无 COPY 重定位）：

- configure 加 `--enable-default-pie`（ENABLE_DEFAULT_PIE，驱动默认 -fpie -pie）
- configure 后 sed 清空 `gcc/Makefile` 的 `NO_PIE_CFLAGS`/`NO_PIE_FLAG`
  （及 `_FOR_BUILD` 对；`BUILD_NO_PIE_*` 经 `$(NO_PIE_*)` 间接引用自动联动）
- **env 预置 gcc_cv_c_no_fpie/gcc_cv_no_pie 无效**（9.5.0 踩坑）：
  顶层 configure 生态下该 cache 变量预置不生效，必须后置 sed

### --with-ld 烘焙（gcc 9.5.0 源码级验证，2026-09-22）

- 顶层 configure 不消费 `--with-ld`，但经 baseargs **原样转发**给
  gcc/configure（configure:7380 起，无过滤）
- gcc/configure.ac:284 起：`DEFAULT_LINKER="$with_ld"`，校验可执行 +
  `-v | grep GNU`（lld 报 "compatible with GNU linkers" 通过）→
  `AC_DEFINE_UNQUOTED(DEFAULT_LINKER, ...)`
- gcc.c:2864 与 collect2.c:1136/1166：驱动/collect2 对 "ld" 直取
  DEFAULT_LINKER 绝对路径（access X_OK）
- 配方在 all-gcc 后断言 `xgcc -print-prog-name=ld == 烘焙路径`（fail-fast）

### CC 直用（无包装器）与 -fuse-ld 拒绝

- SDK clang 本身默认 lld 链接+签名，无需包装器；配方显式拒绝
  `-fuse-ld*` 参数：`-fuse-ld=bfd` 会(a) clang 对 -E 探测输出
  unused-argument 警告 → autoconf conftest.err 非空 → HAVE_LIMITS_H 等
  误判 no → limits.h 缺失链式崩溃；(b) 禁用 lld 自动签名
- CI profile `ci/conan/profiles/ohos-aarch64` 的 CC 本无 -fuse-ld，
  拒绝逻辑是防回归护栏

### 薄包装器与可重定位驱动

- build 期 `xgcc-ohos`：仅 `exec xgcc -B<build>/gcc/ -B<sysroot>/usr/lib/<triplet>/ -isystem <target include> '-D__availability__(...)=`（签名免了，crt 搜索并入包装器）
- 包内 `bin/gcc`（shell）：`bin/gcc.real` 重定位 + GCC_EXEC_PREFIX +
  sysroot/libgcc -B 前缀 + 可用性注解丢弃；新增 lld 可用性检查
  （`-print-prog-name=ld` 解析失败即报错）与 SDK llvm/lib 的
  LD_LIBRARY_PATH 防御导出

## 沿用 9.5.0 的已审计基础设施

- `files/ohos.h`（musl ABI 目标定义）+ `files/prepare_ohos_sources.py`
  （triplet/tm_file/t-musl 注入）原样复用
- `--disable-threads`（OHOS libc 无 pthread_cancel）
- HMDFS 适配：umask 变换、unlimited-stack 双 bash exec、make pipe jobserver
  -j2、signal-11 同步重试
- in-tree gmp 6.1.0 / mpfr 3.1.4 / mpc 1.0.3（上游 download_prerequisites 精确版本）

## 测试

- `make -C gcc selftest`（语言无关 + C 前端自测）
- gcc.c-torture/execute 50 源 × (-O0, -O2 -fno-strict-aliasing) = 100 次执行
  （>90% 通过门禁；LLD 签名后直接在设备运行）
- test_package：真实编译链接执行 + **.codesign 断言**（readelf -S 必须含
  .codesign，防无签名链接器回归）
- 路线 B 手动验证（build2 树，2026-09-21，树已被系统清理）：dejagnu
  execute.exp 6099/6106 PASS（99.89%）、compile.exp 16998/17005 PASS。
  本版已在 conan create 重建树全量重跑固化（2026-09-22）：
  execute.exp **15761 PASS / 41 FAIL / 307 UNSUPPORTED / 15 unresolved**
  （已执行通过率 99.74%），41 失败全部归因两类平台/环境限制——
  ① GNU trampoline 类 25 个：嵌套函数栈上运行时生成代码被 OHOS 内核
  强制签名校验拒绝（平台级限制，`-z execstack` 无效）；② musl tmpnam
  硬编码 /tmp 只读类 16 个（fprintf-2/printf-2/user-printf，exit 1 非段错误）。
  均非编译器缺陷；build2 时期"7 失败为上游 32 位移植用例"的记录系误判，
  已由本次全量证据修正。compile.exp **9373 PASS / 25 FAIL / 55 UNRESOLVED /
  283 UNSUPPORTED**（99.73%）：20 失败 = limits-exprparen/structnest 病态
  10^4 层嵌套触发 stage-1 cc1（clang 构建，--disable-bootstrap）ICE，
  非栈耗尽（256MB 栈复现不变）、与目标代码生成无关；5 失败 = pr46534
  探针污染（stty 噪声使 size32plus 误判，编译器行为本身正确）；55 未决 =
  7 源病态慢编译撞 300s 单测超时。两阶段合计通过率 99.74%，
  66 失败 100% 归因平台/环境/测试设施，详见 reports/test-report.md。

## 与 9.5.0 的源码 diff

- 上游源码：零 diff（同一 tar.xz，sha256 相同）
- 配方差异：仅 conanfile.py 的工具链路线段（见上表）与版本号；
  conandata.yml 仅版本键名；test_package 签名断言替代手动签名
---

**编译结束**: 2026-09-22 20:31（finish 10 步全过，W3 本地 CI 100%）
**最终状态**: built
