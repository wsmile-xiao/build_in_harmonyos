# DRAFT-werror-autotools：上游构建脚本硬编码 `-Werror`，clang/OHOS 交叉编译下告警升级为错误

- 条目主题：autotools / CMake 上游工程在构建脚本中硬编码 `-Werror`（总开关或逐项
  `-Werror=<flag>`），gcc 下可正常构建，**clang15（OHOS SDK 内置）** 把告警升级为错误导致编译失败。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：!14041（`archives/s/schism/20260524` 适配，本条目即由该库适配过程中实测产生）
- 配套产出物（同 PR，位于 `knowledge/drafts/werror-autotools/`）：
  `README.md`（定性）、`detect_werror.py`（检测）、`patch-templates/0003,0004`（处理策略）、
  `reproduce.sh`（双向复现）、`sample-evidence.log` / `sample-verification.json`（证据）

## 适用场景

上游构建脚本中存在 Werror 注入点，且工具链为 clang（OHOS 交叉编译）时命中。典型报错形如：

- `slurp.c:832:1: error: non-void function does not return a value in all control paths [-Werror,-Wreturn-type]`
- `error: unknown warning option '-Wfoo' [-Werror,-Wunknown-warning-option]`
- `error: variable 'x' set but not used [-Werror,-Wunused-but-set-variable]`

关键判据（两点同时满足）：

1. 构建系统为 autotools（`configure` / `configure.ac` / `Makefile.am`），或 CMake 工程显式
   `add_compile_options(-Werror)`；
2. 上游注入 `-Werror` 的位置**晚于**使用方注入的 `CFLAGS` —— 因此 `CFLAGS=-Wno-error`
   覆盖不到（schism 实测即为此顺序）。

## 诊断步骤

1. 对源码树跑检测脚本（按文件名分派规则，避免跨类型误报）：

   ```bash
   python3 knowledge/drafts/werror-autotools/detect_werror.py --src <解包源码目录>
   # exit 1 = 命中；加 --json 取 rule_counts / detail 供机器消费
   ```

2. 交叉核对命中行：`configure` 内的注入行（总 `-Werror` / 逐项 `-Werror=<flag>`）与
   `configure.ac` 的 m4 宏（如 `AX_CHECK_COMPILE_FLAG(-Werror=…)`）需分别处理。
3. 反向定位：已有失败日志时 `detect_werror.py --log <构建日志>`，日志内
   `[-Werror,...]` 行即确证。

## 处理策略（推荐方案）

用**配对补丁**剔除注入点，保留告警可见性（只去 `-Werror`，不屏蔽 `-Wall`）：

| 补丁 | 目标 | 说明 |
|---|---|---|
| `patch-templates/0003-disable-Werror-clang-strict.patch` | 生成的 `configure` | 剔除 `ADD_LUDICROUS`/`CFLAGS="$CFLAGS -Werror"` 类总开关注入行 |
| `patch-templates/0004-remove-per-flag-Werror.patch` | 生成的 `configure` | 正则批量剔除逐项追加（`CFLAGS="$CFLAGS -Werror=<flag>"` → `CFLAGS="$CFLAGS"`） |

模板为**模式参考**：目标行号须按检测脚本给出的 `file:line` 重新 diff，勿盲套。

回退方案：`CFLAGS="$CFLAGS -Wno-error"` **仅当**上游注入顺序早于使用方注入时有效；schism
实测顺序在其后，故本条目默认走补丁路径。

## 边界与局限

- 上游仅在运行时拼接、无固定行的，需按命中行定制 diff；
- 非告警类错误（真实编译错误、平台 API 缺失）与本条目无关，勿混用；
- 为过编译而整体关告警（`-w` / `-Wno-all`）**禁止**——会掩盖真实适配缺陷。

## 验证证据（样例库 schism 20260524）

```
variant-noskill（剔除 0003/0004）：conan create rc=1，落盘证据
  slurp.c:832:1: error: non-void function does not return a value in all control paths [-Werror,-Wreturn-type]
variant-skill（全量补丁）：      conan create rc=0，全流程通过
verdict = pass
```

检测脚本对同一源码树：`verdict=hit`（exit 1），`src_hits=42`（configure 30 / configure.ac 12）、
`log_hits=0`。

## 与既有条目的关系

`E007`（config.guess 无法识别 HarmonyOS）、`E013`（dlopen 等 libc 缺口）覆盖平台识别与
系统接口层；本条目覆盖**编译器严格性差异**层，三者互补，不重叠。同类关系：
`E007` 常与本条目在同一 autotools 工程中先后出现（平台识别失败 → 修好后再暴露 Werror 严格性）。
