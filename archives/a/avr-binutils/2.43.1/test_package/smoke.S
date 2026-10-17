.text
.global _start
.type _start, @function
_start:
    ldi r24, lo8(42)
    ldi r25, hi8(42)
    ret
.size _start, .-_start
