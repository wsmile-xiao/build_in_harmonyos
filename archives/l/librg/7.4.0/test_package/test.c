/* test.c — librg 7.4.0 consumer test (HarmonyOS)
 *
 * Consumer-side test: compiles a TU that defines LIBRG_IMPL (the amalgamated
 * implementation) and exercises the world/entity/query/packing API, asserting
 * on results.  This is the R34 substantive test — it really calls librg.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#define LIBRG_IMPL
#include <librg.h>

static int g_failures = 0;
#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (cond) {                                                         \
            printf("  [PASS] %s\n", msg);                                   \
        } else {                                                            \
            printf("  [FAIL] %s\n", msg);                                   \
            g_failures++;                                                   \
        }                                                                   \
    } while (0)

static int32_t handler_create(librg_world *w, librg_event *e) {
    char *buffer = librg_event_buffer_get(w, e);
    const char *payload = "ohos-create";
    size_t n = strlen(payload);
    if ((int32_t)n > librg_event_size_get(w, e)) return LIBRG_WRITE_REJECT;
    memcpy(buffer, payload, n);
    return (int32_t)n;
}

static int32_t handler_update(librg_world *w, librg_event *e) {
    char *buffer = librg_event_buffer_get(w, e);
    int32_t v = 0x4F484F53; /* "OHOS" little-endian */
    if ((int32_t)sizeof(v) > librg_event_size_get(w, e)) return LIBRG_WRITE_REJECT;
    memcpy(buffer, &v, sizeof(v));
    return (int32_t)sizeof(v);
}

static int32_t handler_remove(librg_world *w, librg_event *e) {
    (void)w; (void)e;
    return 0;
}

static int32_t handler_read_create(librg_world *w, librg_event *e) {
    char *buffer = librg_event_buffer_get(w, e);
    CHECK(strncmp(buffer, "ohos-create", 11) == 0, "read create payload matches write payload");
    return 0;
}

static int32_t handler_read_update(librg_world *w, librg_event *e) {
    char *buffer = librg_event_buffer_get(w, e);
    int32_t v = 0;
    memcpy(&v, buffer, sizeof(v));
    CHECK(v == 0x4F484F53, "read update payload matches write payload");
    return 0;
}

static int32_t handler_read_remove(librg_world *w, librg_event *e) {
    (void)w; (void)e;
    return 0;
}

int main(void) {
    printf("> librg consumer test (HarmonyOS aarch64)\n");

    uint32_t ver = librg_version();
    CHECK(ver == 7004000, "librg_version() == 7004000 (7.4.0)");

    librg_world *world = librg_world_create();
    CHECK(world != NULL, "librg_world_create() returns non-NULL");
    CHECK(librg_world_valid(world) != 0, "created world is valid");

    CHECK(librg_config_chunkamount_set(world, 4, 1, 1) == 0, "chunkamount set ok");
    CHECK(librg_config_chunksize_set(world, 8, 8, 8) == 0, "chunksize set ok");

    librg_event_set(world, LIBRG_WRITE_CREATE, handler_create);
    librg_event_set(world, LIBRG_WRITE_UPDATE, handler_update);
    librg_event_set(world, LIBRG_WRITE_REMOVE, handler_remove);
    librg_event_set(world, LIBRG_READ_CREATE, handler_read_create);
    librg_event_set(world, LIBRG_READ_UPDATE, handler_read_update);
    librg_event_set(world, LIBRG_READ_REMOVE, handler_read_remove);

    const int64_t entities[] = { 1, 2, 3, 4, 5, 6 };
    for (int i = 0; i < 6; ++i) {
        librg_entity_track(world, entities[i]);
        librg_entity_chunk_set(world, entities[i], i);
    }
    CHECK(librg_entity_count(world) == 6, "entity_count == 6");

    const int64_t owner = 777;
    librg_entity_track(world, owner);
    librg_entity_chunk_set(world, owner, 1);
    librg_entity_owner_set(world, owner, owner);
    CHECK(librg_entity_owner_get(world, owner) == owner, "owner get round-trip");

    int64_t ids[16];
    size_t amount = 16;
    CHECK(librg_world_fetch_chunk(world, 1, ids, &amount) == 0 && amount == 2,
          "fetch_chunk(1) returns 2 entities");

    amount = 16;
    CHECK(librg_world_query(world, owner, 1, ids, &amount) == 0 && amount == 4,
          "owner query radius 1 sees 4 entities");

    char buffer[512] = {0};
    size_t total = sizeof(buffer);
    CHECK(librg_world_write(world, owner, 1, buffer, &total, NULL) == 0 && total > 0,
          "librg_world_write returns packed data");
    CHECK(librg_world_read(world, owner, buffer, total, NULL) == 0,
          "librg_world_read consumes packed data");

    CHECK(librg_entity_untrack(world, entities[0]) == 0, "entity untracked");
    CHECK(librg_world_destroy(world) == 0, "world destroyed");

    if (g_failures == 0) {
        printf("> RESULT: ALL LIBRG CONSUMER TESTS PASSED\n");
        return 0;
    }
    printf("> RESULT: %d FAILURE(S)\n", g_failures);
    return 1;
}