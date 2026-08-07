#include <aalib.h>

int main(void) {
    aa_context *context = aa_init(&stdout_d, &aa_defparams, NULL);
    if (context == 0) {
        return 1;
    }
    aa_close(context);
    return 0;
}