#include <s2n.h>
#include <stdio.h>

int main(void) {
    if (s2n_init() != 0) {
        fprintf(stderr, "s2n_init failed\n");
        return 1;
    }

    struct s2n_config *config = s2n_config_new();
    if (config == NULL) {
        fprintf(stderr, "s2n_config_new failed\n");
        s2n_cleanup();
        return 1;
    }

    printf("s2n-tls 1.7.6: s2n_init() and s2n_config_new() succeeded\n");

    s2n_config_free(config);
    s2n_cleanup();
    return 0;
}
