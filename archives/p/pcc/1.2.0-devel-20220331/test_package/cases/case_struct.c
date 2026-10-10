/*
 * HarmonyOS-specific consumer case: struct value passed by value and its
 * fields read back.  Exercises aggregate layout in the emitted code.
 */
struct pcc_pair {
	int a;
	int b;
};

int pcc_total(struct pcc_pair p) { return p.a + p.b; }

int entry(void)
{
	struct pcc_pair p;

	p.a = 19;
	p.b = 23;
	return pcc_total(p);
}
