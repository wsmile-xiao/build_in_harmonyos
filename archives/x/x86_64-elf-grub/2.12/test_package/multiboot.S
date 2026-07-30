/* Minimal Multiboot v1 header for grub-file recognition testing. */
.section .multiboot
.align 4
.long 0x1badb002
.long 0x00000000
.long -(0x1badb002 + 0x00000000)

.text
.global _start
_start:
    cli
1:
    hlt
    jmp 1b
