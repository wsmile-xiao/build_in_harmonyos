/* Consumer test for librecast/0.8.0 (R34: must actually exercise the package).
 *
 * Calls real public API rather than merely linking: context lifecycle, hashing
 * (crypto.h, which pulls in the bundled BLAKE3), and the MDEX channel index.
 * lc_ctx_new()/lc_ctx_free() are also the entry points for the OHOS thread
 * shutdown adaptation (E127), so this exercises an adapted code path.
 */
#include <stdio.h>   /* net.h declares FILE * without including stdio.h */
#include <string.h>

#include <librecast.h>
#include <librecast/crypto.h>
#include <librecast/mdex.h>

#include <arpa/inet.h>
#include <errno.h>

static int failures;

#define CHECK(cond, msg)                                                       \
	do {                                                                   \
		if (cond) {                                                    \
			printf("[ OK ] %s\n", (msg));                          \
		}                                                              \
		else {                                                         \
			printf("[FAIL] %s\n", (msg));                          \
			failures++;                                            \
		}                                                              \
	} while (0)

int main(void)
{
	setvbuf(stdout, NULL, _IONBF, 0);

	/* ── context lifecycle: starts the MLD listener and joins its threads
	 *    on teardown (the cooperative-shutdown adaptation) ── */
	lc_ctx_t *lctx = lc_ctx_new();
	CHECK(lctx != NULL, "lc_ctx_new() returns a context");
	if (!lctx) {
		printf("cannot continue without a context\n");
		return 1;
	}

	/* ── one-shot hashing ── */
	unsigned char hash1[HASHSIZE];
	unsigned char hash2[HASHSIZE];
	CHECK(hash_generic(hash1, HASHSIZE, (unsigned char *)"librecast", 9) == 0,
	      "hash_generic() computes a digest");
	CHECK(hash_generic(hash2, HASHSIZE, (unsigned char *)"librecast!", 10) == 0,
	      "hash_generic() computes a second digest");
	CHECK(memcmp(hash1, hash2, HASHSIZE) != 0,
	      "digests differ for different input");

	/* ── multi-part hashing, and it must agree with the one-shot form ── */
	hash_state state;
	unsigned char hash3[HASHSIZE];
	hash_init(&state, NULL, 0, HASHSIZE);
	hash_update(&state, (unsigned char *)"librecast", 9);
	hash_final(&state, hash3, HASHSIZE);
	CHECK(memcmp(hash1, hash3, HASHSIZE) == 0,
	      "incremental hash equals one-shot hash");

	char hex[HEXLEN];
	hash_bin2hex(hex, sizeof hex, hash3, HASHSIZE);
	CHECK(strlen(hex) == HASHSIZE * 2, "hash_bin2hex() renders 2 hex digits/byte");

	/* ── MDEX channel index ──
	 * Follows the pattern used by the upstream test 0000-0046: index several
	 * entries, then delete a non-root one.  (Deleting the root when it has no
	 * children dereferences a NULL pointer in upstream src/mdex.c, a latent
	 * upstream defect unrelated to this adaptation and out of scope here.) */
	mdex_t *mdex = mdex_init(64);
	CHECK(mdex != NULL, "mdex_init(64)");
	if (mdex) {
		unsigned char keys[4][HASHSIZE];
		mdex_entry_t entry;
		int stored = 1;
		for (int z = 0; z < 4; z++) {
			CHECK(hash_generic(keys[z], HASHSIZE,
			                   (unsigned char *)&z, sizeof z) == 0,
			      "hash_generic() produces an index key");
			memset(&entry, 0, sizeof entry);
			entry.type = MDEX_PTR;
			entry.ptr.size = (size_t)z;
			entry.ptr.data = (void *)0x1234;
			if (mdex_put(mdex, keys[z], HASHSIZE, &entry) != 0)
				stored = 0;
			if (mdex_get(mdex, keys[z], HASHSIZE, NULL) != 0)
				stored = 0;
		}
		CHECK(stored, "mdex_put()/mdex_get() store and find every entry");

		errno = 0;
		CHECK(mdex_get(mdex, keys[0], HASHSIZE, &entry) == 0,
		      "mdex_get() retrieves an entry");
		CHECK(entry.type == MDEX_PTR, "retrieved entry keeps its type");

		CHECK(mdex_del(mdex, keys[3], HASHSIZE) == 0,
		      "mdex_del() removes a non-root entry");
		errno = 0;
		CHECK(mdex_get(mdex, keys[3], HASHSIZE, NULL) == -1 && errno == ENOENT,
		      "deleted entry is gone (ENOENT)");
		CHECK(mdex_get(mdex, keys[0], HASHSIZE, NULL) == 0,
		      "remaining entries stay reachable after deletion");

		mdex_free(mdex);
		printf("[ OK ] mdex_free()\n");
	}

	/* teardown: frees sockets/channels and joins the listener thread */
	lc_ctx_free(lctx);
	printf("[ OK ] lc_ctx_free() tears the context down\n");

	if (failures) {
		printf("%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("test librecast 0.8.0: all checks passed\n");
	return 0;
}
