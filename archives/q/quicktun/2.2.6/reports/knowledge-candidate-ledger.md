# B 判定台账 —— quicktun/2.2.6

> 判据：`经验文档/手册/03-路径B与C.md` §6.2 第 80-89 行（家族命中判 `hit` 的四条件、
> `none` 也要写理由、组合型知识不判重）。
> 引用纪律：一律按 **文件名 + 行号**（`knowledge/drafts/` 里 E 号被大量复用，裸引 E 号即错）。
> 本轮实测环境：鸿蒙 PC B 机，worktree `feat/quicktun-2.2.6`，
> 探针/日志在 `~/tmp/uc2/z45-quicktun/`。

## 1. 候选机制清单（本包实际撞上的面）

| 代号 | 面 | 一手症状证据（本轮/第 1 棒实测） |
|------|----|--------------------------------|
| F1 | HMDFS 禁硬链接 ⇒ `build.sh` 的 `ln` 产出主程序名失败 | `~/tmp/uc2/z45-quicktun/artifact-probe.log:2-3`（`out/quicktun` 与 `out/quicktun.combined` inode 不同 ⇒ 实跑走 `|| cp` 分支） |
| F2 | 裸 shell 构建入口把编译器写死 `cc="cc"`，无 make/configure 覆盖点 | `~/tmp/uc2/z45-quicktun/build-asis.log:5` `build.sh[58]: cc: inaccessible or not found` |
| F3 | 上游用"编译器能否 `-lsodium`"探测加密后端，失败即**静默换成仓库自带 TweetNaCl**、退出码 0、照常产出全部二进制 ⇒ 声明依赖未被使用 | `build-asis.log:2-4`（`Building TweetNaCl...` + 那句性能提示）；归真正照 `reports/w3-local-ci.log:189` `Using shared libsodium.` |
| F4 | 取源面：官网 https 自签证书 / http 503 ⇒ 改取上游官方组织仓 commit 归档，并与发行 `.orig` 做逐文件等价证明 | `~/tmp/uc2/z45-quicktun/src-verify.log`（两个源的 code/size/sha256/聚合哈希/逐文件 diff 全在里面） |
| F5 | 运行期能力面：TUN 设备、`chroot`、`mknod`、`getpw*`、poll/ppoll、getaddrinfo 的真机读数 | `probe-caps.log`、`probe-caps2.log`、`probe-caps3.log` 与三份 `.c`（矩阵正文见 `notes.md` 的「能力矩阵」节） |

## 2. 四范围查重（检索式与计数）

范围口径：① worktree 全部 `knowledge/`（含 `doc/`、`graph/`、`drafts/`、`draft/`、
`operations/`、`recipes/`、根层）；② `knowledge/drafts/` + `knowledge/draft/`
单独再数一遍（**`draft-review` 的相似面只取 `knowledge/graph/index.tsv`、
不扫 `knowledge/drafts/`** ⇒ 该目录必须手工 grep）；③ 仓内 prescan / 规则件
（`ci/config/`、`ci/scripts/`、`scripts/ohc/`）；④ Windows 侧 `经验文档/B草稿库/`。

### 范围 ①②③（grep -rliE，计数为**文件数**，命中≠语义命中）

| 检索式 | ①`knowledge/` | ②`drafts`+`draft` | ③`ci/`+`scripts/ohc/` |
|--------|--------------|-------------------|----------------------|
| `tweetnacl` / `TweetNaCl` | 0 | 0 | 0 |
| `lsodium` | 0 | 0 | 0 |
| `链接期产物` | 0 | 0 | 0 |
| `静默降级` | 35 | 31 | 0 |
| `auto-detect`/`autodetect` | 12 | 9 | 3 |
| `假绿` | 71 | 71 | 0 |
| `DT_NEEDED` | 123 | 111 | 0 |

F3 轴的语义收窄（范围①内两集合取交集）：
`(假绿|静默降级|silently (degrade|fall|use)|falls? back)` ∩ `(断言|assert)`
= 143 ∩ 957 = **58 个文件**。58 条逐一扫面后，只有 5 条落在同一问题域，
逐条语义判定见下节。

### 范围 ④（`经验文档/B草稿库/`，池内 46 份文件）

检索式 `tweetnacl|bundled.{0,30}(fallback|instead)|静默(降级|换|改用)|链接期.{0,10}断言|专有符号`
⇒ **命中 0 份**；`sodium|hardlink|hard link` ⇒ **命中 0 份**。
池内与 F1/F2/F4 相邻的是 `DRAFT-PKG-VER-suckless-baked-paths-makevar-override`
（M18，裸 Makefile 烧死路径）、`DRAFT-PKG-VER-makefile-install-cmd-absent-makevar-override`
（M13）、`DRAFT-PKG-VER-prefer-make-dist-asset-over-tag-archive-for-submodules`（M17）。

## 3. 逐面判定（含层次差的行号对齐）

### F1 硬链接 —— **hit**

| 条件 | 核对 |
|------|------|
| ① 症状一致 | ✅ E079 的 `error_signature` 字面含 `ln.*Operation not permitted`（`knowledge/doc/E079.md:11`），本包 `build.sh:66` 的 `ln out/quicktun.combined out/quicktun` 在 HMDFS 上正是该读数 |
| ② 解法也被该条目覆盖 | ✅ 条目方法名 `command-substitute`、说明原文「将硬链接操作替换为复制（cp）」（`E079.md:20-22`）。本包补丁就是 `ln … 2>/dev/null \|\| cp …`。条目 line 27-30 的 `ac_cv_prog_ln_s` / `DESTDIR+cp -rP` 是 **make install 场景的示例**，不是唯一合法路径 |
| ③ 引用精确 | ✅ `knowledge/doc/E079.md:11,20-22`（复用方案=硬链接换 cp） |
| ④ 替代解法等效性 | 不涉及替换探测宏。等效性实测：cp 与硬链接在 `out/` 下产出**同内容、不同 inode** 的两个文件，上游与消费者都按文件名取用；inode 读数见 `artifact-probe.log:2-3`，L2 七个二进制 `--version` 全 OK（`reports/w3-local-ci.log:298-304`） |
| **结论** | **hit**（不占知识位、不建草稿） |

### F2 写死编译器 —— **hit**

| 条件 | 核对 |
|------|------|
| ① 症状一致 | ✅ `make: cc: No such file or directory` 的 shell 变体 `cc: inaccessible or not found`（`build-asis.log:5`），根因同：干净 PATH 下没有 `cc` 别名 |
| ② 解法已被覆盖 | ✅ `knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.md:58` 那一行就是本包的做法：`cc="${CC:-cc}"` + 「显式传 `CC=<conan conf c compiler>`（R33）」；其 `root_cause`（同文件 line 32）已写明「脚本 `${CC:-cc}` 的默认值在干净 PATH 下不可依赖」。本包只是把上游写死的字面量**改造成**该条目依赖的那个可覆盖形状，方法同一、无新路径 |
| ③ 引用精确 | ✅ `knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.md:32,58`；旁证 `knowledge/drafts/DRAFT-ohos-makefile-explicit-toolchain-and-install-vars.md:9`（`make CC=<profile compiler>`，其前提是"有 make"）与池草稿 M18（同理，前提也是 make） |
| ④ 等效性 | ✅ CC 取自 Conan `AutotoolsToolchain`（R33），未新增 `-I/-L` 之外的语义；补丁不改优化级别 |
| **注** | 本包"没有 make 也没有 configure"这一点看似比 M18 更进一层，但**它不产生新的处置路径**——补丁改 `\${CC:-cc}` 是 qbe 那条已经写下的形状，故仍判 hit |
| **结论** | **hit**（不占知识位） |

### F3 静默换后端 —— **create（本 PR 唯一的知识位）**

同一问题域的 5 条近邻，逐条对齐层次差（行号）：

| 近邻条目（文件名+行号） | 它的机制所在层 | 本包的差异（为什么不可复用它的解法） |
|------------------------|----------------|----------------------------------|
| `knowledge/drafts/DRAFT-libdv-tools-1.0.0-ac-check-lib-warns-instead-of-failing.kv:34,37,40,43`（处置哲学同为"build 阶段断言、把静默降级变构建期失败"） | 判据 = **`config.h` 里的 `#define HAVE_X`**（`rec_impl: assert-config-h-define-after-configure`），并配"运行期 `--version` 非空 / 裸跑不能 139"两道断言 | 本包**没有 `config.h`、没有 configure、没有任何中间配置文件**（上游只有 `build.sh` + `src/*.c`，23 文件清单见 `~/tmp/uc2/z45-quicktun/l-gh.txt`）⇒ 该判据无对象。其运行期断言在本包**恒不成立地通过**：TweetNaCl 版 `quicktun.keypair` 与 libsodium 版对同一标量给出**逐字节相同**的输出（`test_package/test_quicktun.c:14-16` 已把这条写成诚实边界）⇒ 无症可查 |
| `knowledge/drafts/DRAFT-ohos-optional-dep-silent-degrade-stub-api.md:22-24,80,84-92,94-102` | 判据 = 读 `configure.ac` 的 `PKG_CHECK_MODULES` 第三参（line 80「看第三参是 `AC_MSG_ERROR` 还是成功/失败分支」）；处置 = **定性→文档显式化→测试划界**，允许 `if downgraded: self.output.warning(...)`（line 94-102） | 本包既无 `configure.ac` 也无宏守卫；且降级形态不同——它 line 44-51 的降级是「一整块 API 变桩、运行期返回错误码」，本包降级是「**换成另一份功能等价的实现**」，能力面**不减**，只是**交付物与 `requires()` 声明不再一致**。该条 line 87-88 明令"若是 optional，不得为消除告警强行补依赖"+ line 104-108 的 priority-2 是"把可选依赖发布出来"；本包 libsodium **早已发布**、配方**显式 requires**，"warning + 划界"会把"声明 A 实际用 B"放过去 ⇒ 处置方向相反（硬失败，不是 warning） |
| `knowledge/drafts/DRAFT-E590-libyal-optional-dep-autodetect-ohos.md:10-18,37-52` | 假绿"只体现在 configure 摘要里"（line 16），取读数办法 = 先只跑一次 configure 读能力摘要（line 37-52） | 本包没有 configure，也就没有摘要可读；上游探测结论只 echo 一行 `Using shared libsodium.` / `Building TweetNaCl...`（`build.sh:38,50`），措辞随上游变，不能当判据 ⇒ 必须换成产物侧判据 |
| `knowledge/drafts/DRAFT-E2186-autotools-deps-missing-dep-flags.md:33-43` | 判据 = **编译命令行里有没有依赖的 `-I/-L`**（line 33-43 的实证就是贴出 compile 命令行） | 上游 `build.sh` 不回显编译命令行的探测阶段、也没有 `makeopts`/`config.log` 落盘；本包能拿到的只有 `out/*` 与 `obj/*.o` |
| `knowledge/drafts/DRAFT-E623-libheif-dav1d-1.23.0-plugin-consumer-contract-and-dlopen-signing.md:151-158` | 「负对照是本条最不该省的一步：只断言 AV1 解码可用，任何别的后端（含内置 fallback）都能让断言变绿」——**测试面**断言 | 同一原则，但落在 `build()` 之后的**产物**上而不是消费者测试上；本包把这条原则具体化为"选一个**只可能来自被声明依赖**的符号"，并证明它在整棵上游树里出现 0 次 |
| DT_NEEDED 族（`knowledge/` 内 123 个文件命中 `DT_NEEDED`，如 `knowledge/doc/E330.md`、`E502.md`、`E537.md`、`E465.md`） | 用 `DT_NEEDED` 核对依赖是否真被链接 | 本包实测**不可用**：`readelf -d` 的 NEEDED 只有 `libc.so`，libsodium 被 `build.sh` 以 `-lsodium` **静态折进**产物（`artifact-probe.log:6-14`：NEEDED 一行 + `crypto_generichash_blake2b` 等 73 个符号在表内）⇒ 判据只能是"符号是否被折进来"，不是"有没有 DT_NEEDED" |

七轴核对（本包 vs 上述近邻）：

| 轴 | 本包 | 最近邻（libdv 草稿） | 是否同轴 |
|----|------|---------------------|----------|
| 症状签名 | `Building TweetNaCl...` + `cc: inaccessible or not found` | `checking for poptGetContext in -lpopt... no` + 运行期 139 | 否 |
| 触发条件 | 裸 shell 脚本的链接探测失败 | autotools `AC_CHECK_LIB` 失败 | 否（同为"探测失败不失败"） |
| 根因层 | 探测即选型，无配置出口 | 探测即选型，结果写进 `config.h` | 部分同 |
| 降级形态 | **换成等价实现**、功能不减 | 功能块被预处理器裁掉、API 变桩 | 否 |
| 可用判据 | 只剩**链接期产物**（obj 缺席 + 依赖专有符号在位） | `config.h` 宏 + 运行期输出 | 否 |
| 处置方向 | 构建期 `ConanException` 硬失败 | 同为硬失败（+ 运行期断言） | 同 |
| 适用面 | 上游构建入口是无配置出口的裸脚本（ucis/Suckless 之外的第三类） | autotools CLI | 否 |

`hit` 四条件核对：① 症状签名与触发条件与任何既有条目**不相同**（`tweetnacl`/`lsodium`
全库 0 命中）；② 即便宽判为"症状相同"，本包用的也是既有条目没写的另一条解法
（产物级双断言），按手册 03 第 83 行「症状相同、但你用的是既有条目没写的另一条解法时
不算 hit，按 `create` 报」⇒ **create**。
另按手册 03 第 89 行「组合型知识不判重」：本条是
「探测即选型的裸脚本 + 无配置出口 + 静态折入导致 DT_NEEDED 失效 + 换等价实现导致
运行期无症可查」四件组合出的新解题路径。

**交付**：`knowledge/drafts/DRAFT-quicktun-2.2.6-bare-script-silent-backend-swap.{kv,md}`
成对提交，过真实解析器与 `draft-review`；Issue 由主理建（本代理不建）。

### F4 取源面 —— **create 候补，但本 PR 不占位**

- 与近邻不等价：`knowledge/drafts/DRAFT-monocypher-4.0.2-release-vs-tag-archive.md:5-26`
  讲的是**同一仓库** tag 归档与 release 资产的内容差（版本占位符/缺测试向量），
  解法是"换 release 资产 URL"；本包上游**没有 release 资产**（组织仓只有 commit 归档，
  树内还留着 `.hgtags` 说明上游主仓是 Mercurial），要新增的是"与官方 `.orig` 做
  逐文件 diff + `src/` 聚合 sha256 相同"这条**等价性证明方法**。
  其 line 42 的反例（"不得因下载失败回退个人 fork / 非官方镜像"）本包已遵守。
- 不占位理由：**一 PR 只占一个知识位**，F3 更贴主症状（`build-asis.log` 里
  TweetNaCl 分支被实跑到，直接决定"声明的依赖算不算数"）。
- ⇒ 记为候补，机制与证据（`src-verify.log` 全量读数）留在本台账与 `notes.md`
  的「取源」节，由主理决定是否写进 `经验文档/B草稿库/` 供后续包复用。
  **不判 hit**：对不上 monocypher 那条的行号语义（不同症状、不同判据）。

### F5 能力面 —— **hit（并附一条对该条目推论的否证）**

- 同签名先例：`knowledge/drafts/E2164-draft-ocserv-vpn-tun-boundary.md:16-21`
  —— line 16-18 三条读数（`open("/dev/net/tun", O_RDWR) → errno=13`、
  `stat /dev/net/tun → Permission denied`、`ls /dev/net/ → Permission denied`）
  与本包 `probe_caps3` 逐条同型；line 28 另有 `unshare(CLONE_NEWNET)` 被 `SIGSYS(31)` 打死，
  与本包 `chroot(".")` 的 `WTERMSIG=31` 同一拦截形态。
- ⇒ 判 **hit**，引用 `knowledge/drafts/E2164-draft-ocserv-vpn-tun-boundary.md:16-21,28`。
- **但要记一条修正**：该条 line 21 的推论「返回 EACCES 而非 ENOENT，说明设备节点存在」
  在本机**不成立**——存在性对照（`probe_caps3.c:107`：`open("/dev/net/definitely-not-a-device-zzq", O_RDWR)`）
  的读数同样是 `errno=13 EACCES`，而 `/dev/net` 连 `stat` 都是 EACCES ⇒
  本机上 EACCES 只能证明"不可达"，既不能证明节点存在、也不能证伪。
  已按实测定 `notes.md` 的能力矩阵（分列"被拒 EACCES"与"不存在 ENOENT"两类，
  后者本包唯一读数是 `access("/etc/nsswitch.conf", R_OK) → errno=2`）。
  软件级 `archives/q/quicktun/manifest.yaml` 原先那句「该节点存在但 open 被拒(EACCES)」
  一并改成与读数一致的说法。此修正属对既有条目的**订正**，不另占知识位。
- ⛔ 本台账与 notes 都不做"平台不支持/上游无替代后端"定性；定性归主理。

## 4. 最终 B 判定

```
B判定=create
机制：裸 shell 构建入口的"编译器探测即选型"失败会静默换成仓库内置实现且退出码 0，
      使 requires() 声明与交付物不一致；当 config.h / 编译命令行 / DT_NEEDED 三层
      判据都不可用时，唯一硬判据是链接期产物双断言
      （内置实现的目标文件不出现 + 只可能来自该依赖的符号在位）。
草稿：knowledge/drafts/DRAFT-quicktun-2.2.6-bare-script-silent-backend-swap.{kv,md}
其余面：F1 hit(E079)、F2 hit(qbe 草稿 line 58)、F5 hit(E2164 草稿 line 16-21)、
        F4 候补不占位（本 PR 只占一个知识位）
```
