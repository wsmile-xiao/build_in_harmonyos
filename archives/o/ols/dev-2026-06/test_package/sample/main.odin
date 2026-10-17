package main

import "core:fmt"

add :: proc(a, b: int) -> int {
	return a + b
}

main :: proc() {
	fmt.println(add(1, 2))
}
