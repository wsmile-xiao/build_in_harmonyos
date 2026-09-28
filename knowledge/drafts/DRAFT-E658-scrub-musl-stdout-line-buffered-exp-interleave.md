# draft-scrub-2.6.1-git20240819-musl-stdout-line-buffered-exp-interleave

## 症状

scrub 真机 `make check` 中 t12/t22 FAIL：`diff tNN.exp tNN.out` 只出现
顺序移动块（`8d7`/`9a9`、`1a2`/`4d4`），out 与 exp 的**行集合完全一致**，
仅 stderr 诊断行（`warning: -s size < file size`、`does not exist`）在
stdout 行序中的位置不同。

## 根因

glibc 管道 stdout **全缓冲**（约 4K 一刷），stderr 无缓冲 → .exp 捕获顺序 =
「诊断行先落、stdout 批量后落」；musl（OHOS libc）对管道 stdout **逐行刷新**
（等价行缓冲）→ 诊断行按调用顺序插进 stdout 行序中间。同一程序两种 libc 两种
交错顺序，全文 diff 必挂。这不是功能缺陷，不要去改算法。

## 修复（patches/0004-src-scrub.c.patch，+5 行）

main() 入口：

```c
setvbuf(stdout, NULL, _IOFBF, BUFSIZ);
```

统一为全缓冲（POSIX 通用、无平台宏）；进度条既有 `fflush(stdout)` 不受影响。
修复后 t12/t22 PASS，原 PASS 用例无一回退。

## 判据（避免误归因）

失败用例满足「out 与 exp 行集合一致、diff 仅 a/d 移动块、移动行都是 stderr
诊断」即属本类；先 `diff` 确认无内容差异行，再对照本条处置。
