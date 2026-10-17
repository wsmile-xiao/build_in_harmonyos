# Asterisk 22.10.1 Conan/HarmonyOS 制品适配证据报告

## 范围

本 PR（#9608，`feat/asterisk-22.10.1`）负责 Asterisk 22.10.1 的 Conan 配方、
HarmonyOS 编译、运行时和模块交付适配。它不负责修复上游 full-PBX 测试套件或
测试 runner；724 条是上游库存参考值，不是本 PR 的功能验收项。

源码为 Asterisk 22.10.1 tarball，SHA-256
`373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663`。
issue：`TBD`，在项目文件和会话上下文中未找到明确编号。

## 主线修复

当前主线保留 19 个补丁：

| 范围 | 补丁 | 目的 |
|---|---|---|
| 构建和 musl 兼容 | `0001`~`0012` | sounds 下载开关、TMPDIR 构建工具路径、ASTMM/musl 头文件、resolver、menuselect 和 db1-ast 兼容 |
| 运行时时区 | `0015` | 运行时 `TZDIR` 覆盖，未设置时回退编译期默认值 |
| parser 构建 | `0016` | `REBUILD_PARSERS` 下让 `ast_expr2.y` 使用 ASTMM_IGNORE |
| 运行时和模块交付 | `0023`、`0025`~`0027`、`0031` | 配置驱动的 flock、模块运行库、abstract AF_UNIX、PATH_MAX 和 Blocks ABI 导出 |

纯测试夹具和测试断言补丁不在本 PR：`0013`、`0014`、`0017`~`0022`、`0024`、
`0028`~`0030`、`0032`、`0033`。这些内容对应原 PR #9561、#9562、#9563 及其
后续 full-PBX 测试修复，应使用独立 issue、分支和 PR 跟踪。

## 验证关系

此前包含测试修复补丁的真机日志不作为当前主线的验收证据。当前主线已在 HarmonyOS
aarch64 真机完成一次新的 `conan create` 与 `test_package`；知识材料保留与主线直接相关的
TZDIR 和 ELF 依赖扫描草稿：

`knowledge/drafts/DRAFT-asterisk-22-10-1-tzdir.kv` + `.md`、
`knowledge/drafts/DRAFT-asterisk-22-10-1-elf-reader.kv` + `.md`。

## 本地验证

当前已完成的检查：

```text
python -m json.tool archives/a/asterisk/commands.json
python scripts/ohc-run.py draft-review DRAFT-asterisk-22-10-1-tzdir --json
python scripts/ohc-run.py draft-review DRAFT-asterisk-22-10-1-elf-reader --json
python -m py_compile archives/a/asterisk/22.10.1/conanfile.py archives/a/asterisk/22.10.1/test_package/conanfile.py
python -m json.tool archives/a/asterisk/commands.json
git diff --check
git apply --check --ignore-whitespace <retained patch files>
```

`0016` 原补丁的 hunk 行号为 `-10`，Git 应用时可自动偏移，导致此前本地检查误判
通过；官方 Conan 补丁应用器严格按行号处理，CI #46520 在该补丁失败。已修正为
`-12`，对应 Asterisk 22.10.1 原始 `main/ast_expr2.y` 的实际位置。

真机 runner `codex-22.10.1-asterisk-22.10.1-fix-d66aeaef78-conan-20260914-162720-17126`
以 rc=0 完成 `conan create archives/a/asterisk/22.10.1`；包版本为
`Asterisk 22.10.1`，`test_package` 通过。L0/L1 通过，L2 因无 `bin/` 跳过，L4
为危险函数扫描告警，L5 报 `soname_gate_failed`。后者不能作为 Conan 构建失败依据：真机
没有 `readelf`，只有 `llvm-readobj --dynamic-table`，共享 runner 未做同等工具回退。
用 `llvm-readobj` 复核包内文件后，`libasteriskssl.so`、`libc++_shared.so` 和 `libz.so`
有 `DT_SONAME`，但 `libBlocksRuntime.so`、`libjansson.so` 和 `libohosshim.so` 没有，
这 3 个文件仍是需要另行处理的包质量问题。

## 审查修复

最新审查指出 `0007` 在无 resolver 状态分支中存在无配对解锁风险，且 `0023`、
`0026`、`0027` 的补丁文本不应直接引入 `__OHOS__`。本轮已完成以下修复：

- `0007` 直接将无 resolver 状态的 `state` 置空，循环增加空状态保护，并删除函数尾部
  不再有配对加锁的 `ast_mutex_unlock(&res_lock)`。
- `0023` 改用 `AST_LOCK_TYPE_DEFAULT`，`0026` 改用 `AST_USE_ABSTRACT_SOCKET`，
  两个宏仅由 OHOS 配方通过 `AutotoolsToolchain.extra_cflags` 配置；未配置时保留
  原有跨平台默认行为。
- `0027` 改为基于 `PATH_MAX < 4096` 的通用能力判断。

相关补丁不再包含 `__OHOS__` 条件编译文本。

## 官方 CI

官方 CI #46520 的 L0、KC、JC、依赖可达和源码下载均通过；L1 在 Conan 应用
`0016-main-ast_expr2.y.patch` 时失败，未进入 test_package 或上游测试。该失败是
本 PR 的补丁可复现性问题，不是 724 条 full-PBX 测试失败。

官方日志还显示依赖制品均已可达：`jansson/2.15.1`、`libedit/20240808`、
`libxml2/2.15.3`、`openldap/2.6.7`、`sqlite3/3.49.1` 和 `uuid/2.40.1`。

本轮修复后触发的官方 CI #46946 未进入 checkout 或 Conan 阶段：设备侧
`/data/service/hnp/bin/git` 因缺少 `libz.so` 以 127 退出，cleanup 又因设备侧缺少
`ci/conan/cleanup.sh` 以 127 退出。因此该次结果是 runner/设备环境故障，不是本次
补丁或 `test_package` 的失败。

真机日志中曾出现 `libc++_shared.so`、`libz.so`、`libtinfo.so.6` 未在旧候选目录
找到的警告。核对真机实际路径后，配方改为从 Conan 选定的绝对 clang 路径动态推导
编译器 runtime 和 sysroot 候选目录；`d66aeaef78` 真机重跑后这些候选告警已消失。

## 最新验证与工具边界

当前生产主线只保留 19 个补丁：`0001`~`0012`、`0015`、`0016`、`0023`、
`0025`~`0027`、`0031`。`poll/capture/voicemail/JSON` 测试补丁不在当前分支。

当前提交 `2122a08895` 的目标 run 实际结果如下：

```text
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-fix-d66aeaef78-conan-20260914-162720-17126
runner rc=0
conan create=PASS
test_package=PASS; Asterisk 22.10.1
L0=pass; L1=pass; L2=skip(no bin/); L4=warn(dangerous functions); L5=fail(soname_gate_failed)
```

L5 runner 固定执行 `readelf -d`，而真机工具集合没有 `readelf`，只有
`llvm-readobj --dynamic-table`。因此 runner 的 6 个缺失 SONAME 报告包含工具选择造成的
误报。设备侧实际复核显示：`libasteriskssl.so`、`libc++_shared.so` 和 `libz.so` 有
`DT_SONAME`；`libBlocksRuntime.so`、`libjansson.so` 和 `libohosshim.so` 没有，后 3 个
文件的 SONAME 质量问题仍需另行评估。共享 runner 的工具回退属于基础设施问题，不能在
本 PR 修改 `ci/`；配方中的 `_bundle_libs()` 已完成依赖闭包处理。

## 测试范围边界

本 PR 的上游 full-PBX 库存为 724 条，当前未执行：通过 0、失败 0、跳过 0、未执行
724，故通过率为 `N/A（未执行；不纳入本 PR 验收）`。此前含测试修复补丁的定向结果
不归入当前主线。full-PBX runner、测试夹具和测试断言由独立 PR 处理；当前主线应以
Conan 构建、test_package、模块加载和基本运行验证为准。

逐层统计如下，不混合分母：

| 测试层 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 依据/限制 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游 full-PBX | 用例 | 724 | 0 | 0 | 0 | 724 | 赛事方人工检视确认库存；本 PR 不执行 |
| `test_package` / `asterisk -V` | 断言 | 1 | 1 | 0 | 0 | 0 | 真机 run，输出含 `Asterisk 22.10.1` |
| 共享 runner SONAME gate | 检查 | 1 | 0 | 1 | 0 | 0 | 固定调用缺失的 `readelf`；设备复核另发现 3 个包内 `.so` 无 `DT_SONAME` |

## 下一步

1. 另行评估 `libBlocksRuntime.so`、`libjansson.so` 和 `libohosshim.so` 的 SONAME 修复，
   不将 runner 或依赖库适配混入本 PR。
2. 另起基础设施 issue、分支和 PR 修复 runner 的 ELF reader 选择；不要将该修复混入
   Asterisk 制品 PR。
3. full-PBX 测试修复由独立 PR 跟踪；本 PR 不执行也不计算 724 条通过率。
