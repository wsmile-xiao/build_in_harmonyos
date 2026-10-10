# DRAFT-12776 — 官方 conan-verify G4 与 conan 2.29.1 的 JSON 形状不匹配：L2/L4/L5 静默跳过但判 PASS

> 状态：草稿（来自 kea-admin 3.0.3 适配，task_id=12776）

## 问题

`scripts/ohc/conan_verify.py`（官方 runner，模板逐字未改）在 conan 2.29.1 下产生**假绿**：

- G4 执行 `conan list <ref>:* --format=json` 后按 `listing["Local Cache"][self.software][self.ref]["revisions"]` 解析；
- conan 2.29.1 的实际形状是 **平铺**：`{"Local Cache": {"kea-admin/3.0.3@ohpcd/stable": {"revisions": {...}}}}`；
- `["kea-admin"]` 抛 KeyError，被 `except (KeyError, IndexError, StopIteration)` 吞掉，G4 只追加一行 `⚠️ 无法找到程序包 ID`（passed 仍为 True）；
- `_cache_path` 未赋值 → **L2 冒烟 / L4 安全扫描 / L5 产物基线全部输出 `⏭️ 跳过（无 cache 路径）`**，最终 verdict 仍是 PASS。

即：报告看起来全绿，实际三项门禁从未运行。任何用该 runner 验证的包都受影响（不止脚本包）。

## 根因

runner 假定的文档层数（software 名 → 完整引用）比 conan 2.29.1 实际输出多一层；解析失败被宽泛 except 降级吸收，报告不做失败标记。

## 方案

驱动侧在 runner 解析前转置 JSON（保持 runner 逻辑零改动）：

- `_conan` 包装：对 `list ... --format=json` 的返回，若 `["Local Cache"]` 下缺 `self.software` 键而存在以 `<name>/` 开头的完整引用键，则重建为 `{"Local Cache": {name: {full-ref: {...}}}}`；
- 配合**先清缓存**（`conan remove <ref> -c`）保证只有一个 revision/package，G4 的 `list(...values())[0]` 取值无歧义。

上游建议修法：从实际 dict 键推导 software/ref（或兼容两种形状）；解析失败应判 G4 FAIL，而不是降级继续。

## 验证

- kea-admin 3.0.3（task 12776，2026-10-04，conan 2.29.1）：
  - 修复前：G4 `⚠️ 无法找到程序包 ID`，L2/L4/L5 全部跳过；
  - 转置后：G4 解析出包 ID，L2 真正冒烟 `bin/kea-admin`、L4 扫描（脚本包无 ELF → 通过）、L5 首次落基线，报告逐门禁有实质结论。

## 适用边界

- 所有使用 scripts/ohc/conan_verify.py 的验证（与语言/构建系统无关）。
- 判定方法：报告里同时出现 `无法找到程序包 ID` 与 L2/L4/L5 `跳过（无 cache 路径）` 即命中。

## 查重差异

- 与 **E478**（conan-verify 无法解析点号版本号的 package ID，G4/L2/L4/L5 跳过）同一症状族（「无法找到程序包 ID」+ 跳过仍判 PASS）但机理与修法不同：E478 是**点号版本号**打爆 G2 日志提取正则致 _package_id 为空；本条目是 conan 2.29.1 的 `conan list --format=json` **文档形状漂移**（runner 期望多一层 software 嵌套 vs 实际平铺完整引用键）。缓解手段也不同：E478=手动 `conan cache path`；本条目=解析前 JSON 转置 + 先清缓存。`similar_to: E478`
- 与 E618/E622/E666 等"包级 `conan list` 用法"条目不同：本条目是**平台 runner 自身与 conan 版本的形状漂移**，特征是假绿（跳过的门禁不计入失败），修复在工具层。
- 与 DRAFT-E683（pkgconfig 可选特性）等无关。

## 关联交付

- 本草稿与 `archives/k/kea-admin/3.0.3/**` 同属一次交付（驱动脚本 ka_verify2.py 为验证侧附件）。
- 正式 E 编号由知识库主编审核后分配。
