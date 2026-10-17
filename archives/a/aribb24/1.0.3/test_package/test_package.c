#include <aribb24/aribb24.h>
#include <stdio.h>

int main(void) {
    arib_instance_t *instance = arib_instance_new(NULL);
    if (instance == NULL) {
        fprintf(stderr, "Failed to create aribb24 instance\n");
        return 1;
    }
    arib_instance_destroy(instance);
    printf("aribb24 test passed\n");
    return 0;
}
