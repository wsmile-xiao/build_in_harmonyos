// AArch64 port of Asmc entry point
// Original: asmc.asm (x86-64 Asmc assembly)
// This file is the AArch64 (ARM64) translation for the OHOS platform

.section .text
.globl setoname
.type setoname, @function
setoname:
    // x86-64 original: setoname proc __ccall private uses rsi rdi rbx file:string_t, newo:string_t
    // AArch64: parameters in x0, x1 (ARM64 ABI)
    // x0 = file (input filename)
    // x1 = newo (output filename)
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    
    // Store callee-saved registers
    stp x19, x20, [sp, #-16]!
    stp x21, x22, [sp, #-16]!
    
    // Copy parameters to callee-saved registers
    mov x19, x0  // file
    mov x20, x1  // newo
    
    // setoname: substitute '*' in template with file's basename (no extension)
    // x2 = template (name with '*'), or NULL
    // If NULL or no '*': just copy file to newo and return
    // If '*': extract file basename (strip path+ext), replace '*' in template with it
    mov x19, x0         // x19 = file
    mov x20, x1         // x20 = newo
    mov x21, x2         // x21 = template (or NULL)
    mov x22, x21        // x22 = return value (original template)

    cbz x21, 4f
    // Check if template contains '*'
    mov x0, x21
    mov x1, #'*'
    bl tstrchr
    cbz x0, 4f          // no '*' -> copy file to newo

    // File basename: copy file to stack, truncate at last '.'
    sub sp, sp, #1024
    mov x0, x19
    mov x1, sp
    bl tstrcpy
    mov x0, sp
    mov x1, #'.'
    bl tstrrchr
    cbz x0, 2f
    strb wzr, [x0]      // truncate at '.'

2:  // Walk template: copy chars, '*' -> copy basename
    add x23, sp, #0     // x23 = basename
    mov x24, x20        // x24 = output

3:  ldrb w0, [x21]
    cbz w0, 5f
    cmp w0, #'*'
    b.eq 6f
    strb w0, [x24], #1
    add x21, x21, #1
    b 3b

6:  // Copy basename
    mov x0, x23
7:  ldrb w1, [x0], #1
    cbz w1, 8f
    strb w1, [x24], #1
    b 7b
8:  add x21, x21, #1
    b 3b

5:  strb wzr, [x24]
    add sp, sp, #1024
    mov x0, x22
    b 9f

4:  // No template or no '*': copy file to newo
    mov x0, x19
    mov x1, x20
    bl tstrcpy
    mov x0, x22

9:  ldp x23, x24, [sp], #16
    ldp x21, x22, [sp], #16
    ldp x19, x20, [sp], #16
    ldp x29, x30, [sp], #16
    ldp x29, x30, [sp], #16
    ret

// AArch64 port of cmpwarg
// Original: cmpwarg proc fastcall uses rsi rdi wild:string_t, path:string_t
// AArch64: parameters in x0, x1 (ARM64 ABI)
// x0 = wild (wildcard pattern), x1 = path (path to compare)
// Returns: 1 if match, 0 if no match
// Semantics: '*' matches any sequence, '?' matches any single char,
// comparison is case-insensitive (or 0x20 fold)
.globl cmpwarg
.type cmpwarg, @function
cmpwarg:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    stp x19, x20, [sp, #-16]!   // x19=wild, x20=path
    stp x21, x22, [sp, #-16]!   // x21=star ptr, x22=star match pos

    mov x19, x0
    mov x20, x1
    mov x21, xzr                // star = NULL
    mov x22, xzr                // star_match = NULL

1:  // while (*path != 0)
    ldrb w1, [x20]
    cbz w1, 5f                  // path end
    ldrb w0, [x19]              // c = *wild
    cmp w0, #'*'
    b.eq 3f                     // star handling
    cmp w0, #'?'
    b.eq 4f                     // '?' matches any char
    orr w2, w0, #0x20           // case-insensitive compare
    orr w3, w1, #0x20
    cmp w2, w3
    b.eq 4f                     // advance on match
    cbnz x21, 6f                // mismatch: backtrack if star set
    b 8f                        // no star: no match

3:  // star: star=wild; wild++; star_match=path
    mov x21, x19
    add x19, x19, #1
    mov x22, x20
    b 1b

4:  // advance: wild++; path++
    add x19, x19, #1
    add x20, x20, #1
    b 1b

6:  // backtrack: star_match++; path=star_match; wild=star+1
    add x22, x22, #1
    mov x20, x22
    add x19, x21, #1
    b 1b

5:  // *path == 0: skip trailing '*'
    ldrb w0, [x19]
    cmp w0, #'*'
    b.ne 7f
    add x19, x19, #1
    b 5b

7:  // match if wild exhausted
    ldrb w0, [x19]
    cbz w0, 9f

8:  mov x0, xzr                 // no match
    b 10f
9:  mov x0, #1                  // match
10: ldp x21, x22, [sp], #16
    ldp x19, x20, [sp], #16
    ldp x29, x30, [sp], #16
    ret

// AArch64 port of ReadFiles
// Implementation moved to asmc_io.c (musl libc dirent), see there.
// Kept as weak alias reference so entry symbols stay consistent.

// AArch64 port of main
// Original: main proc argc:int_t, argv:array_t, environ:array_t
// AArch64: parameters in x0, x1, x2 (ARM64 ABI)
// x0 = argc, x1 = argv, x2 = environ
.globl main
.type main, @function
main:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    stp x19, x20, [sp, #-16]!
    stp x21, x22, [sp, #-16]!
    stp x23, x24, [sp, #-16]!
    stp x25, x26, [sp, #-16]!
    stp x27, x28, [sp, #-16]!
    
    mov x19, x0  // argc
    mov x20, x1  // argv
    mov x21, x2  // environ

    // MemInit() -- initialize heap
    bl MemInit

    // Save environ for tgetenv
    adrp x0, my_environ
    str x21, [x0, #:lo12:my_environ]

    // Print logo
    bl write_logo

    // process_cmdline(argv, environ) -- init_options + ParseCmdline + AssembleModule
    mov x0, x20         // argv
    mov x1, x21         // environ
    bl process_cmdline

    // Return 0 (success)
    mov x0, xzr
    
    ldp x27, x28, [sp], #16
    ldp x25, x26, [sp], #16
    ldp x23, x24, [sp], #16
    ldp x21, x22, [sp], #16
    ldp x19, x20, [sp], #16
    ldp x29, x30, [sp], #16
    ret

.section .rodata
    .align 8
asmc_str:
    .asciz "ASMC"
asmc_found:
    .asciz "ASMC=%s\n"
asmc_not_found:
    .asciz "ASMC not set; using default\n"
memalloc_str:
    .asciz "MemAlloc(64) = %p\n"
strlen_str:
    .asciz "tstrlen test: %d\n"
lclalloc_str:
    .asciz "LclAlloc(32) = %p\n"
cmpwarg_match:
    .asciz "cmpwarg(*.asm, test.asm) = %d  (expect 1)\n"
cmpwarg_nomatch:
    .asciz "cmpwarg(*.asm, test.txt) = %d  (expect 0)\n"
cmpwarg_any:
    .asciz "cmpwarg(*, anyname.txt) = %d  (expect 1)\n"
wild_asm:
    .asciz "*.asm"
wild_star:
    .asciz "*"
test_asm:
    .asciz "test.asm"
test_txt:
    .asciz "test.txt"
test_any:
    .asciz "anyname.txt"
helloworld:
    .asciz "Hello from Asmc AArch64!\n"
.section .text
