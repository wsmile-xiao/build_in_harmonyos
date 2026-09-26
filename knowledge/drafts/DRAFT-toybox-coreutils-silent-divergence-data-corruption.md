# DRAFT: toybox base64 默认 76 列换行且 sed -i 替换符号链接本体——静默数据损坏需输出规整与解析目标编辑

- slug: toybox-coreutils-silent-divergence-data-corruption
- 分类: musl/libc 与 toybox 差异（B 机理分层: L1 平台语义）
- 实例库: kworkflow 0.10（案例）
- 状态: 草稿（最终编号 Exxx 由知识库主编确认）

## 一句规则

toybox 对 GNU coreutils 的偏离不只有"Unknown option"显式拒绝（E402/E188 族），还有命令 rc=0 但输出/副作用静默偏离的"静默族"：base64 默认 76 列换行（无 --wrap=0）、`sed -i` 替换符号链接本体（无 --follow-symlinks 等价物）、GNU date 字符串算术完全缺失（bad date）——消费单行 token、原地编辑符号链接目标、日历算术的脚本工具会无声损坏数据或丢失功能，必须做输出规整/解析目标编辑/诚实降级，而不是只盯报错。

## 机理链（工具证据 → 触发 → 失败点 → 归类）

1. base64：toybox base64 无 `--wrap=0`，默认 76 列换行（探针：100 字节输入 → 2 行）→ 命令 rc=0，输出从单行 token 变多行 → 消费方（如 base64(PWD) 作环境标识）在第一个换行处断裂（实例失败点：kw env --create/--use，探针 rc=22）→ 归类：toybox 静默输出偏离。
2. sed：GNU `sed --in-place --follow-symlinks`（编辑跟随链接的目标）无 toybox 等价物 → 裸 `sed -i` 以普通文件替换符号链接本体（探针可见：link.txt 变普通文件）→ 破坏"配置文件以链接共享"的上游语义（实例失败点：remote.config 与 kw env 的链接联动）→ 归类：toybox 静默副作用偏离。
3. date：`date -d '2026/01/01'`、`date -d 'X - N day'` 均 `bad date`，仅 `-d @epoch` 可用 → 日历算术类功能（周/月统计）不可桥接 → 归类：平台能力缺失，降级 + 能力诉求登记。

## 方案空间

- rec：①单行 token 场景 `base64 | tr -d '\n'` 输出规整；②需保持链接语义时封装 sed_in_place()——`-L` 探测、`readlink -f` 解析目标后编辑目标；③其余长选项差异按 E402 手法改等价短选项（sort -d / ln -sf / rm -rf / sed -i -r / grep -x / cut -d -f / date -d @ / diff 丢弃 --color=always）。
- fallback（诚实权衡）：无桥接可能的差异（GNU date 算术）不伪装修复——manifest/conandata/README 登记能力诉求 + 相关上游测试逐条排除（附探针证据），可用子集（epoch 秒级换算）明确圈出；这是"掩盖面最小"的退路而非修复。
- forbid：①按平台名 if 分支绕过（判据应是工具能力探测，违反 P005/P013）；②认为 rc=0 即输出可信、不给 base64/sed 输出加断言（静默族只有输出偏离，损坏在下游才炸）。

## 自包含 verification_cmd（OHOS 设备新 shell 可跑）

```sh
head -c 100 /dev/zero | tr '\0' 'a' | base64 | wc -l    # toybox=2（GNU=1）
date -d 2026/01/01                                       # toybox: bad date
ln -sf real.txt link.txt && sed -i '1s/.*/x/' link.txt && ls -l link.txt
# toybox: link.txt 变普通文件
```

## 挂钩与泛化

- affected_scope: 任何在 OHOS 上以 base64 输出作单行 token、对符号链接目标做原地编辑、或依赖 GNU date 字符串算术的脚本工具与测试（不限 shell 项目，任何调起 coreutils 的构建/测试脚本同理）。
- principles: P005（补丁必须可向上游提交）、P013（平台限制必须降级而非绕过）。
- similar_to: E402（显式拒绝族同手法）、E188、E010（install-gnu-tools 退路）、E043、E161/E106（coreutils 管道语义）。

## 与既有条目的差异（新增价值）

既有 toybox 族条目全部覆盖"显式拒绝族"（Unknown option 报错即暴露，改短选项即可）；本条覆盖"静默族"（rc=0 无报错、输出/副作用偏离、数据延迟损坏），桥接手法为输出规整与解析目标编辑，date 类不可桥接差异登记为降级分支——为知识库补上"脚本工具看似成功却损坏数据"这一排查盲区。
