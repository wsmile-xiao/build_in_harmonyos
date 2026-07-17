#include <libusb-1.0/libusb.h>

#include <stdlib.h>
#include <string.h>

struct libusb_context {
    int unused;
};

struct libusb_device {
    int unused;
};

struct libusb_device_handle {
    int unused;
};

static struct libusb_context g_context;

int libusb_init(libusb_context **ctx)
{
    if (ctx != NULL) {
        *ctx = &g_context;
    }
    return LIBUSB_SUCCESS;
}

void libusb_exit(libusb_context *ctx)
{
    (void)ctx;
}

int libusb_set_option(libusb_context *ctx, enum libusb_option option, ...)
{
    (void)ctx;
    (void)option;
    return LIBUSB_SUCCESS;
}

void libusb_set_debug(libusb_context *ctx, int level)
{
    (void)ctx;
    (void)level;
}

ssize_t libusb_get_device_list(libusb_context *ctx, libusb_device ***list)
{
    (void)ctx;
    if (list == NULL) {
        return LIBUSB_ERROR_INVALID_PARAM;
    }
    *list = (libusb_device **)calloc(1, sizeof(libusb_device *));
    if (*list == NULL) {
        return LIBUSB_ERROR_NO_MEM;
    }
    return 0;
}

void libusb_free_device_list(libusb_device **list, int unref_devices)
{
    (void)unref_devices;
    free(list);
}

int libusb_get_device_descriptor(libusb_device *dev, struct libusb_device_descriptor *desc)
{
    (void)dev;
    if (desc == NULL) {
        return LIBUSB_ERROR_INVALID_PARAM;
    }
    memset(desc, 0, sizeof(*desc));
    return LIBUSB_ERROR_NO_DEVICE;
}

uint8_t libusb_get_bus_number(libusb_device *dev)
{
    (void)dev;
    return 0;
}

uint8_t libusb_get_device_address(libusb_device *dev)
{
    (void)dev;
    return 0;
}

int libusb_open(libusb_device *dev, libusb_device_handle **handle)
{
    (void)dev;
    if (handle != NULL) {
        *handle = NULL;
    }
    return LIBUSB_ERROR_NO_DEVICE;
}

int libusb_set_configuration(libusb_device_handle *handle, int configuration)
{
    (void)handle;
    (void)configuration;
    return LIBUSB_ERROR_NOT_SUPPORTED;
}

int libusb_claim_interface(libusb_device_handle *handle, int interface_number)
{
    (void)handle;
    (void)interface_number;
    return LIBUSB_ERROR_NOT_SUPPORTED;
}

int libusb_release_interface(libusb_device_handle *handle, int interface_number)
{
    (void)handle;
    (void)interface_number;
    return LIBUSB_SUCCESS;
}

void libusb_close(libusb_device_handle *handle)
{
    (void)handle;
}

int libusb_reset_device(libusb_device_handle *handle)
{
    (void)handle;
    return LIBUSB_ERROR_NOT_SUPPORTED;
}

int libusb_get_config_descriptor(
    libusb_device *dev,
    uint8_t config_index,
    struct libusb_config_descriptor **config
)
{
    (void)dev;
    (void)config_index;
    if (config != NULL) {
        *config = NULL;
    }
    return LIBUSB_ERROR_NO_DEVICE;
}

void libusb_free_config_descriptor(struct libusb_config_descriptor *config)
{
    free(config);
}

int libusb_control_transfer(
    libusb_device_handle *handle,
    uint8_t request_type,
    uint8_t request,
    uint16_t value,
    uint16_t index,
    unsigned char *data,
    uint16_t length,
    unsigned int timeout
)
{
    (void)handle;
    (void)request_type;
    (void)request;
    (void)value;
    (void)index;
    (void)data;
    (void)length;
    (void)timeout;
    return LIBUSB_ERROR_NOT_SUPPORTED;
}
