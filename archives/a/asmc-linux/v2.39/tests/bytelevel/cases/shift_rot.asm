.code
main proc
    shl al, 1
    shl ax, 1
    shl eax, 1
    shl rax, 1
    shr r8d, 1
    shr r8, 1
    sar r9b, 1
    sal r10w, 3
    rol r11d, 5
    ror r12, 7
    rcl r13b, 2
    rcr r14d, 9
    shl al, cl
    shl ax, cl
    shl eax, cl
    shl rax, cl
    shl r8b, cl
    shl r8w, cl
    shl r8d, cl
    shl r8, cl
    shr rax, cl
    sar r9, cl
    rol r10, cl
    shl dl, cl
    ret
main endp
end