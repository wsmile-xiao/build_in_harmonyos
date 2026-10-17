#include <canard/canard.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Consumer smoke test for libcanard (R34: really exercises the library).
 * TAP-style output: each CHECK prints "ok N name" or "not ok N name".
 * The test_package conanfile counts the "ok" lines (16 checks total).
 */
static int g_n = 0;

#define CHECK(cond, name)                               \
    do {                                                \
        ++g_n;                                          \
        if (!(cond)) {                                  \
            printf("not ok %d %s\n", g_n, name);        \
            return 1;                                   \
        }                                               \
        printf("ok %d %s\n", g_n, name);               \
    } while (0)

static void* mem_alloc(CanardInstance* ins, size_t amount)
{
    (void) ins;
    return malloc(amount);
}

static void mem_free(CanardInstance* ins, void* pointer)
{
    (void) ins;
    free(pointer);
}

int main(void)
{
    /* T1: library version macros. */
    CHECK(CANARD_VERSION_MAJOR == 3, "version-major");
    CHECK(CANARD_VERSION_MINOR == 2, "version-minor");

    /* T2: instance init defaults. */
    CanardInstance ins = canardInit(mem_alloc, mem_free);
    CHECK(ins.node_id == CANARD_NODE_ID_UNSET, "init-node-id-unset");
    CHECK(ins.user_reference == NULL, "init-user-reference-null");

    /* T3: TX push of a single-frame message transfer. */
    ins.node_id = 42;
    CanardTxQueue queue = canardTxInit(16, CANARD_MTU_CAN_CLASSIC);
    static const uint8_t payload[] = {0xDE, 0xAD, 0xBE, 0xEF};
    CanardTransferMetadata meta;
    meta.priority = CanardPriorityNominal;
    meta.transfer_kind = CanardTransferKindMessage;
    meta.port_id = 1234;
    meta.remote_node_id = CANARD_NODE_ID_UNSET;
    meta.transfer_id = 0;
    const int32_t push_rc =
        canardTxPush(&queue, &ins, 1000000U, &meta, sizeof(payload), payload);
    CHECK(push_rc > 0, "tx-push-frames");

    /* T4: TX queue peek/pop drains exactly the enqueued frames. */
    CHECK(canardTxPeek(&queue) != NULL, "tx-peek-nonempty");
    size_t drained = 0;
    const CanardTxQueueItem* item = NULL;
    while ((item = canardTxPeek(&queue)) != NULL) {
        canardTxPop(&queue, item);
        ++drained;
    }
    CHECK(drained == (size_t) push_rc, "tx-drain-count");
    CHECK(canardTxPeek(&queue) == NULL, "tx-queue-empty");

    /* T5: RX subscription lifecycle. */
    CanardRxSubscription sub;
    (void) memset(&sub, 0, sizeof(sub));
    CHECK(canardRxSubscribe(&ins, CanardTransferKindMessage, 1234, 64, 1000000U, &sub) > 0,
          "rx-subscribe");

    /* T6: subscription query (API added in 3.2). */
    CanardRxSubscription* found = NULL;
    CHECK(canardRxGetSubscription(&ins, CanardTransferKindMessage, 1234, &found) == 1,
          "rx-get-exists");
    CHECK((found != NULL) && (found->port_id == 1234), "rx-get-port");

    /* T7: unsubscribe removes it. */
    CHECK(canardRxUnsubscribe(&ins, CanardTransferKindMessage, 1234) == 1, "rx-unsubscribe");
    CHECK(canardRxGetSubscription(&ins, CanardTransferKindMessage, 1234, &found) == 0,
          "rx-get-absent");

    /* T8: acceptance filter helpers. */
    const CanardFilter fa = canardMakeFilterForSubject(1234);
    CHECK(fa.extended_mask != 0U, "filter-subject-mask");
    const CanardFilter fc = canardConsolidateFilters(&fa, &fa);
    CHECK((fc.extended_can_id == fa.extended_can_id) &&
              (fc.extended_mask == fa.extended_mask),
          "filter-consolidate-self");
    const CanardFilter fb = canardMakeFilterForService(987, 42);
    CHECK(fb.extended_mask != 0U, "filter-service-mask");

    printf("libcanard smoke test passed\n");
    return 0;
}
