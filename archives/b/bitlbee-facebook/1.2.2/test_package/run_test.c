/*
 * bitlbee-facebook plugin loader test (host stub) — R34 consumer test.
 *
 * bitlbee plugins are dlopen()ed by the bitlbee daemon and resolve the
 * plugin API (register_protocol, imcb_*, set_*, ...) against the host
 * executable's exported symbols.  This program simulates that contract:
 * it exports the full bitlbee plugin API surface as stubs, dlopen()s the
 * module with RTLD_NOW (every relocation must resolve), calls both
 * G_MODULE_EXPORT entry points and validates the plugin_info ABI struct.
 *
 * L1e destructive reverse proof: when the module file is missing the
 * dlopen below fails and the program exits non-zero (verified manually
 * during adaptation; the test_package conanfile additionally hard-fails
 * when the module is absent from the package).
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

/* ---- bitlbee plugin API stubs (bitlbee 3.6: protocols/nogaim.h, set.h) ---- */

char *SET_INVALID = (char *)0;  /* extern char *SET_INVALID (set.h) */

/* entry points actually called by init_plugin() get real signatures +
 * call counters */
static int register_protocol_calls = 0;
static int root_command_add_calls = 0;

void register_protocol(void *prpl) { (void)prpl; register_protocol_calls++; }
void root_command_add(const char *cmd, int a, void *b, int c) {
    (void)cmd; (void)a; (void)b; (void)c; root_command_add_calls++;
}

/* remaining bitlbee API surface: presence only (RTLD_NOW requires the
 * symbols to exist even though these code paths are never driven here) */
#define S0(f) void f(void) {}
S0(account_get)
S0(b_event_remove) S0(b_input_add) S0(b_timeout_add)
S0(bee_chat_by_title) S0(bee_user_by_handle) S0(bee_user_new) S0(bool2int)
S0(http_close) S0(http_dorequest) S0(imc_logout)
S0(imcb_add_buddy) S0(imcb_buddy_by_handle) S0(imcb_buddy_msg)
S0(imcb_buddy_nick_hint) S0(imcb_buddy_status) S0(imcb_buddy_typing)
S0(imcb_chat_add_buddy) S0(imcb_chat_free) S0(imcb_chat_log)
S0(imcb_chat_msg) S0(imcb_chat_name_hint) S0(imcb_chat_new)
S0(imcb_chat_remove_buddy) S0(imcb_chat_topic) S0(imcb_connected)
S0(imcb_error) S0(imcb_log) S0(imcb_new) S0(imcb_remove_buddy)
S0(imcb_rename_buddy)
S0(irc_rootmsg) S0(irc_user_by_name) S0(is_bool) S0(random_bytes)
S0(set_add) S0(set_eval_bool) S0(set_eval_int) S0(set_find)
S0(set_getbool) S0(set_getint) S0(set_getstr) S0(set_setint) S0(set_setstr)
S0(sha1_append) S0(sha1_init) S0(sha1_random_uuid)
S0(ssl_connect) S0(ssl_disconnect) S0(ssl_getfd) S0(ssl_read)
S0(ssl_sockerr_again) S0(ssl_write) S0(url_set)

/* ---- plugin_info ABI (bitlbee 3.6 bitlbee.h) ---- */
struct plugin_info {
    unsigned int abi_version;
    char *name;
    char *version;
};

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <facebook.so>\n", argv[0]);
        return 10;
    }

    void *h = dlopen(argv[1], RTLD_NOW);
    if (!h) {
        fprintf(stderr, "FAIL dlopen: %s\n", dlerror());
        return 1;
    }

    struct plugin_info *(*info)(void) =
        (struct plugin_info *(*)(void))dlsym(h, "init_plugin_info");
    void (*init)(void) = (void (*)(void))dlsym(h, "init_plugin");
    if (!info || !init) {
        fprintf(stderr, "FAIL dlsym: init_plugin/init_plugin_info missing\n");
        return 2;
    }

    struct plugin_info *pi = info();
    if (!pi || pi->abi_version != 1) {
        fprintf(stderr, "FAIL plugin_info: abi_version=%u (expected 1)\n",
                pi ? pi->abi_version : 0);
        return 3;
    }
    if (!pi->name || strcmp(pi->name, "facebook") != 0) {
        fprintf(stderr, "FAIL plugin_info: name=%s (expected facebook)\n",
                pi->name ? pi->name : "(null)");
        return 4;
    }
    if (!pi->version || strcmp(pi->version, "1.2.2") != 0) {
        fprintf(stderr, "FAIL plugin_info: version=%s (expected 1.2.2)\n",
                pi->version ? pi->version : "(null)");
        return 5;
    }

    init();
    if (register_protocol_calls != 1) {
        fprintf(stderr, "FAIL init_plugin: register_protocol called %d times\n",
                register_protocol_calls);
        return 6;
    }
    if (root_command_add_calls != 3) {
        fprintf(stderr, "FAIL init_plugin: root_command_add called %d times\n",
                root_command_add_calls);
        return 7;
    }

    printf("OK: facebook.so loaded (RTLD_NOW), plugin_info{abi=1, name=%s, "
           "version=%s}, init_plugin ran (register_protocol x%d, "
           "root_command_add x%d)\n",
           pi->name, pi->version, register_protocol_calls,
           root_command_add_calls);
    dlclose(h);
    return 0;
}
