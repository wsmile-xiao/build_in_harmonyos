#include <stddef.h>
#include <X11/extensions/XInput.h>
#include <X11/extensions/XInput2.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* XInput v1 API (XInput.h) */
DECLARE_SYMBOL(XOpenDevice);
DECLARE_SYMBOL(XCloseDevice);
DECLARE_SYMBOL(XQueryDeviceState);
DECLARE_SYMBOL(XSelectExtensionEvent);
DECLARE_SYMBOL(XGetSelectedExtensionEvents);
DECLARE_SYMBOL(XChangeDeviceDontPropagateList);
DECLARE_SYMBOL(XGetDeviceDontPropagateList);
DECLARE_SYMBOL(XSetDeviceMode);
DECLARE_SYMBOL(XSetDeviceValuators);
DECLARE_SYMBOL(XChangeDeviceControl);
DECLARE_SYMBOL(XGetDeviceControl);
DECLARE_SYMBOL(XChangeDeviceKeyMapping);
DECLARE_SYMBOL(XGetDeviceKeyMapping);
DECLARE_SYMBOL(XGetDeviceButtonMapping);
DECLARE_SYMBOL(XSetDeviceButtonMapping);
DECLARE_SYMBOL(XDeviceBell);
DECLARE_SYMBOL(XSetDeviceFocus);
DECLARE_SYMBOL(XGetDeviceFocus);
DECLARE_SYMBOL(XGrabDevice);
DECLARE_SYMBOL(XUngrabDevice);
DECLARE_SYMBOL(XGrabDeviceButton);
DECLARE_SYMBOL(XUngrabDeviceButton);
DECLARE_SYMBOL(XGrabDeviceKey);
DECLARE_SYMBOL(XUngrabDeviceKey);
DECLARE_SYMBOL(XGetDeviceMotionEvents);
DECLARE_SYMBOL(XChangeKeyboardDevice);
DECLARE_SYMBOL(XChangePointerDevice);
DECLARE_SYMBOL(XGetDeviceModifierMapping);
DECLARE_SYMBOL(XSetDeviceModifierMapping);
DECLARE_SYMBOL(XGetDeviceProperty);
DECLARE_SYMBOL(XChangeDeviceProperty);
DECLARE_SYMBOL(XListDeviceProperties);
DECLARE_SYMBOL(XDeleteDeviceProperty);
DECLARE_SYMBOL(XListInputDevices);
DECLARE_SYMBOL(XFreeDeviceList);
DECLARE_SYMBOL(XGetExtensionVersion);
DECLARE_SYMBOL(XSendExtensionEvent);
DECLARE_SYMBOL(XAllowDeviceEvents);
DECLARE_SYMBOL(XFreeDeviceState);
DECLARE_SYMBOL(XFreeDeviceMotionEvents);

/* XInput v2 API (XInput2.h) */
DECLARE_SYMBOL(XIQueryVersion);
DECLARE_SYMBOL(XIQueryDevice);
DECLARE_SYMBOL(XISelectEvents);
DECLARE_SYMBOL(XIGetSelectedEvents);
DECLARE_SYMBOL(XIQueryPointer);
DECLARE_SYMBOL(XIWarpPointer);
DECLARE_SYMBOL(XIDefineCursor);
DECLARE_SYMBOL(XIUndefineCursor);
DECLARE_SYMBOL(XIChangeHierarchy);
DECLARE_SYMBOL(XISetClientPointer);
DECLARE_SYMBOL(XIGetClientPointer);
DECLARE_SYMBOL(XIUngrabDevice);
DECLARE_SYMBOL(XIGrabDevice);
DECLARE_SYMBOL(XIGrabKeycode);
DECLARE_SYMBOL(XIGrabButton);
DECLARE_SYMBOL(XIUngrabButton);
DECLARE_SYMBOL(XIUngrabKeycode);
DECLARE_SYMBOL(XIAllowEvents);
DECLARE_SYMBOL(XIAllowTouchEvents);
DECLARE_SYMBOL(XIGetFocus);
DECLARE_SYMBOL(XISetFocus);
DECLARE_SYMBOL(XIGetProperty);
DECLARE_SYMBOL(XIChangeProperty);
DECLARE_SYMBOL(XIListProperties);
DECLARE_SYMBOL(XIDeleteProperty);
DECLARE_SYMBOL(XIFreeDeviceInfo);
DECLARE_SYMBOL(XIBarrierReleasePointer);
DECLARE_SYMBOL(XIBarrierReleasePointers);
DECLARE_SYMBOL(XIGrabEnter);
DECLARE_SYMBOL(XIGrabFocusIn);
DECLARE_SYMBOL(XIUngrabEnter);
DECLARE_SYMBOL(XIUngrabFocusIn);
DECLARE_SYMBOL(XIGrabTouchBegin);
DECLARE_SYMBOL(XIUngrabTouchBegin);
DECLARE_SYMBOL(XIGrabPinchGestureBegin);
DECLARE_SYMBOL(XIUngrabPinchGestureBegin);
DECLARE_SYMBOL(XIGrabSwipeGestureBegin);
DECLARE_SYMBOL(XIUngrabSwipeGestureBegin);

#define CHECK_SYMBOL(name) \
    do { \
        if (probe_##name == NULL) { \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    /* XInput v1 */
    CHECK_SYMBOL(XOpenDevice);
    CHECK_SYMBOL(XCloseDevice);
    CHECK_SYMBOL(XQueryDeviceState);
    CHECK_SYMBOL(XSelectExtensionEvent);
    CHECK_SYMBOL(XGetSelectedExtensionEvents);
    CHECK_SYMBOL(XChangeDeviceDontPropagateList);
    CHECK_SYMBOL(XGetDeviceDontPropagateList);
    CHECK_SYMBOL(XSetDeviceMode);
    CHECK_SYMBOL(XSetDeviceValuators);
    CHECK_SYMBOL(XChangeDeviceControl);
    CHECK_SYMBOL(XGetDeviceControl);
    CHECK_SYMBOL(XChangeDeviceKeyMapping);
    CHECK_SYMBOL(XGetDeviceKeyMapping);
    CHECK_SYMBOL(XGetDeviceButtonMapping);
    CHECK_SYMBOL(XSetDeviceButtonMapping);
    CHECK_SYMBOL(XDeviceBell);
    CHECK_SYMBOL(XSetDeviceFocus);
    CHECK_SYMBOL(XGetDeviceFocus);
    CHECK_SYMBOL(XGrabDevice);
    CHECK_SYMBOL(XUngrabDevice);
    CHECK_SYMBOL(XGrabDeviceButton);
    CHECK_SYMBOL(XUngrabDeviceButton);
    CHECK_SYMBOL(XGrabDeviceKey);
    CHECK_SYMBOL(XUngrabDeviceKey);
    CHECK_SYMBOL(XGetDeviceMotionEvents);
    CHECK_SYMBOL(XChangeKeyboardDevice);
    CHECK_SYMBOL(XChangePointerDevice);
    CHECK_SYMBOL(XGetDeviceModifierMapping);
    CHECK_SYMBOL(XSetDeviceModifierMapping);
    CHECK_SYMBOL(XGetDeviceProperty);
    CHECK_SYMBOL(XChangeDeviceProperty);
    CHECK_SYMBOL(XListDeviceProperties);
    CHECK_SYMBOL(XDeleteDeviceProperty);
    CHECK_SYMBOL(XListInputDevices);
    CHECK_SYMBOL(XFreeDeviceList);
    CHECK_SYMBOL(XGetExtensionVersion);
    CHECK_SYMBOL(XSendExtensionEvent);
    CHECK_SYMBOL(XAllowDeviceEvents);
    CHECK_SYMBOL(XFreeDeviceState);
    CHECK_SYMBOL(XFreeDeviceMotionEvents);

    /* XInput v2 */
    CHECK_SYMBOL(XIQueryVersion);
    CHECK_SYMBOL(XIQueryDevice);
    CHECK_SYMBOL(XISelectEvents);
    CHECK_SYMBOL(XIGetSelectedEvents);
    CHECK_SYMBOL(XIQueryPointer);
    CHECK_SYMBOL(XIWarpPointer);
    CHECK_SYMBOL(XIDefineCursor);
    CHECK_SYMBOL(XIUndefineCursor);
    CHECK_SYMBOL(XIChangeHierarchy);
    CHECK_SYMBOL(XISetClientPointer);
    CHECK_SYMBOL(XIGetClientPointer);
    CHECK_SYMBOL(XIUngrabDevice);
    CHECK_SYMBOL(XIGrabDevice);
    CHECK_SYMBOL(XIGrabKeycode);
    CHECK_SYMBOL(XIGrabButton);
    CHECK_SYMBOL(XIUngrabButton);
    CHECK_SYMBOL(XIUngrabKeycode);
    CHECK_SYMBOL(XIAllowEvents);
    CHECK_SYMBOL(XIAllowTouchEvents);
    CHECK_SYMBOL(XIGetFocus);
    CHECK_SYMBOL(XISetFocus);
    CHECK_SYMBOL(XIGetProperty);
    CHECK_SYMBOL(XIChangeProperty);
    CHECK_SYMBOL(XIListProperties);
    CHECK_SYMBOL(XIDeleteProperty);
    CHECK_SYMBOL(XIFreeDeviceInfo);
    CHECK_SYMBOL(XIBarrierReleasePointer);
    CHECK_SYMBOL(XIBarrierReleasePointers);
    CHECK_SYMBOL(XIGrabEnter);
    CHECK_SYMBOL(XIGrabFocusIn);
    CHECK_SYMBOL(XIUngrabEnter);
    CHECK_SYMBOL(XIUngrabFocusIn);
    CHECK_SYMBOL(XIGrabTouchBegin);
    CHECK_SYMBOL(XIUngrabTouchBegin);
    CHECK_SYMBOL(XIGrabPinchGestureBegin);
    CHECK_SYMBOL(XIUngrabPinchGestureBegin);
    CHECK_SYMBOL(XIGrabSwipeGestureBegin);
    CHECK_SYMBOL(XIUngrabSwipeGestureBegin);

    return 0;
}
