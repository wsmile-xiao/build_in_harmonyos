# E545 — 测试夹具的平台能力缺口会伪装成 PTY 工具功能失败：退出码透传型断言的识别与最小修法

## 现象（设备实测，真实报错）

sexpect 2.4.0 打上抽象 socket 回退补丁后，24/25 通过，只剩 `chdir-after-logfile`：

```
# sexpect ex -eof
ls: /: Permission denied
# sexpect w
!! ASSERT: sexpect w
```

被测行为（logfile 相对路径必须在 daemon `chdir("/")` **之前**打开）完全正确——
脚本末尾的 `ls -l $tmpfile` 本来就能验证它；失败的却是中间一行的 `sexpect w`。

## 触发条件

- 平台：OHOS（沙箱拒绝 `ls -l /`、列 `/dev`、读部分系统路径等，`EACCES`）
- 形态：测试通过 PTY 驱动子进程，并**断言子进程退出码**（expect 类工具的 `wait` 原样透传子进程退出码）
- 夹具命令（本例 `ls -l /`）只是「产生一些输出」，但它的退出码进入了功能断言

## 根因分析

两层叠加：

1. **夹具命令依赖平台能力**：`ls -l /` 在 Linux 上 rc=0，在 OHOS 沙箱 `EACCES` rc≠0；
2. **断言通道把夹具退出码当功能结果**：`sexpect wait` 的退出码 = 子进程退出码，`assert_run sexpect w`
   因此失败——平台差异被渲染成「工具功能失败」。

同类还有一处「申报口径」问题：上游用 `if (CMAKE_SYSTEM MATCHES "Linux.*")` 守卫的用例
（本库 `spawn-nowait`、`still-open-after-exit`）在 OHOS 上**按上游设计不注册**；若报表只写
「25 个用例」而不说明 27 个注册项的 2 个去向，会被误读为适配裁剪。

与已有条目的差异：`DRAFT-pty-driven-interactive-test-traps` 等 PTY 草稿讲的是「用 pty 驱动交互程序
的三类坑（等待渲染、分批发送、断言假阳性）」，本条聚焦**夹具命令的平台能力与退出码断言通道的
耦合**，以及守卫用例的如实申报，属于测试工程化边界，不是 PTY 使用技巧。

## 解决方案（推荐方案）

1. **夹具命令平台中立化（最小 1 行）**：`ls -l /` → `ls -l $tmpfile`（同 cwd 刚创建的日志文件）。
   语义覆盖不变（回归到 chdir-then-open 时日志会写到 `/` 打不开，最终断言仍会失败），断言逻辑不删不改。
2. **不要动断言**：禁止注释 `assert_run sexpect w`、禁止 `|| true`、禁止给夹具命令加 `exit 0` 包装。
3. **守卫用例单列申报**：测试清单/报表把 `CMAKE_SYSTEM` 守卫用例单列并注明「上游设计（Linux 专用守卫）」，
   同时给出注册数/运行数/通过数（本例 27 注册 → OHOS 运行 25 → 25 通过），不得把未注册项算进通过率、
   也不得静默略去。

验证：设备实测改动后 `ctest --output-on-failure -j1` → **25/25 PASS**；
`ctest -N` 显示 OHOS 注册 25 项（2 个 Linux 守卫项不注册）。

## 禁止做法

- ❌ 为让断言通过而删除/放宽退出码断言（把平台差异藏进测试）。
- ❌ 静默跳过夹具失败所在用例，或在报表中把守卫用例计入「通过」。
- ❌ 用 `set +e`/`|| true` 吞掉夹具命令的非零退出（问题会转移到下一次真实回归）。

## 适用范围与边界

- 适用：所有「子进程退出码 = 断言信号」的测试夹具（PTY 工具、`system()` 包装、e2e 脚本）；
  以及有平台条件注册（CMake `CMAKE_SYSTEM`、autotools `AC_CANONICAL`、meson `host_machine`）的上游套件。
- 边界：若夹具命令确无平台中立等价物，明确 SKIP + 原始报错 + 技术原因，不得伪造通过。
- 关联：`E002`（`/tmp` 只读）、`E545` 同批补丁 `0005/0006`（`${TMPDIR:-/tmp}` 改写）、
  `DRAFT-pty-driven-interactive-test-traps`、`DRAFT-E553-ohos-bash-fd3-pipeline-tap-driver`。
