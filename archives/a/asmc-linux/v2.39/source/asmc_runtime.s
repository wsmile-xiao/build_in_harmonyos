// AArch64 host runtime for Asmc (native port)
// Target: aarch64-unknown-linux-ohos
// Toolchain: OHOS clang 15.0.4
//
// Port of memalloc.asm and ltype.asm functions
// In dependency order: called by asmc.asm main()

.section .bss
    .align 8
    pBase:  .xword 0        // start list of 512 kB blocks
    pCurr:  .xword 0        // points into current block
    currfree: .word 0       // free memory left in current block
    .align 4

.section .text

// MemInit -- initialize heap manager
// Original: memalloc.asm:MemInit
// x86: mov pBase,0; mov currfree,0; ret
.globl MemInit
.type MemInit, @function
MemInit:
    adrp    x0, pBase
    str     xzr, [x0, #:lo12:pBase]
    adrp    x0, pCurr
    str     xzr, [x0, #:lo12:pCurr]
    adrp    x0, currfree
    str     wzr, [x0, #:lo12:currfree]
    ret

// MemAlloc(len) -- allocate zeroed memory
// Original: memalloc.asm:MemAlloc (fastcall: rcx=len)
// AArch64: x0=len, returns x0=ptr
// Uses malloc+memset from musl libc
// NOTE: uses stack for len (x19 is callee-saved; must not clobber it)
.globl MemAlloc
.type MemAlloc, @function
MemAlloc:
    stp     x29, x30, [sp, #-16]!
    str     x0, [sp, #-16]!    // save len on stack (16-byte frame)
    mov     x29, sp
    bl      malloc              // x0 = malloc(len)
    cbz     x0, 1f              // if NULL, error
    mov     x1, xzr             // memset value = 0
    ldr     x2, [sp]            // x2 = len
    bl      memset
    add     sp, sp, #16         // pop len slot
    ldp     x29, x30, [sp], #16
    ret
1:  // malloc failed
    add     sp, sp, #16
    ldp     x29, x30, [sp], #16
    ret

// MemFree(p) -- free memory
// Original: memalloc.asm:MemFree (fastcall: rcx=p)
// AArch64: x0=ptr
.globl MemFree
.type MemFree, @function
MemFree:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      free
    ldp     x29, x30, [sp], #16
    ret

// MemFini -- free all heap blocks
// Original: walks pBase list, frees each block
.globl MemFini
.type MemFini, @function
MemFini:
    stp     x29, x30, [sp, #-16]!
    stp     x19, x20, [sp, #-16]!
    mov     x29, sp
    adrp    x0, pBase
    ldr     x19, [x0, #:lo12:pBase]  // x19 = pBase
    cbz     x19, 2f
1:  // walk list
    ldr     x20, [x19]      // x20 = next ptr (first field)
    mov     x0, x19
    bl      MemFree
    mov     x19, x20
    cbnz    x19, 1b
2:  // clear pBase
    adrp    x0, pBase
    str     xzr, [x0, #:lo12:pBase]
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

// LclAlloc(size) -- allocate from local heap (fast, not freed individually)
// Original: uses pCurr, currfree, allocates new 512KB block when needed
// Constants defined directly (GAS doesn't support C preprocessor)
// GRANULARITY  = 0x10
// HEAP_GROWSIZE = 0x20000  (128KB for UNIX)
.globl LclAlloc
.type LclAlloc, @function
LclAlloc:
    stp     x29, x30, [sp, #-16]!
    stp     x19, x20, [sp, #-16]!
    mov     x29, sp
    mov     x19, x0         // x19 = size
    // Align to 16 (GRANULARITY)
    add     x0, x0, #0xf
    bic     x0, x0, #0xf
    mov     x20, x0         // x20 = aligned size

    adrp    x1, pCurr
    ldr     x2, [x1, #:lo12:pCurr]  // x2 = pCurr
    adrp    x3, currfree
    ldr     w4, [x3, #:lo12:currfree] // w4 = currfree
    cmp     x20, x4
    b.hi    1f              // if size > currfree, need new block

    // allocate from current block
    sub     w4, w4, w20     // currfree -= aligned_size
    str     w4, [x3, #:lo12:currfree]
    mov     x0, x2          // return pCurr
    add     x2, x2, x20     // pCurr += aligned_size
    str     x2, [x1, #:lo12:pCurr]
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

1:  // need new block
    mov     w4, #0x1fff0    // HEAP_GROWSIZE - GRANULARITY = 0x20000 - 0x10
    cmp     x20, x4
    b.ls    2f
    mov     x4, x20         // if size > growsize, use size + GRANULARITY
2:  add     x4, x4, #0x10  // add GRANULARITY
    mov     x0, x4          // x0 = alloc size
    bl      MemAlloc
    cbz     x0, 3f          // if NULL, error

    // link new block into pBase list
    adrp    x1, pBase
    ldr     x2, [x1, #:lo12:pBase]
    str     x2, [x0]        // [block] = old pBase
    str     x0, [x1, #:lo12:pBase] // pBase = new block

    // set up currfree and pCurr
    add     x2, x0, #0x10  // skip the link field (GRANULARITY)
    str     x2, [x1, #:lo12:pCurr] // pCurr = block + GRANULARITY
    // currfree = alloc_size - aligned_size - GRANULARITY
    mov     x3, x4
    sub     x3, x3, x20
    sub     x3, x3, #0x10
    adrp    x1, currfree
    str     w3, [x1, #:lo12:currfree]

    // return the allocation
    mov     x0, x2          // return pCurr (which is block + GRANULARITY)
    add     x2, x2, x20     // pCurr += aligned_size
    adrp    x1, pCurr
    str     x2, [x1, #:lo12:pCurr]
    // update currfree
    sub     w3, w3, w20
    str     w3, [x1, #:lo12:currfree]

    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

3:  // out of memory
    // asmerr(1018)
    mov     x0, xzr
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

// LclDup(string) -- duplicate string via LclAlloc
// Original: fastcall rcx=string, returns rax=duplicate
.globl LclDup
.type LclDup, @function
LclDup:
    stp     x29, x30, [sp, #-16]!
    stp     x19, x20, [sp, #-16]!
    mov     x29, sp
    mov     x19, x0         // x19 = string
    bl      tstrlen         // x0 = strlen
    add     x0, x0, #1     // +1 for null
    bl      LclAlloc        // x0 = LclAlloc(len+1)
    mov     x20, x0         // save dest
    mov     x1, x19         // src = original string
    bl      tstrcpy         // copy
    mov     x0, x20
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

// MemDup(string) -- duplicate string via MemAlloc
.globl MemDup
.type MemDup, @function
MemDup:
    stp     x29, x30, [sp, #-16]!
    stp     x19, x20, [sp, #-16]!
    mov     x29, sp
    mov     x19, x0         // x19 = string
    bl      tstrlen         // x0 = strlen
    add     x0, x0, #1     // +1 for null
    bl      MemAlloc        // x0 = MemAlloc(len+1)
    mov     x20, x0         // save dest
    mov     x1, x19         // src
    bl      tstrcpy
    mov     x0, x20
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

// === String primitives (port of ltype.asm) ===

// tstrlen(s1) -- return length of string
// x86-64: rcx=s1, returns rax=len
// AArch64: x0=s1, returns x0=len
.globl tstrlen
.type tstrlen, @function
tstrlen:
    mov     x1, x0          // save start
1:  ldrb    w2, [x0], #1
    cbnz    w2, 1b
    sub     x0, x0, x1
    sub     x0, x0, #1
    ret

// tstrchr(string, char) -- find first occurrence of char in string
// x86-64: rcx=string, dl=char, returns rax=ptr or 0
// AArch64: x0=string, w1=char, returns x0=ptr or 0
.globl tstrchr
.type tstrchr, @function
tstrchr:
1:  ldrb    w2, [x0]
    cbz     w2, 2f          // end of string
    cmp     w2, w1
    b.eq    3f              // found
    add     x0, x0, #1
    b       1b
2:  mov     x0, xzr         // not found
3:  ret

// tstrrchr(string, char) -- find last occurrence of char in string
// x86-64: rcx=string, dl=char, returns rax=ptr or 0
.globl tstrrchr
.type tstrrchr, @function
tstrrchr:
    mov     x3, xzr         // result = NULL
1:  ldrb    w2, [x0]
    cbz     w2, 2f
    cmp     w2, w1
    csel    x3, x0, x3, eq  // if match, update result
    add     x0, x0, #1
    b       1b
2:  mov     x0, x3
    ret

// tstrcpy(dst, src) -- copy string
// x86-64: rcx=dst, rdx=src, returns rax=dst
// AArch64: x0=dst, x1=src, returns x0=dst
.globl tstrcpy
.type tstrcpy, @function
tstrcpy:
    mov     x2, x0          // save dst
1:  ldrb    w3, [x1], #1
    strb    w3, [x0], #1
    cbnz    w3, 1b
    mov     x0, x2          // return dst
    ret

// tstrcat(dst, src) -- concatenate strings
// x86-64: rcx=dst, rdx=src, returns rax=dst
// AArch64: x0=dst, x1=src, returns x0=dst
.globl tstrcat
.type tstrcat, @function
tstrcat:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    mov     x2, x0          // save dst
    // find end of dst
1:  ldrb    w3, [x0]
    cbz     w3, 2f
    add     x0, x0, #1
    b       1b
2:  // copy src to end of dst
3:  ldrb    w3, [x1], #1
    strb    w3, [x0], #1
    cbnz    w3, 3b
    mov     x0, x2          // return dst
    ldp     x29, x30, [sp], #16
    ret

// tstrncpy(dst, src, len) -- copy at most len chars
// x86-64: rcx=dst, rdx=src, r8d=len, returns rax=dst
// AArch64: x0=dst, x1=src, x2=len, returns x0=dst
.globl tstrncpy
.type tstrncpy, @function
tstrncpy:
    mov     x3, x0          // save dst
    cbz     x2, 2f
1:  subs    x2, x2, #1
    b.lo    2f
    ldrb    w4, [x1], #1
    strb    w4, [x0], #1
    cbnz    w4, 1b
    // pad remaining with zeros
    cbz     x2, 2f
    strb    wzr, [x0], #1
    subs    x2, x2, #1
    b.ne    -4
2:  mov     x0, x3
    ret

// tstrcmp(s1, s2) -- compare strings
// x86-64: rcx=s1, rdx=s2, returns eax=0 eq, 1 lt, -1 gt
// AArch64: x0=s1, x1=s2, returns w0=0 eq, 1 s1>s2, -1 s1<s2
.globl tstrcmp
.type tstrcmp, @function
tstrcmp:
1:  ldrb    w2, [x0], #1
    ldrb    w3, [x1], #1
    cmp     w2, w3
    b.ne    2f
    cbnz    w2, 1b         // continue if not end of both
    mov     w0, wzr         // equal
    ret
2:  // w2 != w3
    sub     w0, w2, w3
    // Normalize to -1, 0, 1
    cmp     w0, #0
    cset    w0, gt
    cneg    w0, w0, le
    ret

// tstricmp(s1, s2) -- case-insensitive compare
.globl tstricmp
.type tstricmp, @function
tstricmp:
1:  ldrb    w2, [x0], #1
    ldrb    w3, [x1], #1
    // lowercase both
    orr     w4, w2, #0x20
    orr     w5, w3, #0x20
    cmp     w4, w5
    b.ne    2f
    cbnz    w2, 1b
    mov     w0, wzr
    ret
2:  sub     w0, w4, w5
    cmp     w0, #0
    cset    w0, gt
    cneg    w0, w0, le
    ret

// tstrstr(haystack, needle) -- find substring
// x86-64: rcx=haystack, rdx=needle, returns rax=ptr or 0
// AArch64: x0=haystack, x1=needle, returns x0=ptr or 0
.globl tstrstr
.type tstrstr, @function
tstrstr:
    stp     x29, x30, [sp, #-16]!
    stp     x19, x20, [sp, #-16]!
    stp     x21, x22, [sp, #-16]!
    mov     x29, sp
    mov     x19, x0         // haystack
    mov     x20, x1         // needle
    bl      tstrlen
    mov     x21, x0         // x21 = needle_len
    cbz     x21, 4f         // empty needle -> found at start
    mov     x0, x19
    bl      tstrlen
    cbz     x0, 3f          // empty haystack -> not found
    mov     x22, x0         // x22 = haystack_len
    sub     x22, x22, x21   // haystack_len - needle_len
    b.lo    3f              // haystack shorter than needle

1:  // loop over haystack positions
    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    bl      tmemicmp        // compare first needle_len chars
    cbnz    w0, 2f          // if match found
    mov     x0, x19
    b       5f
2:  add     x19, x19, #1
    subs    x22, x22, #1
    b.ge    1b
3:  mov     x0, xzr         // not found
    b       5f
4:  mov     x0, x19         // empty needle -> haystack itself
5:  ldp     x21, x22, [sp], #16
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret

// tmemicmp(s1, s2, len) -- case-insensitive compare with length
// x86-64: rcx=s1, rdx=s2, r8d=len, returns eax=0 eq
// AArch64: x0=s1, x1=s2, x2=len, returns w0=0 eq
.globl tmemicmp
.type tmemicmp, @function
tmemicmp:
    cbz     x2, 2f
1:  ldrb    w3, [x0], #1
    ldrb    w4, [x1], #1
    orr     w3, w3, #0x20
    orr     w4, w4, #0x20
    cmp     w3, w4
    b.ne    3f
    subs    x2, x2, #1
    b.ne    1b
2:  mov     w0, wzr         // equal
    ret
3:  // w3 != w4
    sub     w0, w3, w4
    cmp     w0, #0
    cset    w0, gt
    cneg    w0, w0, le
    ret

// === Logo data (port of logo.asm) ===

.section .rodata
    .align 8
cp_logo:
    .asciz "Asmc Macro Assembler (AArch64) Version %d.%02d.%02d\n"
cp_copyright:
    .asciz "Copyright (C) The Asmc Contributors. All Rights Reserved.\n"
cp_usage:
    .asciz "Usage: asmc [ options ] filelist [ -link linkoptions ]\n"
cp_options:
    .asciz "asmc [ options ] filelist [ -link link_options ]\n"

.section .bss
    .align 8
    .globl banner_printed
    banner_printed: .byte 0

.section .text

// tprintf -- printf wrapper (using musl libc printf)
// fastcall: rcx=format, rdx, r8, r9 = args
// AArch64: x0=format, x1, x2, x3 = args
.globl tprintf
.type tprintf, @function
tprintf:
    stp     x29, x30, [sp, #-16]!
    bl      printf
    ldp     x29, x30, [sp], #16
    ret

// write_logo -- print logo banner once
// Original: logo.asm:write_logo
.globl write_logo
.type write_logo, @function
write_logo:
    stp     x29, x30, [sp, #-16]!
    adrp    x0, banner_printed
    ldrb    w1, [x0, #:lo12:banner_printed]
    cbnz    w1, 1f          // already printed
    mov     w1, #1
    strb    w1, [x0, #:lo12:banner_printed] // banner_printed = 1
    adrp    x0, cp_logo
    add     x0, x0, #:lo12:cp_logo
    mov     x1, #2          // _ASMC_MAJOR
    mov     x2, #39         // _ASMC_MINOR
    mov     x3, #0          // _ASMC_BUILD
    bl      tprintf
    adrp    x0, cp_copyright
    add     x0, x0, #:lo12:cp_copyright
    bl      tprintf
1:  ldp     x29, x30, [sp], #16
    ret

// write_usage -- print usage and exit
.globl write_usage
.type write_usage, @function
write_usage:
    stp     x29, x30, [sp, #-16]!
    bl      write_logo
    adrp    x0, cp_usage
    add     x0, x0, #:lo12:cp_usage
    bl      tprintf
    ldp     x29, x30, [sp], #16
    ret

// write_options -- print all options
.globl write_options
.type write_options, @function
write_options:
    stp     x29, x30, [sp, #-16]!
    bl      write_logo
    adrp    x0, cp_options
    add     x0, x0, #:lo12:cp_options
    bl      tprintf
    ldp     x29, x30, [sp], #16
    ret

// my_environ -- saved environ pointer (port of asmc.asm:my_environ)
// Set by main() before tgetenv is used.
.section .bss
    .align 8
    .globl my_environ
    my_environ: .xword 0

.section .text

// tgetenv(enval) -- get environment variable
// Original: asmc.asm:tgetenv (fastcall rcx=enval)
// AArch64: x0=enval, returns x0=value ptr or 0
.globl tgetenv
.type tgetenv, @function
tgetenv:
    stp     x29, x30, [sp, #-16]!
    stp     x19, x20, [sp, #-16]!
    stp     x21, x22, [sp, #-16]!
    mov     x29, sp
    mov     x19, x0         // x19 = enval
    bl      tstrlen
    cbz     x0, 3f          // empty name -> return 0
    mov     x20, x0         // x20 = name length
    adrp    x1, my_environ
    ldr     x21, [x1, #:lo12:my_environ] // x21 = environ
    ldr     x22, [x21]      // x22 = current env entry
    cbz     x22, 3f         // empty environ
    add     x21, x21, #8
1:  // loop over environ entries
    mov     x0, x22
    mov     x1, x19
    mov     x2, x20
    bl      tmemicmp
    cbnz    w0, 2f
    // matched prefix, check '='
    add     x0, x22, x20
    ldrb    w1, [x0]
    cmp     w1, #'='
    b.ne    2f
    // found: return &entry[name_len+1]
    add     x0, x22, x20
    add     x0, x0, #1
    b       4f
2:  ldr     x22, [x21]
    add     x21, x21, #8
    cbnz    x22, 1b
3:  mov     x0, xzr         // not found
4:  ldp     x21, x22, [sp], #16
    ldp     x19, x20, [sp], #16
    ldp     x29, x30, [sp], #16
    ret