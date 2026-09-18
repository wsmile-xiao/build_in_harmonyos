# DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect — 纯脚本包被 lang-preflight 结构性判为非 bash（c/env_unsupported 误报）

> Contributor: cumt-7 | Status: Draft | Updated: 2026-09-18
> Source: PR OpenHarmonyPCDeveloper/build_in_harmonyos!9928（d-shlibs 0.109 OHOS PC 适配）
> 对应 KV: `knowledge/drafts/DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect.kv`
> 类别: 一类问题（纯 bash/sh 脚本 + install-only / packaging-only Makefile 的零编译包），非单库补丁

## 主题 / 触发场景

仓库的主体是**可执行脚本**（无扩展名 + `#!/bin/bash` 文件头），构建系统的全部内容是
一个 **install-only / packaging-only Makefile**（`all:` 为空规则，只做 `install -m 755` 到
`$(DESTDIR)`），源码树内可能还带有 autopkgtest / `debian/tests` 的 C 夹具。这类包在
`ohc-run.py lang-preflight` 下会被判为 `detected_language=c`，与任务语言 `bash` 不匹配，
工具随即**自动写入终态 `env_unsupported`**。

命中本模式时最危险的两种错误处置：

1. 直接接受工具终态，把一个**本可完整适配**的脚本包放弃（或因 `detected=c` 迁移任务语言）；
2. 为了让检测器"满意"而**改写上游 Makefile / 删除 autopkgtest 夹具**——把工具缺陷掩盖成本地 workaround，
   上游零改动原则被破坏，且同类误判会在下一个包原样复现。

## 错误特征

`lang-preflight` 输出（d-shlibs 0.109 实测，逐字）：

```json
{
  "expected": "bash",
  "detected_language": "c",
  "language_evidence": {
    "build_system": "make",
    "manifest": "顶层 Makefile（无更强 manifest）",
    "source_stats": "源文件 1 个（c:1），主体占比 100%"
  }
}
```

同时任务被置为终态：

```
语言不匹配: task=bash, detected=c → env_unsupported
```

可复用字面签名（`|` 分隔）：

```text
语言不匹配: task=bash, detected=c → env_unsupported|detected_language": "c"|build_system.*make.*source_stats.*c:1
```

配套可观测事实（决定复核方向）：

- `grep -nE '^[a-zA-Z_-]+:' Makefile` → `all:` 后无配方行（空规则），只有 `install:` 拷贝脚本/man；
- 被统计的那个 `c:1` 是 `debian/tests/uppercase.d/libUppercase.c`——**上游 autopkgtest 夹具**，
  属 §D.4"辅助脚本/测试夹具不算主体"；
- 两个主体脚本 `d-shlibmove` / `d-devlibdeps` **没有扩展名**（只有 `#!/bin/bash` 文件头），
  语言统计按扩展名进行，永远计不进来。

## 触发条件

- 构建系统：顶层存在名为 `Makefile` 的文件，但 `all:` 为空 / 无 C、C++ 编译目标（install-only、packaging-only）
- 阶段：preflight（语言预检，R47）
- 仓库形态：主体为无扩展名脚本；或源码树内附带 `debian/tests`、autopkgtest 等测试夹具
- 平台：与平台无关（纯检测器行为），OHOS PC 上首次适配此类包即触发

## 根因分析

`lang_detect.py` 的三级判定对「纯脚本包」**结构上无解**，三级各有一处偏置，叠加后必然落到 `c`：

| 级 | 机制 | 在纯脚本包上的行为 |
|---|---|---|
| ① `_manifest_scan` | 顶层存在名为 `Makefile` 的文件即归入 `(c/cpp, make)` | 只看到文件名，**不检查 `all:` 是否为空、是否有 C 编译目标** → 误判为 C 构建系统 |
| ② `_source_stats` | 按扩展名统计主体语言，且把 `bash` 排除在 `total`/`dominant` 之外（§D.4 视 bash 为辅助脚本） | 主体脚本无扩展名 → 不计入；bash 被显式剔除 → 即便有 `.sh` 也不参与主体 |
| ③ 唯一计数 | `source_stats` 命中的 1 个 `.c` 文件 | 是 `debian/tests/uppercase.d/libUppercase.c`（autopkgtest 夹具），被当成 100% 主体 |

结论：该工具在「纯脚本 + install-only Makefile + 测试夹具」这一形态上**无法产出
`detected_language=bash`**——这是检测器启发式与 §D.4 边界规则的偏差，不是被测包的缺陷。

## 解决方案

### 推荐方案：按 R47 §D.4 边界规则人工复核后继续按任务语言适配

**第 1 步 — 判定构建系统是否真的编译 C/C++**：读顶层 Makefile 的目标表，
确认 `all:` 为空规则、无 `.c/.cpp → .o` 规则；若确有 C 编译目标，则本模式不成立（见回退方案）。

**第 2 步 — 判定被统计的 C/C++ 文件归属**：所有命中的 `.c/.cpp` 是否都位于
`debian/tests` / autopkgtest / `tests/` 等**夹具目录**；产品源码为空或仅夹具 → 属 §D.4"辅助不算主体"。

**第 3 步 — 判定主体语言**：主体是否为一组可执行脚本（无扩展名 + shebang）。
三项成立即判**工具误报**，任务语言 `bash` 成立，继续适配。

**第 4 步 — 如实留证，不改框架、不改上游**：
保留 `lang-preflight` 完整输出与它自动写入的 `env_unsupported` `result.json` 作为证据，
在 `notes.md` 的 `language_evidence` 三项与最终回报中写明复核依据，终态用 `result` 命令覆盖。
**不修改 `lang_detect.py`、不改写上游 Makefile、不删除上游夹具。**

```bash
# ① 构建系统是否真的编译 C/C++
grep -nE '^[a-zA-Z_-]+:' Makefile          # all/dbview/... ; 确认 all: 为空规则
# ② 被统计的 .c/.cpp 是否全部是测试夹具
find <src> -name '*.c' -o -name '*.cpp' | grep -E '/tests?/|debian/tests|autopkgtest'
# ③ 主体脚本（无扩展名 + shebang）
file d-shlibmove d-devlibdeps              # POSIX shell script / Bourne-Again shell script
# ④ 复核通过的判据：三项均成立 → 误报，按 bash 继续适配，保留工具输出为证据
```

### 回退方案：主体确非 bash 时如实上报

若复核后确认主体确为 C/C++（例如产品源码就是那批 `.c`，或 Makefile 含真实编译目标），
才按 `env_unsupported` 上报，并附 `detected_language` 与 `language_evidence` 三项，不得强行按 bash 适配。

### 禁止做法

- ❌ 未做 §D.4 复核即接受 `detected_language=c`，或据此把包判为 C 库 / 迁移任务语言——
  会把本可适配的脚本包误判为 `env_unsupported` 而放弃。
- ❌ 为消除误判而删除上游 autopkgtest / `debian/tests` 夹具，或改写上游 Makefile——
  违反上游零改动原则，且把工具缺陷掩盖成本地 workaround，知识无法复用。
- ❌ 把"检测器误报"写成"平台不支持 bash"——两者归因不同，后者会误导后续任务放弃整个脚本包类别。

## 验证

```bash
# 工具原始输出（证据，保留不删）
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight d-shlibs 0.109 --lang bash --src <src>
# → detected_language=c，工具自动写 env_unsupported

# 复核通过后，按 bash 适配并真实运行被测对象（d-shlibs: 两个 bash 脚本本体）
#   注：OHOS PC 镜像无 /bin/bash，脚本 shebang 为 #!/bin/bash，调用方须显式指定解释器
bash <prefix>/bin/d-shlibmove --help  ## 期望退出码符合上游语义
```

实测（PR #9928）：复核判误报后继续适配，`test_package` 26 条断言全过
（`RESULT: ASSERT_PASS=26 ASSERT_FAIL=0`）。

## 关联条目

- 来源: PR #9928 原始草稿 `knowledge/drafts/E6341-draft-E28B`（其 md 为空白模板、kv 的 `id` 为
  模板占位 `E6341`、含未替换的占位字段）；本条目即该判例的**类别化与补全**，kv/md 一一对应。
- 同类判例（同为 lang-preflight 统计/识别偏差，触发源不同，可互相参照）：
  - `DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect`（`GNUmakefile` 不被识别为构建系统 + 辅助 .py 计入主体）
  - `DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect`（辅助 `Cargo.toml` 被 manifest 扫描命中）
  - `DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect`（`doc/doxygen` 生成文档 `.js` 计入主体）
- 相关: E543、E156、E158（脚本/解释器与构建工具相关的既有判例）
