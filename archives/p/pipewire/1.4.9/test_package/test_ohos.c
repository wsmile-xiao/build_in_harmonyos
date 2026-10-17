/* test_ohos.c — HarmonyOS-specific adaptation validation for pipewire.
 *
 * Validates the two OHOS adaptation points that are not exercised by
 * upstream unit tests:
 *  1. pw_mempool memfd mapping path (OHOS memfd denies fstat(); pipewire
 *     falls back to the known block size for the bounds check).
 *  2. pw_data_loop cancel fallback (OHOS libc has no pthread_cancel();
 *     pipewire delivers SIGUSR1 to the loop thread instead, and the join
 *     must still succeed).
 */
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <pipewire/pipewire.h>
#include <spa/buffer/buffer.h>

static int test_mempool_memfd_map(void)
{
	long page_size = sysconf(_SC_PAGESIZE);
	struct pw_mempool *p;
	struct pw_memblock *b;
	struct pw_memmap *m1;

	p = pw_mempool_new(NULL);
	if (p == NULL)
		return -1;

	b = pw_mempool_alloc(p, PW_MEMBLOCK_FLAG_READWRITE, SPA_DATA_MemFd,
			     2 * page_size);
	if (b == NULL || b->fd < 0) {
		pw_mempool_destroy(p);
		return -1;
	}

	/* Map with a non-page-aligned offset: exercises the bounds check
	 * that falls back to the block size when fstat() is denied. */
	m1 = pw_mempool_map_id(p, b->id, PW_MEMMAP_FLAG_READWRITE,
			       page_size / 2, page_size, NULL);
	if (m1 == NULL || m1->ptr == NULL) {
		pw_mempool_destroy(p);
		return -1;
	}
	/* Round-trip a byte through the mapping. */
	((char *)m1->ptr)[0] = 0x5a;
	if (((char *)m1->ptr)[0] != 0x5a) {
		pw_mempool_destroy(p);
		return -1;
	}

	pw_memmap_free(m1);
	pw_mempool_destroy(p);
	return 0;
}

static int test_data_loop_cancel(void)
{
	struct pw_data_loop *dl;
	struct pw_loop *l;

	/* loop.cancel=true enables the cancellation path that on OHOS is
	 * emulated with SIGUSR1 + pthread_exit instead of pthread_cancel. */
	dl = pw_data_loop_new(&(const struct spa_dict) {
		.n_items = 1,
		.items = (struct spa_dict_item[]) {
			{ PW_KEY_LOOP_CANCEL, "true" },
		},
	});
	if (dl == NULL)
		return -1;
	l = pw_data_loop_get_loop(dl);
	if (l == NULL) {
		pw_data_loop_destroy(dl);
		return -1;
	}
	if (pw_data_loop_start(dl) < 0) {
		pw_data_loop_destroy(dl);
		return -1;
	}
	/* Stop must cancel + join the loop thread. */
	pw_data_loop_stop(dl);
	pw_data_loop_destroy(dl);
	return 0;
}

int main(void)
{
	int failed = 0;

	pw_init(NULL, NULL);

	if (test_mempool_memfd_map() != 0) {
		fprintf(stderr, "FAIL: mempool memfd map\n");
		failed++;
	}
	if (test_data_loop_cancel() != 0) {
		fprintf(stderr, "FAIL: data loop cancel fallback\n");
		failed++;
	}

	pw_deinit();

	if (failed == 0)
		printf("ohos adaptation tests: OK\n");
	return failed == 0 ? 0 : 1;
}
