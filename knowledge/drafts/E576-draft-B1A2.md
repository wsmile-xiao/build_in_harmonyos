# E576 — 上游 golden 基准随版本语义变更失效（非平台差异）：须先证明不是平台漂移，再按实测输出刷新

> Contributor: B1A2 | Status: Draft | Updated: 2026-09-11
> Source: dawg 1.2 OHOS PC 适配（C++/CMake 序列演化模拟器；上游缺陷追踪 #56）
> 对应 KV: knowledge/drafts/E576-draft-B1A2.kv

## 主题 / 触发场景

用「固定种子 + 固定输入 → 与签入基准逐字节 diff」型上游测试（golden / fixture 回归）时，
测试在**所有平台上都失败**，而程序行为其实正确：上游改过影响输出的语义（RNG 实现、
数值格式化、默认输出格式或排序），却没有重生成基准文件。

命中本模式时最危险的两种错误处置：

1. 把它当成 OHOS 平台缺陷去写平台补丁（而它跟平台无关）；
2. 照抄 E401 的结论（"禁止修改通用 golden"）而不敢刷新基准，或反过来
   **不经任何跨平台证明就直接用本机输出刷新基准**——后者会把真实的移植缺陷
   写进基准，变成永久假绿。

dawg 1.2 实例：`tests/test0.sh` 是上游唯一的端到端入口，它跑模拟器并把输出与
`tests/test0.fasta` diff。该基准自 v1.0.0 起从未重生成，而 v1.1 改了 RNG 语义，
于是测试对新版本自身恒失败。

## 错误特征

`sh tests/test0.sh` 非 0 退出，diff 输出形如（`<` = 程序实际输出，`>` = 签入基准）：

```text
2,3c2,3
< TCCTTGACCAGTTAGCAAGACGATATGCATCAAGTGCACTGGC---GTAAGTCTTTTTAC
< GCTGATCATA--TAGTCCGTATAGTCACTGAACGCCGTCCTCTCG
---
> AGGAACTGGTCACGTTCTGCTATACGTAGTTCACGTGACCGCATTCAGAAAAATGCGACT
> AGTATTGTGATCAGGCATATCAGTGACTTGCGGCAGGAGAGC
```

可复用字面签名（`|` 分隔，非正则）：

```text
tests/test0.fasta|TCCTTGACCAGTTAGCAAGACGATATGCATCAAGTGCACTGGC|test0.sh
```

配套可观测事实：`tests/CMakeLists.txt` 为 **0 字节**（构建系统从 autotools 迁 CMake 时
没有迁移该测试），`grep -c add_test tests/CMakeLists.txt` = 0 —— 所以 `ctest` 从不运行它，
失败可以长期隐藏；发行版打包则显式忽略（Debian `debian/rules` 的
`override_dh_auto_test` 里写着 `cd tests && PATH=$$PATH:$(BINDIR) sh test0.sh || true`，
并以注释给出上游缺陷编号 `#56`）。

## 触发条件

- 构建系统：任意（本例上游 1.2 为 CMake；测试脚本是 autotools 时代遗留的裸 `sh`）
- 阶段：测试（`make check` / `ctest` / 上游自写脚本）
- 前提：基准是**签入源码树的静态文件**，且上游在版本间改过可观测输出语义

## 根因分析

上游 v1.1 把随机数的实现与比较语义改了：

| 位置 | v1.0.0 语义 | v1.1 起语义 |
|---|---|---|
| `rand_real()` | `union{double d; unsigned long l[2];}` 位拼接，`2.0 - r.d`（ILP32 假设） | `(double)u * (1.0/4294967296.0)` |
| `rand_bool(p)` | `rand_real() <= p` | `rand_real() < p` |

模拟器输出的每个碱基与 gap 都由这些抽样驱动，因此**输出整体改变**，而
`tests/test0.fasta` 仍是旧语义下的产物。上游没有重生成基准，也没有把该测试迁到
CTest，于是在 1.1/1.2 上这个入口从"未运行"变成"必然失败"，只在发行版打包日志里可见。

与 E401 的区别（决定处置方向，不能混用）：

| | E401 | E576（本条） |
|---|---|---|
| 基准归属 | **另一平台**（amd64-linux/glibc）生成，本平台结果才对 | 归属**上游旧版本**语义，新版本结果才对 |
| 平台相关性 | 是（±1ULP 浮点舍入） | 否（两平台输出互相逐行一致） |
| 正解 | 新增 `{arch}-{os}.ok` 平台 oracle 变体，**不动**通用 golden | **刷新**该 golden（它是过期，不是平台专属） |
| 误用后果 | —— | 照搬 E401 会得出"不许动 golden"而无法修；或无证明地刷新会掩盖真缺陷 |

## 解决方案

### 推荐方案：先证明"非平台漂移"，再用实测输出刷新基准

**第 1 步 — 跨平台复现（决定性证据）**：用**未修改**的上游源码在第二平台/工具链上运行
同一测试输入，确认输出与本机一致、且与旧基准不同。优先取发行版的可复核记录
（源码包 orig tarball、构建日志、`debian/rules` 的忽略语句）。

dawg 实测：OHOS（clang 15 + libc++ + musl）与 Debian amd64（glibc + GCC，来自
Debian Med 邮件列表与 salsa 打包记录）在 `tests/test0.dawg` 上的输出**逐行一致**，
两者都与旧基准不同。这一步排除"OHOS 输出错了"。

**第 2 步 — 旧语义还原实验（钉死基准归属）**：只把导致输出变化的实现还原为
旧版本语义重新编译，看输出是否向旧基准收敛。dawg 实测：当前 v1.2 输出与旧基准的
最长公共前缀（LCP）在 A/B/C/D/R 五条序列上**全为 0**；仅还原
`rand_real()`/`rand_bool()` 两处后，LCP 立刻升为 A=2、B=26、C=10、D=50、R=50
（最长 50/102 字符，出现在 D 与 R），证明基准确实属于旧 RNG 语义。

**第 3 步 — 刷新基准并保持测试真实执行**：用本版本源码的**确定性输出**刷新基准
（先确认同 seed 重复运行逐字节一致；`-O0` 与 `-O3` 也逐字节一致，排除优化相关抖动）。
基准是整文件替换时，按仓库口径生成 **delete-item + add-item** 形态补丁并声明
`patch_strip: 0`，并用 `patch_ng` 库调用（而非仅 CLI）本地验证落盘字节。

**第 4 步 — 如实申报，并把外部引证连原始字节一起留档**：notes.md / PR 正文写清上游缺陷
编号、上游未迁移该测试的证据（0 字节 `tests/CMakeLists.txt`、ctest 注册数 0）、发行版忽略
语句、刷新前后 LCP 量化、跨平台逐行一致比对，以及刷新后该入口的真实计数
（dawg：TOTAL=1，PASS=1）。

这一步有一条**容易踩且被独立审计判 P1 实测命中**的硬要求：本模式的正当性高度依赖
**外部引证**（别的平台/发行版的复现记录），而外部链接随时可能不可达——dawg 实例中
该 issue 路径在设备网络下返回 404（`github.com` 主机本身可达，返回 200），抓取结果只有一个
9 字节的 `Not Found` 页；若只把
「据上游 issue #56 / Debian 打包记录」写成叙述而不留原始字节，审计者与评审者都无法复核，
整条「排除平台差异」的论断就退化为不可验证的断言（实测被判 R52 证据一致性 P1×2）。
正确做法：

1. 把每份外部证据的**原始响应字节**入库（放在包内 `reports/evidence/` 这类随 PR 提交的位置），
   逐份记录来源 URL、抓取时 HTTP 状态码与 sha256，并写清每一份**证明了什么**；
2. 优先选择**离线可复核**的来源。本例中 `debian/rules`（Debian 官方源码包内的文件）自身
   在注释里就写着上游缺陷编号，邮件列表归档里也有上游通知邮件的标题——这两条都不依赖
   github.com 可达性，比"直接读 issue 页面"更可复核；
3. **抓取失败也要原样留档**（404 的 9 字节响应一并入库），并在正文明确写"本任务未直接读到
   该页面、编号依据是另两条来源"，不得把未能复核的内容写成既成事实；
4. 同一事实的**所有出现点**（`conandata.yml` 的 patch_description、`conanfile.py` 文档串、
   包级/版本级 manifest、README、MANIFEST.yml、知识草稿）同步同一口径——只改一处会留下
   不一致（该编号会经 `patch_description` 进入 `conan` 构建日志，属对外可见面）。

```bash
# 跨平台复现（第二平台）：OHOS 与 Debian 输出逐行一致
./src/dawg tests/test0.dawg > actual.fasta && diff actual.fasta <debian-recorded-output>
# 外部证据留档：原始字节 + 来源 + HTTP 码 + sha256（失败抓取也留）
curl -sS -L -w '%{http_code}' -o debian-rules.txt \
  https://sources.debian.org/data/main/d/dawg/1.2-5/debian/rules
sha256sum debian-rules.txt
# 旧语义还原实验：把 rand_real()/rand_bool() 还原为旧版本语义后重编
cmake -S src -B build-old -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && make -C build-old -j1
build-old/src/dawg tests/test0.dawg > out.old   # 与旧基准 LCP 显著上升
# 刷新后测试必须真实执行且转绿
DAWG=<build>/src/dawg top_srcdir=<src> sh tests/test0.sh; echo "rc=$?  # 期望 0"
```

### 禁止做法

- ❌ 删除/跳过该测试入口，或把未做比对的结果记为 PASS——这是唯一的上游端到端轴，
  放弃即违反 R51（上游测试必须真实执行 + 如实回填）。
- ❌ 未经"非平台漂移"证明就用本机输出刷新基准——会把可能的移植缺陷写进基准（永久假绿）。
- ❌ 用 `__OHOS__` 之类平台宏分叉基准确立"平台专属 golden"——既违反 R8（补丁内平台
  条件编译默认禁止），又把差异掩盖成平台特性；E401 式的平台 oracle 变体只适用于
  "基准归属另一平台且本平台正确"的场景。
- ❌ 把外部引证（上游 issue 编号、发行版打包记录、邮件列表结论）当作既成事实写进文档，
  却不留可复核的原始字节——链接会失效、设备网络会 404，此时整条论断不可验证（实测被
  独立审计判 R52 证据一致性 P1）；同一事实的多个出现点只改一处同样会留下不一致。

## 验证

```bash
# ① ctest 注册数（证明上游确实未运行该测试）
wc -c tests/CMakeLists.txt && grep -c add_test tests/CMakeLists.txt   # 0 与 0

# ② 刷新后入口真实通过（不是空跑：程序输出需满足条数/结构断言）
DAWG=<build>/src/dawg top_srcdir=<src> sh tests/test0.sh && echo PASS
grep -c '^>' actual.fasta        # 5（树 ((A,B)D,C)R 的全部节点）

# ③ 确定性：同 seed 两次一致、换 seed 必变
```

## 关联条目

- 相关: E401（golden 由另一平台生成、本平台正确 → 加平台 oracle 变体，**不**刷新通用 golden；
  与本条处置方向相反，须先按"基准归属哪个版本/平台"分流）
