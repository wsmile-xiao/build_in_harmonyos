/*
 * HarmonyOS-specific consumer case: loop with an accumulator and a function
 * call in the loop body.  Exercises control flow and register allocation in
 * the amd64 back end of the packaged compiler.
 */
int pcc_sum_to(int n)
{
	int total = 0;
	int i;

	for (i = 1; i <= n; i = i + 1)
		total = total + i;
	return total;
}

int entry(void) { return pcc_sum_to(6); }
