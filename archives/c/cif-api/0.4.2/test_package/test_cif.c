/* cif-api test_package consumer probe.
 * Verifies libcif links and that a cif container can be created.
 */
#include <cif.h>
#include <stdio.h>

int main(void)
{
    cif_tp *container = NULL;
    int status = cif_create(&container);
    if (status != CIF_OK || container == NULL) {
        fprintf(stderr, "FAIL: cif_create failed (status %d)\n", status);
        return 1;
    }
    /* Reaching here proves libcif linked + initialized. */
    printf("cif-api OK (container created)\n");
    cif_destroy(container);
    return 0;
}
