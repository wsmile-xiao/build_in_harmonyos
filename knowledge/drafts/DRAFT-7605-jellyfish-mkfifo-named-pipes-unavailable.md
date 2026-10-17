# DRAFT: HarmonyOS 全局拒绝 mkfifo(2)（EPERM）——命名管道不可用与运行期能力探测

- **草稿 ID**: DRAFT-7605-jellyfish-mkfifo-named-pipes-unavailable
- **来源库**: jellyfish 2.3.1（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18, HongMeng Kernel 1.12.0）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 现象（真机实测）

jellyfish 的 generator 机制（`jellyfish count -g <commands> -G <n>`，从子进程命令
流式读取输入）在真机上抛异常：

```
unknown file: Failure
C++ exception with description "Failed to create named fifos: Operation not permitted" thrown in the test body.
```

对应 `lib/generator_manager.cc` 的 `tmp_pipes::create_pipes()`：

```cpp
path << tmpdir << "/fifo" << i;
if(mkfifo(path.str().c_str(), S_IRUSR|S_IWUSR) == -1)
  throw std::runtime_error(err::msg() << "Failed to create named fifos: " << err::no);
```

## 根因定位过程（排除混淆项）

| 候选目录 | 结果 | 说明 |
|---|---|---|
| `$HOME/...`（HMDFS 用户数据） | `mkfifo` EPERM | 平台策略拒绝 |
| 构建目录（HMDFS） | EPERM | 同上 |
| `/dev/shm`（1777 世界可写） | EPERM | **决定性证据**：可写目录也被拒，非权限位问题 |
| `/tmp` | EROFS | 只读文件系统（另一个已知限制 E002） |
| `/data/local/tmp` | EACCES（不可访问） | 测试用户无权限 |

另：`command -v mkfifo` 返回 not found（toybox 未带 mkfifo 命令），
因此测试脚手架不能靠"命令是否存在"探测，必须以**真实 mkfifo 调用**做能力探测。

结论：HarmonyOS 安全域对普通用户域进程禁止创建命名管道；这是内核/沙箱策略，
运行期无 workaround（提权/重挂载不在适配边界内）。

## 处理方式（jellyfish 2.3.1）

运行期能力探测 + 跳过/等价回退，**不修改库代码、不引入平台宏**：

1. `tests/bloom_counter.sh`：FIFO 可用时保持上游原样（generator 装载两份重复输入）；
   不可用时改用**文件参数**装载同一份重复输入（`seq1m_0.fa seq1m_0.fa`），
   布隆计数器内容与直方图 md5 完全一致。
2. `tests/multi_file.sh`：FIFO 不可用时跳过 generator 子测试并复用普通多文件直方图，
   仍保留"打不开文件必须失败"负例。
3. `unit_tests/unit_tests.sh`：FIFO 不可用时 `--gtest_filter=-TmpPipes.*:GeneratorManager.OneLiners`
   排除 3 个依赖 FIFO 的用例（日志打印原因），其余 51310 个用例照常运行并通过。
4. PR 的"上游测试用例修改说明"逐条披露，不伪造通过率。

## 平台限制（如实记录）

- jellyfish 的 **generator 输入（`-g`/`-G`）在 HarmonyOS PC 上不可用**；
  核心文件输入 k-mer 计数路径不受影响（由 tests/*.sh 与 test_package 消费者测试覆盖）。
- 若未来要求该功能可用，需把 `generator_manager` 从"命名管道路径 + shell 重定向"
  重构为 `pipe()/socketpair()` + `dup2` 的匿名管道方案（见草稿 fallback 方案）。

## 关联

- E002（/tmp 只读 EROFS）：本次 `test_stream_iterator.cc` 的另一处修正是其标准解法（TMPDIR 回退）。
- E051（未实现 syscall 的 SIGSYS 处理）：同属"内核能力缺失 + 源码/测试层优雅降级"族。
