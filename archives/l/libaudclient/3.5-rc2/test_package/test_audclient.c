/* test_package/test_audclient.c — libaudclient 3.5-rc2 consumer test (L1).
 *
 * Link-time layer: takes the address of representative API functions via
 * the real <audacious/audctrl.h> declarations, proving the headers and
 * the audclient.pc link line resolve (compile + link ABI).
 *
 * Runtime layer: dlopen("libaudclient.so.2") — the soname the upstream
 * buildsys produces (GNU branch: -Wl,-soname=${SHARED_LIB}.${LIB_MAJOR},
 * LIB_MAJOR=2) — then dlsym()s every function audctrl.c exports via the
 * EXPORT macro, verifying export visibility under the upstream
 * -fvisibility=hidden + EXPORT scheme (71 symbols, measured by grep over
 * the pristine source).
 *
 * No D-Bus session bus is required: every audctrl entry point sends a
 * D-Bus message immediately, so with no audacious player / dbus-daemon
 * on OHOS the maximal executable scope is load + full export surface
 * (documented in test_package/MANIFEST.yml).
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <glib.h>
#include <dbus/dbus-glib.h>
#include <audacious/audctrl.h>

static int n_checks = 0;
static int n_failures = 0;

#define CHECK(cond, name)                        \
    do {                                         \
        ++n_checks;                              \
        if (cond) {                              \
            printf("ok %d - %s\n", n_checks, name); \
        } else {                                 \
            ++n_failures;                        \
            fprintf(stderr, "not ok %d - %s\n", n_checks, name); \
        }                                        \
    } while (0)

/* Link-time ABI subset (addresses taken through audctrl.h declarations;
 * the linker must resolve these from libaudclient.so). */
static void *const linktime_syms[] = {
    (void *)audacious_remote_playlist,          /* initial API */
    (void *)audacious_remote_get_version,
    (void *)audacious_remote_is_playing,
    (void *)audacious_remote_get_volume,
    (void *)audacious_remote_get_eq,            /* GArray** signature */
    (void *)audacious_remote_quit,              /* XMMS 1.2.1 */
    (void *)audacious_get_tuple_field_data,     /* non-remote namespace, 1.3 */
    (void *)audacious_remote_get_tuple_fields,  /* 1.9 */
    (void *)audacious_remote_playlist_get_active_name, /* 2.4, newest */
};

/* Every function audctrl.c defines with EXPORT (71 total). Header-only
 * declarations without an implementation (audacious_set_session_uri,
 * audacious_get_session_uri, audacious_set_session_type) are deliberately
 * absent — dlsym would legitimately fail for them. */
static const char *const exported_syms[] = {
    "audacious_get_tuple_field_data",
    "audacious_remote_eject",
    "audacious_remote_eq_activate",
    "audacious_remote_get_balance",
    "audacious_remote_get_eq",
    "audacious_remote_get_eq_band",
    "audacious_remote_get_eq_preamp",
    "audacious_remote_get_info",
    "audacious_remote_get_main_volume",
    "audacious_remote_get_output_time",
    "audacious_remote_get_playlist_file",
    "audacious_remote_get_playlist_length",
    "audacious_remote_get_playlist_pos",
    "audacious_remote_get_playlist_time",
    "audacious_remote_get_playlist_title",
    "audacious_remote_get_playqueue_length",
    "audacious_remote_get_playqueue_list_position",
    "audacious_remote_get_playqueue_queue_position",
    "audacious_remote_get_tuple_fields",
    "audacious_remote_get_version",
    "audacious_remote_get_volume",
    "audacious_remote_is_advance",
    "audacious_remote_is_main_win",
    "audacious_remote_is_paused",
    "audacious_remote_is_playing",
    "audacious_remote_is_repeat",
    "audacious_remote_is_running",
    "audacious_remote_is_shuffle",
    "audacious_remote_is_stop_after",
    "audacious_remote_jump_to_time",
    "audacious_remote_main_win_toggle",
    "audacious_remote_pause",
    "audacious_remote_play",
    "audacious_remote_play_pause",
    "audacious_remote_playlist",
    "audacious_remote_playlist_add",
    "audacious_remote_playlist_add_url_string",
    "audacious_remote_playlist_clear",
    "audacious_remote_playlist_delete",
    "audacious_remote_playlist_enqueue_to_temp",
    "audacious_remote_playlist_get_active_name",
    "audacious_remote_playlist_ins_url_string",
    "audacious_remote_playlist_next",
    "audacious_remote_playlist_open_list",
    "audacious_remote_playlist_open_list_to_temp",
    "audacious_remote_playlist_prev",
    "audacious_remote_playqueue_add",
    "audacious_remote_playqueue_clear",
    "audacious_remote_playqueue_is_queued",
    "audacious_remote_playqueue_remove",
    "audacious_remote_quit",
    "audacious_remote_set_balance",
    "audacious_remote_set_eq",
    "audacious_remote_set_eq_band",
    "audacious_remote_set_eq_preamp",
    "audacious_remote_set_main_volume",
    "audacious_remote_set_playlist_pos",
    "audacious_remote_set_volume",
    "audacious_remote_show_about_box",
    "audacious_remote_show_jtf_box",
    "audacious_remote_show_prefs_box",
    "audacious_remote_stop",
    "audacious_remote_toggle_about_box",
    "audacious_remote_toggle_advance",
    "audacious_remote_toggle_aot",
    "audacious_remote_toggle_filebrowser",
    "audacious_remote_toggle_jtf_box",
    "audacious_remote_toggle_prefs_box",
    "audacious_remote_toggle_repeat",
    "audacious_remote_toggle_shuffle",
    "audacious_remote_toggle_stop_after",
};

#define N_LINKTIME (sizeof linktime_syms / sizeof linktime_syms[0])
#define N_EXPORTED (sizeof exported_syms / sizeof exported_syms[0])

int main(void)
{
    printf("libaudclient test_package: %zu link-time + %zu dlsym checks\n",
           N_LINKTIME, N_EXPORTED);

    /* 1. link-time ABI */
    for (size_t i = 0; i < N_LINKTIME; i++)
        CHECK(linktime_syms[i] != NULL, "link-time address resolved");

    /* 2. dlopen by upstream soname */
    void *h = dlopen("libaudclient.so.2", RTLD_NOW | RTLD_LOCAL);
    if (h == NULL) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        fprintf(stderr, "bailing out after %d checks, %d failures\n",
                n_checks, n_failures);
        return 1;
    }
    CHECK(h != NULL, "dlopen(libaudclient.so.2, RTLD_NOW)");

    /* 3. full export surface */
    void *first = NULL;
    for (size_t i = 0; i < N_EXPORTED; i++) {
        void *p = dlsym(h, exported_syms[i]);
        if (i == 0)
            first = p;
        CHECK(p != NULL, exported_syms[i]);
    }

    /* 4. the first resolved symbol really lives in libaudclient */
    Dl_info info;
    CHECK(dladdr(first, &info) != 0 &&
              strstr(info.dli_fname, "libaudclient") != NULL,
          "dladdr locates symbol inside libaudclient");

    printf("checks=%d failures=%d\n", n_checks, n_failures);
    dlclose(h);
    return n_failures == 0 ? 0 : 1;
}
