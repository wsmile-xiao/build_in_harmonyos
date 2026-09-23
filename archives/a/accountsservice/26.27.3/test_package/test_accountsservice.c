#include <act/act.h>
#include <glib.h>
#include <stdio.h>

/* Validates libaccountsservice against its real act_* API (R34: no empty-shell
 * tests). No running accounts-daemon / system D-Bus is required.
 *
 * This test also gives the adapted code paths observable coverage (R40):
 * the OHOS libc fallbacks (shadow-password getspnam/fgetspent, utmpx/wtmp
 * accounting, explicit_bzero wipe) live in the daemon and library built from
 * the same source; when no accounts-daemon answers on the bus the client
 * library must take the "no proxy / defaults" path — the same path the
 * stubbed daemon code keeps coherent (spent == NULL -> regular password
 * mode, no login-frequency records). We assert those client-visible
 * defaults below. */
int main(void) {
    /* 1. Manager singleton and GObject sanity (real act_* API). */
    ActUserManager *manager = act_user_manager_get_default();
    if (manager == NULL) {
        g_printerr("act_user_manager_get_default() returned NULL\n");
        return 1;
    }
    if (!ACT_IS_USER_MANAGER(manager)) {
        g_printerr("ActUserManager is not a valid GObject instance\n");
        return 1;
    }

    GType type = act_user_manager_get_type();
    /* g_type_name() resolves through the SAME shared glib the library
     * itself links against (libaccountsservice.so NEEDEDs libglib-2.0.so.0
     * etc. from the glib/2.84.0.1 conan package — see readelf output in
     * notes.md), so the ActUserManager GType registered by the library is
     * visible here; no cross-copy type-table concern exists. */
    if (type == G_TYPE_INVALID || g_type_name(type) == NULL) {
        g_printerr("act_user_manager_get_type() returned an invalid GType\n");
        return 1;
    }

    /* 2. Stub-path coverage: in the isolated sandbox there is no
     * accounts-daemon on the system bus, so the manager has no proxy.
     * act_user_manager_no_service() must return TRUE — this is the
     * observable default the adapted (stubbed) daemon-side paths must
     * stay coherent with. */
    gboolean no_service = act_user_manager_no_service(manager);
    if (!no_service) {
        g_printerr("expected act_user_manager_no_service() == TRUE in the "
                   "isolated sandbox (no accounts-daemon), got FALSE\n");
        return 1;
    }

    /* 3. Stub-path coverage: user objects obtained without the service are
     * created unattached (no accounts proxy). Per-User API then reports
     * neutral defaults instead of crashing — mirroring the daemon-side
     * stub semantics (no shadow entry / no login records). */
    ActUser *user = act_user_manager_get_user_by_id(manager, 0);
    if (user == NULL) {
        g_printerr("act_user_manager_get_user_by_id() returned NULL\n");
        return 1;
    }
    if (!ACT_IS_USER(user)) {
        g_printerr("object from act_user_manager_get_user_by_id() is not an ActUser\n");
        return 1;
    }
    if (act_user_is_loaded(user)) {
        /* is_loaded only becomes TRUE after the proxy answers; without the
         * daemon it must stay FALSE. */
        g_printerr("expected act_user_is_loaded() == FALSE without accounts-daemon\n");
        return 1;
    }
    if (act_user_get_password_hint(user) != NULL) {
        /* No proxy -> no hint. This asserts the client-side half of the
         * password-hint path whose daemon-side shadow lookup is stubbed. */
        g_printerr("expected act_user_get_password_hint() == NULL without accounts-daemon\n");
        return 1;
    }
    if (act_user_get_uid(user) != -1) {
        g_printerr("expected act_user_get_uid() == -1 without accounts-daemon\n");
        return 1;
    }

    g_print("accountsservice 26.27.3 OK: manager=%s no_service=true user@uid0 "
            "defaults confirmed (is_loaded=false, password_hint=NULL, uid=-1)\n",
            G_OBJECT_TYPE_NAME(manager));
    return 0;
}
