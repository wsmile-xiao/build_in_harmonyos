# DRAFT-ohos-signed-so-inplace-rewrite-dlopen-denied: 对已签名 .so 的 package() 内原地改写使签名失效，dlopen 报 Permission denied

> **Contributor**: GoliWie | **Status**: DRAFT (pending editor review) | **Updated**: 2026-09-13
> **Source**: kio 6.14.0 HarmonyOS PC 适配（build_in_harmonyos，archives/k/kio/6.14.0，run kio-6.14.0）+ 2026-09-13 path-update 补证轮判别实验
> **重构说明**: 本条目重构自 DRAFT-ohos-hmdfs-elf-rewrite-exec-deny（已删除）。旧版把根因归为"HMDFS W^X：创建后被改写的 ELF 被 security.isolate 标签拒绝 exec"——判别实验证伪了该机理，见下。

## Scope（何时用）

在 OHOS 真机上做 conan 包适配时，凡在 `package()`/打包阶段对**自带
.codesign 签名的 ELF 做内容改写**（patchelf `--replace-needed`/
`--set-soname`/`--set-rpath`、strip、objcopy、in-place 二进制改写），随后
加载该 .so 出现：

```text
Error loading shared library /storage/.../p/lib/libXXX.so: Permission denied
```

（musl loader 报 EACCES；`readelf`/`file`/属主/权限位全部正常。）

## 根因（判别实验实证，2026-09-13）

**判别因素是 .codesign 签名有效性，不是 HMDFS xattr 标签。** 实验设计
（KIO r1/r2 双产物 + 自包含最小探针双路验证；日志
`tmp/oh-device-porting-v2/kio-6.14.0/logs/wxexp-discriminating.log`、
`wxexp-minimal-probe.log`）：

| 对象 | 字节来源 | xattr（isolate/hmdfs.perm/selinux） | dlopen |
|------|----------|--------------------------------------|--------|
| A. r2 改写产物的普通副本 | patchelf 改写后的发布包 .so | 三项在场 | **Permission denied** |
| B. A 的 E077 四步重签版（同 inode） | 同上，仅 remove-section→重签→chmod | 三项在场（**逐字节相同**） | **OK** |
| C. r1 未改写产物副本 | 未改写的发布包 .so | 三项在场 | OK |
| D. 负对照：仅 remove-section 不重签 | 同 B 的前身 | 三项在场 | **Permission denied** |

四行对照中 xattr 恒定不变而加载结局两分，标签机理（旧版表述
"标签在场即拒绝 exec"）被证伪；唯一样本差异是签名有效性：
改写→失配→拒载；重签→恢复→可载；未签→拒载。
字节复制到新 inode 不改变结局（无效签名随字节走）。

补充观察（同日志 stage4）：已被 dlopen 过的 inode 对 patchelf 的写打开报
`open: Operation not permitted`，对同一文件的新副本则正常——构建后改写
必须在**首次加载之前**完成（或对新副本做后换名）。该写入门的域/触发面
未穷尽（ssh 会话域实测），按观察记录、不作机理论断。

## 附加危害：worker 依赖型静默 no-op（假阳性交付）

seed recipe 常见写法 `subprocess.run(["readelf", ...])` +
`except OSError: continue`：CI worker PATH 上没有 readelf 时整个改写步骤
**静默跳过**——产物保持绝对路径 DT_NEEDED 状态、测试居然还能过（绝对路径
在构建机上恰好存在）；换到有 readelf 的 worker 上，同一配方立刻产出整体
不可加载的包。**同一配方、两类 worker、相反结论**：判断"改写是否真的
发生"必须看日志里 patchelf 的输出行数，不能看 CI 结论。

## 修法

- **主方案：前移链接期**（link-time-fix-forward）。SONAME 修复见
  DRAFT-cmake-harmonyos-platform-soname-flag（本 run 以 patch 0015
  `LINK_OPTIONS "-Wl,-soname,<实际产物文件名>"` 落地，4 个 KIO 主库
  L5 门清零）；路径形态 DT_NEEDED 用链接期 `-Wl,-rpath-link`/显式 .so 输入。
- **退路：E077 四步重签**（诚实权衡：多两步签名/改段、量产需批量脚本、
  必须在首次 dlopen 之前；掩盖产物形态而非根因）。工具可用性本 run 已验：
  binary-sign-tool / llvm-objcopy（~/.harmonybrew/bin）、patchelf
  （/data/service/hnp/bin）。

## 确认去重证据（可复跑命令与逐项划界）

检索命令（2026-09-13 于 worktree 根目录真实执行，设备 grep 不支持 BRE
`\|` 交替——静默零命中，必须用 `-iE` 或单模式）：

```sh
cd <worktree>
for p in "hmdfs" "patchelf" "isolate" "Permission denied" "soname" "abstract.{0,3}namespace|abstract namespace"; do
  echo "$p: graph=$(grep -riEl "$p" knowledge/graph | wc -l) files, drafts=$(grep -riEl "$p" knowledge/drafts | wc -l) files"
done
```

实测计数：hmdfs graph=81/drafts=179；patchelf graph=10/drafts=13；
isolate graph=27/drafts=17；Permission denied graph=87/drafts=67；
soname graph=16/drafts=40；abstract namespace graph=1/drafts=3。
（此前会话用 `grep 'a\|b'` 去重，全部静默零命中，检索无效——本次为有效重扫。）

graph 中 patchelf 命中文件逐一核对：E042、E077、E088、E186、E383、E509、
E518、E537（principles.kv/index.tsv 非条目）。与本条目最近邻的五项逐项差异：

| 条目 | 处理面 | 与本条目的边界 |
|------|--------|----------------|
| E077 | post-install 改写 ELF（RPATH/strip）致签名失效，四步重签流程（executable 侧重） | 本条目把同一机理落到**共享库 dlopen + 发布包 package() 内改写**场景，新增：worker 静默 no-op 假阳性、链接期前移主方案、标签判别证伪；退路直接复用 E077 流程 |
| E517 | 已发布包 .so 带消费端不接受的签名，dlopen Permission denied | 同一加载面；E517 记录现象与消费端隔离修法；本条目给出**成因判别实验**（改写→重签闭环）与**预防方案**（不改变发布包字节），并澄清与标签无关 |
| E212 | hmmac 按路径标签阻止用户路径 .so 的 dlopen | 症状同形（dlopen Permission denied）。本条目实验证明本场景中标签**不是**判别因素（两种结局标签相同）；划界探针=做 E077 重签：能恢复→本条目面；不能恢复且路径标签异常→E212 面。E212 的修法（装到 hnp 路径）不修复签名失配 |
| E453 | HMDFS 模式位投影（group-write 位）导致 mode 相等校验误判 | 同属"HMDFS 语义被误判为缺陷"族，但对象是权限位校验，与 ELF 加载无关；本条目的 forbid_2 与其共享"勿把平台语义当缺陷修"态度 |
| DRAFT-E077B-ohos-sdk-autocodesign-invalid | SDK 链接器自动插入的 .codesign 占位段**从未有效**（可执行文件 exec 被拒） | 触发面不同：E077B 是"生而无效"，本条目是"改而失效"（r1 未改写产物可载证明发布签名在本设备可被接受）；补救同为 E077 四步 |

另与 E461（AF_UNIX bind EPERM → abstract namespace）无涉：不同错误面
（测试环境 socket），其相关内容归 headless-test-env 经验材料，不进入本条目。
DRAFT-cmake-harmonyos-platform-soname-flag 是本条目的**上游诱因**条目
（库为何缺 SONAME→为何有人想 post-build 改写），两文互链。

## principles 挂钩

- P-SIGN-001（ELF 签名必须与运行环境匹配）：签名失配即拒载的直接依据。
- P-PACK-001（修改 ELF 的操作后必须重新签名）：退路方案的流程依据。
- P-HMDFS-001（HMDFS 限制必须用替代方案）：HMDFS 面限制不硬顶，用链接期替代。
- P-BUILD-001（平台限制必须降级而非绕过）：禁止以 chmod/重试绕过签名门。

## 申报定位

- B 申报域：构建系统语义/工具链行为（签名与加载器语义）。
- 机理分层：L1（平台加载器/签名语义，单库发现即可申报，阻塞面=运行失败，
  有真实 dlopen Permission denied 日志与判别探针）。
- 本 run 配额使用：主条 1 条（本条目）；次条 0 条
  （cmake-soname 面按重复判定并入既有草稿实例段，不占独立申报；
  headless-test-env 维持经验仓降级）。
