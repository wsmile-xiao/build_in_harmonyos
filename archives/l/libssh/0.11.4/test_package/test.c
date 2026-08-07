#include <stdio.h>
#include <libssh/libssh.h>

int main(void) {
    /* Initialize libssh — calls ssh_init() which sets up crypto backend */
    int rc = ssh_init();
    if (rc != SSH_OK) {
        fprintf(stderr, "ssh_init failed: %d\n", rc);
        return 1;
    }

    /* Print version to verify the library is linked correctly */
    printf("libssh version: %s\n", ssh_version(0));

    /* Clean up */
    ssh_finalize();

    printf("test libssh 0.11.4: OK\n");
    return 0;
}
