# libffi 3.5.2 ffi_closure 闭包功能 — 鸿蒙移植方案

> **状态**：四补丁与 CFI 配方修复已固化；目标端 r10 的上游测试通过率为 363/363（100%），O0/O2 共 726/726 条执行记录 PASS，安装包 consumer 1/1 PASS。r7 的 722 PASS、4 FAIL 作为根因定位历史保留。
> **日期**：2026-07-24（由 2026-03-28 探索记录收敛）
> **适用版本**：libffi 3.5.2
> **目标平台**：OpenHarmony / HarmonyOS (aarch64, musl libc, HongMeng Kernel 1.11.0)

---

## 一、问题背景

### 1.1 ffi_closure 是什么？

`ffi_closure` 是 libffi 提供的**闭包/回调机制**。它允许用户在运行时动态创建一个可调用的函数入口点，当外部代码调用这个入口点时，控制流会被转发到用户预先注册的 C 函数上。

典型应用场景：
- **Python ctypes** 的 `CFUNCTYPE` 回调函数
- **JS/NAPI ↔ C** 的互调回调桥接
- **动态代码生成**中的间接调用跳板

核心需求：**在运行时分配一块可执行内存**，写入跳转指令，供外部调用者跳转执行。

### 1.2 鸿蒙为什么会导致 ffi_closure 失败？

鸿蒙系统实施了**内核级 W^X（Write XOR Execute）安全策略**：

- **禁止**所有带有 `PROT_EXEC` 的 `mmap()`（匿名、文件、memfd 均拒绝，errno=22 EINVAL）
- **禁止**通过 `mprotect()` 将已映射内存提升为可执行
- **但允许** `MAP_FIXED` 替换**已有可执行映射**（这是我们的突破口）

此外，鸿蒙的 **HMDFS（分布式文件系统）** 会导致 `/proc/self/maps` 中的文件路径与应用进程可访问的路径不一致（详见第四章根因分析）。

---

## 二、libffi 闭包的四种实现策略

libffi 在 Linux 上为闭包内存分配提供了四种策略，按优先级依次尝试：

### 策略对比

| # | 策略名称 | 宏定义 | 原理 | 鸿蒙兼容性 |
|---|---------|--------|------|-----------|
| 1 | Static Trampoline | `FFI_EXEC_STATIC_TRAMP` | 将 .so 内已有的 trampoline code table 通过 MAP_FIXED 覆盖到匿名 RW 映射的上半部分 | ✅ **理论可行** |
| 2 | MMAP Exec Writ | `FFI_MMAP_EXEC_WRIT` | 创建临时文件，分别用 RW 和 RX 映射到不同地址 | ❌ 文件 RX 映射被禁止 |
| 3 | Trampoline Table | `FFI_EXEC_TRAMPOLINE_TABLE` | macOS Mach vm_remap() | ❌ 仅 Apple |
| 4 | malloc 直接分配 | 默认 fallback | malloc 返回的内存即可执行 | ❌ W^X 禁止 |

**结论：只有策略 1（FFI_EXEC_STATIC_TRAMP）在鸿蒙上有可能工作。**

---

## 三、FFI_EXEC_STATIC_TRAMP 原理详解

### 3.1 核心思想

`FFI_EXEC_STATIC_TRAMP` 是 Linux 5.18+ 内核引入的方案，libffi 3.5.2 实现了用户态支持。核心思想是：

> **不创建新的可执行内存，而是复用 .so 文件本身已有的可执行代码段。**

### 3.2 trampoline code table

在 libffi 编译时，源码 `src/aarch64/trampoline_table.S` 会生成一段静态的跳板代码，编译进 `libffi.so` 的 `.text` 段。这段代码被称为 `trampoline_code_table`。

每个 trampoline 是一小段固定大小的 aarch64 指令序列，功能是：
1. 通过 PC 相对寻址读取参数块（目标地址 + 数据指针）
2. 跳转到目标地址执行

通过修改参数块的内容，可以动态控制跳转目标——这就是「闭包」的实现。

### 3.3 内存布局

```
tramp_globals.fd 指向的文件: libffi.so
tramp_globals.offset: trampoline_code_table 在文件中的偏移 (如 0x10000)

分配闭包时的内存布局：
┌─────────────────────────────┐ ── addr
│  上半部分: code_table        │  PROT_READ | PROT_EXEC
│  (MAP_FIXED from libffi.so)  │  内容 = trampoline_code_table 的拷贝
│  包含 N 个 trampoline slot   │
├─────────────────────────────┤ ── addr + map_size
│  下半部分: parm_table        │  PROT_READ | PROT_WRITE
│  (匿名映射)                  │  每个 slot 对应一个 tramp_parm
│  { target, data } 对         │
└─────────────────────────────┘ ── addr + 2*map_size
```

关键步骤：
1. 先用 `MAP_ANONYMOUS` 分配 `2 * map_size` 的 RW 区域
2. 再用 `MAP_FIXED | PROT_READ | PROT_EXEC` 将上半部分替换为 `libffi.so` 文件中 `trampoline_code_table` 的映射
3. 由于 MAP_FIXED 替换的是已有映射（非新建），鸿蒙 W^X 不阻止

### 3.4 调用链

```
ffi_closure_alloc(size, &code)
  │
  ├─ dlmalloc(size)                         // closures.c 内嵌的 dlmalloc 分配器
  │    └─ dlmmap(RW, ANONYMOUS)             // dlmalloc 的 mmap hook
  │         └─ ffi_tramp_is_supported()     // 检查 static tramp 是否可用
  │              └─ ffi_tramp_init()        // 首次调用时初始化
  │                   ├─ ffi_tramp_arch()    // ✅ 获取 trampoline_code_table 地址
  │                   │    返回 .text 段中的 code_table 地址
  │                   │    设置 tramp_globals.text / size / map_size
  │                   │
  │                   └─ ffi_tramp_init_os()  // 获取 libffi.so 的文件 fd
  │                        ├─ ffi_tramp_get_libffi()   // ← 🔴 这里失败！
  │                        │    从 /proc/self/maps 找路径 → open()
  │                        │    鸿蒙上 open(HMDFS路径) 返回 ENOENT
  │                        │
  │                        └─ ffi_tramp_get_temp_file() // 回退：创建临时文件
  │                             └─ open_temp_exec_file() // 🔴 鸿蒙上也失败
  │                                  (memfd_create 不存在、tmp 不可执行)
  │
  ├─ ffi_tramp_alloc(0)                  // 分配一个 trampoline slot
  │    └─ tramp_table_alloc()            // 需要 fd 来做 MAP_FIXED 映射
  │         └─ tramp_table_map()         // mmap ANONYMOUS + mmap MAP_FIXED
  │              └─ mmap(MAP_FIXED, fd, offset)  // 需要有效的 fd
  │
  └─ ffi_tramp_get_addr(ftramp)          // 获取可执行的跳板地址
       返回 code_table 中某个 slot 的地址（这就是 *code）
```

### 3.5 依赖条件

- **编译时**：`FFI_EXEC_STATIC_TRAMP=1` 需要在 `fficonfig.h` 中定义
- **项目头文件**：官方 3.5.2 已提供 `include/tramp.h`，不需要内核头或空 stub
- **运行时**：需要一个指向包含 trampoline code table 的已映射 ELF（共享库或静态链接后的可执行文件）的有效文件描述符 `fd`

---

## 四、根因分析

### 4.1 失败位置

`ffi_tramp_get_libffi()` 函数（`src/tramp.c` 第 ~175-230 行）：

```c
static int ffi_tramp_get_libffi(void) {
    // 1. 读 /proc/self/maps，找到 libffi.so 的映射段
    //    解析出文件路径 file 和页内偏移 offset
    //    计算 tramp_globals.offset = offset + (addr - start)
    
    // 2. 打开文件
    tramp_globals.fd = open(file, O_RDONLY | O_CLOEXEC);  // ← 🔴 这里失败
    if (tramp_globals.fd == -1)
        return 0;  // 返回失败
    
    // 3. 用 fd 做 MAP_FIXED 映射验证
    if (!tramp_table_alloc()) { ... return 0; }
    return 1;
}
```

### 4.2 失败原因：HMDFS 路径不可访问

`/proc/self/maps` 中 libffi.so 的路径为：

```
5a497c4000-5a497d5000 r-xp 00004000 104:65 4132362 \
    /data/service/el2/100/hmdfs/account/files/Docs/usr/local/lib/libffi.so.8.2.0
```

但 `open("/data/service/el2/100/hmdfs/account/files/Docs/...", O_RDONLY)` 返回 `ENOENT (errno=2)`。

原因：这是 HMDFS 的**内核内部挂载路径**，对应用进程不可直接访问。应用只能通过用户空间挂载点 `/storage/Users/currentUser/...` 访问文件。

### 4.3 路径映射关系

从 `/proc/self/mounts` 可以看到：

```
/data/service/el2/100/hmdfs/account  /storage/Users/currentUser  hmdfs  rw,...
```

路径转换关系：
```
maps 路径:   /data/service/el2/100/hmdfs/account/files/Docs/usr/local/lib/libffi.so.8.2.0
             |←───────── mount_source ──────────→|←─ 中间层 ──→|←── 实际路径 ──→|

可访问路径:  /storage/Users/currentUser/usr/local/lib/libffi.so.8.2.0
             |←───────── mount_target ──────────→|←── 实际路径 ──→|
```

转换规则：`去掉 mount_source 前缀，再去掉 "/files/Docs/" 中间层前缀（保留末尾的 '/'，即跳过 11 个字符），拼接 mount_target`

### 4.4 其他 fd 获取方式的失败

| 方案 | 结果 | 失败原因 |
|------|------|---------|
| `open(maps_path)` | ❌ ENOENT | HMDFS 内部路径不可直接访问 |
| `open("/proc/self/map_files/...")` | ❌ ENOENT | 鸿蒙未实现此 procfs 接口 |
| `readlink("/proc/self/map_files/...")` | ❌ ENOENT | 同上 |

### 4.5 已验证可行的方案

直接用可访问路径 open：
```
open("/storage/Users/currentUser/usr/local/lib/libffi.so.8.2.0", O_RDONLY)
→ 成功, fd=3
```

MAP_FIXED 映射已验证：
```
mmap(NULL, 8192, RW, ANONYMOUS)     → 成功 (匿名区域)
mmap(addr, 4096, RX, MAP_FIXED, fd, offset) → 成功 (替换上半部分)
memcmp(orig, copy, 32) → 0 (内容一致)
```

---

## 五、解决方案：Mount 表路径回退

### 5.1 修改位置

修改 `src/tramp.c`：增加候选路径打开与映射内容校验辅助函数，并在
`ffi_tramp_get_libffi()` 的官方路径打开失败后调用该辅助流程。

### 5.2 修改逻辑

在原有 `open(file, open_flags)` 失败后，读取 `/proc/self/mounts` 中的 HMDFS
挂载关系，将 maps 路径转换为可访问路径后重试。下面的代码只展示控制流；
提交中的 `0003-tramp-hmdfs-path.patch` 还强制执行挂载类型精确匹配、路径前缀边界、
`snprintf` 截断检查、普通文件类型检查，以及从
`tramp_globals.offset` 开始逐段读取并与当前映射字节比较。任一检查不满足都会
关闭候选文件并继续下一个候选，不会接受仅凭路径推导得到的文件。

```c
static int
ffi_tramp_get_libffi (void)
{
  FILE *fp;
  char file[PATH_MAX], line[PATH_MAX + 100], perm[10], dev[10];
  unsigned long start, end, offset, inode;
  uintptr_t addr = (uintptr_t) tramp_globals.text;
  int nfields, found;
  int open_flags = O_RDONLY;

#ifdef O_CLOEXEC
  open_flags |= O_CLOEXEC;
#endif

  /* ---- 原有逻辑：读 /proc/self/maps ---- */
  snprintf(file, PATH_MAX, "/proc/%d/maps", getpid());
  fp = fopen(file, "r");
  if (fp == NULL)
    return 0;

  found = 0;
  while (feof(fp) == 0) {
    if (fgets(line, sizeof(line), fp) == 0)
      break;
    nfields = sscanf(line, "%lx-%lx %9s %lx %9s %ld %s",
        &start, &end, perm, &offset, dev, &inode, file);
    if (nfields != 7)
      continue;
    if (addr >= start && addr < end) {
      tramp_globals.offset = offset + (addr - start);
      found = 1;
      break;
    }
  }
  fclose(fp);

  if (!found)
    return 0;

  /* ---- 原有逻辑：打开文件 ---- */
  tramp_globals.fd = open(file, open_flags);
  if (tramp_globals.fd == -1)
    {
      /*
       * 鸿蒙 HMDFS 回退：/proc/self/maps 中的路径是 HMDFS 内部路径，
       * 对应用进程不可见。需要通过 /proc/self/mounts 做路径转换。
       *
       * 路径转换示例：
       *   maps 路径: /data/service/el2/100/hmdfs/account/files/Docs/usr/local/lib/libffi.so
       *   mount 表:  /data/service/el2/100/hmdfs/account → /storage/Users/currentUser
       *   可访问路径: /storage/Users/currentUser/usr/local/lib/libffi.so
       *   转换规则: mount_target + (maps_path 去掉 mount_src 前缀，再去掉 "/files/Docs/")
       */
      FILE *mf;
      char mline[PATH_MAX * 3];
      char resolved[PATH_MAX];

      mf = fopen("/proc/self/mounts", "r");
      if (mf != NULL)
        {
          while (fgets(mline, sizeof(mline), mf) != NULL)
            {
              char msrc[PATH_MAX], mtgt[PATH_MAX], mtype[64];

              if (sscanf(mline, "%1023s %1023s %63s", msrc, mtgt, mtype) < 3)
                continue;

              /* 检查 maps 文件路径是否以挂载源路径为前缀 */
              if (strncmp(file, msrc, strlen(msrc)) != 0)
                continue;

              const char *suffix = file + strlen(msrc);

              /* 尝试 1：直接替换 mount_source → mount_target */
              snprintf(resolved, sizeof(resolved), "%s%s", mtgt, suffix);
              tramp_globals.fd = open(resolved, open_flags);
              if (tramp_globals.fd != -1)
                break;

              /*
               * 尝试 2：跳过 HMDFS 插入的中间路径前缀。
               * HMDFS 在挂载点下插入 "/files/Docs/" 作为实际文件访问根目录，
               * 需要去掉这个前缀才能得到实际可访问的路径。
               */
              if (strncmp(suffix, "/files/Docs/", 12) == 0)
                {
                  snprintf(resolved, sizeof(resolved), "%s%s",
                           mtgt, suffix + 11);
                  tramp_globals.fd = open(resolved, open_flags);
                  if (tramp_globals.fd != -1)
                    break;
                }
            }
          fclose(mf);
        }

      if (tramp_globals.fd == -1)
        return 0;
    }

  /* ---- 原有逻辑：验证 trampoline table 可映射 ---- */
  if (!tramp_table_alloc())
    {
      close(tramp_globals.fd);
      tramp_globals.fd = -1;
      return 0;
    }
  return 1;
}
```

### 5.3 方案优点

1. **最小侵入性**：仅修改 `ffi_tramp_get_libffi()` 一个函数，在原有 `open()` 失败后才触发回退，不影响非鸿蒙平台
2. **边界清晰**：只处理 mount 类型为 `hmdfs` 且前缀边界完整匹配的记录
3. **内容绑定**：候选必须是普通文件，并与当前 trampoline 映射的全部字节一致
4. **无额外依赖**：只用标准 POSIX API（fopen、fgets、sscanf、open）
5. **向后兼容**：如果路径转换失败，仍会 fallback 到 `ffi_tramp_get_temp_file()`

### 5.4 需要的其他修改

#### 5.4.1 编译时启用 FFI_EXEC_STATIC_TRAMP

确保 `fficonfig.h` 中包含：
```c
#define FFI_EXEC_STATIC_TRAMP 1
```

官方 3.5.2 `configure` 使用 `--enable-exec-static-tramp` 命名，且 aarch64 `linux-*` 主机规则会自动定义该宏。当前 SDK12 构建通过 `grep '^#define FFI_EXEC_STATIC_TRAMP 1' fficonfig.h` 验证；不手改生成的 `fficonfig.h`。

#### 5.4.2 使用官方 tramp.h

官方 3.5.2 压缩包已包含 `include/tramp.h`，构建直接使用该头文件。不创建空 stub，也不向 CFLAGS 注入额外 stub 路径。

#### 5.4.3 closures.c 保持官方内容

官方 3.5.2 `src/closures.c` 不含探索阶段的调试 `fprintf`，当前四补丁也不修改该文件。官方与补丁 replay 后 SHA256 均为 `bf5d74f3fd1fc9060f71598c4ca25a84b6d5ea38313fa86e41e3ab743c2abc5f`。

### 5.5 完整的编译流程

```bash
# 1. 准备源码
tar xzf libffi-3.5.2.tar.gz
cd libffi-3.5.2

# 2. 按 conandata.yml 顺序应用四补丁
patch -p1 < patches/0001-config-guess-sub-ohos.patch
patch -p1 < patches/0002-configure-hmdfs-umask.patch
patch -p1 < patches/0003-tramp-hmdfs-path.patch
patch -p1 < patches/0004-tramp-posix-capability.patch

# 3. 配置静态 PIC 制品
CFLAGS="-fPIC -O2 -funwind-tables" ./configure \
  --disable-shared --enable-static --disable-multi-os-directory \
  --disable-dependency-tracking \
  --host=aarch64-linux-ohos --prefix=$HOME/usr/local
grep '^#define FFI_EXEC_STATIC_TRAMP 1' fficonfig.h
grep '^#define HAVE_MMAP_STATIC_TRAMP 1' fficonfig.h

# 4. 编译和安装
make -j$(nproc)
make install
```

---

## 六、AArch64 异常展开链与 CFI 修复

### 6.1 目标端 r7 的失败闭集

r7 在目标端完整执行 363 个官方独立入口的 O0/O2 配置，共 726 次。结果为
`722 PASS / 4 FAIL`，即 361/363 个独立入口通过。失败闭集只有：

| 官方入口 | O0 | O2 |
|---|---|---|
| `libffi.closures/unwindtest.cc` | FAIL | FAIL |
| `libffi.closures/unwindtest_ffi_call.cc` | FAIL | FAIL |

普通 C++ `throw/catch` 基线和其余 722 次配置均通过，因此问题被限定在异常需要跨越
libffi AArch64 汇编调用帧时。r7 不是成功结果，四项失败也不会计入通过数。

### 6.2 配置探针为何得到错误结论

上游 `m4/asmcfi.m4` 使用一个 C 函数内的 inline assembly 编译检查
`.cfi_remember_state` 与 `.cfi_restore_state`。目标 clang 在普通 C 编译且没有请求
unwind table 时，不一定为该函数建立 `.cfi_startproc`/`.cfi_endproc` 区间；汇编器
因此拒绝位于活动帧区间之外的 state 指令。配置日志随即记录：

```text
checking assembler .cfi pseudo-op support... no
```

这不是汇编器缺少 CFI 指令，而是探针所在的 C 函数没有建立帧区间。后续影响沿以下
链路传播：

```text
configure probe = no
  -> fficonfig.h 不定义 HAVE_AS_CFI_PSEUDO_OP
  -> include/ffi_cfi.h 将 cfi_startproc/cfi_endproc 等宏展开为空
  -> src/aarch64/sysv.S 生成的 sysv.o 没有 .eh_frame
  -> 异常无法可靠跨越 ffi_call_SYSV / ffi_closure_SYSV
  -> 两个官方 unwind 入口在 O0/O2 均失败
```

### 6.3 配方修复及其约束

OHOS 分支在 `AutotoolsToolchain` 生成配置环境前追加 `-funwind-tables`。该选项使
配置探针的 C 函数建立 unwind frame，探针由实际编译得到 `yes`，并使上游发布版
`configure` 正常生成：

```c
#define HAVE_AS_CFI_PSEUDO_OP 1
```

配方随后读取 `fficonfig.h`，要求该定义恰好出现一次，否则立即终止构建。修复不写
Autoconf cache 结论，不修改生成的 `configure` 或 `fficonfig.h`，也不改变官方测试
源码与成功判定。非 OHOS 构建不增加该标志。

### 6.4 聚焦诊断与全量验收

`device-cfi-diagnostic-r2.sh` 只允许在全新目录启动一次，并按以下顺序验收：

1. fresh configure 必须输出 CFI 探针 `yes`，`fficonfig.h` 必须有唯一宏定义；
2. `sysv.o` 必须同时包含 `.eh_frame` 和 `.rela.eh_frame`；
3. `llvm-nm -S` 的函数起点与长度必须和 `llvm-objdump --dwarf=frames` 的 FDE
   区间精确对应，至少覆盖 `ffi_call_SYSV` 与 `ffi_closure_SYSV`；
4. 链接后的 O0/O2 上游程序必须继续保留对应 FDE 区间；
5. 普通 C++ 基线 1 项及四个原失败配置必须全部按官方输出通过。

runner 会保留源码、四补丁、生成头文件、静态库、目标对象、链接产物、原始日志和
SHA256 清单。独立回读校验器会重新计算所有哈希，并重新解析 symbol/FDE 对应关系。
任何缺失、重复、未知终态或区间不一致均为失败。

### 6.5 r10 最终全量结果

r10 从同一官方归档重新发现 363 个独立入口，按 O0/O2 生成 726 条唯一执行记录。
上游测试通过率为 `363/363 (100%)`，O0 为 `363/363 PASS`，O2 为
`363/363 PASS`，合计 `726/726 PASS`。安装包 consumer 为 `1/1 PASS`。
FAIL、XPASS、XFAIL、UNSUPPORTED、UNRESOLVED、TIMEOUT、ERROR 和未知终态均为 0。

独立校验器重新派生发现清单，逐项核对 726 条 manifest、每项原始编译/签名/运行
日志、消费者输出和 3661 个证据文件，并验证 3662 条 SHA256 记录。证据归档 SHA256
为 `a8b2a328ccb5f59d7fcc547ab59a811cbf86ffe5ff138fe73d2fd29ad383873c`，
summary SHA256 为
`b7d9cf4c4fcaa83203d717d13fc1b7ce6aaa8a08372fce6d11ff655565d5f8c9`。
这完成了 r7 四项失败到 r10 全量通过的闭环；O0/O2 不重复计入独立测试数。

---

## 七、验证计划

### 7.1 编译验证

```bash
# 检查 fficonfig.h
grep FFI_EXEC_STATIC_TRAMP fficonfig.h
# 预期输出: #define FFI_EXEC_STATIC_TRAMP 1

# 检查 tramp.o 被编译
ls -la src/.libs/tramp.o
ls -la src/.libs/libffi_la-tramp.o

# 检查静态 archive 符号表
llvm-nm $HOME/usr/local/lib/libffi.a | grep tramp
```

### 7.2 功能验证

```c
#include <stdio.h>
#include <ffi.h>

// 回调函数
void callback(ffi_cif *cif, void *ret, void **args, void *userdata) {
    int *input = (int *)args[0];
    *(int *)ret = *input * 2;
    printf("callback called with %d, userdata=%s\n", *input, (char *)userdata);
}

int main(void) {
    ffi_cif cif;
    ffi_type *args[] = { &ffi_type_sint };
    
    if (ffi_prep_cif(&cif, FFI_DEFAULT_ABI, 1, &ffi_type_sint, args) != FFI_OK) {
        printf("ffi_prep_cif failed\n");
        return 1;
    }
    
    // 分配闭包
    void *code;
    ffi_closure *closure = ffi_closure_alloc(sizeof(ffi_closure), &code);
    if (closure == NULL || code == NULL) {
        printf("ffi_closure_alloc failed\n");
        return 1;
    }
    printf("closure=%p, code=%p\n", closure, code);
    
    // 绑定回调
    if (ffi_prep_closure_loc(closure, &cif, callback, "hello", code) != FFI_OK) {
        printf("ffi_prep_closure_loc failed\n");
        return 1;
    }
    
    // 通过函数指针调用回调
    int (*func)(int) = (int (*)(int))code;
    int result = func(21);
    printf("func(21) = %d (expected 42)\n", result);
    
    ffi_closure_free(closure);
    printf("SUCCESS!\n");
    return 0;
}
```

编译运行：
```bash
clang -o test_closure test_closure.c \
    -I$HOME/usr/local/include \
    $HOME/usr/local/lib/libffi.a -lpthread
./test_closure
```

预期输出：
```
closure=0x..., code=0x...
callback called with 21, userdata=hello
func(21) = 42 (expected 42)
SUCCESS!
```

### 7.3 Python ctypes 验证边界

```python
import ctypes

# 仅适用于另行构建的共享 libffi，不属于当前静态 Conan 包门禁
# 加载 libffi
libffi = ctypes.CDLL("libffi.so.8")

# 定义回调类型
CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)

def my_callback(value):
    print(f"Python callback: {value}")
    return value * 3

# 创建回调
cb = CALLBACK(my_callback)
result = cb(10)
print(f"Result: {result}")  # 预期: 30
```

---

## 八、风险与注意事项

### 8.1 HMDFS 中间路径可能变化

当前观察到的 HMDFS 中间层是 `/files/Docs/`，但这个路径可能在以下情况变化：
- 不同鸿蒙版本
- 不同设备
- 不同用户账户配置

为增强健壮性，回退逻辑中应尝试多种路径前缀：
```c
/* 按优先级尝试多种中间层路径 */
const char *hmdfs_prefixes[] = { "/files/Docs/", "/files/", NULL };
```

### 8.2 闭包性能

`FFI_EXEC_STATIC_TRAMP` 方案下：
- 每次分配闭包需要一次 `mmap(MAP_FIXED)` 系统调用
- trampoline table 以 `map_size`（通常是 `ntramp * tramp_size`，对齐到页）为单位分配
- 每个 table 包含多个 trampoline slot，后续分配可直接复用已有 table 的空闲 slot

### 8.3 线程安全

`tramp.c` 使用 `pthread_mutex_t` 保护全局状态，多线程调用是安全的。

### 8.4 静态链接

静态链接 libffi 时，`trampoline_code_table` 会被链接到最终可执行文件中。此时 `/proc/self/maps` 找到的是可执行文件本身而非 .so，mount 表回退逻辑同样适用（如果可执行文件在 HMDFS 挂载点下）。

---

## 九、补丁清单

| 补丁文件 | 修改内容 |
|---------|---------|
| `0001-config-guess-sub-ohos.patch` | config.guess/config.sub 识别 HarmonyOS 和 `linux-ohos` triplet |
| `0002-configure-hmdfs-umask.patch` | 仅对 `linux-ohos*` 的 configure 临时目录使用 HMDFS 可用的 022，其他 host 保持 077 |
| `0003-tramp-hmdfs-path.patch` | 解析 hmdfs mount，并以普通文件类型和映射字节全量一致性校验候选路径 |
| `0004-tramp-posix-capability.patch` | 由 configure 编译探针检查 mmap、文件和 pthread 接口，并通过 `HAVE_MMAP_STATIC_TRAMP` 门禁实现 |

---

## 十、关键知识总结

### 鸿蒙 W^X 策略

- **禁止**：所有 `mmap(MAP_ANONYMOUS, PROT_EXEC)`、`mmap(fd, PROT_EXEC)`、`mprotect(PROT_EXEC)`
- **允许**：`mmap(MAP_FIXED, fd, PROT_EXEC)` 替换已有映射
- **原理**：MAP_FIXED 不创建新的可执行映射，只是替换已有映射的属性/内容

### HMDFS 路径转换

- `/proc/self/maps` 中的路径是 HMDFS 内核内部路径
- 应用进程只能通过用户空间挂载点访问文件
- 路径转换依赖 `/proc/self/mounts` 中的映射关系
- HMDFS 在挂载点下插入 `/files/Docs/` 作为文件访问根目录

### 鸿蒙软链接限制（历史探索路径）

- `ln -sf` 受 SELinux 限制，创建带随机后缀的文件而非真正软链接
- musl 动态加载器不认这种伪软链接
- 解决方案：使用 `cp` 创建实际文件副本

### make install .so 截断（历史共享库路径）

- `make install` 安装的 `.so` 文件可能被截断（10K vs 实际 109K）
- 当前配方固定 `--disable-shared --enable-static`，不生成或安装 `.so`；该现象不属于当前制品路径

---

## 附录：调试记录摘要

| 日期 | 调试内容 | 结论 |
|------|---------|------|
| 03-28 | 第一次编译（不含 STATIC_TRAMP） | ffi_closure_alloc 返回 NULL（预期） |
| 03-28 | 第二次编译（含 STATIC_TRAMP） | 编译成功，trampoline_code_table 存在于 .so 中 |
| 03-28 | 独立 C 程序验证 MAP_FIXED | 匿名 RW + MAP_FIXED 替换为文件 RX ✅ 可行 |
| 03-28 | ffi_tramp_is_supported() 返回 0 | tramp 初始化失败 |
| 03-28 | closures.c 添加 dlmmap 调试 | 确认 ffi_tramp_is_supported()=0, execfd=-1 |
| 03-28 | 分析 ffi_tramp_init 调用链 | ffi_tramp_get_libffi 中 open() 失败 |
| 03-28 | 诊断 maps 路径类型 | 确认为 HMDFS 内部路径，open 返回 ENOENT |
| 03-28 | 测试 /proc/self/map_files | 鸿蒙未实现此接口 |
| 03-28 | 分析 /proc/self/mounts | 找到 HMDFS 挂载映射关系 |
| 03-28 | 验证 mount 表路径转换 | open(转换后路径) 成功，fd=3 |
| 03-28 | 设计 mount 表回退方案 | 记录为本文档 |
| 07-23 | r7 全量执行 | 363 个入口的 O0/O2 共 722 PASS、4 FAIL，失败限定到两个 unwind 入口 |
| 07-23 | CFI 配方修复 | `-funwind-tables` 使官方探针通过，`sysv.o` 恢复帧信息 |
| 07-23 | r10 全量执行 | 上游 363/363（100%），O0/O2 共 726/726 PASS，consumer 1/1 PASS |
