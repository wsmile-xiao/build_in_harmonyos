package main

import "core:fmt"
import "core:math"

main :: proc() {
	x := math.sqrt(f64(144.0))
	fmt.printf("sqrt(144) = %v\n", x)
	assert(x == 12.0)
}
