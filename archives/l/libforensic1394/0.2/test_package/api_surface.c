/*
 * Contract test for the installed libforensic1394 package.
 *
 * Every exported function is bound to a pointer with the exact signature
 * declared in <forensic1394.h>.  That turns any header/ABI drift into a
 * compile error and forces the linker to resolve each symbol from the
 * installed library rather than from the header alone.
 *
 * The public result enum is then exercised through
 * forensic1394_get_result_str(), whose table is defined in the upstream
 * source, so the strings prove that the shipped object code is the one the
 * header documents.
 */

#include <forensic1394.h>

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int checks;

#define CHECK(cond)                                                          \
    do {                                                                     \
        ++checks;                                                            \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);  \
            return 1;                                                        \
        }                                                                    \
    } while (0)

static forensic1394_bus *(*const fn_alloc)(void)
    = forensic1394_alloc;
static forensic1394_result (*const fn_enable_sbp2)(forensic1394_bus *)
    = forensic1394_enable_sbp2;
static forensic1394_dev **(*const fn_get_devices)(forensic1394_bus *, int *,
                                                  forensic1394_device_callback)
    = forensic1394_get_devices;
static void (*const fn_destroy)(forensic1394_bus *)
    = forensic1394_destroy;
static void *(*const fn_get_bus_user_data)(forensic1394_bus *)
    = forensic1394_get_bus_user_data;
static void (*const fn_set_bus_user_data)(forensic1394_bus *, void *)
    = forensic1394_set_bus_user_data;
static forensic1394_result (*const fn_open_device)(forensic1394_dev *)
    = forensic1394_open_device;
static void (*const fn_close_device)(forensic1394_dev *)
    = forensic1394_close_device;
static int (*const fn_is_device_open)(forensic1394_dev *)
    = forensic1394_is_device_open;
static forensic1394_result (*const fn_read_device)(forensic1394_dev *, uint64_t,
                                                   size_t, void *)
    = forensic1394_read_device;
static forensic1394_result (*const fn_read_device_v)(forensic1394_dev *,
                                                     forensic1394_req *, size_t)
    = forensic1394_read_device_v;
static forensic1394_result (*const fn_write_device)(forensic1394_dev *, uint64_t,
                                                    size_t, void *)
    = forensic1394_write_device;
static forensic1394_result (*const fn_write_device_v)(
    forensic1394_dev *, const forensic1394_req *, size_t)
    = forensic1394_write_device_v;
static void (*const fn_get_device_csr)(forensic1394_dev *, uint32_t *)
    = forensic1394_get_device_csr;
static uint16_t (*const fn_get_device_nodeid)(forensic1394_dev *)
    = forensic1394_get_device_nodeid;
static int64_t (*const fn_get_device_guid)(forensic1394_dev *)
    = forensic1394_get_device_guid;
static const char *(*const fn_get_device_product_name)(forensic1394_dev *)
    = forensic1394_get_device_product_name;
static int (*const fn_get_device_product_id)(forensic1394_dev *)
    = forensic1394_get_device_product_id;
static const char *(*const fn_get_device_vendor_name)(forensic1394_dev *)
    = forensic1394_get_device_vendor_name;
static int (*const fn_get_device_vendor_id)(forensic1394_dev *)
    = forensic1394_get_device_vendor_id;
static int (*const fn_get_device_request_size)(forensic1394_dev *)
    = forensic1394_get_device_request_size;
static void *(*const fn_get_device_user_data)(forensic1394_dev *)
    = forensic1394_get_device_user_data;
static void (*const fn_set_device_user_data)(forensic1394_dev *, void *)
    = forensic1394_set_device_user_data;
static const char *(*const fn_get_result_str)(forensic1394_result)
    = forensic1394_get_result_str;

int main(void)
{
    /* Opaque handles and the request struct must keep their public shape. */
    forensic1394_req request;
    request.addr = 0x40000000ull;
    request.len = 512;
    request.buf = &request;
    CHECK(request.addr == 0x40000000ull);
    CHECK(sizeof(request.len) == sizeof(size_t));

    /* Whole exported surface resolves with the declared signatures. */
    CHECK(fn_alloc != NULL);
    CHECK(fn_enable_sbp2 != NULL);
    CHECK(fn_get_devices != NULL);
    CHECK(fn_destroy != NULL);
    CHECK(fn_get_bus_user_data != NULL);
    CHECK(fn_set_bus_user_data != NULL);
    CHECK(fn_open_device != NULL);
    CHECK(fn_close_device != NULL);
    CHECK(fn_is_device_open != NULL);
    CHECK(fn_read_device != NULL);
    CHECK(fn_read_device_v != NULL);
    CHECK(fn_write_device != NULL);
    CHECK(fn_write_device_v != NULL);
    CHECK(fn_get_device_csr != NULL);
    CHECK(fn_get_device_nodeid != NULL);
    CHECK(fn_get_device_guid != NULL);
    CHECK(fn_get_device_product_name != NULL);
    CHECK(fn_get_device_product_id != NULL);
    CHECK(fn_get_device_vendor_name != NULL);
    CHECK(fn_get_device_vendor_id != NULL);
    CHECK(fn_get_device_request_size != NULL);
    CHECK(fn_get_device_user_data != NULL);
    CHECK(fn_set_device_user_data != NULL);
    CHECK(fn_get_result_str != NULL);

    /* Public constants. */
    CHECK(FORENSIC1394_CSR_SZ == 256);

    /* Result code -> string table of the shipped object code.  The wording
       (including the upstream "permisisons" typo) is part of the 0.2 ABI. */
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_SUCCESS), "Success") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_OTHER_ERROR),
                 "General error") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_BUS_RESET),
                 "Bus reset has occurred") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_NO_PERM),
                 "Insufficient permisisons") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_BUSY),
                 "Device is busy") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_IO_ERROR),
                 "General I/O error") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_IO_SIZE),
                 "Bad I/O request size") == 0);
    CHECK(strcmp(fn_get_result_str(FORENSIC1394_RESULT_IO_TIMEOUT),
                 "I/O timeout") == 0);

    /* Out-of-range inputs must be rejected, not indexed. */
    CHECK(fn_get_result_str(FORENSIC1394_RESULT_END) == NULL);
    CHECK(fn_get_result_str((forensic1394_result) 1) == NULL);

    printf("forensic1394_api_surface: %d checks passed\n", checks);
    return 0;
}
