#include <cassert>
#include <cstdio>
#include <string>
#include <vector>
#include <sys/types.h>

#include "mmap_allocator.h"
#include "mmappable_vector.h"
#include "mmap_file_pool.h"
#include "mmap_access_mode.h"

using namespace mmap_allocator_namespace;

/* Actual consumer-style test: exercise the public library API on OHOS.
 * Verifies that a file-backed mmappable_vector reads back the file
 * content through the mmap allocator, that the file pool reuses the
 * same mapping, and that the plain allocator path works. */
int main(void)
{
	const char *testfile = "testfile";
	FILE *f = fopen(testfile, "w+");
	int i;
	if (!f) {
		fprintf(stderr, "cannot create %s\n", testfile);
		return 1;
	}
	for (i = 0; i < 1024; i++) {
		if (fwrite(&i, 1, sizeof(i), f) != sizeof(i)) {
			fclose(f);
			return 1;
		}
	}
	fclose(f);

	/* 1. file-backed vector must see the file content via mmap */
	mmappable_vector<int, mmap_allocator<int> > vec(
	    mmap_allocator<int>(testfile, READ_ONLY, 0));
	vec.mmap_file(1024);
	assert(vec.size() == 1024);
	for (i = 0; i < 1024; i++) {
		assert(vec[i] == i);
	}

	/* 2. file pool must return the same mapping for the same file */
	int *p1 = (int*)the_pool.mmap_file(testfile, READ_ONLY, 0, 1024, false, false);
	int *p2 = (int*)the_pool.mmap_file(testfile, READ_ONLY, 0, 1024, false, false);
	assert(p1 == p2);
	assert(p1[0] == 0 && p1[1023] == 1023);
	the_pool.munmap_file(testfile, READ_ONLY, 0, 1024);
	the_pool.munmap_file(testfile, READ_ONLY, 0, 1024);

	/* 3. DEFAULT_STL_ALLOCATOR path behaves like a normal allocator */
	mmap_allocator<int> plain;
	int *q = plain.allocate(8);
	q[0] = 42;
	assert(q[0] == 42);
	plain.deallocate(q, 8);

	/* Release the file-backed mapping before removing the file: pool
	 * bookkeeping stats the file when the mapping is released, so the
	 * file must still exist at that point. */
	vec.munmap_file();
	remove(testfile);
	printf("test_mmap_allocator: OK\n");
	return 0;
}