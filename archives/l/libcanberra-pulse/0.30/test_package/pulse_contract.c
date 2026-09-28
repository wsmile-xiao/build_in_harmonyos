/* Version/error-code contract and PulseAudio-driver test for
 * libcanberra-pulse/0.30.
 *
 * The recipe compiles the pulse driver INTO libcanberra.so
 * (--with-builtin=pulse), so there is no plugin module to dlopen and no
 * public "which driver is compiled in" query.  The observable contract is
 * the driver-name guard every backend implements at open time, e.g. pulse.c:
 *
 *     int driver_open(ca_context *c) {
 *         ca_return_val_if_fail(!c->driver || ca_streq(c->driver, "pulse"),
 *                               CA_ERROR_NODRIVER);
 *         ... connect to the PulseAudio server ...
 *     }
 *
 * A backend that is not compiled in can never be reached, so opening a
 * context that names it reports CA_ERROR_NODRIVER.  This consumer uses that
 * to prove the pulse backend is the one that is built in and that the
 * null/alsa backends are not - with no PulseAudio server and no audio device
 * required, because the driver-name guard runs before any server contact.
 *
 * Compile-time contracts pin CA_MAJOR/CA_MINOR (preprocessor macros); the
 * error *enumeration* values are enum constants, invisible to the C
 * preprocessor, and are pinned at runtime instead.
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
            fprintf(stderr, "pulse_contract: FAIL line %d: %s\n", __LINE__, #cond); \
        }                                                                    \
    } while (0)

/* Open a fresh context that names 'driver' and return what open() reported. */
static int open_named_driver(const char *driver) {
    ca_context *c = NULL;
    int ret;

    if (ca_context_create(&c) != CA_SUCCESS)
        return CA_ERROR_OOM;
    if (ca_context_set_driver(c, driver) != CA_SUCCESS)
        return CA_ERROR_STATE;
    ret = ca_context_open(c);
    ca_context_destroy(c);
    return ret;
}

int main(void) {
    ca_context *c = NULL;
    ca_proplist *p = NULL;
    int pulse_open;

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

    /* --- The compiled-in backend must be PulseAudio. ---
     * A pulse build accepts the name "pulse" and moves on to the server
     * connection (CA_SUCCESS with a server running, a connection-family
     * error on a headless device); a build without the pulse driver cannot
     * get past the name guard. */
    pulse_open = open_named_driver("pulse");
    CHECK(pulse_open != CA_ERROR_NODRIVER);
    CHECK(ca_strerror(pulse_open) != NULL);   /* a named libcanberra error */
    printf("INFO: ca_context_open(pulse) -> %d (%s)\n", pulse_open,
           ca_strerror(pulse_open));

    /* --- The null and alsa backends must NOT be built in. ---
     * archives/l/libcanberra/0.30 (--with-builtin=null) reports CA_SUCCESS
     * for "null" here; this package must not. */
    CHECK(open_named_driver("null") == CA_ERROR_NODRIVER);
    CHECK(open_named_driver("alsa") == CA_ERROR_NODRIVER);
    CHECK(open_named_driver("no-such-backend") == CA_ERROR_NODRIVER);

    /* --- play/cache demand an identifying event/media property; that guard
     * runs before any driver contact, so it holds on the pulse backend too. --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(ca_proplist_create(&p) == CA_SUCCESS);
    CHECK(ca_context_play_full(c, 7, p, NULL, NULL) == CA_ERROR_INVALID);
    CHECK(ca_context_cache_full(c, p) == CA_ERROR_INVALID);
    CHECK(ca_proplist_destroy(p) == CA_SUCCESS);
    p = NULL;
    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    /* --- Playback reaches the pulse backend (never NODRIVER) and, without a
     * server, cannot complete. --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(ca_proplist_create(&p) == CA_SUCCESS);
    CHECK(ca_proplist_sets(p, CA_PROP_EVENT_ID,
                           "org.example.canberra.pulse.contract") == CA_SUCCESS);
    {
        int ret = ca_context_play_full(c, 42, p, NULL, NULL);
        CHECK(ret != CA_ERROR_NODRIVER);
        if (pulse_open == CA_SUCCESS)
            CHECK(ret == CA_SUCCESS);
        else
            CHECK(ret != CA_SUCCESS);
    }
    CHECK(ca_proplist_destroy(p) == CA_SUCCESS);
    p = NULL;
    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    /* --- Varargs helpers build their own proplists and take the same path. --- */
    CHECK(ca_context_create(&c) == CA_SUCCESS);
    CHECK(ca_context_change_props(c, CA_PROP_APPLICATION_NAME,
                                  "canberra-pulse-contract", NULL) == CA_SUCCESS);
    {
        int ret = ca_context_play(c, 1, CA_PROP_EVENT_ID,
                                  "org.example.canberra.pulse.va", NULL);
        CHECK(ret != CA_ERROR_NODRIVER);
    }
    CHECK(ca_context_destroy(c) == CA_SUCCESS);
    c = NULL;

    fprintf(stdout, "pulse_contract: %d checks, %d failed\n", nchecks, nfailed);
    return nfailed == 0 ? 0 : 1;
}
