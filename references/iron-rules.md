> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# 十四条铁律与 AI 执行风格规范

来源: SKILL.md §1.2

## 十四条铁律（违反任何一条都是 bug）

| # | 规则 | 正确做法 | 禁止 |
|---|------|---------|------|
| R1 | **参数最少化** | `./configure --prefix=$P && make` | 加 `--build/--host`/CFLAGS hack |
| R2 | **Phase 3 不生成 .patch** | 只改源码+记录到 PROGRESS.md | diff/sed 结果写文件 |
| R3 | **补丁只用 ohc-run.py refresh-patch** | `ohc-run.py refresh-patch --auto` | 手动 diff/AI 写 patch |
| R4 | **危险库必须静态编译** | ncurses `--without-shared` | 编译共享库导致系统崩溃 |
| R5 | **软链接必须验证可执行 + 禁止 ln -sf** | `ls -la` 验证 + `rm -f && ln -s` | 只检查 `-L` 存在性 / `ln -sf` 覆盖 |
| R6 | **禁止修改生成文件** | 只改 configure.ac/CMakeLists.txt/*.c/*.h（源码层） | sed 改 configure/Makefile/Makefile.in（不可复现） |
| R7 | **安全弹窗必须先触发再测试** | make install 后 `find $DEFAULT_PREFIX/bin -exec {} --version \;` 扫一遍 | 直接跑 make check 不触发弹窗→进程被杀→假阴性 |
| R8 | **源码修改"四不"准则** | `#ifdef __OHOS__` 守卫 / 保持上游风格 / 追加平台分支 | 删跨平台代码 / 硬编码路径 / 改原逻辑流 / 偏离代码风格 |
| R9 | **质量门禁 FAIL 禁止标 success** | ohc-run.py verify-build 非零 → partial 或 failed | 产物有问题仍标记成功分发 |
| R10 | **临时文件必须用 $TMPDIR** | 所有 tmp 文件操作使用 `$TMPDIR` 或 `$HOME/tmp` | 硬编码 `/tmp`（鸿蒙 /tmp 只读，见 E002） |
| **R11** | **脚本步骤失败必须先查归档再动手** | 读 `archives/{pkg}/{ver}/README.md` + `manifest.yaml` 获取历史方案 | 直接手动摸索 / 忽略已有补丁和解决方案 |
| **R12** | **遇到错误必须先匹配错误模式再修复** | 搜索 `knowledge/error-patterns.md` + 同类软件 manifest 的 known_issues | 凭直觉试错 / 重复踩已知坑 |
| **R13** | **脚本调用必须使用完整路径** | `python3 $SKILL_ROOT/scripts/ohc-run.py <command>` | `./scripts/xxx` 相对路径（工作目录不固定时调用失败） |
| **R14** | **脚本失败=手动模式入口，非终止** | 失败时按提示切换手动模式，完成后 `--resume-from=StepN` 继续 | 脚本 exit 后 AI 放弃/什么都不做（如 automake 会话） |

---

## R8 详细说明：源码修改"四不"准则

> **核心原则：你的修改对非鸿蒙平台必须是透明的。**
> **检验方法：去掉所有 `#ifdef __OHOS__` 块后，上游代码应与原始 tarball 一模一样。**

| 不 | 含义 | 错误示例 | 正确做法 |
|----|------|---------|---------|
| **不破坏上游逻辑** | 不删除/反转/改变原有代码行为 | 删除某个 `if (linux)` 分支 | 用 `#elif defined(__OHOS__)` 追加新分支 |
| **不破坏跨平台兼容性** | 不删除其他平台的已有适配 | 删掉 `#ifdef _WIN32` 块因为它"用不到" | 保留所有平台守卫，在旁边加 `__OHOS__` |
| **不绕过鸿蒙标识机制** | 不硬编码平台特征 | `if (strstr(path, "/usr/local") != NULL)` | `#ifdef __OHOS__` + config.guess/sub 统一处理 |
| **不偏离上游代码风格** | 缩进/命名/注释风格与项目一致 | 项目 4 空格你用 tab | 读周边 50 行代码，保持一致 |

### 常见反模式（绝对禁止）

```bash
# ❌ 硬编码路径 — 换设备就挂
sed -i 's|/usr/bin|/data/local/tmp/usr/bin|g' Makefile

# ❌ 删除跨平台检测 — 破坏 macOS/Windows 构建
sed -i '/case.*darwin/d' config.sub

# ❌ 条件注入 — 无法 upstream
echo "#define OHOS_FIX 1" >> config.h

# ✅ 正确方式：平台守卫 + 可 upstream
# 在 configure.ac 中追加:
#   AC_CHECK_DECLS([__OHOS__], [ohos_fix=1])
# 在 C 代码中:
#   #if defined(__OHOS__)
#   /* 鸿蒙特定修复 */
#   #endif
```

---

## AI 执行风格规范

> **原则：在鸿蒙 toybox ash 环境下，复杂 shell 脚本是地雷区。保持简单。**

### 测试脚本原则

| ✅ 推荐 | ❌ 禁止 |
|---------|--------|
| 每个测试一条独立的 `[ ] && echo OK \|\| echo FAIL` | 单次 tool_call 写 >30 行复杂 shell 脚本 |
| 变量先赋值再使用，避免管道内嵌套命令替换 | heredoc（与 `curl \| sh` 冲突，toybox ash 支持差） |
| 用 `$TMPDIR/$HOME/tmp` 替代 `/tmp`（R10） | `for desc cmd exp in ...` 多变量循环 + 引号嵌套 |
| `grep -F` 做固定字符串匹配（防正则元字符陷阱） | grep 不加 `-F` 匹配含 `()` `[]` `$` 的输出 |
| `case "$var" in *pattern*)` 做 shell 原生模式匹配 | 复杂 awk/sed 管道做简单字符串判断 |
| 逐条顺序执行，每步可独立验证 | 一次性提交大量命令，出错后难以定位 |

### configure/make 长时间命令

```bash
# ✅ 正确：给足够 timeout，不提前中断
cd $BUILD_SRC_DIR && ./configure --prefix=$TEST_PREFIX 2>&1 | tail -3
#   autotools 项目 timeout=600s, 其他 timeout=300s

# ❌ 错误：频繁中断重启（浪费每次 3-10 分钟的 conftest 编译）
```

### configure 预期耗时参考

| 构建系统 | 典型软件 | 预期耗时 | 说明 |
|----------|---------|---------|------|
| autotools | 小工具(sed/grep) | 3-8 min | 大量 conftest 编译 |
| autotools | 大型(gcc/bash) | 10-20 min | 更多特性检测 |
| cmake | 一般项目 | 1-3 min | 较快 |
| meson | 一般项目 | <1 min | 最快 |

⚠️ **首次 configure 必须等完成**（用于触发安全弹窗确认）。timeout 建议：autotools ≥600s，其他 ≥300s。

---

## 失败处理标准流程（R11+R12 强制执行）

> **任何脚本步骤失败或编译错误触发时，必须按以下顺序执行。跳过任何一步都是 bug。**

```
脚本/编译步骤失败
  │
  ├─ [R11] 第一步：查归档记录
  │   │
  │   ├─ ① 读 archives/{pkg}/{ver}/README.md
  │   │    → 已有完整方案？（补丁/特殊构建方式/gen-all.pl 等）
  │   │    → 有 → 直接使用历史方案重新执行
  │   │    → 无 → 继续 ②
  │   │
  │   ├─ ② 读 archives/{pkg}/{ver}/manifest.yaml
  │   │    → status=success？说明之前成功过，对比差异
  │   │    → patches_applied 有补丁？确认是否已正确应用
  │   │    → knowledge_gained 有经验？参考历史做法
  │   │
  │   └─ ③ 读 archives/{pkg}/README.md（软件级）
  │        → 其他版本的通用经验（如 automake 的鸡生蛋问题）
  │
  ├─ [R12] 第二步：匹配错误模式（⭐ 使用知识图谱引擎）
  │   │
  │   ├─ ① **引擎匹配**（推荐，v4.8+）
  │   │    → 从错误日志提取关键词
  │   │    → Phase A: grep 关键词于 graph/index.tsv → 候选集
  │   │    → Phase B: 加载候选 graph/E*.kv → error_signature 精确匹配
  │   │    → Phase C: 读取 rec_*/forbid_*/fallback_* 方案
  │   │    → Phase D: principles 原则过滤
  │   │    → Phase E: 输出结构化修复方案
  │   │    → 命中？→ 直接用推荐方案修复 ✅
  │   │
  │   ├─ ② 快速查找（备选）
  │   │    → grep -i "关键词" knowledge/graph/index.tsv
  │   │    → 找到 E 编号 → 读 knowledge/doc/E{NNN}.md
  │   │
  │   └─ ③ 人类浏览（备选）
  │        → 阅读 knowledge/error-patterns.md 总览表
  │        → 按 E 编号查找对应条目
  │
  │   └─ ② 搜索同类软件的 manifest.yaml（同 build_system）
  │        → autotools 项目怎么处理的？→ 参考其 configure 参数
  │        → 同类错误别人怎么修的？→ 直接复用方案
  │
  └─ [诊断完成] 第三步：基于历史方案动手修复
      → 如果归档和知识库都没有 → 记录为新问题（§2.5 实时知识提取）
      → 修复后更新 PROGRESS.md + 继续执行
```

### 典型反面案例（automake 会话实录）

```
❌ build-driver Step 3 失败（unknown build system）
   → 放弃 build-driver，手动 ls 目录找 configure
   → 手动跑 configure → config.guess 不识别
   → 从 GNU FTP 下载最新版 → 还是不识别
   → 试 --build 参数 → 用户杀掉进程

✅ 正确流程（遵循 R11+R12）：
   → build-driver Step 3 失败
   → [R11] 读 archives/a/automake/1.16.5/README.md
      → 发现：需要 gen-all.pl 鸡生蛋绕过 + 已有补丁
   → [R11] 读 manifest.yaml → status=success, 有 0001-port-for-ohos.patch
   → [R12] 错误是 config.guess 不识别 → E002 标准解法：应用已有补丁
   → 应用补丁后重新跑 build-driver → 通过
```

```
