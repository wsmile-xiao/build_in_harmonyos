# 子集数据包消费者验证：全树生效许可行精确不变量 + 引用自包含 + 负向锚点

- **草稿 ID**: DRAFT-ldraw-parts-free-2602-subset-license-invariant-probe
- **来源**: ldraw-parts-free 2602 HarmonyOS PC 适配（LDraw 零件库 DFSG 自由子集消费者探针）
- **分类**: conan / consumer-test / licensing / data-package / ohos
- **状态**: 本地草稿（路径 B 知识库扩展申请中，位于 knowledge/drafts/）

## 问题 / 错误签名

- **误报非自由**：自由子集文件内存在被注释掉的历史旧许可行 `0 // !LICENSE Redistributable under CCAL version 2.0 : see CAreadme.txt`（973pxis01.dat 第 145 行实证，LDraw 再授权历史记录）。按「全文不得出现 CCAL 子串」校验时，合法文件被误报为 `non-free license line`。
- **判定语义错位**：上游过滤工具 gendfsgsrc.py 只认首个 `0 !LICENSE` **生效行**（注释行 `0 //` 天然不匹配）；消费者测试若语义比过滤工具更严，探针自身成为错误来源。
- **可观测特征**：探针输出 `[BAD] parts/s/973pxis01.dat: non-free license line`，仅 1 个文件挂（其余 32240 个全过）。

## 根因

1. 自由子集的合规边界由「每文件生效许可行精确等于 CC BY 4.0 行」定义；
2. LDraw 再授权历史使许多文件保留被注释的旧许可行（`0 // !LICENSE ... CCAL`）——合法历史记录，非当前许可；
3. 第一版探针用全文子串检查（CCAL / 双许可），比上游过滤工具语义更严，误报合法文件。

## 最小修复方案

探针逐文件校验，许可判定取「首个生效许可行」语义：

```cpp
// 与 Debian gendfsgsrc.py 同语义：只认生效许可行（"0 !LICENSE" 前缀），
// 历史注释里被注释掉的旧许可行（"0 // !LICENSE ..."）不参与判定。
if (starts_with(s, "0 !LICENSE")) {
    if (s == kLicense) { has_license = true; break; }  // 首个生效行即判定依据
    return "non-free license line";
}
```

配套三件套（缺一不可）：

- **引用自包含**：同一遍读取收集全部 type-1 引用（第 15 token），对候选集 {引用名, 引用者目录/引用名, `p/`+引用名, `parts/`+引用名} 校验 0 缺失——验证祖先剔除没有留下悬空引用（368173 引用全部解析成功）；
- **被剔件负向锚点**：被剔除的著名非自由件（2412b/10048/10928/car/pyramid/textures）必须不在包内；
- **注入负向用例**：CCAL 许可样本写入包目录 → 校验拒绝 → 清理，证明执行器真实读写且生效行判定仍拒绝非自由。
- **消费者端到端用例（审查规则要求）**：静态检查再多不算跑通功能——需一条与真实消费流同构的端到端用例：载入装配体 → 引用递归解析至图元 → 图元几何载入 → 颜色对照（LDraw 实例：3001 装配图 10 文件 / 25 引用 / 三角 16 + 四边形 46，真机实证）。

单遍全读（格式 + 许可 + 引用收集同一次文件遍历）使 32241 文件全树校验在真机秒级完成。

回退方案（仅 shell 工具链时）：`grep -Rhv '^0 //'` 先过滤注释行，再对剩余行做 CCAL/双许可子串检查与精确 CC-BY-4.0 行计数——语义等价，代价是多一遍全树读取；注意 CRLF 先剥 `\r`。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本机（Windows MinGW）· 按 package() 布局 1:1 模拟包 | 修复前：973pxis01.dat 误报；修复后：执行器 7 用例全过（`TEST SUMMARY: 7 passed, 0 failed`） |
| HarmonyOS PC aarch64 真机 · Conan 2.29.1 | conan create test_package EXIT=0，消费者测试执行器 7 用例全过（`TEST SUMMARY: 7 passed, 0 failed`，含渲染管线端到端，见 archives/l/ldraw-parts-free/2602/reports/） |

## 禁止策略

- 禁止全文任意行含 "CCAL version 2.0" / "CC BY 2.0 and CC BY 4.0" 子串即判非自由——注释历史行是合法记录，全文子串检查语义比上游过滤工具更严，合法文件误报、探针必红。
- 禁止为过测试而放宽许可校验（如只抽查部分文件）——全树不变量正是 free 子集的定义性质，抽查即失守。
- 禁止只验许可不验引用完整性 / 只做正向锚点不做被剔件负向锚点——子集正确性三件套缺一即可能混入非自由内容或产出断裂库。

## 相关

- 关联经验：姊妹包 ldraw-parts 2602（完整库）探针为「全树格式校验 + 精确计数」口径；本条目为自由子集增加的「许可不变量 + 引用自包含 + 负向锚点」三层强化。
