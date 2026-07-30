#include <assert.h>
#include <stdio.h>

#include <libxsmm.h>

int main(void) {
    const char* target;
    void* memory;

    libxsmm_init();
    target = libxsmm_get_target_arch();
    assert(target != NULL && target[0] != '\0');

    memory = libxsmm_malloc(64);
    assert(memory != NULL);
    libxsmm_free(memory);
    libxsmm_finalize();

    puts("libxsmm consumer test passed");
    return 0;
}
