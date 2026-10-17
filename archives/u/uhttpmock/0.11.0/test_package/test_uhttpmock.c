/* test_uhttpmock.c — Conan L1 test for uhttpmock 0.11.0.
 *
 * Exercises the real libuhttpmock-1.0 API (no network traffic, no trace
 * files): construct a UhmResolver, add A records, resolve existent and
 * non-existent names through the GResolver interface, reset it, then
 * construct a UhmServer and check its fresh-object defaults. Each check
 * prints one "CHECK-OK: <name>" line; the conanfile counts checks from this
 * source (8), success is exit code 0 — stdout is diagnostic only, never the
 * count source.
 */
#include <gio/gio.h>
#include <glib.h>
#include <libuhttpmock-1.0/uhttpmock/uhm.h>
#include <stdio.h>

#define CHECK(name, cond) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "CHECK-FAIL: %s\n", name); \
            return 1; \
        } \
        printf("CHECK-OK: %s\n", name); \
    } while (0)

int
main(void)
{
    UhmResolver *resolver = NULL;
    UhmServer *server = NULL;
    GList *addresses = NULL;
    GError *error = NULL;
    char *addr_str = NULL;

    /* 1: resolver construction. */
    resolver = uhm_resolver_new();
    CHECK("resolver-new", UHM_IS_RESOLVER(resolver));

    /* 2: add A records. */
    CHECK("resolver-add-A",
          uhm_resolver_add_A(resolver, "example.com", "127.0.0.1") &&
          uhm_resolver_add_A(resolver, "test.com", "10.0.0.1"));

    /* 3: resolve an existent name through the GResolver interface. */
    addresses = g_resolver_lookup_by_name(G_RESOLVER(resolver),
                                          "example.com", NULL, &error);
    CHECK("resolver-lookup-ok", error == NULL && addresses != NULL);
    g_assert_no_error(error);
    addr_str = g_inet_address_to_string(G_INET_ADDRESS(addresses->data));
    CHECK("resolver-lookup-addr",
          g_list_length(addresses) == 1 &&
          g_strcmp0(addr_str, "127.0.0.1") == 0);
    g_free(addr_str);
    g_resolver_free_addresses(addresses);
    addresses = NULL;

    /* 5: resolving an unknown name must fail. */
    addresses = g_resolver_lookup_by_name(G_RESOLVER(resolver),
                                          "nonexistent.invalid", NULL, &error);
    CHECK("resolver-lookup-miss", addresses == NULL && error != NULL);
    g_clear_error(&error);

    /* 6: reset clears all records. */
    uhm_resolver_reset(resolver);
    addresses = g_resolver_lookup_by_name(G_RESOLVER(resolver),
                                          "example.com", NULL, &error);
    CHECK("resolver-reset", addresses == NULL);
    g_clear_error(&error);

    /* 7: server construction with default properties. */
    server = uhm_server_new();
    CHECK("server-new", UHM_IS_SERVER(server));

    /* 8: fresh server defaults (not running, no trace directory/address). */
    CHECK("server-defaults",
          uhm_server_get_port(server) == 0 &&
          uhm_server_get_trace_directory(server) == NULL &&
          uhm_server_get_address(server) == NULL);

    g_object_unref(server);
    g_object_unref(resolver);

    printf("ALL CHECKS PASSED\n");
    return 0;
}
