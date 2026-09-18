/* Second consumer: the way a program translated by f2c runs.
 *
 * f2c output does not define main() - it defines MAIN__() and links the
 * start-up routine, the run-time initialisation and the shutdown flushing
 * out of libf2c. This executable therefore has no main() of its own: the
 * entry point, f_init() and the atexit(f_exit) registration all come from
 * the package's main.c. It fails only if the run time cannot be used that
 * way, or if MAIN__ did not override the weak fallback the package
 * provides.
 */

#include <stdio.h>

#include "f2c.h"

extern integer s_wsle(cilist *a);
extern integer e_wsle(void);
extern integer do_lio(ftnint *type, ftnint *number, char *ptr, ftnlen len);

#define TYLONG 3

static cilist stdout_desc = {0, 6, 0, 0, 0};

int
MAIN__(void)
{
	integer value = 12345;
	ftnint tylong = TYLONG;
	ftnint one = 1;

	if (s_wsle(&stdout_desc) != 0)
		return 1;
	if (do_lio(&tylong, &one, (char *)&value, (ftnlen)sizeof(integer)) != 0)
		return 2;
	if (e_wsle() != 0)
		return 3;
	return 0;
}
