# E-DRAFT: 纯 C 的 libyal/autotools 发布包在 OHOS 上的三处假信号（语言判定 / libtool 测试分发 / API 返回值）

- **触发实例**：libfsfat 0-20260208 适配（2026-09-19，任务 libfsfat-0-20260208，分支 feat/libfsfat-0-20260208）
- **错误签名**：`语言不匹配: task=cpp, detected=mixed`、`冲突: manifest=python 但统计 c 占`、
  `FAIL: volume_close failed`、`FAIL: file system format is not FAT-16`、
  `FAIL: libfsfat is not the expected OHOS package`
- **类别**：language-preflight + upstream-test-harness + API 契约（autotools / libyal / OHOS）
- **严重度**：2（三处都是"看起来是失败、实际不是"的形态；处置模式固定，不涉及库本身缺陷）

## 症状

### 假信号 1（最贵）：lang-preflight 把纯 C 库判成 `mixed → env_unsupported`

```text
  ❌ 语言不匹配: task=cpp, detected=mixed → env_unsupported
  ⚠️   协议要求: 不要硬着头皮适配；平台将按 detected_language 迁移/取消
{
  "expected": "cpp",
  "detected_language": "mixed",
  "language_evidence": {
    "build_system": "setuptools",
    "manifest": "pyproject.toml 存在（python 打包 manifest）；命中 manifest 路径: pyproject.toml（未排除）；
                 已排除绑定/示例/文档/测试目录 manifest: tests/Makefile.am",
    "source_stats": "源文件 237 个（c:232, bash:7, python:3, cpp:2），主体占比 98%"
  },
  "notes": ["冲突: manifest=python 但统计 c 占 98% → mixed"]
}
```

工具随后会把 `env_unsupported` **终态**写进全设备共用的
`$HOME/ohpcd-ai-worker-result.json` 槽位（本机 4 个并行任务共用；实测 44 秒后被另一任务的
里程碑草稿覆盖）。若不人工复核，一个纯 C 库的适配会被平台按"语言不符"取消。

同批 2026-09-19 在同一设备上，**libfsxfs、libfvde、libfsfat 三个 libyal 任务独立命中同一形态**
（编排方跨任务观测）。

### 假信号 2：`test_runner.sh` 的 libtool 判定在 OHOS 上失效，但 `make check` 仍全绿

libyal 的 `tests/test_runner.sh` 用 `file -b` 输出里是否含字面量 `POSIX shell script`
判断测试程序是不是 libtool 包装脚本：

```bash
$ file -b ./tests/fsfat_test_volume      # 期望：POSIX shell script text executable
/bin/sh script                            # OHOS 实测输出
```

判定因此恒不成立 → 测试直接执行 libtool 包装脚本本身（而不是解析到 `.libs/` 下的真实 ELF）。
**这不影响结果**：设备实测 `make check` 读数
`# TOTAL: 3 / # PASS: 2 / # SKIP: 1 / # FAIL: 0`，19 个 `check_PROGRAMS` 全部 PASS。
同族先例（libfsntfs 20251028）为此在 `build()` 内改写了 `test_runner.sh` 的两处锚点——
本包逐项核验后确认**不需要**，照抄反而会引入"修改上游测试用例"的审查成本。

### 假信号 3：消费者测试照抄同族先例会连撞三处反直觉 API 约定

```text
FAIL: version mismatch                          # 期望 "0-20260208"，实为上游版本串 "20260208"
FAIL: file system format is not FAT-16          # 该 API 写回单字节枚举，不是字符串
FAIL: volume_close failed                       # 该 API 成功返回 0，不是 1
```

## 根因

1. **语言判定顺序**：`lang_detect.py` 的 `_manifest_scan()` 把根目录
   `pyproject.toml`/`setup.py`/`setup.cfg` 排在 `configure.ac`/`Makefile.am` **之前**。
   libyal 上游把 **python 绑定模块（`pyXXX`）** 的打包元数据放在源码根：
   `pyproject.toml` 全文只有 3 行（`[build-system] requires = ["setuptools", "wheel"]` /
   `build-backend = "setuptools.build_meta"`），`setup.cfg` 自述
   `name = libfsfat-python`、`description = Python bindings module for libfsfat`。
   于是 `manifest=python` 与「C 占 98%」矛盾 → 协议 §4.7 冲突规则判 `mixed`。
   而 `binding_override` 的触发条件是 `dominant == "cpp" and share >= 0.70`：
   **纯 C 主体（dominant == "c"）拿不到覆盖**。overlay 的「缺陷 C」修正只排除
   绑定/示例/文档/测试**目录内**的 manifest（`_AUX_MANIFEST_DIRS`），管不住根目录形态。
2. **libtool 分发**：`find_binary_executable()` 依赖 `file -b` 的英文描述串
   `POSIX shell script`；OHOS（toybox/file 5.x 形态）输出 `/bin/sh script`，
   于是 `grep "POSIX shell script"` 失败、函数原样返回包装脚本路径。
   失败面仅限"优先解析真实 ELF"这一优化，执行链本身仍然成立。
3. **API 契约**：libyal 的头文件对这些 API 的返回值有非统一约定，且
   `*_get_file_system_format()` 的参数是 `uint8_t *`（写回枚举值）而非字符串缓冲：
   - `libfsfat_volume_get_file_system_format(volume, uint8_t *file_system_format, error)`
     → 写回 `LIBFSFAT_FILE_SYSTEM_FORMAT_*`（`FAT16 = 3`）；`"FAT-16"` 只是 `fsfatinfo` 的显示名；
   - `libfsfat_volume_close(volume, error)` → 头文件注明 "Returns 0 if successful or -1 on error"；
   - `libfsfat_get_version()` → 返回上游版本串 `20260208`，不是包管理器版本 `0-20260208`
     （本包 Conan 版本按发行版 `0~20260208` 口径写作 `0-20260208`）。

## 处置（三处都不改上游一个字节）

| # | 处置 | 留痕 |
|---|------|------|
| 1 | 人工逐份核验命中 manifest 的**全文**（确认只是绑定打包元数据）+ 确认真实构建入口是 `configure`/`Makefile.am` + 确认配方 `--disable-python` → 判假阳性，用编排 `--skip-step lang-preflight --start-note "<理由>"` 跳步 | readiness 记 `skip`（**不是通过**）；证据落 `$TASK_DIR/lang-preflight-review.md`；工具问题写 `feedback/pending/` |
| 2 | 先原样跑 `make check`；只有出现 `Invalid test executable` 之类真实失败才考虑同族先例的补丁 | `make check` 原始读数（`tests/test-suite.log` + 各 `*.sh.log`）逐字留档 |
| 3 | 对每个 API 先写最小探针断言**实测返回值**，再写正式断言 | 探针脚本与读数落 `$TASK_DIR`；消费者测试注释写明三处约定 |

## 复核命令（设备可直接执行）

```sh
TASK_DIR=$HOME/tmp/libfsfat-0-20260208
sh "$TASK_DIR/lang-preflight-check.sh"     # 重算主体语言占比 + 打印命中 manifest 全文（不写共享 result 槽）
sh "$TASK_DIR/api-contract-probe.sh"       # 对已安装包编译探针，打印三处 API 实测返回值
```

## 与既有条目的边界

- **E007**（`config.guess` 不识别 HarmonyOS）：本条不含三元组适配内容；相反，本包实测
  2026 版 `config.sub` **已原生接受** `linux-ohos`，只需显式传
  `--build/--host=aarch64-unknown-linux-ohos`，无需改 `config.guess`/`config.sub`。
- **E011**（`umask 077` 在 HMDFS 上生成不可写临时目录）：本条只引用它作为前置处置。
- **E386**（capability-tested shell / LOG_COMPILER）：本条不涉及 shell 能力探测；
  本包的 `TESTS` 入口是 `#!/usr/bin/env bash`（不是 `#!/bin/bash`），
  经 `LOG_COMPILER` 指定设备 bash 即可。
- **E584**（libyal `TESTS` runner 的 `TEST_PREFIX` 缺陷与驱动子集）：那是**目录名相关的
  确定性失败**；本条是**假失败/假终态识别**，且本包 `test_library.sh` 用显式
  `./fsfat_test_${TEST_NAME}`，不存在 `TEST_PREFIX` 推导。

## 影响面

- 假信号 1 影响面最广：任何「autotools/C 为主体 + 仓库根目录有 pyproject.toml/setup.py/setup.cfg
  （python 绑定打包元数据）」的包都会命中；判据是"命中 manifest 的全文内容"而不是包名。
- 假信号 2 只对「`tests/` 下存在 `test_runner.sh` 且含 `grep "POSIX shell script"`」的
  libyal 修订成立。
- 假信号 3 逐字实测的只有 libfsfat 0-20260208；其它 libyal 包的 API 返回值须按各自
  `include/<lib>.h` 的头文件注释逐条核对，**不作逐包断言**。
