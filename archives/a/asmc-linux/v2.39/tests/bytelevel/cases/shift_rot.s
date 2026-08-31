.text
	.globl main
main:
	shlb $1, %al
	shlw $1, %ax
	shll $1, %eax
	shlq $1, %rax
	shrl $1, %r8d
	shrq $1, %r8
	sarb $1, %r9b
	salw $3, %r10w
	roll $5, %r11d
	rorq $7, %r12
	rclb $2, %r13b
	rcrl $9, %r14d
	shlb %cl, %al
	shlw %cl, %ax
	shll %cl, %eax
	shlq %cl, %rax
	shlb %cl, %r8b
	shlw %cl, %r8w
	shll %cl, %r8d
	shlq %cl, %r8
	shrq %cl, %rax
	sarq %cl, %r9
	rolq %cl, %r10
	shlb %cl, %dl
	ret