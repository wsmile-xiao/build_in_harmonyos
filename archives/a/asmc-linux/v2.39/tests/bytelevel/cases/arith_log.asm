.code
main proc
    add al, 1
    add ax, 1
    add eax, 1
    add rax, 1
    add r8d, 1
    add r8, 1
    sub al, 2
    sub eax, 2
    sub rax, 2
    sub r9b, 2
    sub r9, 2
    cmp al, 3
    cmp eax, 3
    cmp rax, 3
    cmp r10d, 3
    and eax, 4
    and rax, 4
    and r11b, 4
    or eax, 5
    or rax, 5
    or r12w, 5
    adc eax, 6
    adc rax, 6
    adc r13d, 6
    sbb eax, 7
    sbb rax, 7
    sbb r14b, 7
    xor eax, 8
    xor rax, 8
    xor r15, 8
    add al, bl
    add ax, bx
    add eax, ebx
    add rax, rbx
    add r8d, r9d
    add r8, r9
    sub al, bl
    sub r8d, r9d
    cmp rax, rbx
    xor r8, r9
    xor r8d, r9d
    and rax, r8
    or r8, rax
    adc al, bl
    sbb eax, ebx
    ret
main endp
end