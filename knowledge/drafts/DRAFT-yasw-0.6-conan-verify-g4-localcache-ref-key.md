# DRAFT-yasw-0.6-conan-verify-g4-localcache-ref-key：G4「无法找到程序包 ID」的第二机制

> Contributor: ohc-worker | Status: Draft | Updated: 2026-09-21
> Source: yasw 0.6 适配 conan-verify（`## G4: ✅ PASS` 但 `L2/L4/L5 ⏭️ 跳过`）
> 对应：`knowledge/drafts/DRAFT-yasw-0.6-conan-verify-g4-localcache-ref-key.kv`
> 相关：**E478**（同症状、不同机制）

## 现象

`conan-verify` 走到 G4 即报：

```
## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
```

四个门禁**都标 PASS**，但 G4 与 L2/L4/L5 实际上**一个都没执行**。

## 根因（实测）

`scripts/ohc/conan_verify.py::gate4_artifact_integrity`：

```python
rc, list_out = self._conan(["list", self.ref + ":*", "--format=json"], timeout=30)
listing = json.loads(list_out)
pkgs = list(listing["Local Cache"][self.software][self.ref]["revisions"].values())[0]["packages"]
```

而 Conan **2.29** 的实际输出（实测本机）：

```console
$ conan list "yasw/0.6@ohpcd/stable:*" --format=json
{
    "Local Cache": {
        "yasw/0.6@ohpcd/stable": {          ← 唯一键 = 完整 ref，没有软件名中间层
            "revisions": { "18ab16f0f7eb99ae2ec5effffb538604": {
                "packages": { "0f8defcd8d7c98a4819c11895b0843c9bb571858": { … } } } }
        }
    }
}
```

`listing["Local Cache"]["yasw"]` → **KeyError** → 被
`except (KeyError, IndexError, StopIteration)` 捕获 → 打印「⚠️ 无法找到程序包 ID」并
**以 `passed=True` 提前 return**；`self._cache_path` 未赋值 → L2/L4/L5 全部跳过。

## 影响范围（非本包特有）

仓库内**几乎所有归档包**同款。抽样实测：

| 归档 | G4 详情 |
|---|---|
| `abiword-plugin-pdb/3.0.8` | `✅ PASS / ⚠️ 无法找到程序包 ID` |
| `abook/0.6.1` | 同 |
| `adobe-source-sans/3.052` | 同 |
| `airspyhf/1.6.8` | 同 |
| `aiven-client/4.16.0` | 同 |
| `allow-html-temp/10.1.1` | 同 |
| **`yasw/0.6`** | 同 |

即：**默认**没有产物完整性检查、没有平台冒烟（L2）、没有静态安全扫描（L4）、没有产物基线对比（L5）。

> 与 **E478** 区分：E478 是 G2 用正则 `(\w+/\w+@\w+/\w+):(\w+)` 提取 package id 时，
> `\w+` 不匹配**含点号的版本号**。yasw 版本号 `0.6` 含点号 ⇒ **E478 的缺陷也命中**
> （实测该正则在 `reports/conan-create.log` 上返回 `None`）。
> 两者是同一症状族的**两个独立机制**，可同时发生。

## 处置（本包口径：不改共享工具）

`scripts/ohc/` 属共享框架 → 单包 PR 不得修改（R21 文件权限边界 / W2 PR 原子性）。
本包采取**等价补偿**：自行取 package id → 拿 cache path → 手工执行 L2 等价冒烟。

```bash
# 取 40 位 package id（"Local Cache" 下唯一键就是完整 ref）
conan list "yasw/0.6@ohpcd/stable:*" --format=json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); ref=next(iter(d['Local Cache'])); \
                rev=next(iter(d['Local Cache'][ref]['revisions'].values())); \
                print(f'{ref}:{next(iter(rev[\"packages\"]))}')"
# → yasw/0.6@ohpcd/stable:0f8defcd8d7c98a4819c11895b0843c9bb571858

conan cache path yasw/0.6@ohpcd/stable:0f8defcd8d7c98a4819c11895b0843c9bb571858
```

随后复用配方自带 `test_package/test.sh` 执行 3 个消费者用例 → **3/3 用例、9/9 断言通过**
（含 GUI `offscreen` 真实启动，退出码 124）。证据：`archives/y/yasw/0.6/reports/yasw-0.6-l2-smoke.log`。

**正解**（另开框架 PR）：把取键改为取 `"Local Cache"` 的唯一键 ——
`ref = next(iter(listing["Local Cache"]))`。

## 禁止

1. 不得因为 G4/L2/L4/L5 标 PASS 就认为"产物已充分验证" —— 实为**门禁未生效**。
2. 不得在本包 PR 中夹带 `scripts/ohc/conan_verify.py` 的修改（违反 R21 / W2）。
3. 不得把"跳过"改写为 FAIL 以强制人工介入（R24：CI 门禁不可绕过，且会影响全仓基线）。
