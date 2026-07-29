#include <openobex/obex.h>

static void on_event(
    obex_t *handle,
    obex_object_t *object,
    int mode,
    int event,
    int command,
    int response)
{
    (void)handle;
    (void)object;
    (void)mode;
    (void)event;
    (void)command;
    (void)response;
}

int main(void)
{
    obex_t *handle = OBEX_Init(OBEX_TRANS_CUSTOM, on_event, 0);
    obex_object_t *object;

    if (handle == 0) {
        return 1;
    }
    if (OBEX_SetTransportMTU(handle, 1024, 1024) < 0) {
        OBEX_Cleanup(handle);
        return 2;
    }

    object = OBEX_ObjectNew(handle, OBEX_CMD_CONNECT);
    if (object == 0) {
        OBEX_Cleanup(handle);
        return 3;
    }
    if (OBEX_ObjectDelete(handle, object) < 0) {
        OBEX_Cleanup(handle);
        return 4;
    }

    OBEX_Cleanup(handle);
    return 0;
}
