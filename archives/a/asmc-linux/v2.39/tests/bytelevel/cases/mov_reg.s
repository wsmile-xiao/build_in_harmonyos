.text
	.globl main
main:
	movb %bl, %al
	movb %dl, %cl
	movw %bx, %ax
	movw %cx, %dx
	movl %ebx, %eax
	movl %edx, %ecx
	movq %rbx, %rax
	movq %rdx, %rcx
	movq %r9, %r8
	movl %r9d, %r8d
	movw %r9w, %r8w
	movb %r9b, %r8b
	movq %r8, %rax
	movq %rax, %r8
	movl %r8d, %eax
	movl %eax, %r9d
	movw %ax, %r10w
	movb %al, %r11b
	movq %r13, %r12
	ret