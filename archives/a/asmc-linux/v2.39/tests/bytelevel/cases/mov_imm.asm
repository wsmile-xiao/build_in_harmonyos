.code
main proc
    mov al, 1
    mov cl, 0x0FF
    mov ax, 0x1234
    mov dx, 0xFFFF
    mov eax, 0x12345678
    mov ebx, 0x7FFFFFFF
    mov rax, 0x123456789ABCDEF0
    mov rcx, 0xFFFFFFFF
    mov r8, 1
    mov r8d, 2
    mov r9w, 3
    mov r10b, 4
    mov r11, 0xFFFFFFFFFFFFFFFF
    mov r12d, 0xFFFFFFFF
    ret
main endp
end