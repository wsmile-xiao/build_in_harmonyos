fn fib(n int) int {
	if n < 2 {
		return n
	}
	return fib(n - 1) + fib(n - 2)
}

fn main() {
	mut values := []int{}
	for i in 0 .. 7 {
		values << fib(i)
	}
	assert values.len == 7
	assert values[0] == 0
	assert values[1] == 1
	assert values[3] == 2
	assert values[6] == 8
	println('v-test-package-ok')
}
