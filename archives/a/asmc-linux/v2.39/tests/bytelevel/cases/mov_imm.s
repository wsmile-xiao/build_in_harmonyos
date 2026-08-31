.text
	.globl main
main:
	movb $1, %al
	movb $0xff, %cl
	movw $0x1234, %ax
	movw $0xffff, %dx
	movl $0x12345678, %eax
	movl $0x7fffffff, %ebx
	movabsq $0x123456789abcdef0, %rax
	movabsq $0xffffffff, %rcx
	movq $1, %r8
	movl $2, %r8d
	movw $3, %r9w
	movb $4, %r10b
	movq $0xffffffffffffffff, %r11
	movl $0xffffffff, %r12d
	ret