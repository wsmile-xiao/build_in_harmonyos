#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ikcp.h"

#define MAX_PACKET_SIZE 2048
#define MAX_QUEUED_PACKETS 64
#define PAYLOAD_SIZE 4096

typedef struct {
    unsigned char data[MAX_PACKET_SIZE];
    int length;
} Packet;

typedef struct {
    Packet packets[MAX_QUEUED_PACKETS];
    int count;
} PacketQueue;

static int failures;

static void check(int condition, const char *description) {
    if (condition) {
        printf("ok - %s\n", description);
    } else {
        printf("FAILED - %s\n", description);
        failures++;
    }
}

static int output_callback(const char *buffer, int length, ikcpcb *kcp,
                           void *user) {
    PacketQueue *queue = (PacketQueue *)user;
    (void)kcp;
    if (length <= 0 || length > MAX_PACKET_SIZE ||
        queue->count >= MAX_QUEUED_PACKETS) {
        return -1;
    }
    memcpy(queue->packets[queue->count].data, buffer, (size_t)length);
    queue->packets[queue->count].length = length;
    queue->count++;
    return 0;
}

static int deliver(PacketQueue *queue, ikcpcb *peer) {
    int result = 0;
    for (int index = 0; index < queue->count; index++) {
        int rc = ikcp_input(peer, (const char *)queue->packets[index].data,
                            queue->packets[index].length);
        if (rc < 0) {
            result = rc;
        }
    }
    queue->count = 0;
    return result;
}

int main(void) {
    PacketQueue left_to_right = {0};
    PacketQueue right_to_left = {0};
    ikcpcb *left = ikcp_create(0x4b435031u, &left_to_right);
    ikcpcb *right = ikcp_create(0x4b435031u, &right_to_left);
    unsigned char payload[PAYLOAD_SIZE];
    unsigned char received[PAYLOAD_SIZE];
    int received_length = -1;
    int left_to_right_result = 0;
    int right_to_left_result = 0;

    check(left != NULL, "ikcp_create left endpoint");
    check(right != NULL, "ikcp_create right endpoint");
    if (left == NULL || right == NULL) {
        if (left != NULL) {
            ikcp_release(left);
        }
        if (right != NULL) {
            ikcp_release(right);
        }
        return 1;
    }

    left->output = output_callback;
    right->output = output_callback;

    check(ikcp_nodelay(left, 1, 10, 2, 1) == 0,
          "configure left endpoint");
    check(ikcp_nodelay(right, 1, 10, 2, 1) == 0,
          "configure right endpoint");
    check(ikcp_wndsize(left, 64, 64) == 0, "set left window size");
    check(ikcp_wndsize(right, 64, 64) == 0, "set right window size");
    check(ikcp_setmtu(left, 1200) == 0, "set left MTU");
    check(ikcp_setmtu(right, 1200) == 0, "set right MTU");

    for (int index = 0; index < PAYLOAD_SIZE; index++) {
        payload[index] = (unsigned char)((index * 37 + 11) & 0xff);
    }
    check(ikcp_send(left, (const char *)payload, PAYLOAD_SIZE) >= 0,
          "send fragmented payload");

    for (IUINT32 now = 0; now <= 5000 && received_length < 0; now += 10) {
        ikcp_update(left, now);
        if (deliver(&left_to_right, right) != 0) {
            left_to_right_result = -1;
        }
        ikcp_update(right, now);
        if (deliver(&right_to_left, left) != 0) {
            right_to_left_result = -1;
        }
        received_length = ikcp_recv(right, (char *)received, PAYLOAD_SIZE);
    }

    check(left_to_right_result == 0,
          "deliver left-to-right packet batches");
    check(right_to_left_result == 0,
          "deliver right-to-left packet batches");
    check(received_length == PAYLOAD_SIZE, "receive complete payload");
    if (received_length == PAYLOAD_SIZE) {
        check(memcmp(received, payload, PAYLOAD_SIZE) == 0,
              "received payload matches sent payload");
    }

    ikcp_release(left);
    ikcp_release(right);

    if (failures != 0) {
        printf("%d consumer check(s) FAILED\n", failures);
        return 1;
    }
    printf("all KCP consumer checks passed\n");
    return 0;
}
