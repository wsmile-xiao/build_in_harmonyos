# Draft: libopf 结构体哨兵字段 plain char 无符号导致 NIL 比较失效与堆越界

(配套 knowledge/drafts/draft-libopf-2.1-snode-char-unsigned-nil-sentinel.kv)

## 错误特征

`opf_split data/boat.dat 0.5 0 0.5 0` 在 "Splitting data set ..." 后 **Signal 11
(core dumped)**。ASan 定位 `opf_SplitSubgraph`（OPF.c:1505）heap-buffer-overflow：
sg2 只分配 51 个节点（√(100 总量 - 49 训练))，却被写入了全部 100 个节点。

## 根因

libopf 的 `SNode.status`/`SNode.relevant` 字段声明为 `char`（include/util/subgraph.h），
代码以 `status = NIL(-1)` 标记节点已消费，并以 `status != NIL` 判定是否可复制。但
OHOS aarch64 工具链（clang 15）默认 plain char **无符号**（`CHAR_MIN==0`，
`__CHAR_UNSIGNED__` 预定义）：`-1` 存入后变成 `255`，`255 != -1` 恒真。于是：

- while 循环正常结束（totelems 递减到 0，复制了 49 个节点到 sg1）；
- 随后 sg2 填充循环 `if (sg->node[i].status != NIL)` 对**所有**节点恒真，把 100 个
  节点全部写入只分配 51 容量的 sg2 → 堆越界写 → SIGSEGV。

## 修复

`include/util/subgraph.h` 中两处字段显式改为 `signed char`（源码级类型修正，
无平台宏、不改算法、API 语义不变）：

```c
signed char  status;    //0 - nothing, 1 - prototype (must be signed: NIL == -1 comparison relies on it)
signed char  relevant;  //0 - irrelevant, 1 - relevant
```

重编后全部 6 个 examples 脚本 + 2 个 tools 脚本 rc=0；conan create 干净构建
G2 PASS（test_libopf + ohos_specific_test 2/2 通过）；鸿蒙专项测试断言
`opf_SplitSubgraph` 6+2=8 分割无崩溃、`opf_ConfusionMatrix/opf_Accuracy`
在聚类 label>nlabels 时无越界（acc=50.00%）。

## 与既有知识的关系

- **E419**（librasterlite2）：同根因（aarch64 plain char 无符号），但症状是
  INT8 样本值差 256（数据还在、数值错），修复用 toolchain `-fsigned-char`；
  本场景是内存结构体**哨兵字段**不可表示 → **控制流崩溃/堆越界**，修复用
  源码显式 `signed char`。E419 的 alter 口径（fallback_approach =
  upstream-explicit-signed-type）与本修复一致。
- **DRAFT-8543**（looktxt）：EOF 哨兵存 char → 死循环（IO/扫描状态机）；同为
  哨兵不可表示，但发生在 IO 读路径，修复是扩宽接收变量为 int。
- **DRAFT-9645**（polyseed）/ **DRAFT-clipp**：`*p<0` 非 ASCII 判定 / 值转换
  钳位；均为数据判断路径，修复用 `-fsigned-char`。

本条目新增边界：**结构体内存字段哨兵 + 源码级显式 signed char**，且提供
鸿蒙专项测试覆盖哨兵比较路径（区别于纯数据路径的既有条目）。

## 适用范围与反例

- 适用：任何把 -1/NIL/EOF 类哨兵存进 plain char 结构体字段并在循环/控制流中
  与其比较的 C 库，目标平台 plain char 默认无符号（OHOS aarch64、ARM32、RISC-V）。
- 反例：字段未与 -1 比较（仅 0/1 判别）、或全部字段本就声明 signed char/int8_t
  的库不适用；纯 toolchain 模式切换能解决数据类场景，但结构体哨兵语义建议
  源码级类型修正（全对象符号性一致）。