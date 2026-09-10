# binutils 2.46.0 测试报告

- 测试日期：2026-09-08
- 适配路径：C（高难度挑战候选，最终类别由赛事复审确认）
- 上游：`binutils-2_46` / `49d4d3fafa4ec4ff5a3460d91d5b1ed5286487db`
- 目标：HarmonyOS PC aarch64，Clang 15，Conan 2.29.1
- 最终 clean run：`final-build39`，Conan create 退出码 0
- 输入 bundle SHA256：`61f2ab642e0405787a1af1fa34e47b9e12281eb9fd1d8a93d509348fc2beec79`
- 结果归档 SHA256：`8efd26e9be91e44d4deb7eb53a4d85ebc9320dc54481f00d392936b183d7c6f3`

## 一、上游清点

官方归档包含 386 个 DejaGNU `.exp` 文件。gprofng 的 7 个文件随 Linux 专用
collector 组件显式关闭；其余 379 个文件中，367 个是执行驱动，12 个是
`config/`、`lib/` 支持文件。另有 gprof 2 个 shell 测试入口和 libiberty 7 个
Make 目标。

| 套件 | `.exp` 清点 / 执行驱动 | PASS | FAIL | XFAIL | UNRESOLVED | UNTESTED | UNSUPPORTED |
|---|---:|---:|---:|---:|---:|---:|---:|
| binutils | 37 / 34 | 273 | 1 | 2 | 0 | 2 | 8 |
| gas | 145 / 142 | 1239 | 0 | 0 | 0 | 0 | 10 |
| ld | 187 / 184 | 1721 | 34 | 13 | 0 | 2 | 182 |
| libctf | 6 / 4 | 18 | 0 | 0 | 0 | 0 | 3 |
| libsframe | 4 / 3 | 168 | 0 | 0 | 0 | 0 | 0 |
| **DejaGNU 合计** | **379 / 367** | **3419** | **35** | **15** | **0** | **4** | **203** |

普通结果分母不把上游预期失败和能力探测排除项写成通过：

```text
3419 / (3419 + 35 + 0) = 98.99%
```

该结果高于随附《路径判断.pdf》第 11 页所述的路径 C 90% 测试口径。35 个 FAIL 均
保留原 verdict；完整逐项名称、根因、对照试验和影响见
`../ohos-failure-analysis.md`。分类器完成 35/35 名称映射；结合日志上下文和对照试验
复核，未发现当前适配引入的失败。

## 二、其他上游目标

- libiberty：7 个目标完成。三组 demangle 数据 420 + 365 + 75 = 860 例；
  expandargv 26、strtol 21、linked-list 22、pexecute 1，共 930/930 检查通过。
- gprof：上游发现 2 个 shell 入口，但 OHOS 配置为 `gprof_cv_sys_native=no`，最终
  `TOTAL=0 / PASS=0 / FAIL=0 / ERROR=0`。该项明确记录为 0 discovered / 0 executed，
  原因是 SDK 不提供 profiling 编译/启动闭包，不计为通过。
- gprofng：7 个 `.exp` 随明确关闭的 Linux collector 组件排除。

## 三、测试执行层修改

没有修改产品 C/C++ 行为或上游期望值。25 个补丁中的测试执行层修改包括：

1. 在 HMDFS 上以 HNP bash 读取脚本，使用 DejaGNU pipe/file channel 代替 PTY 依赖。
2. 复制只读 SFrame 数据夹具和需覆盖的版本 DSO，避免受限 symlink/truncate 语义。
3. `send_log --` 将负退出状态作为数据记录，防止 Tcl 把它解析为选项而中止驱动。
4. Clang 在 libctf 中显式选择本轮 GNU ld。
5. `compress.exp` 在 OHOS + Clang 范围内调用本轮 GNU as，完成后恢复编译标志；
   该组从失败变为 28/28 PASS，且 `mbind2a/b` 恢复为基线的 UNSUPPORTED，未形成 FAIL。
6. 运行前仅签名当前 `tmpdir` 中被请求的 AArch64 ELF、其本地 `DT_NEEDED` 闭包和
   明确列出的 literal `dlopen` 夹具；不重写测试结果。

执行环境预检为 5/5 PASS，其中包含 256 次真实子进程生命周期。运行时 tmpfile
preload 和 GNU ld 产物签名探针也均为退出码 0。

## 四、安装包消费者

`test_package/test.sh` 由 Conan 与设备入口共用，包含 9 个步骤和 13 个断言：

- 7 个安装包命令的版本/ELF 工作流：`as`、`readelf`、`objdump`、`nm`、`ar`、
  `ld`、`strip`；
- 精确检查目标 ELF、反汇编符号和归档结果；
- 缺失输入负例必须返回非零并包含路径。

OHOS 原生补充 3 个断言：安装包 GNU ld 生成的程序、objcopy 副本和 strip 产物分别
按平台流程签名后执行，均输出 `binutils native consumer: 2460`。最终为 16/16 PASS。

## 五、制品与依赖闭包

- 完整 package reference：
  `binutils/2.46.0#11a4a9b63a85bc14b6f4edc65fc4fdfe:6b129b068851896169fae42d399fa922d239ce8a#79f95fb4875a2b5b802d4eaec2ee7349`。
- 安装包：453 个文件，65,975,560 字节；包含 16 个顶层 CLI。
- 新 `CONAN_HOME=final-cache39` 从空目录开始，解析并构建/取得
  DejaGNU、Expect、Tcl、zlib 测试闭包；Expect 上游为 28 PASS / 1 SKIP / 0 FAIL。
- 运行时 Conan requirements 仍为 `required: []`；测试工具不进入发布包依赖。

## 六、历史差分与结论

初始设备结果 `final20` 为 3393 PASS / 60 FAIL。诊断后修复 compressed-debug
汇编器选择和 `pr21964-2b.so` literal dlopen 签名。过宽试验 `final34` 虽达到
3425 PASS / 36 FAIL，却新增 `mbind2a/b` 两项 FAIL，已明确淘汰。最终收窄候选
`final39` 将两项恢复为基线的 UNSUPPORTED，没有这两项 FAIL 回归；Conan create、
打包、消费者和分类器完整性检查全部返回 0；日志与对照试验证据复核未发现当前适配
引入项。

工程证据满足路径 C 的复杂架构和测试率条件；赛事路径 C 身份仍须先提交
`【高难度挑战】` Issue，并以评审委员会复审结果为准。
