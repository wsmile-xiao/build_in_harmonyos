# werror-autotools — 上游 autotools 硬编码 `-Werror` 在 clang/OHOS 交叉编译下的共性阻塞

## 问题定性（Step1：一类共性问题，非单库补丁）

大量 autotools 上游工程在 `configure.ac` / 生成的 `configure` / `Makefile.am` 中**硬编码注入
`-Werror` 或逐项 `-Werror=<flag>`**（常见于 "add -Werror if supported" 探测宏，如
`AX_CHECK_COMPILE_FLAG(-Werror=return-type)`、`SCHISM_CHECK_COMPILE_FLAG` 等）。
gcc 下可正常构建；**clang/OHOS 交叉编译**（aarch64-linux-ohos clang15）对告警更严格，
同一份代码在 gcc 只产生 warning 的位置被升级为 error，直接编译失败。

典型报错特征（B 类证据，样例库实测）：

```
slurp.c:832:1: error: non-void function does not return a value in all control paths [-Werror,-Wreturn-type]
```

触发条件（同时满足即命中）：
1. 构建系统为 autotools（configure/configure.ac），或 CMake 工程显式加 `-Werror`；
2. 工具链为 clang（OHOS SDK 内置 clang15），且上游 flag 注入晚于使用方注入（无法用
   `CFLAGS=-Wno-error` 覆盖——顺序在其后）。

与既有知识条目的关系：E007/E013 等条目覆盖 config.guess 平台识别、dlopen 等 libc 缺口，
**未覆盖 Werror 严格性差异**；本条目填补该空白。

## 产出物清单（四件套，缺一不可）

| 产出物 | 文件 | 说明 |
|---|---|---|
| ① 检测脚本 | `detect_werror.py` | 自动扫描源码特征（按文件名分派：`configure` / `configure.ac` / `Makefile.am` / `CMakeLists.txt` 各取适用规则）与构建日志特征（`[-Werror...]` 报错行）；命中输出规则分布 + 策略建议，无需人工干预；`--json` 供机器消费 |
| ② 处理策略（补丁模板） | `patch-templates/0003-disable-Werror-clang-strict.patch`、`patch-templates/0004-remove-per-flag-Werror.patch` | 0003 剔除 configure 中总 `-Werror` 注入行；0004 剔除逐项 `-Werror=<flag>` 追加（正则批量替换 `CFLAGS="$CFLAGS -Werror=xxx"` → `CFLAGS="$CFLAGS"`）。适用方式：按检测脚本列出的命中行位置套用模板重 diff |
| ③ 复现脚本 | `reproduce.sh` | 双向验证：①不启用 SKILL（剔除 0003/0004 补丁）→ conan create 失败并落盘 `[-Werror]` 证据；②启用 SKILL（全量补丁）→ conan create 通过。全程日志重定向到文件（规避 SIGPIPE，绝不直接管道 head），退出码显式捕获 |
| ④ 样例演示库 | `archives/s/schism/20260524` | 双向验证已实测通过（见下"样例验证"），配方 + 4 补丁 + 鸿蒙消费者测试完整 |

## 样例验证（Step4 实测，schism 20260524）

```
noskill_rc = 1（未启用：conan create 失败）
werror_evidence_lines = 1（slurp.c:832 [-Werror,-Wreturn-type]，见 werror-evidence.log）
skill_rc   = 0（启用：conan create 全流程通过）
verdict    = pass
```

检测脚本实测（同一源码树，`--src schismtracker-20260524`）：

```
verdict = hit（exit 1）
src_hits = 42（按文件名分派后规则分布：configure 30 处 / configure.ac 12 处）
log_hits = 0（无 --log 参数时不计 B 类证据）
```

复现命令（在 build_in_harmonyos 仓库根执行）：

```bash
bash knowledge/drafts/werror-autotools/reproduce.sh \
    archives/s/schism/20260524 "$HOME/tmp/werror-repro"
# 输出 reproduce-result.json：verdict=pass 即双向验证成立
# 注意：输出目录勿用 /tmp —— 本平台 /tmp 只读（E002 陷阱），须用 $HOME/tmp 或工作区内目录
```

检测命令（对新库快速判定是否受影响）：

```bash
# 默认人读摘要（verdict / 命中数 / 规则分布 / 前若干命中行）
python3 knowledge/drafts/werror-autotools/detect_werror.py --src <解包后源码目录>
# 机器可读：--json 输出完整 JSON（含 rule_counts、detail、detail_truncated）
python3 knowledge/drafts/werror-autotools/detect_werror.py --src <解包后源码目录> --json
# exit 1 = 命中（应用补丁模板）；exit 0 = 干净；exit 2 = 参数/环境错误
```

## 使用方法（适配流程内接法）

1. `init-build` 后、`conan create` 前对源码跑 `detect_werror.py`；
2. 命中 → 按模板制作 `patches/0003-*` / `patches/0004-*`（目标行号按检测输出的 file:line 重 diff），
   注册进 conandata.yml；
3. 正常走 conan create / finish；W3/CI 失败日志出现 `[-Werror` 时也可反向用
   `detect_werror.py --log <日志>` 定位。

## 适用范围与局限（边界）

适用：
- autotools 工程在 configure 脚本/m4 宏中注入 `-Werror`（总开关或逐项宏）；
- CMake 工程显式 `add_compile_options(-Werror)`（源码特征同可检出，补丁模板需按 CMake 语法改写）。

不适用/局限：
- 上游仅在 Makefile 运行时拼接且无固定行的，需按命中行定制 diff（模板为模式参考而非盲套）；
- `-Wno-error` 环境变量方式仅当上游注入顺序先于外部 CFLAGS 时有效——clang 严格性报错
  在 flag 顺序不可控时必须走补丁（本 SKILL 策略选补丁即因 schism 实测顺序不可控）；
- 非告警类错误（真实编译错误、平台 API 缺失）与本条目无关，勿混用。

## 平台约束

- 脚本仅用 Python3 标准库 / POSIX shell，无本地绝对路径、无终端缓存依赖；
- 工具链由 conan profile（ci/conan/profiles/ohos-aarch64）决定，使用项目内置 clang；
- 所有输出重定向到文件，规避 SIGPIPE。
