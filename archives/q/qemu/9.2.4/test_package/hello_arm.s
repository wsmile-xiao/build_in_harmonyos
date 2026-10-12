@ A tiny ARM (32-bit, little-endian) Linux program written directly in
@ assembly.  It prints a fixed line to stdout and exits with status 0, using
@ only the kernel's own system-call interface — no C library, no libgcc and no
@ dynamic loader are involved.
@
@ Rationale: the host has no AArch32 compatibility layer, so this program can
@ only run through the emulator.  Executing it inside test_package() is
@ therefore a positive proof that the packaged qemu-arm works, not merely that
@ its --version flag responds.
@
@   r7 = 4  (sys_write)   r0 = fd   r1 = buffer   r2 = length
@   r7 = 1  (sys_exit)    r0 = status

        .syntax unified
        .arm
        .global _start

        .section .text
_start:
        mov     r7, #4                  @ __NR_write
        mov     r0, #1                  @ stdout
        ldr     r1, =message
        ldr     r2, =message_len
        svc     #0

        mov     r7, #1                  @ __NR_exit
        mov     r0, #0                  @ exit status
        svc     #0

        .section .rodata
message:
        .ascii  "qemu-arm-ok\n"
        .equ    message_len, . - message
