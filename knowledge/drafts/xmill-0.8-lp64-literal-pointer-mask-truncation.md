# Draft: `DRAFT-XMILL-08-LP64-LITERAL-POINTER-MASK-TRUNCATION`
> Stem: `xmill-0.8-lp64-literal-pointer-mask-truncation` — pairs with the same-stem `.kv`

# 老 32 位代码的字面量指针掩码在 aarch64 上截断指针：首错只在运行期以 SIGSEGV 出现

## 基本信息

- **ID**: DRAFT-XMILL-08-LP64-LITERAL-POINTER-MASK-TRUNCATION
- **严重度**: 1（编译全绿、运行必崩，且崩溃点与根因相距很远）
- **类别**: portability | arch | 64bit | lp64 | undefined-behavior
- **触发工具**: clang | cmake | conan | runtime
- **阶段**: compilation（无诊断）→ runtime（SIGSEGV）
- **来源**: xmill 0.8 适配（2026-10-01）

## 错误特征

编译期**完全没有任何警告**：`cmake --build . -j2` → `rc=0`，两个可执行文件正常产出，
`readelf` 显示正确的 `e_machine=0xAArch64`(0x00B7) 与 `/lib/ld-musl-aarch64.so.1` 解释器。
压缩路径也完全正常（压缩结果与上游自带压缩件逐字节一致）。

真正的失败出现在**解压的第一次小容器读取**：

```
$ xdemill t.xmi ; echo $?
139                      # 128+11 = SIGSEGV
# 输出文件 0 字节；日志无任何报错文本
```

## 根因（一类）

1999 年前后的 Win32/MSVC 代码把指针等同于 32 位整数，直接用字面量做对齐运算：

```c
// xmill/src/MemMan.hpp:131（修复前）
inline void WordAlignMemBlock()
{
   memoryalloc_curptr =
      (unsigned char *)(((unsigned long)memoryalloc_curptr+3)&0xFFFFFFFCL);
}                                                    //   ^^^^^^^^^ 32 位掩码
```

LP64（OHOS aarch64）下 `unsigned long` 与指针同为 64 位，但 `0xFFFFFFFC` 只有 32 位宽 →
**指针被静默截断**。插桩实测：

```
T   alloc size=12 buf=0x5983e553c0 curptr=0x83e553c0 bufsize=48
T   smallcont size=12 dataptr=0x83e553c0
```

`buf` 的低 32 位与 `curptr` 完全相同 → 一眼确诊。截断值随后被当作容器数据缓冲基址逐级传递，
写操作落到未映射地址，`memcpy` 处 SIGSEGV。

**为什么难发现**：

1. 不是类型错误，也不是未定义符号，编译器/链接器一言不发；
2. 崩溃点（`UncompressContainer::UncompressSmallContainer` 的 `memcpy`）与根因
   （`EnumCompress` 解压初始化里提前调用的 `WordAlignMemBlock`）相距多个调用层；
3. 只在真正走到该内存路径时才崩——`conan create` 通过 ≠ 可用。

## 修法

```c
memoryalloc_curptr =
   (unsigned char *)(((unsigned long)memoryalloc_curptr+3)&~(unsigned long)3);
```

掩码必须与指针同宽。同文件注释里还留着一份相同写法的副本（`MemStreamer.hpp`），需一并排查。

## 验证

```
$ xdemill rt.xmi && cmp rt.xml sprot1_2.xml  → IDENTICAL rc=0
$ xdemill up.xmi && cmp up.xml sprot1_2.xml  → IDENTICAL rc=0
$ xmill sprot1_2.xml  → sha256 与上游自带 .xmi 一致（f6e1a0ff…）
```

## 定位手法（本环境）

`gdb` / `lldb` 因 SELinux 拒绝 ptrace（`ptrace: Permission denied`）不可用。
可行替代：把源码复制到独立目录，在要害位置插 `fprintf(stderr, ...)` 打印地址/规模，
用 `buf` 与 `curptr` 的地址差异直接确诊截断；ASan 在本平台未产出报告（不可依赖）。

## 适用面

- Win32/MSVC 时代写的、后直接编到 64 位 Unix/aarch64 的 C/C++ 包；
- 自带内存池 / 对齐分配器（`MemStreamer` / `MemMan` / `BlockAlloc` 之类）的库；
- 预扫特征：源码含 `WIN32`/`.vcproj`/`.sln` 且无 64 位构建历史，同时出现
  `0xFFFFFFF0|F8|FC` 与 `(unsigned long)<ptr>` 的组合。

## 关联

- `notes.md` §3.3（首个运行期错误、插桩证据、修复与复验）
- 同类：`zpaq-7.15-nojit-aarch64-sigill`（同属"能编过但运行不可用"，需运行期往返验收）
