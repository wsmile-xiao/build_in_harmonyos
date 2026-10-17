#include <arv.h>
#include <glib-object.h>
#include <stdio.h>

int main(void)
{
    ArvDevice *device = NULL;
    ArvGc *genicam = NULL;
    GError *error = NULL;

    if (!ARAVIS_CHECK_VERSION(0, 8, 36)) {
        fprintf(stderr, "unexpected aravis header version: %u.%u.%u\n",
                arv_get_major_version(),
                arv_get_minor_version(),
                arv_get_micro_version());
        return 1;
    }

    device = arv_fake_device_new("TEST0", &error);
    if (!ARV_IS_FAKE_DEVICE(device)) {
        fprintf(stderr, "failed to create fake device: %s\n",
                error != NULL ? error->message : "unknown error");
        g_clear_error(&error);
        return 1;
    }

    genicam = arv_device_get_genicam(device);
    if (!ARV_IS_GC(genicam)) {
        fprintf(stderr, "fake device did not expose a GenICam model\n");
        g_object_unref(device);
        return 1;
    }

    printf("aravis %u.%u.%u fake device test passed\n",
           arv_get_major_version(),
           arv_get_minor_version(),
           arv_get_micro_version());
    g_object_unref(device);
    return 0;
}
