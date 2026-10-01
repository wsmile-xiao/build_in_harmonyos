# DRAFT-qconf-2.5-langpreflight-c-cpp-share-misdetect

## 基本信息

- **触发工具**: `ohc-run.py lang-preflight`（`scripts/ohc/lang_detect.py`）
- **阶段**: preflight / language-detection（R47 协议 v0.8 附录 D）
- **软件**: qconf 2.5（`feat/qconf-2.5` 任务）— 纯 qmake 工程
- **严重度**: 2
- **类别**: preflight / language / tooling / qmake / conan

## 错误特征

```
detected_language = "mixed"
任务标记 cpp，实测源码为 mixed（none）……
源文件 6 个（cpp:4, c:2, bash:1），主体占比 67%
→ exit 2 + 自动写 result.json(status=env_unsupported)
```

## 复现

```bash
python3 scripts/ohc-run.py lang-preflight qconf 2.5 --src <qconf-2.5-src>
# → detected_language=mixed，exit 2
```

源码构成（qconf v2.5）：

| 扩展名 | 数量 | 文件 |
|---|---|---|
| `.cpp` | 4 | `src/qconf.cpp`、`src/stringhelp.cpp`、`conf/conf4.cpp`、`conf/conf.cpp` |
| `.c` | 2 | `src/configexe/configexe.c`、`src/configexe/embed.c`（Windows 专用 stub） |
| `.sh` | 1 | `package.sh`（辅助脚本，D.4 不计主体） |
| `.pro` | 4 | `qconf.pro`、`conf/conf4.pro`、`conf/conf.pro`、`src/configexe/configexe.pro` |

## 根因

两个缺口叠加：

1. `_source_stats()` 只按扩展名分别统计 `c` 与 `cpp`，主体占比 `share = max(c, cpp) / total`
   → qconf = `max(2, 4)/6 = 67% < 70%`。
2. `_manifest_scan()` 不识别 **qmake**（无 `*.pro` / `qmake.conf` 分支），而 qconf 仓库是纯 qmake
   工程（无 CMakeLists / configure.ac / 顶层 Makefile / meson）→ 返回 `build_system=none`、
   `m_lang=None`，`family_manifest=False`，失去「c/cpp 族内再分」兜底。

于是落到 `elif dominant is not None: detected = "mixed"`，触发 R47 的 `exit 2` 与自动终态。

按 R47 附录 D.4「**C/C++ 混编按主体判 c 或 cpp（不算 mixed，E13）**」以及
「c↔cpp 视为兼容族不迁移（conan 流程通吃）」，`c + cpp` 合并占比 = **6/6 = 100% ≥ 70%**，
主体为 C++（`qconf.pro` / `src/qconf.cpp`，Qt5 控制台工具）→ 正确判定应为 `cpp`。

## 处置（本次实际采用）

1. 不采信 `mixed` false-negative 终态；统计扩展名并合并 c+cpp 占比（100%），确认唯一构建入口为 qmake。
2. 判定 `detected=cpp`（与任务语言同族）→ 继续适配主流程。
3. 证据写入 `archives/q/qconf/2.5/notes.md`「语言预检处置记录」；登记本工具缺陷草稿。
4. 未删改上游任何文件。

## 修复建议（框架 PR，需单独提交）

```python
# ① _source_stats: c/cpp 合并计数（族内再分）
combined = counts.get("c", 0) + counts.get("cpp", 0)
# ② _manifest_scan: 增加 qmake 探测分支
if any(n.endswith(".pro") for n in names) or "qmake.conf" in names:
    return ("c/cpp", "qmake", _clip("顶层 *.pro / qmake.conf 存在"))
```

## 同族条目

- `DRAFT-cmsis-dsp-1.18.0-lang-preflight-pyproject-python-misdetect`（同根因：`_source_stats` 未合并 c+cpp）
- `DRAFT-E592-libyal-root-pep517-langpreflight-mixed-misdetect`
- `DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest`

## 来源

- `archives/q/qconf/2.5`（qconf 2.5 HarmonyOS PC 适配，纯 qmake 工程）
