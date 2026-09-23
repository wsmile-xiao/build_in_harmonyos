#include <stddef.h>
#include <X11/extensions/XInput.h>
#include <X11/extensions/XInput2.h>
#include <X11/extensions/XI2.h>
#include <X11/extensions/Xfixes.h>
#include <X11/extensions/xfixeswire.h>

/* X Input protocol version advertised by xorgproto/2025.1 headers. */
_Static_assert(XI_2_Major == 2, "unexpected X Input 2 major");
_Static_assert(XI_2_Minor == 4, "unexpected X Input 2 minor");

/* XI2 event type opcodes (stable wire protocol constants). */
_Static_assert(XI_DeviceChanged == 1, "unexpected XI_DeviceChanged opcode");
_Static_assert(XI_KeyPress == 2, "unexpected XI_KeyPress opcode");
_Static_assert(XI_KeyRelease == 3, "unexpected XI_KeyRelease opcode");
_Static_assert(XI_ButtonPress == 4, "unexpected XI_ButtonPress opcode");
_Static_assert(XI_ButtonRelease == 5, "unexpected XI_ButtonRelease opcode");
_Static_assert(XI_Motion == 6, "unexpected XI_Motion opcode");
_Static_assert(XI_RawKeyPress == 13, "unexpected XI_RawKeyPress opcode");
_Static_assert(XI_RawMotion == 17, "unexpected XI_RawMotion opcode");
_Static_assert(XI_TouchBegin == 18, "unexpected XI_TouchBegin opcode");

/* X Fixes protocol/library version consumed by the PointerBarrier typedef. */
_Static_assert(XFIXES_MAJOR == 6, "unexpected X Fixes protocol major");
_Static_assert(XFIXES_MINOR == 0, "unexpected X Fixes protocol minor");
_Static_assert(XFIXES_REVISION == 1, "unexpected X Fixes client revision");
_Static_assert(X_XFixesSetClientDisconnectMode == 33,
               "unexpected SetClientDisconnectMode opcode");
_Static_assert(X_XFixesGetClientDisconnectMode == 34,
               "unexpected GetClientDisconnectMode opcode");

/* XInput v1 device event selectors from the installed XInput.h. */
_Static_assert(_deviceKeyPress == 0, "unexpected _deviceKeyPress selector");
_Static_assert(_deviceKeyRelease == 1, "unexpected _deviceKeyRelease selector");
_Static_assert(_deviceButtonPress == 0,
               "unexpected _deviceButtonPress selector");
_Static_assert(_deviceButtonRelease == 1,
               "unexpected _deviceButtonRelease selector");
_Static_assert(_propertyNotify == 6, "unexpected _propertyNotify selector");

int main(void)
{
    XIDeviceInfo device_info = {0};
    device_info.deviceid = 1;
    if (device_info.deviceid != 1) {
        return __LINE__;
    }

    XIEventMask event_mask = {0};
    event_mask.deviceid = 2;
    event_mask.mask_len = 3;
    if (event_mask.deviceid != 2 || event_mask.mask_len != 3) {
        return __LINE__;
    }

    XIModifierState mods = {0};
    mods.base = 1;
    mods.latched = 2;
    mods.locked = 3;
    if (mods.base != 1 || mods.latched != 2 || mods.locked != 3) {
        return __LINE__;
    }

    XIGroupState groups = {0};
    groups.base = 4;
    if (groups.base != 4) {
        return __LINE__;
    }

    XIAnyClassInfo class_info = {0};
    class_info.type = 8;
    class_info.sourceid = 9;
    if (class_info.type != 8 || class_info.sourceid != 9) {
        return __LINE__;
    }

    XIBarrierReleasePointerInfo release_info = {0};
    release_info.deviceid = 10;
    release_info.barrier = 11;
    if (release_info.deviceid != 10 || release_info.barrier != 11) {
        return __LINE__;
    }

    PointerBarrier barrier = (PointerBarrier)0x12345678;
    if (barrier == 0) {
        return __LINE__;
    }

    XDevice device = {0};
    device.device_id = 10;
    if (device.device_id != 10) {
        return __LINE__;
    }

    return 0;
}
