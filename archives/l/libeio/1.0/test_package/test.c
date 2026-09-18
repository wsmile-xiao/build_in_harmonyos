#include <stdio.h>
#include <stdlib.h>

/* libeio public API: eio.h (public header, installed to include/) */
#include <eio.h>

/* eio 请求完成回调（公开 API eio_nop 的 cb 参数，eio_cb 为 int(*)(eio_req*)） */
static int req_cb(eio_req *req) {
    (void)req;
    return 0;
}

int main(void) {
    /* eio_init: initialize the libeio async I/O library (public API). */
    int rc = eio_init(0, 0);
    if (rc != 0) {
        fprintf(stderr, "eio_init failed: rc=%d\n", rc);
        return 1;
    }
    fprintf(stderr, "eio_init: OK (rc=%d)\n", rc);

    /* Worker threads must be running after eio_init (public API): */
    unsigned int nthreads = eio_nthreads();
    fprintf(stderr, "eio_nthreads=%u\n", nthreads);

    /* Synchronous working-directory open/close (public API): */
    eio_wd wd = eio_wd_open_sync(EIO_CWD, ".");
    if (wd == EIO_INVALID_WD) {
        fprintf(stderr, "eio_wd_open_sync failed\n");
        return 1;
    }
    fprintf(stderr, "eio_wd_open_sync: OK (wd=%d)\n", (int)wd);
    eio_wd_close_sync(wd);

    /* Submit a no-op async request and poll for its completion
     * (public API eio_nop + eio_poll): */
    eio_req *req = eio_nop(0, req_cb, 0);
    if (!req) {
        fprintf(stderr, "eio_nop failed\n");
        return 1;
    }
    int pending = 0;
    while (eio_npending() > 0) {
        eio_poll();
        if (++pending > 100000) {
            fprintf(stderr, "eio_poll timeout\n");
            return 1;
        }
    }
    fprintf(stderr, "eio_nop+eio_poll: OK (req result=%d)\n", req->result);

    printf("test libeio 1.0: eio_init/eio_wd/eio_nop OK\n");
    return 0;
}