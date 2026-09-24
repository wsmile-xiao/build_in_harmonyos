# E543-draft-27D5 — 纯 Zsh 生态包在 lang-preflight 中零覆盖

> 草稿（draft）。来源：zgen 0-20150919 适配（分支 `feat/zgen-0-20150919`）。
> 配对数据文件：`knowledge/drafts/E543-draft-27D5.kv`

## 现象

对纯 Zsh 项目跑 R47 语言预检，得到：

```json
{
  "detected_language": "other",
  "language_evidence": {
    "build_system": "none",
    "manifest": "未发现语言 manifest 文件",
    "source_stats": "无源文件可统计"
  },
  "notes": ["无可统计源文件"]
}
```

而该项目的源码其实全部是 Zsh：

```
LICENSE  README.md  _zgen  zgen.zsh
```

若按默认任务语言（`cpp`）执行 `lang-preflight`，会 exit 2 并**自动写入终态
`env_unsupported`**，一个完全可以交付的包就此被挡在门外。

## 根因

`scripts/ohc/lang_detect.py` 对 zsh 生态零覆盖，三级判定同时落空：

| 判据 | 为什么落空 |
|---|---|
| manifest | zsh 包没有 `package.json`/`Cargo.toml`/`pyproject.toml` 一类语言 manifest |
| 构建系统 | 没有 `Makefile`/`CMakeLists.txt`/`meson.build`/`configure` |
| 源码统计 | `_EXT_LANG` 只有 `.sh`/`.bash` → `bash`，**没有 `.zsh`**；补全函数按约定叫 `_<命令>`（如 `_zgen`），**无扩展名**，同样不计入 |

于是 `total = 0`，`dominant = None`，判定退化为 `other`。

还有一层协议问题：协议 §4.6 的语言枚举里**没有 `zsh`**。`bash` 与 `zsh` 不等价——
`typeset -f`、`emulate -L zsh`、`setopt`、`#compdef`、`${1[1]}` 这些 zsh 专有语法在
bash 下都不成立，所以把任务语言填 `bash` 属于谎报，而不是“近似”。

矛盾之处在于：本仓库已经有 6 个同形态 zsh 包合入 main——`zinit`、`zimfw`、
`zsh-autopair`、`zsh-autocomplete`、`zsh-git-prompt`、`zsh-history-substring-search`。
规则会拦掉实践中明确接受的包类型。

## 处置

1. **先零副作用预判**，不要直接让 CLI 写终态：

   ```bash
   python3 -c "import sys;sys.path.insert(0,'scripts');\
   from ohc.lang_detect import detect_language;print(detect_language('<源码目录>'))"
   ```

2. 确认判定为 `other` 后，**按检测结果如实申报**并继续适配：

   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight <软件> <版本> \
       --src <源码目录> --lang other        # => milestone=lang_checked
   ```

   既不谎报 `bash`，也不因工具零覆盖放弃一个可交付的包；理由与证据写进 `notes.md`。

3. 按 **zsh 生态打包范式**产出配方：

   | 要点 | 做法 |
   |---|---|
   | 解释器 | 补丁把 `#!/bin/zsh` 改为 `#!/usr/bin/env zsh`（OHOS 无 `/bin/zsh`；无平台宏，不触发 R8/PF5） |
   | 主脚本 | 装到 `share/<pkg>/`，置可执行位 |
   | 补全函数 | `_<命令>` 装到 `share/zsh/site-functions/`，并 `runenv_info.prepend_path("FPATH", ...)` |
   | package_id | `self.info.clear()`——解释型脚本与 arch/compiler/build_type 无关 |
   | 门禁 | `package_type="application"` + 软件级 `commands.json`（`binary:false`）满足 PF8/R38 |
   | 测试 | 用构建机 zsh 实跑（`zsh -n` + `source` 后调用公开子命令）；**无 zsh 时显式 warning skip，不记为通过** |

## 禁止

- ❌ 给纯 zsh 项目填 `--lang bash`：bash 与 zsh 语法不兼容，字段失真会连锁误导后续决策。
- ❌ 为迎合检测器在源码树里加 `.sh` 壳文件或把 `.zsh` 改名——改写上游结构属本地
  workaround，补丁虚增且知识不可复用。

## 建议的框架侧改动（供主编参考）

1. `_EXT_LANG` 增加 `.zsh`/`.zsh-theme`/`.plugin.zsh`，或新增“shell 族”聚合（sh/bash/zsh/fish）。
2. 统计阶段对**无扩展名文件读首行 shebang**（`#!/…/zsh`、`#!/…/bash`）或识别 `#compdef` 头。
3. 协议 §4.6 枚举补 `shell`（或允许 `bash` 表示整个 shell 族并在 evidence 里写明具体解释器）。

## 查重

- `DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect`：纯 bash + install-only
  Makefile **被错判成 `c`**；本条是**统计面为空判 `other`**、且枚举里没有 zsh，触发路径与
  处置口径都不同，故另立条目并在 `similar_to` 互引。
- `E483`：codeload 快照 URL 导致 `BadZipFile`，同一次适配中命中，属源码下载面，无重叠。

## 验证

```bash
# zgen 0-20150919：按 --lang other 申报后完整走通
python3 scripts/ohc-run.py conan-verify zgen 0-20150919     # G1/G2 PASS
# test_package: 18 布局断言 + 7 功能断言 + 1 语法检查 = 26/26
```
