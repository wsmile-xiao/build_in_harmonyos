#include <slirp/libslirp.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct ConsumerState {
    Slirp *initialized;
    unsigned int timer_count;
    unsigned int registered_socket_count;
    unsigned int poll_index;
} ConsumerState;

static slirp_ssize_t send_packet(const void *buf, size_t len, void *opaque) {
    (void)buf;
    (void)opaque;
    return (slirp_ssize_t)len;
}

static void guest_error(const char *msg, void *opaque) {
    (void)msg;
    (void)opaque;
}

static int64_t clock_get_ns(void *opaque) {
    (void)opaque;
    return 0;
}

static void *timer_new_opaque(
    SlirpTimerId id,
    void *cb_opaque,
    void *opaque
) {
    ConsumerState *state = (ConsumerState *)opaque;
    (void)id;
    state->timer_count++;
    return cb_opaque;
}

static void timer_free(void *timer, void *opaque) {
    ConsumerState *state = (ConsumerState *)opaque;
    (void)timer;
    if (state->timer_count > 0) {
        state->timer_count--;
    }
}

static void timer_mod(void *timer, int64_t expire_time, void *opaque) {
    (void)timer;
    (void)expire_time;
    (void)opaque;
}

static void register_poll_socket(slirp_os_socket socket, void *opaque) {
    ConsumerState *state = (ConsumerState *)opaque;
    (void)socket;
    state->registered_socket_count++;
}

static void unregister_poll_socket(slirp_os_socket socket, void *opaque) {
    ConsumerState *state = (ConsumerState *)opaque;
    (void)socket;
    if (state->registered_socket_count > 0) {
        state->registered_socket_count--;
    }
}

static void notify(void *opaque) {
    (void)opaque;
}

static void init_completed(Slirp *slirp, void *opaque) {
    ConsumerState *state = (ConsumerState *)opaque;
    state->initialized = slirp;
}

static int add_poll(int fd, int events, void *opaque) {
    ConsumerState *state = (ConsumerState *)opaque;
    (void)fd;
    (void)events;
    return (int)state->poll_index++;
}

static int get_revents(int index, void *opaque) {
    (void)index;
    (void)opaque;
    return 0;
}

int main(void) {
    ConsumerState state = {0};
    SlirpConfig config = {0};
    SlirpCb callbacks = {0};
    uint32_t timeout = UINT32_MAX;
    const char *version = slirp_version_string();

    if (version == NULL || strcmp(version, "4.9.3") != 0) {
        fprintf(stderr, "unexpected libslirp version: %s\n", version);
        return 1;
    }

    config.version = SLIRP_CONFIG_VERSION_MAX;
    config.restricted = true;
    config.in_enabled = false;
    config.vnetwork.s_addr = htonl(0x0a000200);
    config.vnetmask.s_addr = htonl(0xffffff00);
    config.vhost.s_addr = htonl(0x0a000202);
    config.vdhcp_start.s_addr = htonl(0x0a00020f);
    config.vnameserver.s_addr = htonl(0x0a000203);
    config.disable_host_loopback = true;
    config.disable_dns = true;
    config.disable_dhcp = true;

    callbacks.send_packet = send_packet;
    callbacks.guest_error = guest_error;
    callbacks.clock_get_ns = clock_get_ns;
    callbacks.timer_free = timer_free;
    callbacks.timer_mod = timer_mod;
    callbacks.register_poll_socket = register_poll_socket;
    callbacks.unregister_poll_socket = unregister_poll_socket;
    callbacks.notify = notify;
    callbacks.init_completed = init_completed;
    callbacks.timer_new_opaque = timer_new_opaque;

    Slirp *slirp = slirp_new(&config, &callbacks, &state);
    if (slirp == NULL || state.initialized != slirp) {
        fprintf(stderr, "failed to create and initialize the slirp context\n");
        return 1;
    }
    if (slirp_state_version() < 0) {
        fprintf(stderr, "invalid slirp state version\n");
        slirp_cleanup(slirp);
        return 1;
    }

    slirp_pollfds_fill(slirp, &timeout, add_poll, &state);
    slirp_pollfds_poll(slirp, 0, get_revents, &state);
    slirp_cleanup(slirp);

    if (state.timer_count != 0 || state.registered_socket_count != 0) {
        fprintf(stderr, "libslirp cleanup left callbacks registered\n");
        return 1;
    }

    printf(
        "PASS libslirp consumer version=%s poll_entries=%u\n",
        version,
        state.poll_index
    );
    return 0;
}
