/* Installed-package API surface test for libcanberra/0.30.
 *
 * Takes a strong-typed function pointer for every exported public symbol in
 * canberra.h so each one is relocated against libcanberra.so at load time,
 * then performs a small runtime sweep (proplist lifecycle, error strings).
 */

#include <canberra.h>

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef int (*fn_proplist_create_t)(ca_proplist **);
typedef int (*fn_proplist_destroy_t)(ca_proplist *);
typedef int (*fn_proplist_sets_t)(ca_proplist *, const char *, const char *);
typedef int (*fn_proplist_setf_t)(ca_proplist *, const char *, const char *, ...);
typedef int (*fn_proplist_set_t)(ca_proplist *, const char *, const void *, size_t);
typedef int (*fn_context_create_t)(ca_context **);
typedef int (*fn_context_set_driver_t)(ca_context *, const char *);
typedef int (*fn_context_change_device_t)(ca_context *, const char *);
typedef int (*fn_context_open_t)(ca_context *);
typedef int (*fn_context_destroy_t)(ca_context *);
typedef int (*fn_context_change_props_t)(ca_context *, ...);
typedef int (*fn_context_change_props_full_t)(ca_context *, ca_proplist *);
typedef int (*fn_context_play_full_t)(ca_context *, uint32_t, ca_proplist *,
                                      ca_finish_callback_t, void *);
typedef int (*fn_context_play_t)(ca_context *, uint32_t, ...);
typedef int (*fn_context_cache_full_t)(ca_context *, ca_proplist *);
typedef int (*fn_context_cache_t)(ca_context *, ...);
typedef int (*fn_context_cancel_t)(ca_context *, uint32_t);
typedef int (*fn_context_playing_t)(ca_context *, uint32_t, int *);
typedef const char *(*fn_strerror_t)(int);

static int nchecks = 0;
static int nfailed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        nchecks++;                                                           \
        if (!(cond)) {                                                       \
            nfailed++;                                                       \
            fprintf(stderr, "api_surface: FAIL line %d: %s\n", __LINE__, #cond); \
        }                                                                    \
    } while (0)

#define TAKE_PTR(var, fn)                                                    \
    do {                                                                     \
        var = (fn);                                                          \
        CHECK(var != NULL);                                                  \
    } while (0)

int main(void) {
    fn_proplist_create_t p_create = NULL;
    fn_proplist_destroy_t p_destroy = NULL;
    fn_proplist_sets_t p_sets = NULL;
    fn_proplist_setf_t p_setf = NULL;
    fn_proplist_set_t p_set = NULL;
    fn_context_create_t c_create = NULL;
    fn_context_set_driver_t c_set_driver = NULL;
    fn_context_change_device_t c_change_device = NULL;
    fn_context_open_t c_open = NULL;
    fn_context_destroy_t c_destroy = NULL;
    fn_context_change_props_t c_change_props = NULL;
    fn_context_change_props_full_t c_change_props_full = NULL;
    fn_context_play_full_t c_play_full = NULL;
    fn_context_play_t c_play = NULL;
    fn_context_cache_full_t c_cache_full = NULL;
    fn_context_cache_t c_cache = NULL;
    fn_context_cancel_t c_cancel = NULL;
    fn_context_playing_t c_playing = NULL;
    fn_strerror_t strerror_fn = NULL;

    TAKE_PTR(p_create, &ca_proplist_create);
    TAKE_PTR(p_destroy, &ca_proplist_destroy);
    TAKE_PTR(p_sets, &ca_proplist_sets);
    TAKE_PTR(p_setf, &ca_proplist_setf);
    TAKE_PTR(p_set, &ca_proplist_set);
    TAKE_PTR(c_create, &ca_context_create);
    TAKE_PTR(c_set_driver, &ca_context_set_driver);
    TAKE_PTR(c_change_device, &ca_context_change_device);
    TAKE_PTR(c_open, &ca_context_open);
    TAKE_PTR(c_destroy, &ca_context_destroy);
    TAKE_PTR(c_change_props, &ca_context_change_props);
    TAKE_PTR(c_change_props_full, &ca_context_change_props_full);
    TAKE_PTR(c_play_full, &ca_context_play_full);
    TAKE_PTR(c_play, &ca_context_play);
    TAKE_PTR(c_cache_full, &ca_context_cache_full);
    TAKE_PTR(c_cache, &ca_context_cache);
    TAKE_PTR(c_cancel, &ca_context_cancel);
    TAKE_PTR(c_playing, &ca_context_playing);
    TAKE_PTR(strerror_fn, &ca_strerror);

    /* Every *real* error code (-18..0; _CA_ERROR_MAX is the -19 sentinel
     * which ca_strerror deliberately rejects) must produce a non-empty
     * descriptive string. */
    {
        int code;
        for (code = _CA_ERROR_MAX + 1; code <= 0; code++) {
            const char *msg = strerror_fn(code);
            CHECK(msg != NULL);
            CHECK(msg[0] != '\0');
        }
    }
    /* Out-of-domain codes are rejected (ca_strerror's ca_return_val_if_fail
     * guard makes positive codes return NULL rather than some junk string). */
    CHECK(strerror_fn(1000) == NULL);

    /* Exercise the proplist factory through the relocated pointers. */
    {
        ca_proplist *p = NULL;
        CHECK(p_create(&p) == CA_SUCCESS);
        CHECK(p != NULL);
        CHECK(p_destroy(p) == CA_SUCCESS);
    }

    fprintf(stdout, "api_surface: %d checks, %d failed, 19 symbols relocated\n",
            nchecks, nfailed);
    return nfailed == 0 ? 0 : 1;
}
