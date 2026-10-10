/*
 * Consumer translation unit for the packaged pcc driver.
 *
 * pcc's default target here is amd64-linux and the package ships no amd64 C
 * library headers, so the case deliberately avoids system headers while still
 * exercising the preprocessor, the parser, code generation and register
 * allocation: two functions, one calling the other inside a loop.
 */
int pcc_add(int a, int b) { return a + b; }

int pcc_sum(int n)
{
	int total = 0;
	int i;

	for (i = 0; i < n; i++)
		total = pcc_add(total, i);
	return total;
}
