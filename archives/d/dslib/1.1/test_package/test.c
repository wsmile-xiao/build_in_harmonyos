/* test_package consumer test: exercise the dslib stack API end-to-end.
 * Uses the installed headers (include/ds) and links libds (dslib::dslib). */
#include <stdio.h>
#include "stack.h"

/* debug_log() in the library references this symbol; upstream test
 * programs define it at file scope (see upstream test/test_stack_1.c). */
int current_log_level = DEBUG;

int main(void)
{
	int arr[5] = { 10, 20, 30, 40, 50 };
	int i;
	int *val = NULL;
	stack_p stack = get_stack();

	if (stack == NULL)
		return 1;

	for (i = 0; i < 5; i++) {
		if (push(stack, &arr[i]) == FALSE) {
			destroy_stack(stack);
			return 2;
		}
	}

	/* LIFO round-trip: pop in reverse insertion order */
	for (i = 4; i >= 0; i--) {
		val = pop(stack);
		if (val == NULL || *val != arr[i]) {
			destroy_stack(stack);
			return 4;
		}
	}

	destroy_stack(stack);
	printf("dslib stack API test: PASS (5/5 LIFO round-trip)\n");
	return 0;
}
