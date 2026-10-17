#include <stdio.h>
#include <termpaint_input.h>

int main(void) {
    termpaint_input *ctx = termpaint_input_new();
    if (ctx != NULL) {
        printf("termpaint_input_new: OK (non-null)\n");
        termpaint_input_free(ctx);
        printf("termpaint_input_free: OK\n");
        return 0;
    } else {
        printf("termpaint_input_new: FAIL (null)\n");
        return 1;
    }
}
