.text
	.globl main
main:
	movabsq $0xffffffff, %rax
	movl $0xffffffff, %eax
	movq $0xffffffffffffffff, %rax
	movabsq $0x7fffffffffffffff, %rax
	movabsq $0x8000000000000000, %rax
	movabsq $0xffffffff00000000, %rax
	movl $0xffffffff, %r8d
	movabsq $0xffffffff, %r8
	movq $0xffffffffffffffff, %r8
	movb $0xff, %al
	movw $0xffff, %ax
	movl $0xffff, %eax
	movq $0xffff, %rax
	movl $0xff, %ebx
	movq $0xff, %rbx
	movl $0xffffffff, %r12d
	movq $0xffffffffffffffff, %r13
	movw $0xffff, %r14w
	movb $0xe1, %r15b
	movb $0, %r15b
	movq $0, %rax
	movq $0, %r9
	movl $0xffffffff, %r10d
	ret