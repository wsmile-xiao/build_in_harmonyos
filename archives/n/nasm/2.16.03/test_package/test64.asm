bits 64
global nasm_test_add

section .text
nasm_test_add:
    lea rax, [rdi + rsi]
    ret
