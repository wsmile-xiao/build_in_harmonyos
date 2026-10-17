# E545 — PseudoTCP 随机传输测试将 EWOULDBLOCK 计为负字节数

## 错误特征

HarmonyOS aarch64 上运行 libnice 的 `test-pseudotcp-random` 时，可能看到：

```text
Sending 1024 bytes : -1
seeking  ... from ...
Binary files rand and rand-copy differ
```

若比较内容而非只检查长度，输出文件会比 1 MiB 输入多 1 字节；本次复现的首个差异位于第 92161 字节。测试也可能以 `total_wrote <= total_read` 断言失败结束。

## 触发条件

- 环境：HarmonyOS PC aarch64，Meson 原生运行上游测试
- 阶段：随机 PseudoTCP 文件传输测试
- 条件：发送队列暂满时 `pseudo_tcp_socket_send()` 返回 `-1`（EWOULDBLOCK）

## 根因分析

返回值 `-1` 表示零字节被接受。上游测试直接把它累加到 `total_read`，并以 `wlen - len` 回退刚读取的输入文件。请求 1024 字节且返回 `-1` 时，回退量变成 -1025 字节，比应有的 -1024 多一个字节，因此重试会再次发送前一缓冲区的末字节；同时计数器也被减一。

## 解决方案

### 推荐方案

在更新传输计数和计算文件回退量前，将负返回值归一为 0。保持随机丢包和输入/输出逐字节比较不变。

### 禁止做法

- ❌ 不要跳过随机传输用例，也不要放宽断言或移除文件比较。

## 验证
```bash
MALLOC_PERTURB_=84 bash tests/test-pseudotcp-random.sh tests/nice-test-pseudotcp
```

## 关联条目

- 暂无直接关联条目。
