# E543 — C 库源码树附带 *.rockspec 触发 lang-preflight 误判 mixed（env_unsupported）

> 关联：配方 PR !8398（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/8398，分支 feat/hashchop-0.8-0）；
> 知识库扩展 Issue #2677；回填时 HEAD 5278e9cdd27ac5acaa85ae007882c6b9609108cb。

## 错误特征

对 Lua 生态的 C 扩展库运行语言预检：

```
❌ 语言不匹配: task=c, detected=mixed → env_unsupported
language_evidence:
  build_system: "luarocks"
  manifest: "*.rockspec 存在"
  source_stats: "源文件 5 个（c:4, lua:1），主体占比 80%"
notes: ["冲突: manifest=lua 但统计 c 占 80% → mixed"]
```

任务被自动写入终态 `env_unsupported`（result.json, draft:false），协议提示"不要硬着头皮适配"。

## 触发条件

- 任务语言 c（或 cpp），源码主体 C/C++ 占比 ≥ 70%。
- 源码树根**附带** `*.rockspec`（LuaRocks 打包描述文件）。
- 常见于"提供 Lua 绑定的 C 库"：hashchop 0.8-0（hashchop.c/lhashchop.c/bench.c/test.c + test.lua + hashchop-0.8-0.rockspec）。

## 根因分析

`scripts/ohc/lang_detect.py` 的 `_manifest_scan` 按文件名优先级判语言：

```python
if any(n.endswith(".rockspec") for n in names):
    return ("lua", "luarocks", ...)          # 优先级高于顶层 Makefile
if "Makefile" in names:
    return ("c/cpp", "make", ...)            # 永远轮不到
```

rockspec 是 LuaRocks 的**打包描述**（声明 modules、`lua >= 5.1` 依赖、`type = "builtin"` 编译方式），
不是项目主语言声明。当它存在时检测输出 `manifest=lua`，与源码统计（c 80%）矛盾，
按 R47 边界规则"manifest 与统计矛盾判 mixed"终态 env_unsupported——把可正常按 C 适配的库误杀。

## 解决方案

判定链（全部命中即判误报，继续按任务语言适配）：

1. **rockspec 内容核对**：`dependencies = { "lua >= 5.1" }`、`build.type = "builtin"`、
   `modules` 列出 C 源——只是打包描述。
2. **真实构建入口核对**：顶层 Makefile 默认目标（hashchop：`all: hashchop.o test bench`）
   不依赖 lua；`make -j1 CC=clang` + `./test` 可独立构建并全量通过上游测试。
3. **源码统计核对**：c 源 4/5（80%）主体；lua 仅 1 个绑定测试（test.lua），按"辅助脚本不算主体"规则不计。
4. **留证**：保留 lang-preflight 完整输出 + 自动写入的 env_unsupported result.json；
   任务真实终态上报时 `result --force` 覆盖 ECS 默认路径文件。

禁止动作：不删除/改名上游 rockspec（属篡改源码）；不在配方 PR 里改 lang_detect.py（框架只读）。

## 真实验证（hashchop 0.8-0，2026-09-05）

- 复现：`OHPCD_LANG=c python3 scripts/ohc-run.py lang-preflight hashchop 0.8-0 --src builds/hashchop-0.8-0.work`
  → `task=c, detected=mixed → env_unsupported`（输出全文存档）。
- 反证 C 路径可行：同目录 `make -j1 CC=clang && ./test` →
  `81 tests - 81 pass, 0 fail, 0 skipped (21.368 sec)`。
- Conan 路径可行：makefile 型配方 conan create 干净构建通过，conan-verify G0-G4/L2/L4/L5 全 PASS，
  test_package 5/5（真实调用 hashchop_new/sink/poll/finish/reset/free）。

## 适用范围与反例

- **适用**：C/C++ 为主体、rockspec 只是附带的 LuaRocks 打包描述的库；判定链 1-3 全命中。
- **反例**（不适用本条）：任务语言=lua 且包定位是 Lua 模块（lua 文件为主体，如 lua-microlight）——
  detected=lua 匹配或走平台语言迁移；任务语言与源码主体确实不符（如 Rust 项目标 c）——
  env_unsupported 是正确终态，保留证据停止。
- **解除条件**：若 lang_detect.py 后续把 rockspec 降级为弱信号（框架单独 PR 修正），
  本条判别流程自然失效，仅保留误报历史价值。

## 风险

- 人工复核误报必须落完整证据（预检输出 + 构建测试反证），否则"绕过语言门禁"无法服众；
  PR 正文需单列路径 B 知识贡献说明并关联 Issue。
- 平台侧若按 detected_language 做任务迁移，误报未及时澄清可能被挂起——发现即报用户。
