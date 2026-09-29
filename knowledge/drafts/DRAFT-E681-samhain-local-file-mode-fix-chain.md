# DRAFT-E681-samhain-local-file-mode-fix-chain

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-E681-samhain-local-file-mode-fix-chain.kv`

**标题**：samhain 4.1.4（HIDS）在 OHOS 上 configure/运行/测试五类断点：
                        sum 缺失致 AC_SUBST 空宏、dnmalloc 断言、seccomp 禁 SysV IPC、
                        glibc 传递 include 假设、hmmac mktemp 权限坏的修复链

**阶段: `configure|build|test_package` · 触发: `configure|autotools|make|conan` · 类别: `autotools|configure|entropy|allocator|seccomp|portability|hmdfs` · 严重级: `2`**

## 错误签名（error_signature）

```text
'assertion failed \(.*\): hashval < AMOUNTHASH|invalid token at start of a preprocessor expression|expr: non-integer argument|Signal 31 \(core dumped\)|Bad system call \(core dumped\)|use of undeclared identifier ._PATH_MOUNTED.|could not setup config files machinery|subs1\.awk: Permission denied'
```

## 根因（root_cause）

>
  1) 熵源空宏：c_random.sh 用 sum(1) 计算 16 位校验当熵源，设备（toybox）无 sum →
     命令not found 被 2>/dev/null 吞掉 → configure 里 my_key_*/POS_TF 的
     `expr` 链拿到空串（`expr % 65536` 报 non-integer、`expr / 32768` 报
     Unexpected extra input）→ AC_SUBST/AC_DEFINEUNQUOTED 写出空宏 →
     源码 `#if (POS_TF == 1)` 展开成 `#if ( == 1)` →
     invalid token at start of a preprocessor expression，make 期集中爆炸。
  2) dnmalloc 运行期断言：samhain 自带的 dnmalloc 分配器哈希假设
     （hash(p)=(p-startheap)>>7 与 AMOUNTHASH 上界）在 OHOS 上失配，
     任何 samhain 调用（含 -v）启动即 `assertion failed ... hashval < AMOUNTHASH`。
  3) seccomp 禁 SysV IPC：OHOS 应用层 seccomp 拒绝 msgget（C 探针直接
     Bad system call / rc=159）。上游 `--enable-message-queue` 变体编译出的
     sh_err_console.c 在启动早期 msgget → 进程被 SIGSYS 杀（samhain 信号处理器
     打印 `Signal 31 (core dumped)`），表现为「测试 9 条 hash 向量全部崩溃」，
     极易误判成 hash 实现坏了。
  4) glibc 传递 include 假设：老 C 代码靠上游系统的传递包含拿宏/类型
     （_PATH_MOUNTED 经 glibc 链、u_int 经 glibc sys/time.h 链），OHOS libc
     头文件不传递 → undeclared identifier / unknown type name。
  5) hmmac mktemp：`mktemp -d`（umask 077）产出 2700+属主映射的目录，
     config.status 写 confXXXX/subs1.awk Permission denied →
     could not setup config files machinery。

## 方案（rec_approach）

local-file-mode-five-fix（回退熵源 + 关自定义分配器 + 摘 IPC 旗标 + 补显式 include + mktemp shim）

## 关键词

POS_TF, c_random.sh, sum(1), dnmalloc, hashval, AMOUNTHASH,
                        message-queue, msgget, SysV IPC, SIGSYS, Signal 31,
                        _PATH_MOUNTED, paths.h, mntent, config.status, subs1.awk,
                        mktemp -d, AS_TMPDIR, AC_SUBST, preprocessor expression

## 来源

本条目取自 `knowledge/drafts/DRAFT-E681-samhain-local-file-mode-fix-chain.kv`；promote 后对应 `knowledge/doc/E###.md`。
