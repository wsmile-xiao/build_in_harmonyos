/* End-to-end consumer flow for plasma-wayland-protocols/1.14.0 (HarmonyOS PC).
 *
 * This is a complete consumer use case (rule-12 "Hongmeng-specific test"), not an
 * assertion list.  A package that ships protocol *descriptions* is consumed by
 * turning them into code and then speaking the protocol -- exactly what
 * kwayland5 / kwin / libkscreen do.  This flow does the same thing for real:
 *
 *   BUILD TIME (test_package/CMakeLists.txt + e2e/gen_protocol.py)
 *     The bindings compiled into this binary are generated from
 *     <PLASMA_WAYLAND_PROTOCOLS_DIR>/keystate.xml -- the file this package
 *     installs, resolved through the package's own
 *     PlasmaWaylandProtocolsConfig.cmake.  The generator is strict: a missing or
 *     malformed XML, or a message it cannot translate exactly, fails the build.
 *     (Upstream's wayland-scanner cannot be invoked here: the binary published in
 *     wayland/1.22.0 is an ELF the OHOS loader rejects -- PR #13500 fixes it.)
 *
 *   RUN TIME
 *     The generated tables drive a real client<->server exchange over libwayland
 *     on an AF_UNIX socketpair:
 *        server: wl_display_create + wl_client_create(fd)
 *                + wl_global_create(org_kde_kwin_keystate, v4)
 *                + the generated request handlers
 *        client: wl_display_connect_to_fd -> wl_display_get_registry -> sees the
 *                global -> wl_registry_bind -> generated fetchStates()
 *        server: handler runs -> generated stateChanged(key, state) is posted
 *        client: generated listener receives it, payload compared
 *        client: generated destroy() -> server's destroy handler must run
 *
 * Success requires the requests to really cross the wire and the event payload
 * to come back unchanged, and the installed XML to be byte-identical to the one
 * the bindings were generated from.  A failing check exits non-zero, so ctest
 * reports a real failure; the run prints `assertions=N failures=M` either way.
 */
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include <wayland-client-core.h>
#include <wayland-client-protocol.h>
#include <wayland-server-core.h>

/* Generated at build time by e2e/gen_protocol.py from this package's XML. */
#include "keystate-protocol.h"

/* Values taken from the XML enums (key: numlock = 1, state: locked = 2), so the
 * comparison is meaningful rather than a pair of zeroes. */
#define EXPECTED_KEY 1u
#define EXPECTED_STATE 2u

#define IFACE_EXPECTED_NAME "org_kde_kwin_keystate"
#define IFACE_EXPECTED_VERSION 4
#define IFACE_EXPECTED_REQUESTS 2 /* fetchStates, destroy */
#define IFACE_EXPECTED_EVENTS 1   /* stateChanged */

static atomic_int g_server_ready = 0;
static atomic_int g_server_ok = 0;
static atomic_int g_client_done = 0;
static atomic_int g_server_binds = 0;
static atomic_int g_server_requests = 0;
static atomic_int g_server_destroys = 0;
static atomic_int g_client_globals = 0;
static atomic_int g_client_global_version = 0;
static atomic_int g_client_events = 0;
static atomic_uint g_client_key = 0;
static atomic_uint g_client_state = 0;

static int g_assertions = 0;
static int g_failures = 0;

/* Machine-readable tally, printed on every exit path. */
static int finish(int code)
{
    printf("assertions=%d failures=%d\n", g_assertions, g_failures);
    printf("hongmeng_e2e_flow=%s\n", (code == 0 && g_failures == 0) ? "PASS" : "FAIL");
    fflush(stdout);
    return (code == 0 && g_failures == 0) ? 0 : (code ? code : 1);
}

#define REQUIRE(condition, label, code)                                        \
    do {                                                                       \
        if (condition) {                                                       \
            g_assertions++;                                                    \
            printf("E2E CHECK %-58s OK\n", label);                             \
            fflush(stdout);                                                    \
        } else {                                                               \
            g_failures++;                                                      \
            fprintf(stderr, "E2E FAIL: %s\n", label);                          \
            return finish(code);                                               \
        }                                                                      \
    } while (0)

static void sleep_ms(int ms)
{
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (long) (ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

/* Identifies the exact XML file the bindings were generated from (the generator
 * stamps the same value into the header as KEYSTATE_XML_FNV1A64). */
static unsigned long long fnv1a64_file(const char *path, int *ok)
{
    unsigned char buf[4096];
    unsigned long long digest = 0xCBF29CE484222325ULL;
    FILE *handle = fopen(path, "rb");
    size_t got, i;
    *ok = 0;
    if (!handle)
        return 0;
    while ((got = fread(buf, 1, sizeof(buf), handle)) > 0) {
        for (i = 0; i < got; i++) {
            digest ^= buf[i];
            digest *= 0x100000001B3ULL;
        }
    }
    if (ferror(handle)) {
        fclose(handle);
        return 0;
    }
    fclose(handle);
    *ok = 1;
    return digest;
}

/* ------------------------------------------------------------------ server */
/* Handlers come from the XML through the generated table, so their shape is
 * dictated by the package's protocol description. */
static void server_fetch_states(struct wl_client *client, struct wl_resource *resource)
{
    (void) client;
    atomic_fetch_add(&g_server_requests, 1);
    fprintf(stderr, "SRV: fetchStates() decoded from the generated protocol\n");
    /* Reply through the generated event sender. */
    org_kde_kwin_keystate_send_stateChanged(resource, EXPECTED_KEY, EXPECTED_STATE);
}

static void server_destroy(struct wl_client *client, struct wl_resource *resource)
{
    (void) client;
    atomic_fetch_add(&g_server_destroys, 1);
    fprintf(stderr, "SRV: destroy() decoded from the generated protocol\n");
    wl_resource_destroy(resource);
}

static const struct org_kde_kwin_keystate_interface k_server_impl = {
    server_fetch_states, /* fetchStates */
    server_destroy,      /* destroy */
};

static void server_bind(struct wl_client *client, void *data, uint32_t version, uint32_t id)
{
    struct wl_resource *resource;
    (void) data;
    resource = wl_resource_create(client, &org_kde_kwin_keystate_interface, version, id);
    if (!resource) {
        wl_client_post_no_memory(client);
        return;
    }
    wl_resource_set_implementation(resource, &k_server_impl, NULL, NULL);
    atomic_fetch_add(&g_server_binds, 1);
    fprintf(stderr, "SRV: global bound (version %u)\n", (unsigned) version);
}

static void *server_main(void *arg)
{
    int fd = *(int *) arg;
    struct wl_display *display;
    struct wl_event_loop *loop;
    int iterations = 0;

    display = wl_display_create();
    if (!display) {
        fprintf(stderr, "SRV: wl_display_create failed\n");
        atomic_store(&g_server_ready, 1);
        return NULL;
    }
    /* The client end of the socketpair is adopted directly; no filesystem socket
     * is created (this sandbox denies filesystem AF_UNIX binds). */
    if (!wl_client_create(display, fd)) {
        fprintf(stderr, "SRV: wl_client_create failed\n");
        wl_display_destroy(display);
        atomic_store(&g_server_ready, 1);
        return NULL;
    }
    /* Interface name and version come from the XML through the generated code. */
    if (!wl_global_create(display, &org_kde_kwin_keystate_interface,
                          IFACE_EXPECTED_VERSION, NULL, server_bind)) {
        fprintf(stderr, "SRV: wl_global_create failed\n");
        wl_display_destroy(display);
        atomic_store(&g_server_ready, 1);
        return NULL;
    }

    atomic_store(&g_server_ok, 1);
    atomic_store(&g_server_ready, 1);

    loop = wl_display_get_event_loop(display);
    while (!atomic_load(&g_client_done) && iterations < 3000) {
        wl_display_flush_clients(display);
        wl_event_loop_dispatch(loop, 20);
        iterations++;
    }
    wl_display_flush_clients(display);
    wl_display_destroy(display);
    fprintf(stderr, "SRV: event loop finished after %d iterations\n", iterations);
    return NULL;
}

/* ------------------------------------------------------------------ client */
static void on_state_changed(void *data, struct org_kde_kwin_keystate *keystate,
                             uint32_t key, uint32_t state)
{
    (void) data;
    (void) keystate;
    atomic_store(&g_client_key, key);
    atomic_store(&g_client_state, state);
    atomic_fetch_add(&g_client_events, 1);
    fprintf(stderr, "CLI: stateChanged(key=%u, state=%u) received\n",
            (unsigned) key, (unsigned) state);
}

static const struct org_kde_kwin_keystate_listener k_listener = {on_state_changed};

static atomic_uint g_keystate_name = 0;

static void on_global(void *data, struct wl_registry *registry, uint32_t name,
                      const char *interface, uint32_t version)
{
    (void) data;
    (void) registry;
    if (strcmp(interface, IFACE_EXPECTED_NAME) == 0) {
        atomic_store(&g_keystate_name, name);
        atomic_store(&g_client_global_version, (int) version);
        atomic_fetch_add(&g_client_globals, 1);
        fprintf(stderr, "CLI: global %s name=%u version=%u\n",
                interface, (unsigned) name, (unsigned) version);
    }
}

static void on_global_remove(void *data, struct wl_registry *registry, uint32_t name)
{
    (void) data;
    (void) registry;
    (void) name;
}

static const struct wl_registry_listener k_registry_listener = {
    on_global, on_global_remove};

int main(int argc, char **argv)
{
    const char *xml_path;
    struct wl_display *client_display;
    struct wl_registry *registry;
    struct org_kde_kwin_keystate *keystate;
    pthread_t server_thread;
    int sockets[2];
    int fingerprint_ok = 0;
    unsigned long long fingerprint;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <keystate.xml from the installed package>\n", argv[0]);
        return 2;
    }
    xml_path = argv[1];

    /* 1. The protocol XML the package installs must be the exact file these
     *    bindings were generated from, otherwise the flow would be speaking a
     *    protocol the package does not actually deliver. */
    fingerprint = fnv1a64_file(xml_path, &fingerprint_ok);
    REQUIRE(fingerprint_ok, "the package's protocol XML is readable", 2);
    printf("E2E STEP installed XML fingerprint=0x%016llx, bindings built from 0x%016llx\n",
           fingerprint, (unsigned long long) KEYSTATE_XML_FNV1A64);
    REQUIRE(fingerprint == KEYSTATE_XML_FNV1A64,
            "the installed XML is the bindings' source", 3);

    /* 2. The generated wl_interface must describe the protocol as declared. */
    REQUIRE(strcmp(org_kde_kwin_keystate_interface.name, IFACE_EXPECTED_NAME) == 0,
            "generated interface name", 4);
    REQUIRE(org_kde_kwin_keystate_interface.version == IFACE_EXPECTED_VERSION,
            "generated interface version is 4", 5);
    REQUIRE(org_kde_kwin_keystate_interface.method_count == IFACE_EXPECTED_REQUESTS,
            "generated request count (fetchStates + destroy)", 6);
    REQUIRE(org_kde_kwin_keystate_interface.event_count == IFACE_EXPECTED_EVENTS,
            "generated event count (stateChanged)", 7);

    /* 3. Real connection: one end adopted by a server display, the other by a
     *    client display. */
    REQUIRE(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0,
            "socketpair(AF_UNIX, SOCK_STREAM)", 8);
    REQUIRE(pthread_create(&server_thread, NULL, server_main, &sockets[0]) == 0,
            "server thread started", 9);
    while (!atomic_load(&g_server_ready))
        sleep_ms(2);
    REQUIRE(atomic_load(&g_server_ok) != 0,
            "server display + wl_client_create + global registered", 10);

    client_display = wl_display_connect_to_fd(sockets[1]);
    REQUIRE(client_display != NULL, "wl_display_connect_to_fd(client end)", 11);
    registry = wl_display_get_registry(client_display);
    REQUIRE(registry != NULL, "wl_display_get_registry", 12);
    wl_registry_add_listener(registry, &k_registry_listener, NULL);
    REQUIRE(wl_display_roundtrip(client_display) >= 0,
            "roundtrip while fetching globals", 13);
    REQUIRE(atomic_load(&g_client_globals) >= 1,
            "client saw the org_kde_kwin_keystate global", 14);

    /* 4. Bind through the generated helper and issue the request. */
    keystate = wl_registry_bind(registry, atomic_load(&g_keystate_name),
                               &org_kde_kwin_keystate_interface,
                               (uint32_t) atomic_load(&g_client_global_version));
    REQUIRE(keystate != NULL, "wl_registry_bind(org_kde_kwin_keystate)", 15);
    org_kde_kwin_keystate_add_listener(keystate, &k_listener, NULL);
    org_kde_kwin_keystate_fetchStates(keystate);
    REQUIRE(wl_display_roundtrip(client_display) >= 0,
            "roundtrip carrying request and event", 16);

    REQUIRE(atomic_load(&g_server_binds) >= 1, "server bound the global", 17);
    REQUIRE(atomic_load(&g_server_requests) >= 1,
            "fetchStates() reached the server handler", 18);
    REQUIRE(atomic_load(&g_client_events) >= 1, "client received stateChanged", 19);
    REQUIRE(atomic_load(&g_client_key) == EXPECTED_KEY,
            "event key arrived unchanged (numlock=1)", 20);
    REQUIRE(atomic_load(&g_client_state) == EXPECTED_STATE,
            "event state arrived unchanged (locked=2)", 21);

    /* 5. The destructor request must reach its server-side handler too. */
    org_kde_kwin_keystate_destroy(keystate);
    REQUIRE(wl_display_roundtrip(client_display) >= 0,
            "roundtrip carrying the destroy request", 22);
    REQUIRE(atomic_load(&g_server_destroys) >= 1,
            "destroy() reached the server handler", 23);

    wl_registry_destroy(registry);
    wl_display_disconnect(client_display);
    atomic_store(&g_client_done, 1);
    pthread_join(server_thread, NULL);
    close(sockets[0]);
    close(sockets[1]);

    printf("E2E STEP client events=%d key=%u state=%u; server binds=%d fetchStates=%d "
           "destroys=%d\n",
           atomic_load(&g_client_events), atomic_load(&g_client_key),
           atomic_load(&g_client_state), atomic_load(&g_server_binds),
           atomic_load(&g_server_requests), atomic_load(&g_server_destroys));
    printf("E2E STEP payload delivered unchanged over the protocol generated from this "
           "package's XML=OK\n");
    return finish(0);
}
