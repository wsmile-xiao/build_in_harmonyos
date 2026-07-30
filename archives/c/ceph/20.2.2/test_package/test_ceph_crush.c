#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "crush/builder.h"
#include "crush/crush.h"
#include "crush/hash.h"
#include "crush/mapper.h"

#define REQUIRE(condition)                                                       \
    do {                                                                         \
        if (!(condition)) {                                                      \
            fprintf(stderr, "consumer check failed at line %d: %s\n",           \
                    __LINE__, #condition);                                       \
            goto cleanup;                                                        \
        }                                                                        \
    } while (0)

int main(void)
{
    struct crush_map *map = NULL;
    struct crush_bucket *bucket;
    struct crush_rule *first_rule;
    struct crush_rule *rule;
    int items[4] = {0, 1, 2, 3};
    int bucket_weights[4] = {0x10000, 0x10000, 0x10000, 0x10000};
    __u32 device_weights[4] = {0x10000, 0x10000, 0x10000, 0x10000};
    int before[2];
    int after[2];
    int root_id;
    int excluded;
    int add_result;
    int rule_id;
    int status = 1;
    void *workspace = NULL;

    REQUIRE(
        crush_hash32_3(CRUSH_HASH_DEFAULT, 17, 29, 41) ==
        UINT32_C(0xfd449d65));

    map = crush_create();
    REQUIRE(map != NULL);
    bucket = crush_make_bucket(
        map, CRUSH_BUCKET_STRAW2, CRUSH_HASH_RJENKINS1,
        1, 4, items, bucket_weights);
    REQUIRE(bucket != NULL);
    add_result = crush_add_bucket(map, 0, bucket, &root_id);
    if (add_result != 0)
        crush_destroy_bucket(bucket);
    REQUIRE(add_result == 0);

    first_rule = crush_make_rule(3, CRUSH_RULE_TYPE_REPLICATED);
    REQUIRE(first_rule != NULL);
    crush_rule_set_step(first_rule, 0, CRUSH_RULE_TAKE, root_id, 0);
    crush_rule_set_step(
        first_rule, 1, CRUSH_RULE_CHOOSE_FIRSTN, CRUSH_CHOOSE_N, 0);
    crush_rule_set_step(first_rule, 2, CRUSH_RULE_EMIT, 0, 0);
    add_result = crush_add_rule(map, first_rule, -1);
    if (add_result < 0)
        crush_destroy_rule(first_rule);
    REQUIRE(add_result == 0);

    rule = crush_make_rule(3, CRUSH_RULE_TYPE_REPLICATED);
    REQUIRE(rule != NULL);
    crush_rule_set_step(rule, 0, CRUSH_RULE_TAKE, root_id, 0);
    crush_rule_set_step(
        rule, 1, CRUSH_RULE_CHOOSE_FIRSTN, CRUSH_CHOOSE_N, 0);
    crush_rule_set_step(rule, 2, CRUSH_RULE_EMIT, 0, 0);
    add_result = crush_add_rule(map, rule, -1);
    if (add_result < 0)
        crush_destroy_rule(rule);
    REQUIRE(add_result > 0);
    rule_id = add_result;
    crush_finalize(map);

    workspace = malloc(crush_work_size(map, 2));
    REQUIRE(workspace != NULL);
    crush_init_workspace(map, workspace);
    REQUIRE(
        crush_do_rule(
            map, rule_id, 2026, before, 2,
            device_weights, 4, workspace, NULL) == 2);
    REQUIRE(before[0] >= 0 && before[0] < 4);
    REQUIRE(before[1] >= 0 && before[1] < 4);
    REQUIRE(before[0] != before[1]);

    excluded = before[0];
    device_weights[excluded] = 0;
    crush_init_workspace(map, workspace);
    REQUIRE(
        crush_do_rule(
            map, rule_id, 2026, after, 2,
            device_weights, 4, workspace, NULL) == 2);
    REQUIRE(after[0] >= 0 && after[0] < 4);
    REQUIRE(after[1] >= 0 && after[1] < 4);
    REQUIRE(after[0] != excluded);
    REQUIRE(after[1] != excluded);
    REQUIRE(after[0] != after[1]);

    status = 0;
cleanup:
    free(workspace);
    if (map)
        crush_destroy(map);
    if (status == 0)
        puts("Ceph CRUSH consumer test passed");
    return status;
}
