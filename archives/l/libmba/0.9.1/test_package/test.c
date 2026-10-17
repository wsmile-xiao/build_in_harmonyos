#include <stdio.h>
#include <stdlib.h>
#include "mba/allocator.h"
#include "mba/varray.h"
#include "mba/linkedlist.h"
#include "mba/csv.h"

/* Consumer test: exercise real libmba public APIs (linkedlist, varray,
 * csv) from the installed package to prove headers + lib link correctly. */

static int
_del_data(void *data, void *context)
{
	(void)context;
	free(data);
	return 0;
}

int
main(void)
{
	int rc = 0;

	/* linkedlist (uses the package-provided global stdlib allocator) */
	{
		struct linkedlist l;
		int *a, *b;
		if (linkedlist_init(&l, 10, stdlib_allocator) == -1) {
			fprintf(stderr, "linkedlist_init failed\n");
			return 1;
		}
		a = malloc(sizeof *a);
		b = malloc(sizeof *b);
		if (!a || !b) {
			fprintf(stderr, "malloc failed\n");
			return 1;
		}
		*a = 42;
		*b = 7;
		if (linkedlist_add(&l, a) == -1 || linkedlist_add(&l, b) == -1) {
			fprintf(stderr, "linkedlist_add failed\n");
			return 1;
		}
		if (linkedlist_size(&l) != 2) {
			fprintf(stderr, "linkedlist_size != 2\n");
			rc = 1;
		}
		linkedlist_deinit(&l, _del_data, NULL);
	}

	/* varray: indexed access with varray_get */
	{
		struct varray va;
		unsigned int i;
		if (varray_init(&va, sizeof(int), stdlib_allocator) == -1) {
			fprintf(stderr, "varray_init failed\n");
			return 1;
		}
		for (i = 0; i < 4; i++) {
			int *p = varray_get(&va, i);
			if (!p) {
				fprintf(stderr, "varray_get[%u] NULL\n", i);
				return 1;
			}
			*p = (int)i;
		}
		for (i = 0; i < 4; i++) {
			int *p = varray_get(&va, i);
			if (!p || *p != (int)i) {
				fprintf(stderr, "varray_get[%u] mismatch\n", i);
				rc = 1;
			}
		}
		varray_release(&va, 4);
		varray_deinit(&va);
	}

	/* csv: parse one row from a string */
	{
		unsigned char data[] = "a,b,c";
		unsigned char buf[64];
		unsigned char *row[8];
		int n;

		if ((n = csv_row_parse_str(data, sizeof data - 1, buf, sizeof buf,
				row, 8, ',', 0)) != (int)(sizeof data - 1)) {
			fprintf(stderr, "csv_row_parse_str returned %d (expected consumed chars %lu)\n",
					n, (unsigned long)(sizeof data - 1));
			rc = 1;
		}
	}

	if (rc == 0) {
		printf("test libmba 0.9.1: OK\n");
	}
	return rc;
}