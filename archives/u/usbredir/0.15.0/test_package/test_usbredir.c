#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>
#include <usbredirhost.h>
#include <usbredirparser.h>
#include <usbredirproto.h>

struct callback_state {
    int log_calls;
    int read_calls;
    int write_calls;
    int bytes_written;
};

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "usbredir test failed: %s\n", message);
        exit(1);
    }
}

static void log_cb(void *priv, int level, const char *msg)
{
    (void)level;
    struct callback_state *state = (struct callback_state *)priv;
    require_true(state != NULL, "log callback state");
    require_true(msg != NULL, "log callback message");
    state->log_calls++;
}

static int read_cb(void *priv, uint8_t *data, int count)
{
    struct callback_state *state = (struct callback_state *)priv;
    require_true(state != NULL, "read callback state");
    require_true(data != NULL, "read callback buffer");
    require_true(count > 0, "read callback count");
    state->read_calls++;
    return 0;
}

static int write_cb(void *priv, uint8_t *data, int count)
{
    struct callback_state *state = (struct callback_state *)priv;
    require_true(state != NULL, "write callback state");
    require_true(data != NULL, "write callback buffer");
    require_true(count > 0, "write callback count");
    state->write_calls++;
    state->bytes_written += count;
    return count;
}

int main(void)
{
    uint32_t caps[USB_REDIR_CAPS_SIZE] = {0};
    struct callback_state parser_state;
    struct callback_state host_state;
    libusb_context *usb_ctx = NULL;
    int usb_init_result;
    int host_smoke_ran = 0;
    const struct libusb_init_option usb_options[] = {
        { LIBUSB_OPTION_NO_DEVICE_DISCOVERY, { .ival = 1 } },
    };

    memset(&parser_state, 0, sizeof(parser_state));
    memset(&host_state, 0, sizeof(host_state));

    struct usbredirparser *parser = usbredirparser_create();
    require_true(parser != NULL, "create parser");
    parser->priv = &parser_state;
    parser->log_func = log_cb;
    parser->read_func = read_cb;
    parser->write_func = write_cb;

    usbredirparser_caps_set_cap(caps, usb_redir_cap_bulk_streams);
    usbredirparser_init(parser, "usbredir-test", caps, USB_REDIR_CAPS_SIZE, 0);
    usbredirparser_send_device_disconnect(parser);
    require_true(usbredirparser_has_data_to_write(parser) > 0,
                 "parser queued disconnect packet");
    require_true(usbredirparser_do_write(parser) == 0,
                 "parser wrote queued packet");
    require_true(parser_state.write_calls > 0, "parser write callback invoked");
    require_true(parser_state.bytes_written > 0, "parser wrote bytes");
    usbredirparser_destroy(parser);

    usb_init_result = libusb_init_context(&usb_ctx, usb_options, 1);
    if (usb_init_result == LIBUSB_ERROR_OTHER) {
        /* WSL and other sandboxed hosts may not expose a usbfs backend. */
        fprintf(stderr, "skipping host context smoke: %s\n",
                libusb_error_name(usb_init_result));
    } else {
        struct usbredirhost *host;

        require_true(usb_init_result == 0,
                     "initialize libusb context without device discovery");
        host = usbredirhost_open(
            usb_ctx, NULL, log_cb, read_cb, write_cb, &host_state, "usbredir-test", 0, 0);
        require_true(host != NULL, "open host with libusb context");
        usbredirhost_close(host);
        libusb_exit(usb_ctx);
        host_smoke_ran = 1;
    }

    if (host_smoke_ran) {
        puts("usbredir parser packet and host context test passed");
    } else {
        puts("usbredir parser packet test passed; host context skipped");
    }
    return 0;
}
