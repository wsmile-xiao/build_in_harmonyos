/* libusb.h - minimal subset of libusb-1.0 types/decls for chaosread 1.1
 *
 * Only the symbols chaosread.c references are declared. This is paired with
 * libusb_stub.c which provides no-op implementations.
 */
#ifndef LIBUSB_H_STUB_CHAOSREAD
#define LIBUSB_H_STUB_CHAOSREAD

#include <stdint.h>
#include <sys/types.h>

#define LIBUSB_API
#define LIBUSB_CALL

#define LIBUSB_ERROR_IO              -1
#define LIBUSB_ERROR_INVALID_PARAM   -2
#define LIBUSB_ERROR_ACCESS          -3
#define LIBUSB_ERROR_NO_DEVICE       -4
#define LIBUSB_ERROR_NOT_FOUND       -5
#define LIBUSB_ERROR_BUSY            -6
#define LIBUSB_ERROR_TIMEOUT         -7
#define LIBUSB_ERROR_OVERFLOW        -8
#define LIBUSB_ERROR_PIPE            -9
#define LIBUSB_ERROR_INTERRUPTED    -10
#define LIBUSB_ERROR_NO_MEM         -11
#define LIBUSB_ERROR_NOT_SUPPORTED  -12
#define LIBUSB_ERROR_OTHER          -99

struct libusb_context;
typedef struct libusb_context libusb_context;

struct libusb_device;
typedef struct libusb_device libusb_device;

struct libusb_device_handle;
typedef struct libusb_device_handle libusb_device_handle;

struct libusb_device_descriptor {
    uint8_t  bLength;
    uint8_t  bDescriptorType;
    uint16_t bcdUSB;
    uint8_t  bDeviceClass;
    uint8_t  bDeviceSubClass;
    uint8_t  bDeviceProtocol;
    uint8_t  bMaxPacketSize0;
    uint16_t idVendor;
    uint16_t idProduct;
    uint16_t bcdDevice;
    uint8_t  iManufacturer;
    uint8_t  iProduct;
    uint8_t  iSerialNumber;
    uint8_t  bNumConfigurations;
};

int  libusb_init(libusb_context **ctx);
void libusb_exit(libusb_context *ctx);
ssize_t libusb_get_device_list(libusb_context *ctx, libusb_device ***list);
void libusb_free_device_list(libusb_device **list, int unref_devices);
int  libusb_get_device_descriptor(libusb_device *dev,
                                   struct libusb_device_descriptor *desc);
int  libusb_open(libusb_device *dev, libusb_device_handle **handle);
void libusb_close(libusb_device_handle *handle);
int  libusb_get_string_descriptor_ascii(libusb_device_handle *handle,
                                        uint8_t index, unsigned char *data,
                                        int length);
int  libusb_kernel_driver_active(libusb_device_handle *handle, int interface);
int  libusb_detach_kernel_driver(libusb_device_handle *handle, int interface);
int  libusb_attach_kernel_driver(libusb_device_handle *handle, int interface);
int  libusb_claim_interface(libusb_device_handle *handle, int interface);
int  libusb_release_interface(libusb_device_handle *handle, int interface);
int  libusb_bulk_transfer(libusb_device_handle *handle, unsigned char endpoint,
                          unsigned char *data, int length, int *transferred,
                          unsigned int timeout);
const char *libusb_strerror(int errcode);

#endif /* LIBUSB_H_STUB_CHAOSREAD */
