# Simple MIPS assembly test program for spim
# Prints "Hello from SPIM!" and exits with code 0
        .data
hello_msg:  .asciiz "Hello from SPIM!\n"
        .text
        .globl  main
main:
        li      $v0, 4          # syscall: print_string
        la      $a0, hello_msg
        syscall
        li      $v0, 10         # syscall: exit
        syscall
