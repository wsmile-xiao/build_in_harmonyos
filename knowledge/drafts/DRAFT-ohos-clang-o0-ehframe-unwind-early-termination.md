# DRAFT — OHOS clang 15 无 -g 时 .eh_frame 不完整致 _Unwind_Backtrace 提前终止

## 错误特征

_Unwind_Backtrace 消费者（Boost.Stacktrace basic 形态等）在 **-O0 且无 -g**
（"无调试符号"变体）编译后运行，栈深异常浅：

    rc=2（断言失败）：ns1 != return_from_nested_namespaces()
                      min_size > 2（实际只收集到 1 帧）
    stdout 栈仅 1-2 帧即止，深层调用链全部丢失

机器可匹配：min_size > 2 / ns1 != return_from_nested_namespaces / 栈深 1-2 帧 /
仅 no_dbg（NO_DEBUG_AT_ALL）变体失败 / 同代码加 -g 或 gcc 构建机正常。

## 触发条件

- 编译器：OHOS SDK clang 15（aarch64-linux-ohos，libc++）
- 参数：无 -g（无调试符号构建/Release-strip）
- 运行时：栈回溯走 unwind 表（_Unwind_Backtrace / execinfo backtrace()）

## 根因分析

gcc 默认生成完整异步展开表，clang 仅按需生成。OHOS clang 15 在 -O0 无 -g
时对部分函数省略 .eh_frame CFI 项，_Unwind_Backtrace 逐帧展开遇缺表项函数
提前终止。上游 gcc 构建机不可见，故上游测试（Boost.Stacktrace no_dbg 变体）
在 OHOS 才暴露。已排除：ICF 符号合并（llvm-readelf）、内联吞帧（加 -g 即恢复）。

## 解决方案

无 -g 的目标追加 `-fasynchronous-unwind-tables`（不引入 -g，保持上游语义）：
见 .kv solution 代码块（boost1.84-stacktrace_basic 1.84.0 实测，CI #41620）。

三步鉴别法：加 -g 对照 → readelf 查表 → 加 flag 复测。

## 红线

- 禁止与"-O2 内联吞帧"混为一谈：内联加 -g 不解决，本条加 -g 即恢复
- 禁止加了 -g 还宣称"无调试符号变体"成立（语义已变）
- 修在"无 -g 目标"的编译参数上，不要全局加 -g 了事

## 证据

t7_nodbg（-O0 无 -g）rc=2 仅 1 帧；t9_autounwind（+flag）rc=0；t6（+-g）
rc=0 完整 19 帧；llvm-readelf 无 ICF 合并。CI #41620：no_dbg 4 目标全过。
