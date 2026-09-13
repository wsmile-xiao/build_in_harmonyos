/* libgudev test_package consumer probe.
 * Creates a GUdevClient (the minimal public API) and verifies the
 * library links and initializes. No udev subsystem is queried.
 */
#include <gudev/gudev.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    const gchar *subsystems[] = {NULL};
    GUdevClient *client = g_udev_client_new(subsystems);
    if (client == NULL) {
        fprintf(stderr, "FAIL: g_udev_client_new returned NULL\n");
        return 1;
    }
    /* Reaching here proves libgudev linked + initialized (no udev hwdb needed). */
    g_object_unref(client);
    printf("gudev client OK\n");
    return 0;
}
