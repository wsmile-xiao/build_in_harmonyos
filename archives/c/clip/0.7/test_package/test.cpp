#include <clip/api.h>
#include <cassert>
#include <cstdio>

int main() {
    clip_t* ctx = clip_init();
    assert(ctx != nullptr);
    clip_destroy(ctx);
    printf("clip test: OK\n");
    return 0;
}
