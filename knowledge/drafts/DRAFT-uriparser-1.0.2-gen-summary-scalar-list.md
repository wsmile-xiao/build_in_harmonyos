# DRAFT-uriparser-1.0.2-gen-summary-scalar-list：gen_summary 简单 YAML 解析器对列表键标量值调用 append 崩溃

> Contributor: pc1-52 executor round | Status: Draft | Updated: 2026-08-29
> Source: uriparser 1.0.2 R05 完整 finish（授权 goaccess 基线隔离窗口内）实测复现，共享框架问题

## 现象

`ohc-run.py finish <软件> <版本>` 的 step 8/10 `gen_summary` 失败，输出：

```text
ℹ️ Step 8/10: 生成 SUMMARY.md...
⚠️ gen_summary 失败: 'str' object has no attribute 'append'
```

完整 traceback 定位到 `scripts/ohc/summary.py`：

```text
File ".../scripts/ohc/summary.py", line 455, in generate_summary
    archive_entries = _scan_archives_dir(archives_dir)
File ".../scripts/ohc/summary.py", line 394, in _scan_archives_dir
    manifest = _parse_yaml_simple(manifest_path)
File ".../scripts/ohc/summary.py", line 89, in _parse_yaml_simple
    data.setdefault(current_list_key, []).append(item)
AttributeError: 'str' object has no attribute 'append'
```

已知触发清单（对全仓 4385 个 `archives/**/manifest.yaml` 逐一复测，恰好命中 2 个）：

- `archives/q/qpdf/12.3.2.1/manifest.yaml`
- `archives/q/qpdf/12.3.2/manifest.yaml`

## 根因

`_parse_yaml_simple` 用 `data.setdefault(current_list_key, []).append(item)` 收集
缩进的 `- ` 列表项。Python `setdefault` 在键已存在时**不会替换**已有值；当某个
`manifest.yaml` 中同一列表键此前被该简单解析器读成**标量字符串**（`data[key]` 为
`str`）时，`setdefault` 返回该 `str`，随后调用 `.append` 即抛
`AttributeError: 'str' object has no attribute 'append'`（summary.py:87-89）。

由于 `generate_summary` 全仓扫描 `_index.yaml` 与 `archives/**/manifest.yaml`，
任何仓库中存在上述清单形态都会使 step 8/10 失败——与当前库无关，属共享框架解析器缺陷。

## 最小本地复现

```sh
# 未修复框架时（R05 实测，uriparser 工作区根目录）
python3 -c "from scripts.ohc.summary import generate_summary; generate_summary(pdir='.')"
# -> AttributeError: 'str' object has no attribute 'append' (summary.py:89)
```

## 最小临时修复原则

在缩进 `- ` 列表项处 append 前将键值强制为 list：

```python
if not isinstance(data.get(current_list_key), list):
    data[current_list_key] = []
data[current_list_key].append(item)
```

该修复仅使解析器对既有键值类型鲁棒（幂等、无行为回归），不改动任何 manifest 数据语义。

## 验证结果（R03-R05 三次实测一致）

- 修复后对 4385 个 manifest.yaml 扫描：`'str' object has no attribute 'append'`
  触发器归零。
- `generate_summary` 正常输出（约 363446 字节）。
- uriparser 1.0.2 完整 finish 在授权 goaccess 基线隔离下：W3 阻塞门禁通过
  （JC_RESULT=pass, Junk Files=0, L0-L5 pass, Build Summary 100% 1/1），
  `.ci-result.json` exit_code=0；完整 finish 首错仅为该框架 step 8/10
  （外加 step5b 知识完整性警告），无当前库失败。

## 还原 / 零 diff 要求

`scripts/ohc/summary.py`（及被成功生成的 `SUMMARY.md`）属共享框架/生成物，验证后必须
逐字节还原：修改前记录原始 sha256 与 git blob，还原后核对哈希匹配，并证明其在
staged/unstaged/untracked/cached/committed 与最终 diff 中零残留。本知识草稿不申请
任何框架改动入 PR、不虚构 Issue 号/PR 链接/发布状态/框架交付声明。

## 适用边界

适用于所有 `archives/**/manifest.yaml` 中存在"列表键值被简单解析器读成标量"形态的库，
以及任何执行完整 finish（触发 gen_summary 全仓扫描）的库。uriparser 1.0.2 仅是该
缺陷被观测到的验证上下文：其配方、conan 验证、W2、W3（基线隔离下）全部通过，
该错误不构成 uriparser 配方/测试缺陷。