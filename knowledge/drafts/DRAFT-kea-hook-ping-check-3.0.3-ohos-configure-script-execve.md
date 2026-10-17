# DRAFT-kea-hook-ping-check-3.0.3: OHOS 内核拒 shebang execve——Meson 配方 configure 期脚本执行的三层修法与 patch-ng 行号陷阱

- **条目 ID**: `DRAFT-kea-hook-ping-check-3.0.3-ohos-configure-script-execve`
- **严重度**: 2（🟡 中等）
- **类别**: meson, shell, configure, conan, python, patch, portability, ohos
- **触发工具/阶段**: meson | conan | patch — configuration / build
- **来源**: kea-hook-ping-check 3.0.3 适配（feat/kea-hook-ping-check-3.0.3，OHOS PC aarch64）
- **路径**: Path B（知识库扩展）

## 症状

kea-hook-ping-check 3.0.3（Meson 单工程构建）真机 conan create 连续四轮在同一族
症状上递进失败：

```
# 第 1 层（build() 调 meson 之前就死）
conan create Error 126: /bin/sh: <conan 缓存>/bin/meson: Permission denied

# 第 2 层（meson setup 过程中，上游源码内部）
Running command: scripts/env.sh KEA_PKG_TYPE_IN_CONFIGURE
ERROR: Unhandled python OSError. This is probably not a Meson bug ...（Error 13）
Configuring config.report with command            → 同上
Configuring config_report.cc with command         → 同上

# 第 3 层（补丁应用阶段，与脚本无关但同轮出现）
WARN: 0003-meson.build.patch: hunk no.2 doesn't match source file at line 1022
      expected: b'CONFIG_REPORT = configure_file('
      actual  : b'config_report_sh = configure_file('
```

## 根因

1. **内核层**：OHOS PC 内核在 execve 系统调用层拒绝带 shebang 的脚本执行
   （与文件可执行位无关；`sh 脚本` 能跑，直接 `./脚本` 或经 subprocess 裸名
   exec 都报 EACCES→conan 侧 Error 13；经包装层报告为 Error 126）。
2. **工具链层**：Conan 制品仓的 meson 包 `bin/meson` 是 shell 包装脚本
   （`exec python3 .../meson.py`），不修的话 build() 第一步就死。
3. **上游源码层**：Kea 3.0.3 顶层 `meson.build` 用 `find_program()` 直接指认
   脚本并在 configure 期执行：`ENV=scripts/env.sh`（探包类型）、
   `GRABBER=scripts/grabber.py`（9 处文件列表探针）、`CD_AND_RUN=scripts/
   cd-and-run.sh`、`command: [TOP_BUILD_DIR/'config-report.sh']`（**configure_file
   现场生成的**脚本）、`src/lib/process/cfgrpt/meson.build` 的
   `command: [tools/mk_cfgrpt.sh, ...]`。每处都是 execve 直呼脚本。
4. **补丁层**：conan 的 patch-ng 引擎把每个 hunk 行号解释为「已打过**先前补丁
   文件**的源」中的位置（0001 在 165 行 +6 行 → 1022 变 1028），且实测**不累计
   同文件先前 hunk 的行数增量**；而 git apply 按 pristine 坐标解释。同一份多
   hunk 补丁在 git apply --check 下通过、在 conan 应用时被拒。

## 最小复现

```meson
# 顶层 meson.build（pristine 行号 125/1022）
ENV = find_program(TOP_SOURCE_DIR / 'scripts/env.sh')
CONFIG_REPORT = configure_file(output: 'config.report', input: config_report_sh,
    command: [TOP_BUILD_DIR / 'config-report.sh'])   # 现场生成的脚本也要 sh 包
```

OHOS 真机 `meson setup` 必炸在上述任一 exec 点；补丁里若第二个 hunk 还写
pristine 行号 `@@ -1022`，conan 应用时在「1022（已含 0001 的 +6）＝
config_report_sh」处 mismatch。

## 已试过的失败方案

1. 只给脚本 chmod +x：与执行位无关，无效。
2. 只修 `build()` 的 meson 调用：setup 死在上游 `run_command(ENV, ...)`。
3. 逐点改每个 `run_command(ENV, ...)` 调用点：调用点十几处且散在子目录，改
   不干净，下一次崩溃点总在下一个文件。
4. 按 pristine 行号写多 hunk 补丁、用 git apply --check 验证：本地全绿，真机
   patch-ng 报 hunk mismatch（行号语义不同）。

## 解决方案

- 第 1 层：`build()` 用 `sh "<meson 包>/bin/meson"` 前缀（sh 读脚本不触发
  execve；内部 exec 的 python3 是 ELF 正常执行）。
- 第 2 层：**改变量不改调用点**——把 `ENV/CD_AND_RUN` 重定义为
  `['/bin/sh', <脚本>]`、`GRABBER` 重定义为 `[find_program('python3')
  .full_path(), <脚本>]`，所有 `run_command(变量, ...)` 零改动；两个
  `configure_file(command:)` 点各加一个 hunk 把命令数组首元素换成
  `/bin/sh`。meson 的数组首参语法已真机探针验证（RC_SH_OK/RC_PY_OK）。
  之后整树 grep `run_command|command:` 扫残余（含**崩溃点之后才评估的**
  subdir 构建文件——fuzz/doc 子目录的 run_target 是 build-time 不触发，
  fuzz 另有 FUZZ_OPT 门控）。
- 第 3 层：同一文件的多 hunk 补丁，后续 hunk 行号 = pristine 行号 + 先前
  **补丁文件**的行数增量（实测同文件先前 hunk 的增量不参与）；本地用
  pip 装 patch-ng 按 conan 同路径（strip=1、按 conandata 顺序连打）模拟
  验证，不依赖 git apply 的坐标语义。

## 验证

kea-hook-ping-check 3.0.3 真机 conan create：0003（解释器前缀数组 +
config-report.sh 两个 hunk）+ 0004（mk_cfgrpt.sh）应用后 meson setup 全程
通过（依赖探针全 YES、config.report/config.h/config_report.cc 均生成），
进入编译与上游测试阶段。
