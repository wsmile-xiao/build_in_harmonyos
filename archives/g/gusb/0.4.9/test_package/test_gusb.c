/* gusb test_package consumer probe.
 * Creates a GUsbContext (the minimal public API) and verifies the
 * library links and initializes. No USB device is required.
 */
#include <gusb.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    g_autoptr(GUsbContext) context = g_usb_context_new(NULL);
    if (context == NULL) {
        fprintf(stderr, "FAIL: g_usb_context_new returned NULL\n");
        return 1;
    }
    /* No platform lookup forced; reaching here proves libgusb linked + initialized. */
    printf("gusb context OK\n");
    return 0;
}
