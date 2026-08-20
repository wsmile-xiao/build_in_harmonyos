#include <X11/extensions/Xfixes.h>
#include <X11/extensions/xfixeswire.h>

_Static_assert(XFIXES_MAJOR == 6, "unexpected X Fixes protocol major");
_Static_assert(XFIXES_MINOR == 0, "unexpected X Fixes protocol minor");
_Static_assert(XFIXES_REVISION == 1, "unexpected client header revision");
_Static_assert(XFIXES_VERSION == 60001, "unexpected composite version");
_Static_assert(X_XFixesGetClientDisconnectMode == 34,
               "unexpected final request opcode");
_Static_assert(XFixesNumberRequests == 35, "unexpected request count");
_Static_assert(XFixesNumberEvents == 2, "unexpected event count");
_Static_assert(XFixesNumberErrors == 2, "unexpected error count");
_Static_assert(XFixesClientDisconnectFlagDefault == 0,
               "unexpected default disconnect flag");
_Static_assert(XFixesClientDisconnectFlagTerminate == 1,
               "unexpected terminate disconnect flag");
_Static_assert(XFixesClientDisconnectFlagForceTerminate == 2,
               "unexpected force-terminate disconnect flag");

int main(void)
{
    XFixesSelectionNotifyEvent selection = {0};
    XFixesCursorNotifyEvent cursor = {0};
    XFixesCursorImage image = {0};
    XFixesCursorImageAndName named_image = {0};
    XserverRegion region = 0;
    PointerBarrier barrier = 0;

    selection.window = 1;
    cursor.window = 2;
    image.width = 3;
    named_image.height = 4;
    region = 5;
    barrier = 6;

    if (selection.window != 1 || cursor.window != 2 || image.width != 3 ||
        named_image.height != 4 || region != 5 || barrier != 6) {
        return 1;
    }
    return XFixesVersion() == XFIXES_VERSION ? 0 : 2;
}
