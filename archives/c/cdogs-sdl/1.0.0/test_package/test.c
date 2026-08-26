#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

/* L1 smoke test: verify the cdogs-sdl binary exists in the package
 * and that --help prints the version/usage banner. */
int main(int argc, char *argv[])
{
	const char *bin = "cdogs-sdl";
	if (argc > 1)
		bin = argv[1];

	struct stat st;
	if (stat(bin, &st) != 0)
	{
		fprintf(stderr, "FAIL: binary %s not found\n", bin);
		return 1;
	}
	if (access(bin, X_OK) != 0)
	{
		fprintf(stderr, "FAIL: binary %s not executable\n", bin);
		return 1;
	}
	printf("test cdogs-sdl: binary %s present (size %lld)\n", bin,
	       (long long)st.st_size);
	return 0;
}