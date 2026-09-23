#include <sandbird.h>
#include <string.h>

static int handler(sb_Event *event) {
    (void)event;
    return SB_RES_OK;
}

int main(void) {
    sb_Options options;
    sb_Server *server;
    memset(&options, 0, sizeof(options));
    options.port = "0";
    options.handler = handler;
    server = sb_new_server(&options);
    if (!server) return 1;
    if (sb_poll_server(server, 0) != SB_ESUCCESS) return 2;
    sb_close_server(server);
    return strcmp(sb_error_str(SB_ESUCCESS), "success") == 0 ? 0 : 3;
}
