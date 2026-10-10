/*
 * HarmonyOS-specific consumer case: pointer parameter plus a global array.
 * Exercises address computation and array indexing in the emitted code.
 */
int pcc_sum(int *p, int n)
{
	int r = 0;
	int i;

	for (i = 0; i < n; i = i + 1)
		r = r + p[i];
	return r;
}

int pcc_xs[4] = { 1, 2, 3, 4 };

int entry(void) { return pcc_sum(pcc_xs, 4); }
