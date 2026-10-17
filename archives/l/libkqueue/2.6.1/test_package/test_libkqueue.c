#include <sys/event.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int kq = kqueue();
    if (kq < 0) {
        fprintf(stderr, "FAIL: kqueue() returned negative\n");
        return 1;
    }
    printf("OK: kqueue() = %d\n", kq);
    close(kq);
    return 0;
}
