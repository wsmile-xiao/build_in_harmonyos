/* Consumer test for ck/0.7.2: exercises the real libck ck_hs API
 * (init/insert/count/get/duplicate-reject/remove/destroy) with
 * behavioural assertions. */
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ck_hs.h>

static char keybuf[8][16];
static const char *keys[8];

static unsigned long
hs_hash(const void *object, unsigned long seed)
{
	const char *c = object;
	unsigned long h = seed;

	while (*c != 0)
		h = (h << 5) - h + (unsigned char)*c++;
	return h;
}

static bool
hs_compare(const void *previous, const void *compare)
{
	return strcmp(previous, compare) == 0;
}

static void *
hs_malloc(size_t size)
{
	return malloc(size);
}

static void
hs_free(void *p, size_t size, bool defer)
{
	(void)size;
	(void)defer;
	free(p);
	return;
}

static struct ck_malloc allocator = {
	.malloc = hs_malloc,
	.free = hs_free
};

int
main(void)
{
	struct ck_hs hs;
	unsigned int i;

	for (i = 0; i < 8; i++) {
		snprintf(keybuf[i], sizeof(keybuf[i]), "key-%u", (unsigned)i);
		keys[i] = keybuf[i];
	}

	if (ck_hs_init(&hs, CK_HS_MODE_SPMC | CK_HS_MODE_OBJECT,
	    hs_hash, hs_compare, &allocator, 16, 0) == false) {
		fprintf(stderr, "FAIL: ck_hs_init\n");
		return 1;
	}

	for (i = 0; i < 8; i++) {
		if (ck_hs_put(&hs, hs_hash(keys[i], 0), keys[i]) == false) {
			fprintf(stderr, "FAIL: ck_hs_put(%s)\n", keys[i]);
			return 1;
		}
	}

	if (ck_hs_count(&hs) != 8) {
		fprintf(stderr, "FAIL: ck_hs_count=%lu != 8\n",
		    (unsigned long)ck_hs_count(&hs));
		return 1;
	}

	for (i = 0; i < 8; i++) {
		const void *found = ck_hs_get(&hs, hs_hash(keys[i], 0), keys[i]);

		if (found == NULL || strcmp(found, keys[i]) != 0) {
			fprintf(stderr, "FAIL: ck_hs_get(%s)\n", keys[i]);
			return 1;
		}
	}

	/* Duplicate insert must be rejected. */
	if (ck_hs_put(&hs, hs_hash(keys[0], 0), keys[0]) != false) {
		fprintf(stderr, "FAIL: duplicate ck_hs_put accepted\n");
		return 1;
	}

	/* Remove an existing key; it must be gone afterwards. */
	if (ck_hs_remove(&hs, hs_hash(keys[3], 0), keys[3]) == NULL) {
		fprintf(stderr, "FAIL: ck_hs_remove(key-3)\n");
		return 1;
	}
	if (ck_hs_count(&hs) != 7) {
		fprintf(stderr, "FAIL: ck_hs_count after remove=%lu != 7\n",
		    (unsigned long)ck_hs_count(&hs));
		return 1;
	}
	if (ck_hs_get(&hs, hs_hash(keys[3], 0), keys[3]) != NULL) {
		fprintf(stderr, "FAIL: removed key still present\n");
		return 1;
	}

	ck_hs_destroy(&hs);

	printf("ck_hs consumer test: OK (init/insert/count/get/dup/remove/destroy)\n");
	return 0;
}
