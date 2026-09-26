# DRAFT: OHOS musl 管道 stdout 逐行冲刷反转 `2>&1` 合并流字节序

- **状态**: draft（待 promote 审核）
- **来源**: hashrat 1.25 R02 返工（check.sh "Checking files" 1/49 断言修复）
- **日期**: 2026-09-23

## 错误特征

上游测试对合并流做整流哈希的断言失配（无编译错误，输出内容正确但字节序不同）：

```bash
HR_INPUT="hash='sha1:5aa622e49b541f9a71409358d2e20feca1fa1f44' mode='100644' uid='0' gid='0' size='621' mtime='1423180289' inode='2359456' path='tests/quotes.txt'"
echo "$HR_INPUT" | ./hashrat -c 2>&1 | ./hashrat -sha256
# 上游参考期望: d50f1b64549232b7d79f094910ef3b578a65ffe5681a69907750e2519861dda7
# OHOS 实测(修复前): 8ff7d1448c73a0454528a9c39ffbbc0db1193385ce2d9e6ff3453b0a28a83cbe
```

期望字节序（stderr 摘要先行）：`\nChecked 1 files. 0 Failures\n` 后接 stdout
`tests/quotes.txt: OKAY\n`；OHOS 实测相反：`tests/quotes.txt: OKAY\n` 先落盘。

## 根因分析

上游 check-hash.c 第 74-75 行 `printf("%s: OKAY\n", Path)` 写 stdout；第 149 行
`fprintf(stderr, "\nChecked %d files. %d Failures\n", ...)` 写 stderr。上游参考
环境（glibc）对管道 stdout 默认全缓冲 + stderr 无缓冲 → stderr 摘要先行写出，
stdout 缓冲在进程退出时冲刷，合并流为"摘要先行"字节序。OHOS musl 对管道
stdout 逐行冲刷（line-buffered 语义），OKAY 行先于 stderr 摘要写出，合并流
字节序相反。功能输出内容完全正确（文件校验 OKAY、0 Failures、退出码用例通过），
仅断言合并流整流哈希的上游测试会失败。

## 修复方案（已验证）

main() 启动时对非 tty stdout 强制全缓冲，恢复上游参考字节序；tty 交互行为不变：

```c
/* OHOS portability fix: OHOS musl flushes piped stdout eagerly, which
 * reverses the byte order of a `2>&1` merged stream relative to the
 * upstream reference environment (glibc fully buffers piped stdout, so
 * the final stderr summary lands before buffered stdout lines). Force
 * full buffering for non-tty stdout to reproduce the upstream reference
 * ordering expected by check.sh's "Checking files" assertion; terminal
 * (tty) stdout keeps the default line-buffered behavior unchanged. */
if (!isatty(fileno(stdout))) setvbuf(stdout, NULL, _IOFBF, 0);
```

关键事实依据：
1. 上游参考环境（glibc）管道 stdout 全缓冲是合并流"摘要先行"字节序的来源；
2. OHOS musl 管道 stdout 行缓冲导致 OKAY 行先写出（最小程序复现 + 真实二进制复现）；
3. `isatty` 守卫保证交互终端行为不变（行缓冲保留）；
4. 修复后整流哈希恢复 d50f1b64...，check.sh 49/49 全量通过，功能输出内容不变。

## 验证

- 最小复现：`printf("OKAY\n"); fprintf(stderr,"\nChecked..."); fflush(NULL)` 管道
  `2>&1 | sha256sum` 默认 8ff7d144...，加 `setvbuf(_IOFBF)` 后 d50f1b64...。
- 真实二进制：conan create（ohos-aarch64）产物实测整流哈希恢复 d50f1b64...。
- 上游测试：check.sh 49 断言组 49/49 全量通过（两段日志，SHA-256 见 test-report.md）。
- 回归：tty 行为未变（isatty 守卫）；其他 48 断言组不受缓冲模式影响（内容不变）。

## 适用边界 / 反例

- 适用：任何在 OHOS 下运行、且上游测试对 `2>&1` 合并流做整流哈希/严格字节序
  断言的 CLI 工具（autotools/make check 中 `cmd 2>&1 | hashrat/sha256sum` 模式）。
- 反例：
  - 若程序输出依赖实时可见（交互进度、长时运行日志），强制全缓冲会延迟输出，
    此时应改用显式 `fflush` 控制冲刷时机而非全局 _IOFBF；
  - 若上游参考环境本身无固定字节序（如同时断言两种顺序），无需修复；
  - 只读 stdout 内容的断言（非合并流）不受影响，无需本方案。

## 关系

- similar_to: E999（open_memstream fclose 丢缓冲——同为 OHOS libc 缓冲语义差异，
  但方案方向相反：E999 是 _IONBF/显式 fflush，本候选是 _IOFBF 全缓冲恢复顺序）
- caused_by: OHOS musl 与 glibc 的 stdio 管道缓冲语义差异（line-buffered vs fully-buffered）
- prerequisite_of: 无
- conflicts_with: 无
