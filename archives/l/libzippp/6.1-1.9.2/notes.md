# libzippp 6.1-1.9.2 正确版本适配

旧 PR13396 的任务版本为 6.2，但实际下载官方 6.1-1.9.2 标签。用户明确要求独立适配真实 6.1；本目录不沿用错误版本、旧补丁或历史 PASS。

2026-10-05 探索事务 libzippp-20261005-r003 已真实通过：24/24 上游函数、1/1 消费者、1/1 签名 HMDFS 中文路径 ZIP 读写专项。独立 receipt/WAL 校验、唯一 launch、进程清零、release/postrelease 均 PASS。该事务绑定探索源码闭包，尚不等于正式 Conan 配方复现或平台 CI/提审。

源码修改意图：修正官方 6.1 标签内陈旧的 CMake 6.0.0 元数据；仅测试 target 取消 NDEBUG 并增加编译期 guard，保证原有 24 项 assert 检查和 API 调用不被 Release 移除；保留用户 toolchain 的 C++ 标准；修正 pkg-config 安装路径拼写。补丁仅由官方 refresh-patch --auto 从精确原始归档生成。

分母为 24 个上游函数和 1 个 CTest 容器；不能把容器数与内部函数数累加。正式配方、知识草稿、Issue 和提审仍待完成。
## Native formal correction (2026-10-05)

Formal r001 failed at the actual test command: `CMake.test()` invokes
`cmake --build --target test`, so CTest `--output-log` is not accepted.
Use Conan's dedicated `CMake.ctest()` entry with the exact build directory.
The consumed r001 FAIL and its release/postrelease evidence remain unchanged.
This correction requires a new candidate-bound native transaction; no PASS is
claimed here for the corrected recipe.

Formal r002 reached the official CTest entry but the test could not execute:
the signer output replaced the executable without preserving execute mode.
Preserve the original mode on the signed pending file before replacement,
including the independent installed-package consumer. The native CMake also
reported an unknown HarmonyOS platform and emitted an unversioned library;
select its ELF/Unix library rules through the existing generic-system block,
without changing Conan OHOS identity or native HarmonyOS runtime checks.
The next immutable transaction must verify these changes.

Formal r003 executed native Conan create with RC0 and 24/24 + 1/1 + 1/1,
but its controller failed parsing child-tool text mixed with graph JSON.
It remains FAIL. r004 used the supported separate --out-file graph output,
but official GitHub download timed out and returned RC1; FAIL retained.
r005 froze the original official archive bytes/SHA-256 into a task-private
Conan source cache, preserved the official recipe URL, and executed a new
complete transaction. Native Conan, 24/24 upstream, consumer1/1, Harmony1/1,
independent graph/target hashes, one launch and release/postrelease PASS.
The new reusable knowledge concerns separate machine-report and process-log
channels; E301/E077/E489 were reused rather than claimed as new knowledge.
Finish and current platform CI/Review remain pending; no artifact upload.
