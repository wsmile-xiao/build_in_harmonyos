# DRAFT: Windows 交叉宿主跑 ohc 工具链与 Conan self.run 的 /bin/sh 假设

> 草稿。与同 stem `.kv` 成对。触发事件：wordplay 9.0.1 适配（Windows 宿主 + OHOS clang 交叉，profile fathom-local）。
> 查重：知识库中 shlex 相关草稿均为 Linux 侧正面用法（hoedown/smemstat/makefile-origin-guard 等），无 Windows 宿主场景条目。

## 现象（三条，同一次 Windows 宿主会话先后出现）

1. `ohc-run.py conan-verify` 到 G2 即 FAIL，conan-create.log 全文只有一行：
   ```text
   [WinError 2] 系统找不到指定的文件。
   ```
   知识图谱误命中 E422（"Windows 特有错误码"），报告方向完全跑偏。
2. test_package 里用 `shlex.quote()` 拼接 `python ohos_abi_check.py --binary <path>` 后
   `self.run()` 失败：
   ```text
   The filename, directory name, or volume label syntax is incorrect.
   ConanException: Error 1 while executing
   ```
3. `pre_pr_audit.py` 在 GBK 控制台 print emoji 直接 `UnicodeEncodeError: 'gbk' codec can't encode`。

## 根因

三个都是「工具/写法假设了 POSIX 宿主」：

1. `scripts/ohc/conan_verify.py` 的 `_run()` 对字符串命令固定 `["/bin/sh", "-c", cmd]`
   （conan_verify.py:108-109）——Windows 没有 `/bin/sh`，`subprocess.run` 抛
   `FileNotFoundError`，被 except 吃掉后写成一行日志。G1（纯 Python 检查）能过，
   G2 起全部不可运行。**不是配方问题**。
2. `shlex.quote` 在 POSIX 产生 `'C:\...'` 单引号形式；Conan 2 在 Windows 上用
   `cmd/pwsh` 执行 `self.run()`，单引号不是合法 quoting → 路径解析失败。
3. 审计脚本用 emoji 输出，Windows 控制台默认 GBK 代码页。

## 正确做法

1. **不修改公共脚本**（基础设施边界）。Windows 宿主上：
   - G1 可跑（有用）；G2+ 的 conan create 用**手动等价命令**执行并留证：
     `conan create . -pr:h <ohos-cross-profile> -pr:b <build-profile> --build=missing`
   - 报告/notes 如实写「conan-verify G2 在 Windows 宿主不可运行（工具 /bin/sh 限制），
     已用手动 conan create + test_package 全量等价验证替代」——**不把未跑的
     conan-verify 写成通过**。
   - 完整 conan-verify 交真机 shadow CI（build_and_test.sh 在 zsh 下跑，无此问题）。
2. test_package 的 `self.run()` **弃用 shlex.quote，改双引号拼接**——路径不含引号
   字符时对 cmd/pwsh/POSIX sh 三方都安全：
   ```python
   self.run(f'"{sys.executable}" "{checker}" --binary "{binary}" --words "{words}"')
   ```
   （Python 侧路径拼接仍可用 shlex.split，只是不要让 quote 产物进 Windows shell。）
3. emoji 崩溃：设置 `PYTHONIOENCODING=utf-8` 或 `chcp 65001` 后重跑。

## 复用判定（为什么值得留）

Windows 宿主 + OHOS 交叉 profile（fathom-local 类）是本项目支持的 W3/W4 验证路径，
任何在此宿主上跑 `conan-verify` / 写 test_package `self.run()` 的库都会命中 1 或 2；
且 E422 误命中会把人引向「给源码加平台宏」的错误方向，值得一条草稿纠偏。

## 证据

wordplay/9.0.1：修 quoting 前 test_package Layer 1 必失败；改双引号后同机 conan create
rc=0、ohos_abi_check A1-A9 9/9；conan-verify G1 PASS / G2 WinError 2（手动等价验证通过）；
真机 shadow CI r4 全绿（L0/L1/L4/L5 pass + F1-F20 20/20），证明 Windows 侧跳过的
conan-verify 缺口由真机闭环。
