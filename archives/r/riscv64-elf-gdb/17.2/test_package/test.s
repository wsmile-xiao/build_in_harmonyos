	.text
	.globl _start
_start:
	li a0, 42        # exit code 42
	li a7, 93        # sys_exit
	ecall
