/* test_package consumer test for iqueue 2.2.
 * Uses only the installed public API (iqueue.h) to exercise a broker-style
 * flow: new_iqueue -> trysend/tryrecv -> delete_iqueue.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "iqueue.h"

int main(void) {
    iqueue_t *queue = NULL;
    int rc;

    rc = new_iqueue(&queue, 16u);
    if (rc != 0) {
        fprintf(stderr, "new_iqueue failed: %d\n", rc);
        return 1;
    }

    {
        static char msga[] = "hello-iqueue-a";
        static char msgb[] = "hello-iqueue-b";
        void *out = NULL;

        rc = trysend_iqueue(queue, msgb);
        if (rc != 0) {
            fprintf(stderr, "trysend_iqueue(b) failed: %d\n", rc);
            return 1;
        }
        rc = trysend_iqueue(queue, msga);
        if (rc != 0) {
            fprintf(stderr, "trysend_iqueue(a) failed: %d\n", rc);
            return 1;
        }
        rc = tryrecv_iqueue(queue, &out);
        if (rc != 0 || out == NULL) {
            fprintf(stderr, "tryrecv_iqueue failed: %d\n", rc);
            return 1;
        }
        if (strcmp((char *)out, "hello-iqueue-b") != 0) {
            fprintf(stderr, "unexpected payload: %s\n", (char *)out);
            return 1;
        }
        printf("iqueue consumer test: PASS (payload=%s, size=%u)\n",
               (char *)out, size_iqueue(queue));
    }

    close_iqueue(queue);
    rc = delete_iqueue(&queue);
    if (rc != 0 || queue != NULL) {
        fprintf(stderr, "delete_iqueue failed: %d\n", rc);
        return 1;
    }

    printf("iqueue test_package: OK\n");
    return 0;
}