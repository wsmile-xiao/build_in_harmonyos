/*
 * C API ports of four CRUSH scenarios from src/test/crush/crush.cc.
 * The topology, rule, input count, and mapping semantics match upstream;
 * only the Ceph C++ wrapper and GoogleTest harness are replaced.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "crush/builder.h"
#include "crush/crush.h"
#include "crush/hash.h"
#include "crush/mapper.h"

#define MAX_DEVICES 32
#define MAX_RACKS 4
#define MAX_HOSTS 4
#define MAX_OSDS_PER_HOST 4

static const char *current_scenario;
static unsigned long long assertion_count;

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++assertion_count;                                                      \
        if (!(condition)) {                                                     \
            fprintf(stderr, "[FAIL] %s:%d: %s\n", current_scenario, __LINE__,   \
                    #condition);                                                \
            status = 1;                                                         \
            goto cleanup;                                                       \
        }                                                                       \
    } while (0)

struct crush_fixture {
    struct crush_map *map;
    void *workspace;
    int device_count;
    int rule_id;
};

static void fixture_destroy(struct crush_fixture *fixture)
{
    free(fixture->workspace);
    if (fixture->map)
        crush_destroy(fixture->map);
    memset(fixture, 0, sizeof(*fixture));
}

static int fixture_add_bucket(
    struct crush_fixture *fixture,
    int algorithm,
    int type,
    int size,
    int *items,
    int *weights,
    int *bucket_id)
{
    struct crush_bucket *bucket = crush_make_bucket(
        fixture->map, algorithm, CRUSH_HASH_RJENKINS1,
        type, size, items, weights);
    int result;

    if (!bucket)
        return 1;
    result = crush_add_bucket(fixture->map, 0, bucket, bucket_id);
    if (result != 0)
        crush_destroy_bucket(bucket);
    return result != 0;
}

static int fixture_finish(
    struct crush_fixture *fixture,
    int root_id,
    int rule_type,
    int choose_operation,
    int choose_type,
    int max_result)
{
    struct crush_rule *rule;
    int rule_length = choose_operation == CRUSH_RULE_CHOOSELEAF_FIRSTN ? 4 : 3;
    int step = 0;
    int result;

    rule = crush_make_rule(rule_length, rule_type);
    if (!rule)
        return 1;
    if (choose_operation == CRUSH_RULE_CHOOSELEAF_FIRSTN) {
        crush_rule_set_step(
            rule, step++, CRUSH_RULE_SET_CHOOSELEAF_TRIES, 0, 0);
    }
    crush_rule_set_step(rule, step++, CRUSH_RULE_TAKE, root_id, 0);
    crush_rule_set_step(
        rule, step++, choose_operation, CRUSH_CHOOSE_N, choose_type);
    crush_rule_set_step(rule, step, CRUSH_RULE_EMIT, 0, 0);

    result = crush_add_rule(fixture->map, rule, -1);
    if (result < 0) {
        crush_destroy_rule(rule);
        return 1;
    }
    fixture->rule_id = result;

    crush_finalize(fixture->map);
    fixture->workspace = malloc(
        crush_work_size(fixture->map, max_result));
    if (!fixture->workspace)
        return 1;
    crush_init_workspace(fixture->map, fixture->workspace);
    return 0;
}

static int fixture_init_firstn(
    struct crush_fixture *fixture,
    int rack_count,
    int hosts_per_rack,
    int osds_per_host,
    int max_result)
{
    int rack_ids[MAX_RACKS];
    int rack_weights[MAX_RACKS];
    int next_device = 0;
    int rack;

    memset(fixture, 0, sizeof(*fixture));
    if (rack_count > MAX_RACKS ||
        hosts_per_rack > MAX_HOSTS ||
        osds_per_host > MAX_OSDS_PER_HOST) {
        return 1;
    }
    fixture->device_count = rack_count * hosts_per_rack * osds_per_host;
    if (fixture->device_count > MAX_DEVICES)
        return 1;

    fixture->map = crush_create();
    if (!fixture->map)
        return 1;

    for (rack = 0; rack < rack_count; ++rack) {
        int host_ids[MAX_HOSTS];
        int host_weights[MAX_HOSTS];
        int host;

        for (host = 0; host < hosts_per_rack; ++host) {
            int osd_ids[MAX_OSDS_PER_HOST];
            int osd_weights[MAX_OSDS_PER_HOST];
            int osd;

            for (osd = 0; osd < osds_per_host; ++osd) {
                osd_ids[osd] = next_device++;
                osd_weights[osd] = 0x10000;
            }
            if (fixture_add_bucket(
                    fixture, CRUSH_BUCKET_STRAW, 1, osds_per_host,
                    osd_ids, osd_weights, &host_ids[host]) != 0) {
                fixture_destroy(fixture);
                return 1;
            }
            host_weights[host] = osds_per_host * 0x10000;
        }

        if (fixture_add_bucket(
                fixture, CRUSH_BUCKET_STRAW, 3, hosts_per_rack,
                host_ids, host_weights, &rack_ids[rack]) != 0) {
            fixture_destroy(fixture);
            return 1;
        }
        rack_weights[rack] =
            hosts_per_rack * osds_per_host * 0x10000;
    }

    {
        int root_id;

        if (fixture_add_bucket(
                fixture, CRUSH_BUCKET_STRAW, 5, rack_count,
                rack_ids, rack_weights, &root_id) != 0 ||
            fixture_finish(
                fixture, root_id, CRUSH_RULE_TYPE_ERASURE,
                CRUSH_RULE_CHOOSELEAF_FIRSTN, 1, max_result) != 0) {
            fixture_destroy(fixture);
            return 1;
        }
    }
    return 0;
}

static int fixture_init_straw2(
    struct crush_fixture *fixture,
    int device_count,
    int *bucket_weights)
{
    int items[MAX_DEVICES];
    int root_id;
    int index;

    memset(fixture, 0, sizeof(*fixture));
    if (device_count > MAX_DEVICES)
        return 1;
    fixture->device_count = device_count;
    fixture->map = crush_create();
    if (!fixture->map)
        return 1;

    for (index = 0; index < device_count; ++index)
        items[index] = index;
    if (fixture_add_bucket(
            fixture, CRUSH_BUCKET_STRAW2, 2, device_count,
            items, bucket_weights, &root_id) != 0 ||
        fixture_finish(
            fixture, root_id, CRUSH_RULE_TYPE_REPLICATED,
            CRUSH_RULE_CHOOSE_FIRSTN, 0, 1) != 0) {
        fixture_destroy(fixture);
        return 1;
    }
    return 0;
}

static int run_rule(
    struct crush_fixture *fixture,
    int input,
    int *result,
    int result_max,
    const __u32 *weights)
{
    crush_init_workspace(fixture->map, fixture->workspace);
    return crush_do_rule(
        fixture->map, fixture->rule_id, input, result, result_max,
        weights, fixture->device_count, fixture->workspace, NULL);
}

static int test_firstn_basic(void)
{
    struct crush_fixture fixture = {0};
    __u32 weights[MAX_DEVICES];
    int status = 0;
    int input;
    int index;

    if (fixture_init_firstn(&fixture, 3, 3, 3, 3) != 0)
        return 1;
    for (index = 0; index < fixture.device_count; ++index)
        weights[index] = 0x10000;

    for (input = 0; input < 100; ++input) {
        int result[3];
        int left;
        int right;

        CHECK(run_rule(&fixture, input, result, 3, weights) == 3);
        for (left = 0; left < 3; ++left)
            CHECK(result[left] >= 0 && result[left] < fixture.device_count);
        for (left = 0; left < 3; ++left)
            for (right = left + 1; right < 3; ++right)
                CHECK(result[left] != result[right]);
    }

cleanup:
    fixture_destroy(&fixture);
    return status;
}

static int test_firstn_toosmall(void)
{
    struct crush_fixture fixture = {0};
    __u32 weights[MAX_DEVICES];
    int status = 0;
    int input;
    int index;

    if (fixture_init_firstn(&fixture, 1, 3, 1, 5) != 0)
        return 1;
    for (index = 0; index < fixture.device_count; ++index)
        weights[index] = 0x10000;

    for (input = 0; input < 100; ++input) {
        int result[5];
        int count = run_rule(&fixture, input, result, 5, weights);
        int left;
        int right;

        CHECK(count == 3);
        for (left = 0; left < count; ++left)
            CHECK(result[left] >= 0 && result[left] < fixture.device_count);
        for (left = 0; left < count; ++left)
            for (right = left + 1; right < count; ++right)
                CHECK(result[left] != result[right]);
    }

cleanup:
    fixture_destroy(&fixture);
    return status;
}

static int test_firstn_single_out_first(void)
{
    struct crush_fixture fixture = {0};
    int status = 0;
    int input;

    if (fixture_init_firstn(&fixture, 3, 3, 3, 3) != 0)
        return 1;

    for (input = 0; input < 1000; ++input) {
        __u32 weights[MAX_DEVICES];
        int before[3];
        int after[3];
        int excluded;
        int left;
        int right;

        for (left = 0; left < fixture.device_count; ++left)
            weights[left] = 0x10000;

        CHECK(run_rule(&fixture, input, before, 3, weights) == 3);
        for (left = 0; left < 3; ++left)
            CHECK(before[left] >= 0 && before[left] < fixture.device_count);
        for (left = 0; left < 3; ++left)
            for (right = left + 1; right < 3; ++right)
                CHECK(before[left] != before[right]);

        excluded = before[0];
        weights[excluded] = 0;
        CHECK(run_rule(&fixture, input, after, 3, weights) == 3);
        for (left = 0; left < 3; ++left) {
            CHECK(after[left] >= 0 && after[left] < fixture.device_count);
            CHECK(after[left] != excluded);
        }
        for (left = 0; left < 3; ++left)
            for (right = left + 1; right < 3; ++right)
                CHECK(after[left] != after[right]);
    }

cleanup:
    fixture_destroy(&fixture);
    return status;
}

static double calculate_adjusted_stddev(
    const int *weights,
    const int *counts,
    int device_count,
    int total)
{
    double total_weight = 0.0;
    double adjusted_total = 0.0;
    double variance = 0.0;
    double expected = (double)total / (double)device_count;
    double average_weight;
    int index;

    for (index = 0; index < device_count; ++index)
        total_weight += (double)weights[index] / (double)0x10000;
    average_weight = total_weight / (double)device_count;

    for (index = 0; index < device_count; ++index) {
        double weight = (double)weights[index] / (double)0x10000;
        double adjusted = (double)counts[index] * average_weight / weight;

        variance += (adjusted - expected) * (adjusted - expected);
        adjusted_total += adjusted;
    }
    if (adjusted_total <= 0.0)
        return NAN;
    return sqrt(variance / (double)device_count);
}

static int test_straw2_distribution(void)
{
    static const double steps[] = {1.0, 1.25, 1.5, 1.75};
    const int device_count = 15;
    const int mapping_count = 1000000;
    struct crush_fixture fixture = {0};
    int status = 0;
    int step_index;

    for (step_index = 0;
         step_index < (int)(sizeof(steps) / sizeof(steps[0]));
         ++step_index) {
        __u32 device_weights[MAX_DEVICES];
        int bucket_weights[MAX_DEVICES];
        int counts[MAX_DEVICES] = {0};
        int weight = 0x10000;
        int input;
        int index;
        int total_seen = 0;
        double stddev;

        for (index = 0; index < device_count; ++index) {
            bucket_weights[index] = weight;
            device_weights[index] = 0x10000;
            weight = (int)((double)weight * steps[step_index]);
        }
        if (fixture_init_straw2(
                &fixture, device_count, bucket_weights) != 0) {
            return 1;
        }

        for (input = 0; input < mapping_count; ++input) {
            int result[1];

            CHECK(
                run_rule(
                    &fixture, input, result, 1, device_weights) == 1);
            CHECK(result[0] >= 0 && result[0] < device_count);
            ++counts[result[0]];
        }

        for (index = 0; index < device_count; ++index) {
            CHECK(counts[index] > 0);
            total_seen += counts[index];
        }
        CHECK(total_seen == mapping_count);
        stddev = calculate_adjusted_stddev(
            bucket_weights, counts, device_count, mapping_count);
        CHECK(isfinite(stddev));
        printf(
            "[INFO] straw2 step=%.2f stddev=%.3f\n",
            steps[step_index], stddev);

        fixture_destroy(&fixture);
    }

cleanup:
    fixture_destroy(&fixture);
    return status;
}

struct scenario {
    const char *name;
    int (*run)(void);
};

int main(int argc, char **argv)
{
    static const struct scenario scenarios[] = {
        {"firstn_basic", test_firstn_basic},
        {"firstn_toosmall", test_firstn_toosmall},
        {"firstn_single_out_first", test_firstn_single_out_first},
        {"straw2_distribution", test_straw2_distribution},
    };
    size_t index;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <scenario>\n", argv[0]);
        return 2;
    }
    current_scenario = argv[1];
    for (index = 0;
         index < sizeof(scenarios) / sizeof(scenarios[0]);
         ++index) {
        if (strcmp(argv[1], scenarios[index].name) == 0) {
            int result = scenarios[index].run();

            if (result == 0) {
                printf(
                    "[PASS] %s assertions=%llu\n",
                    argv[1], assertion_count);
            }
            return result;
        }
    }
    fprintf(stderr, "unknown scenario: %s\n", argv[1]);
    return 2;
}
