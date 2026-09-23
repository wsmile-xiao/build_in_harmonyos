# DRAFT-E659 — quickfix 1.15.1 AtomicCount 的 x86 专用内联汇编在 aarch64 上汇编失败

- 草稿号：E659（`tools/knowledge_id.py --claim --task feat/quickfix-1.15.1` 取号，
  取号时刻三面扫描 + 同级 worktree 人工扫描均确认空号）
- 配套：`.kv` 同名文件（本目录）
- 状态：UNMATCHED，待人工审核晋升正式 E 条目

## 错误形态（逐字）

```text
../AtomicCount.h:163:11: error: unrecognized instruction mnemonic
          "lock\n\t"
          ^
<inline asm>:1:2: note: instantiated into assembly here
        lock
        ^
../AtomicCount.h:163:18: error: unrecognized instruction mnemonic, did you mean: add, addp, adds, addv, fadd, madd?
          "lock\n\t"
                 ^
<inline asm>:2:2: note: instantiated into assembly here
        xadd x8, [x9]
        ^
```

实测环境：OHOS aarch64 + clang（OHOS SDK，`aarch64-unknown-linux-ohos`），
quickfix 1.15.1 `src/C++` 首个触及 `AtomicCount.h` 的 TU。

## 根因

`src/C++/AtomicCount.h` 的分支链：

```cpp
#if defined(__SUNPRO_CC) || defined(__TOS_AIX__)   // mutex 兜底
#elif _MSC_VER                                     // Interlocked*
#else                                              // ← 所有其他 GCC/Clang
  // boost/detail/atomic_count_gcc_x86.hpp 的拷贝
  __asm__ __volatile__("lock\n\t" "xadd %1, %0": ...);
#endif
```

最后的 `#else` 分支只按编译器厂牌分流、没有架构判据，把 **x86 专用** 的
`lock; xadd` 当成 GCC/Clang 通用实现。aarch64 汇编器无此助记符，直接拒绝。
这是 boost `atomic_count_gcc_x86` 被第三方拷贝时的经典误用形态：boost 原文
件名里的 `gcc_x86` 才是真正的适用面判据。

## 修复（rec_approach: replace-inline-asm-with-atomic-builtin）

```cpp
// 原：内联汇编（返回旧值，"memory","cc" 全屏障）
// 新：
return __atomic_fetch_add(pw, dv, __ATOMIC_SEQ_CST);
```

- `__atomic_fetch_add` 返回**修改前**旧值 = `xadd` 语义；
- `__ATOMIC_SEQ_CST` = 原 `"memory","cc"` clobber 的全屏障；
- 函数其余部分（`+1/-1` 的调用点语义、`int value_` 存储宽度）零改动；
- x86/aarch64/riscv/loongarch 全部可用，纯局部 diff，可上游化。

实测：补丁后 quickfix 1.15.1 全库编译干净，单元测试 200/200 通过
（Success: 200 tests passed.）。

## 禁忌（forbid）

- ❌ 手工翻译成 aarch64 `ldxr/stxr` 独占循环：引入新的架构专属维护面，
  独占监视器释放条件极易写错；
- ❌ 用非原子 `++/--` 替换：该计数被跨线程读改写，非原子替换是数据竞争；
- ❌ 关优化/换标志位掩盖：汇编器对未知助记符的拒绝与优化级别无关。

## 复现/验证命令（设备可直执行，落当前目录不用 /tmp）

```sh
d="$PWD/atomiccount-probe" && mkdir -p "$d" && printf 'int main(){ int v=0; return __atomic_fetch_add(&v,1,__ATOMIC_SEQ_CST)==0 ? 0 : 1; }\n' > "$d/probe.c" && clang -fsyntax-only "$d/probe.c" && echo "builtin OK on this target"
```
