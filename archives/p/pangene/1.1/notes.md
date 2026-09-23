# pangene 1.1 — HarmonyOS PC 适配笔记

## 软件概述
pangene（作者 Heng Li，lh3）是构建泛基因组基因图（pangenome gene
graph）的命令行工具：输入 miniprot 的蛋白-基因组 PAF 比对，输出 GFA
格式的基因图（节点=标记基因，边=基因组邻接关系）。适用于大型真核
泛基因组，含基因冗余消除与伪基因过滤。纯 C99 实现，内嵌 klib 头文件，
无 SIMD。

## 源码来源
- 上游仓库：https://github.com/lh3/pangene（官方唯一仓库，作者 lh3）
- 1.1 版本：tag `v1.1` = "Pangene-1.1 (r231)"，2024-02-22 发布，版本串
  `1.1-r231`（pangene.h `PG_VERSION`）
- 官方源码 tarball：`https://github.com/lh3/pangene/archive/refs/tags/v1.1.tar.gz`
  （无 GitHub Release asset，tag 归档即官方源码包）
- SHA256：`9fbb6faa4d53b1e163a186375ca01bbac4395aa4c88d1ca00d155e751fb89cf8`
- License：MIT（GitHub API license.spdx_id=MIT；注意 tarball 内无 LICENSE
  文件，manifest/conanfile 按上游官方仓库声明 MIT）
- 解压后顶层目录：`pangene-1.1/`

## 构建适配要点
- plain Makefile：无 configure / 无 install 规则；产物为单个 `pangene`
  可执行文件。`make -C <src> CC=<conf> LIBS="..."` 驱动，R9 `-j1`。
- R33：CC 取自 `tools.build:compiler_executables`（profile conf），禁止
  裸用 shell 环境变量。
- R26：Makefile 默认 `LIBS=-lpthread -lz -lm` 中 `-lz` 必须指向 Conan
  zlib 包（`-L<zlib libdir>`），避免链到 sysroot 系统 zlib。
- 零 patch 预期：源码审计无 syscall/mmap/dlopen/popen/system、无 SIMD、
  仅 getrusage/gettimeofday（musl 支持）；同作者 miniprot 0.18 已实证
  同结构零 patch 通过。

## 上游测试核查（R51 三步法，结论：无正式测试）
1. **Makefile**：仅 all/clean/depend 目标，无 test/check。
2. **test/C4/**：33 个 `*.paf.gz` fixture（miniprot PAF，8 个灵长类基因
   组），无脚本、无期望输出。
3. **test/bubble/**：pangene.js（node）的测试数据——node 不在 CI 能力
   矩阵，pangene.js 非 C 构建产物，不入包、不测试（如实记录）。
4. **CI workflow**：v1.1 源码树无 .github 目录。
5. **README quick-start**：`./pangene test/C4/*.paf.gz > C4.gfa` 为唯一
   官方演示用法；已重实现于 test_package/test_pangene.sh（C4 fixture
   解压为纯文本——zlib gzopen 透明读取未压缩文件，同时规避 CI JC2/JC3
   对压缩制品的拦截）。

## test_package 说明
- 5 条断言：--version 含 `1.1-r231`；quick-start rc=0；GFA 输出含
  S/L/W 行（segment/edge/walk）。
- 用 `CONFIG_SHELL` 起 bash（OHOS mksh 无法 exec ELF 二进制），miniprot
  同款处理。

## 参考
- 配方结构 1:1 对齐 archives/m/miniprot/0.18/（同作者、同 Makefile+klib
  +zlib 模式、application 型 CLI、零 patch）。
- 依赖 zlib 选 1.3.2（制品仓 recipe + OHOS armv8 binary 均实测可
  consume；miniprot 用的 1.3.1 亦在仓，如需对齐可切换）。

## 源码下载镜像（CI 教训，PR #9631 build #44698）
- CI worker 无法直连 github.com（ConnectTimeout），且 worker 缺 curl
  导致 CI 预下载（gh-proxy 注入）全部失败。
- 解法（与 boids 2.0.0 配方同构）：conandata.yml url 列表官方源首位 +
  gh-proxy.com 镜像次位；conan get() 顺序重试，任一成功即通过
  sha256 校验（gh-proxy 镜像已实测哈希一致
  9fbb6faa...fb89cf8，与官方 tarball 逐字节相同）。
- 该镜像 URL 与 preflight PF7 静态黑名单（gh-proxy.com）冲突：此处
  为 CI hint 明示的官方建议路径（"请在 conandata.yml 中将 github.com
  URL 改为镜像 URL"），属官方托管例外，PR 描述已说明理由。
