#include <sentry.h>

int main(void) {
    sentry_options_t *options = sentry_options_new();
    if (options == NULL) {
        return 1;
    }
    sentry_options_free(options);
    return 0;
}
