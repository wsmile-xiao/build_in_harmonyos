/* Version/error-code contract and null-driver lifecycle test for
 * libcanberra/0.30.
 *
 * Compile-time contracts pin CA_MAJOR/CA_MINOR (both are preprocessor
 * macros, so #if works); the ca_error_t-like *error enumeration* values
 * are enum constants -- invisible to the C preprocessor -- and are pinned
 * at runtime instead.  Runtime checks drive the public ca_context_* /
 * ca_proplist_* API on the built-in null driver (no audio device required)
 * over a full create/set_driver/change_device/open/play_full(callback)/
 * playing/cancel/cache/destroy lifecycle plus the expected failure modes.
 */

#include <canberra.h>

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#if CA_MAJOR != 0
#error "CA_MAJOR contract violated"
#endif
#if CA_MINOR != 30
#error "CA_MINOR contract violated"
#endif

static int nchecks = 0;
static int nfailed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        nchecks++;                                                           \
        if (!(cond)) {                                                       \
            nfailed++;                                                       \
            fprintf(stderr, "version_contract: FAIL line %d: %s\n", __LINE__, #cond); \
        }                                                                    \
    } while (0)

struct finish_record {
    int called;
    uint32_t id;
    int code;
    const void *userdata;
};

/* ca_finish_callback_t.  The callback must not call back into libcanberra
 * (the context may hold its lock), so it only records what it saw. */
static void finish_cb(ca_context *c, uint32_t id, int error_code, void *userdata) {
    struct finish_record *r = (struct finish_record *) userdata;
    (void) c;
    r->called++;
    r->id = id;
    r->code = error_code;
    r->userdata = userdata;
}

int main(void) {
    ca_context *c = NULL;
    ca_proplist *p = NULL;
    struct finish_record fr;

    /* --- Error-code numeric contract.  Every named error code must keep
     * its upstream numeric value.  (enum constants: checked at runtime.) --- */
    CHECK(CA_SUCCESS == 0);
    CHECK(CA_ERROR_NOTSUPPORTED == -1);
    CHECK(CA_ERROR_INVALID == -2);
    CHECK(CA_ERROR_STATE == -3);
    CHECK(CA_ERROR_OOM == -4);
    CHECK(CA_ERROR_NODRIVER == -5);
    CHECK(CA_ERROR_SYSTEM == -6);
    CHECK(CA_ERROR_CORRUPT == -7);
    CHECK(CA_ERROR_TOOBIG == -8);
    CHECK(CA_ERROR_NOTFOUND == -9);
    CHECK(CA_ERROR_DESTROYED == -10);
    CHECK(CA_ERROR_CANCELED == -11);
    CHECK(CA_ERROR_NOTAVAILABLE == -12);
    CHECK(CA_ERROR_ACCESS == -13);
    CHECK(CA_ERROR_IO == -14);
    CHECK(CA_ERROR_INTERNAL == -15);
    CHECK(CA_ERROR_DISABLED == -16);
    CHECK(CA_ERROR_FORKED == -17);
    CHECK(CA_ERROR_DISCONNECTED == -18);
    CHECK(_CA_ERROR_MAX == -19);

    /* --- Version macro semantics. --- */
    CHECK(CA_CHECK_VERSION(0, 0));
    CHECK(CA_CHECK_VERSION(0, 29));
    CHECK(CA_CHECK_VERSION(0, 30));
    CHECK(!CA_CHECK_VERSION(0, 31));
    CHECK(!CA_CHECK_VERSION(1, 0));

    /* --- ca_strerror string table and guards. --- */
    CHECK(strcmp(ca_strerror(CA_SUCCESS), "Success") == 0);
    CHECK(strcmp(ca_strerror(CA_ERROR_INVALID), "Invalid argument") == 0);
    CHECK(strcmp(ca_strerror(CA_ERROR_NODRIVER), "No such driver") == 0);
    CHECK(ca_strerror(_CA_ERROR_MAX) == NULL);   /* sentinel is not a code */
    CHECK(ca_strerror(1) == NULL);               /* positive codes rejected */
    {
        int code;
        for (code = CA_ERROR_DISCONNECTED; code <= CA_SUCCESS; code++) {
            const char *msg = ca_strerror(code);
            CHECK(msg != NULL && msg[0] != '\0');
        }
    }

    /* --- NULL-argument validation on the factory functions. --- */
    CHECK(ca_proplist_create(NULL) == CA_ERROR_INVALID);
    CHECK(ca_proplist_destroy(NULL) == CA_ERROR_INVALID);
    CHECK(ca_context_open(NULL) == CA_ERROR_INVALID);

    /* --- Full lifecycle on the built-in null driver. --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(c != NULL);
    CHECK(ca_context_set_driver(c, "null") == CA_SUCCESS);
    CHECK(ca_context_change_device(c, "canberra-contract-device") == CA_SUCCESS);

    CHECK(ca_proplist_create(&p) == CA_SUCCESS);
    CHECK(p != NULL);
    CHECK(ca_proplist_sets(p, CA_PROP_EVENT_ID, "org.example.canberra.contract") == CA_SUCCESS);
    CHECK(ca_proplist_sets(p, CA_PROP_APPLICATION_NAME, "canberra-version-contract") == CA_SUCCESS);
    CHECK(ca_proplist_setf(p, CA_PROP_APPLICATION_VERSION, "%d.%d", 0, 30) == CA_SUCCESS);

    CHECK(ca_context_change_props_full(c, p) == CA_SUCCESS);
    CHECK(ca_proplist_destroy(p) == CA_SUCCESS);
    p = NULL;

    CHECK(ca_context_open(c) == CA_SUCCESS);

    /* The driver name is locked in once the context is open. */
    CHECK(ca_context_set_driver(c, "null") == CA_ERROR_STATE);

    /* Play through the null driver: it finishes synchronously, so the
     * completion callback must already have run when play_full returns. */
    memset(&fr, 0, sizeof(fr));
    CHECK(ca_proplist_create(&p) == CA_SUCCESS);
    CHECK(ca_proplist_sets(p, CA_PROP_EVENT_ID, "org.example.canberra.contract.play") == CA_SUCCESS);
    CHECK(ca_context_play_full(c, 42, p, finish_cb, &fr) == CA_SUCCESS);
    CHECK(fr.called == 1);
    CHECK(fr.id == 42);
    CHECK(fr.code == CA_SUCCESS);
    CHECK(fr.userdata == &fr);
    CHECK(ca_proplist_destroy(p) == CA_SUCCESS);
    p = NULL;

    /* The null driver never keeps a sound playing. */
    {
        int playing = -1;
        CHECK(ca_context_playing(c, 42, &playing) == CA_SUCCESS);
        CHECK(playing == 0);
    }

    CHECK(ca_context_cancel(c, 42) == CA_SUCCESS);

    /* The null driver does not support pre-caching samples. */
    CHECK(ca_proplist_create(&p) == CA_SUCCESS);
    CHECK(ca_proplist_sets(p, CA_PROP_EVENT_ID, "org.example.canberra.contract.cache") == CA_SUCCESS);
    CHECK(ca_context_cache_full(c, p) == CA_ERROR_NOTSUPPORTED);
    CHECK(ca_proplist_destroy(p) == CA_SUCCESS);
    p = NULL;

    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    /* --- A driver name that no builtin provides fails open(), not
     * set_driver(). --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(ca_context_set_driver(c, "no-such-backend") == CA_SUCCESS);
    CHECK(ca_context_open(c) == CA_ERROR_NODRIVER);
    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    /* --- play/cache demand an identifying event/media property. --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(ca_proplist_create(&p) == CA_SUCCESS);
    CHECK(ca_context_play_full(c, 7, p, NULL, NULL) == CA_ERROR_INVALID);
    CHECK(ca_context_cache_full(c, p) == CA_ERROR_INVALID);
    CHECK(ca_proplist_destroy(p) == CA_SUCCESS);
    p = NULL;
    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    /* --- Varargs play()/change_props() build their own proplists. --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(ca_context_set_driver(c, "null") == CA_SUCCESS);
    CHECK(ca_context_change_props(c, CA_PROP_APPLICATION_NAME, "va-client", NULL) == CA_SUCCESS);
    CHECK(ca_context_open(c) == CA_SUCCESS);
    CHECK(ca_context_play(c, 1, CA_PROP_EVENT_ID, "org.example.canberra.contract.va", NULL) == CA_SUCCESS);
    CHECK(ca_context_cancel(c, 1) == CA_SUCCESS);
    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    fprintf(stdout, "version_contract: %d checks, %d failed\n", nchecks, nfailed);
    return nfailed == 0 ? 0 : 1;
}
