/**
 * napi_init.cpp - NAPI bridge for MyNotePad (Scintilla OHOS)
 *
 * Architecture:
 *   ArkTS (Index.ets)  --NAPI-->  libentry.so (this file)  --C API-->  libscintilla_ohos.so
 *
 * XComponent registration (API 8+ standard approach):
 *   When XComponent has libraryname='entry', the framework calls our Init()
 *   with exports containing OH_NATIVE_XCOMPONENT_OBJ. We use napi_unwrap
 *   to get the OH_NativeXComponent* pointer and register callbacks immediately.
 *   The framework then calls OnSurfaceCreated with a proper NativeWindow.
 *
 * Rendering approach:
 *   Since XComponent surface uses GPU buffer (virAddr may be NULL),
 *   RenderFrame creates an independent OH_Drawing_Bitmap (with its own memory),
 *   renders Scintilla onto it, then copies pixels to the NativeWindow buffer
 *   (via virAddr or mmap fallback) using row-by-row copy to handle stride differences.
 */

#include "napi/native_api.h"
#include "ScintillaOHOS.h"
#include <ace/xcomponent/native_interface_xcomponent.h>
#include <ace/xcomponent/native_xcomponent_key_event.h>
#include <native_window/external_window.h>
#include <native_drawing/drawing_canvas.h>
#include <native_drawing/drawing_bitmap.h>
#include <native_drawing/drawing_brush.h>
#include <native_drawing/drawing_rect.h>
#include <arkui/ui_input_event.h>
#include <arkui/native_key_event.h>
#include <arkui/native_node.h>
#include <arkui/native_node_napi.h>
#include <arkui/native_interface.h>
#include <hilog/log.h>
#include <string>
#include <cstdio>
#include <cstring>
#include <atomic>
#include <unistd.h>
#include <sys/mman.h>
#include <errno.h>

// ============================================================================
// Logging
// ============================================================================
// HarmonyOS hilog sanitizes all values by default (shows <private>).
// Use %{public}s / %{public}d / %{public}p etc. to make values visible.
// DBG macro uses stderr which bypasses hilog entirely.
#undef LOG_TAG
#define LOG_TAG "MyNotePad"
#define MYLOGI(fmt, ...) OH_LOG_Print(LOG_APP, LOG_INFO, LOG_DOMAIN, LOG_TAG, fmt, ##__VA_ARGS__)
#define MYLOGE(fmt, ...) OH_LOG_Print(LOG_APP, LOG_ERROR, LOG_DOMAIN, LOG_TAG, fmt, ##__VA_ARGS__)
#define MYLOGW(fmt, ...) OH_LOG_Print(LOG_APP, LOG_WARN, LOG_DOMAIN, LOG_TAG, fmt, ##__VA_ARGS__)
#define DBG(fmt, ...) fprintf(stderr, "[MNP-DBG] " fmt "\n", ##__VA_ARGS__)

// ============================================================================
// Global state
// ============================================================================

static void *g_editor = nullptr;
static OHNativeWindow *g_nativeWindow = nullptr;
static uint64_t g_surfaceWidth = 0;
static uint64_t g_surfaceHeight = 0;
static std::atomic<int> g_needsRedraw{0};
static std::atomic<int> g_rendering{0};  // re-entrancy guard for RenderFrame
static OH_NativeXComponent *g_nativeXComponent = nullptr;
static bool g_callbacksRegistered = false;

// OH_ArkUI_SurfaceHolder based state
static OH_ArkUI_SurfaceHolder *g_surfaceHolder = nullptr;
static OH_ArkUI_SurfaceCallback *g_surfaceCallback = nullptr;
static ArkUI_NodeHandle g_nodeHandle = nullptr;
static ArkUI_NativeNodeAPI_1 *g_nodeAPI = nullptr;

// ============================================================================
// Helpers: BigInt <-> void*
// ============================================================================

static napi_value PointerToNapi(napi_env env, void *ptr) {
    napi_value result;
    napi_create_bigint_uint64(env, reinterpret_cast<uint64_t>(ptr), &result);
    return result;
}

static void* NapiToPointer(napi_env env, napi_value val) {
    bool lossless;
    uint64_t v;
    napi_get_value_bigint_uint64(env, val, &v, &lossless);
    return reinterpret_cast<void *>(v);
}

// ============================================================================
// Helper: register XComponent callbacks
// ============================================================================

static void OnSurfaceCreated(OH_NativeXComponent *component, void *window);
static void OnSurfaceChanged(OH_NativeXComponent *component, void *window);
static void OnSurfaceDestroyed(OH_NativeXComponent *component, void *window);
static void OnDispatchTouchEvent(OH_NativeXComponent *component, void *window);
static void OnKeyEvent(OH_NativeXComponent *component, void *window);
static void OnUIInputEvent(OH_NativeXComponent *component, ArkUI_UIInputEvent *event,
                           ArkUI_UIInputEvent_Type type);

static bool RegisterXComponentCallbacks(OH_NativeXComponent *component) {
    OH_NativeXComponent_Callback xcompCallback = {};
    xcompCallback.OnSurfaceCreated = OnSurfaceCreated;
    xcompCallback.OnSurfaceChanged = OnSurfaceChanged;
    xcompCallback.OnSurfaceDestroyed = OnSurfaceDestroyed;
    xcompCallback.DispatchTouchEvent = OnDispatchTouchEvent;

    int32_t ret = OH_NativeXComponent_RegisterCallback(component, &xcompCallback);
    MYLOGI("RegisterXComponentCallbacks: component=%{public}p, ret=%{public}d", component, ret);

    // Enable soft keyboard when XComponent is focused
    OH_NativeXComponent_SetNeedSoftKeyboard(component, true);

    // Register key event callback (API 10+) for hardware keys + IME
    int32_t keyRet = OH_NativeXComponent_RegisterKeyEventCallback(component, OnKeyEvent);
    MYLOGI("RegisterXComponentCallbacks: KeyEvent ret=%{public}d", keyRet);

    // Register UI input event callback (API 12+) for soft keyboard input
    int32_t uiInputRet = OH_NativeXComponent_RegisterUIInputEventCallback(
        component, OnUIInputEvent, ARKUI_UIINPUTEVENT_TYPE_KEY);
    MYLOGI("RegisterXComponentCallbacks: UIInputEvent ret=%{public}d", uiInputRet);

    return (ret == 0);
}

// ============================================================================
// XComponent surface callbacks (forward declarations)
// ============================================================================


// ============================================================================
// RenderFrame - render Scintilla to independent bitmap, then copy to NativeWindow
// ============================================================================

static void RenderFrame() {
    if (!g_nativeWindow || !g_editor || g_surfaceWidth == 0 || g_surfaceHeight == 0) {
        MYLOGW("RenderFrame skipped: window=%{public}p, editor=%{public}p, size=%{public}lux%{public}lu",
               g_nativeWindow, g_editor, (unsigned long)g_surfaceWidth, (unsigned long)g_surfaceHeight);
        return;
    }

    // Re-entrancy guard: BN_Sci_OnTouch* → InvalidateAll → RequestRedraw → RenderFrame
    // would cause nested rendering and potential crash. Skip if already rendering.
    int expected = 0;
    if (!g_rendering.compare_exchange_strong(expected, 1)) {
        MYLOGI("RenderFrame: re-entrancy blocked, setting dirty flag instead");
        g_needsRedraw.store(1);
        return;
    }

    // --- Phase 1: Render Scintilla to independent bitmap ---

    OH_Drawing_Image_Info imageInfo = {};
    imageInfo.width = (uint32_t)g_surfaceWidth;
    imageInfo.height = (uint32_t)g_surfaceHeight;
    imageInfo.colorType = COLOR_FORMAT_RGBA_8888;
    imageInfo.alphaType = ALPHA_FORMAT_PREMUL;

    size_t pixelBytesPerRow = (size_t)g_surfaceWidth * 4;
    size_t pixelBufSize = pixelBytesPerRow * (size_t)g_surfaceHeight;
    void *pixelBuf = malloc(pixelBufSize);
    if (!pixelBuf) { MYLOGE("RenderFrame: malloc failed"); return; }
    memset(pixelBuf, 0xFF, pixelBufSize); // white background

    OH_Drawing_Bitmap *bitmap = OH_Drawing_BitmapCreateFromPixels(
        &imageInfo, pixelBuf, pixelBytesPerRow);
    if (!bitmap) {
        MYLOGE("RenderFrame: BitmapCreateFromPixels failed");
        free(pixelBuf);
        return;
    }

    OH_Drawing_Canvas *canvas = OH_Drawing_CanvasCreate();
    if (!canvas) {
        MYLOGE("RenderFrame: CanvasCreate failed");
        OH_Drawing_BitmapDestroy(bitmap);
        free(pixelBuf);
        return;
    }
    OH_Drawing_CanvasBind(canvas, bitmap);

    // Clear to white
    OH_Drawing_Brush *brush = OH_Drawing_BrushCreate();
    if (brush) {
        OH_Drawing_BrushSetColor(brush, 0xFFFFFFFF);
        OH_Drawing_BrushSetAntiAlias(brush, true);
        OH_Drawing_CanvasAttachBrush(canvas, brush);
        OH_Drawing_Rect *rect = OH_Drawing_RectCreate(
            0.0f, 0.0f, (float)g_surfaceWidth, (float)g_surfaceHeight);
        if (rect) {
            OH_Drawing_CanvasDrawRect(canvas, rect);
            OH_Drawing_RectDestroy(rect);
        }
        OH_Drawing_CanvasDetachBrush(canvas);
        OH_Drawing_BrushDestroy(brush);
    }

    // Draw Scintilla content
    MYLOGI("RenderFrame: calling BN_Sci_OnDraw");
    BN_Sci_OnDraw(g_editor, canvas);

    // Diagnostic: check if any non-white pixels exist (Scintilla drew something)
    {
        uint32_t *px = static_cast<uint32_t*>(pixelBuf);
        int nonWhite = 0;
        int totalChecked = std::min((int)(g_surfaceWidth * g_surfaceHeight), 100000);
        for (int i = 0; i < totalChecked; i++) {
            if ((px[i] & 0x00FFFFFF) != 0x00FFFFFF) { nonWhite++; }
        }
        char dbg2[256];
        snprintf(dbg2, sizeof(dbg2),
                 "RF: pixel check: nonWhite=%d/%d w=%lu h=%lu stride=%zu",
                 nonWhite, totalChecked,
                 (unsigned long)g_surfaceWidth, (unsigned long)g_surfaceHeight, pixelBytesPerRow);
        MYLOGI("%{public}s", dbg2);
    }

    // Cleanup canvas/bitmap (pixelBuf still holds the rendered pixels)
    OH_Drawing_CanvasDestroy(canvas);
    OH_Drawing_BitmapDestroy(bitmap);

    // --- Phase 2: Copy pixelBuf to NativeWindow buffer ---

    OHNativeWindowBuffer *buffer = nullptr;
    int fenceFd = -1;
    int ret = OH_NativeWindow_NativeWindowRequestBuffer(g_nativeWindow, &buffer, &fenceFd);
    if (ret != 0 || !buffer) {
        MYLOGE("RenderFrame: RequestBuffer failed ret=%{public}d", ret);
        free(pixelBuf);
        return;
    }

    BufferHandle *handle = OH_NativeWindow_GetBufferHandleFromNative(buffer);
    {
        char dbg[512];
        snprintf(dbg, sizeof(dbg),
                 "RF: handle=%p va=%p w=%d h=%d st=%d fmt=%d fd=%d sz=%d myW=%lu myH=%lu myStride=%zu",
                 (void*)handle,
                 handle ? handle->virAddr : nullptr,
                 handle ? handle->width : -1,
                 handle ? handle->height : -1,
                 handle ? handle->stride : -1,
                 handle ? handle->format : -1,
                 handle ? handle->fd : -1,
                 handle ? (int)handle->size : -1,
                 (unsigned long)g_surfaceWidth, (unsigned long)g_surfaceHeight, pixelBytesPerRow);
        MYLOGI("%{public}s", dbg);
    }

    size_t copySize = pixelBufSize;
    if (handle && handle->size > 0 && copySize > (size_t)handle->size) {
        copySize = (size_t)handle->size;
    }

    // Get the target buffer pointer
    void *dstBuf = nullptr;
    bool usedMmap = false;
    if (handle && handle->virAddr) {
        dstBuf = handle->virAddr;
    } else if (handle && handle->fd >= 0) {
        dstBuf = mmap(nullptr, handle->size, PROT_WRITE, MAP_SHARED, handle->fd, 0);
        if (dstBuf == MAP_FAILED) {
            MYLOGE("RenderFrame: mmap failed fd=%{public}d sz=%{public}d errno=%{public}d",
                   handle->fd, (int)handle->size, errno);
            dstBuf = nullptr;
        } else {
            usedMmap = true;
        }
    }

    if (dstBuf) {
        // Always do row-by-row copy to handle stride differences.
        // Our bitmap stride = width * 4, but the NativeWindow buffer may have
        // a different stride (e.g., GPU-aligned). A single memcpy would cause
        // diagonal stripe artifacts when strides don't match.
        int32_t srcStride = (int32_t)(g_surfaceWidth * 4);
        int32_t dstStride = (handle && handle->stride > 0) ? handle->stride : srcStride;
        uint32_t h = (uint32_t)g_surfaceHeight;
        if (handle && handle->height > 0) h = (uint32_t)std::min(h, (uint32_t)handle->height);

        const uint8_t *srcRow = static_cast<const uint8_t*>(pixelBuf);
        uint8_t *dstRow = static_cast<uint8_t*>(dstBuf);
        int32_t copyRowBytes = std::min(srcStride, dstStride);

        for (uint32_t y = 0; y < h; y++) {
            memcpy(dstRow, srcRow, copyRowBytes);
            srcRow += srcStride;
            dstRow += dstStride;
        }

        DBG("RF: row-copy done h=%u srcStride=%d dstStride=%d copyBytes=%d",
            h, srcStride, dstStride, copyRowBytes);

        if (usedMmap) {
            msync(dstBuf, handle->size, MS_SYNC);
            munmap(dstBuf, handle->size);
        }
    } else {
        MYLOGE("RenderFrame: no dst buffer (no virAddr, no fd)");
    }

    // Diagnostic: stride mismatch check
    if (handle && handle->stride > 0) {
        int expectedStride = (int)g_surfaceWidth * 4;
        if (handle->stride != expectedStride) {
            char warn[256];
            snprintf(warn, sizeof(warn),
                     "RF: STRIDE MISMATCH! bufStride=%d expected=%d (width=%lu*4). Row-by-row copy applied.",
                     handle->stride, expectedStride, (unsigned long)g_surfaceWidth);
            MYLOGI("%{public}s", warn);
        }
    }

    Region region = {nullptr, 0};
    int flushRet = OH_NativeWindow_NativeWindowFlushBuffer(g_nativeWindow, buffer, fenceFd, region);
    MYLOGI("RenderFrame: FlushBuffer ret=%{public}d", flushRet);
    if (fenceFd >= 0) close(fenceFd);

    free(pixelBuf);
    g_needsRedraw.store(0);
    g_rendering.store(0);  // release re-entrancy guard
}

static void RequestRedraw() {
    g_needsRedraw.store(1);
    RenderFrame();
}

// ============================================================================
// XComponent surface callbacks (implementations)
// ============================================================================

static void OnSurfaceCreated(OH_NativeXComponent *component, void *window) {
    MYLOGI("OnSurfaceCreated: component=%{public}p, window=%{public}p", component, window);
    if (!window) { MYLOGE("OnSurfaceCreated: window is NULL"); return; }
    g_nativeWindow = static_cast<OHNativeWindow*>(window);
    uint64_t width = 0, height = 0;
    OH_NativeXComponent_GetXComponentSize(component, window, &width, &height);
    g_surfaceWidth = width;
    g_surfaceHeight = height;
    {
        char dbg[256];
        snprintf(dbg, sizeof(dbg), "OnSurfaceCreated: size=%lux%lu",
                 (unsigned long)width, (unsigned long)height);
        MYLOGI("%{public}s", dbg);
    }
    if (g_editor) {
        BN_Sci_Init(g_editor, (int)width, (int)height);
        MYLOGI("OnSurfaceCreated: BN_Sci_Init done");
    }
    RenderFrame();
}

static void OnSurfaceChanged(OH_NativeXComponent *component, void *window) {
    uint64_t width = 0, height = 0;
    OH_NativeXComponent_GetXComponentSize(component, window, &width, &height);
    g_surfaceWidth = width;
    g_surfaceHeight = height;
    if (g_editor) { BN_Sci_SetSize(g_editor, (int)width, (int)height); }
    if (g_needsRedraw.load()) { RenderFrame(); }
}

static void OnSurfaceDestroyed(OH_NativeXComponent *component, void *window) {
    MYLOGI("OnSurfaceDestroyed");
    g_nativeWindow = nullptr;
    g_surfaceWidth = 0;
    g_surfaceHeight = 0;
    if (g_editor) { BN_Sci_SetFocus(g_editor, 0); }
}

// ============================================================================
// Key event callback (API 10+) — hardware keys
// ============================================================================

static void OnKeyEvent(OH_NativeXComponent *component, void *window) {
    if (!g_editor) return;

    OH_NativeXComponent_KeyEvent *keyEvent = nullptr;
    if (OH_NativeXComponent_GetKeyEvent(component, &keyEvent) != 0 || !keyEvent) return;

    OH_NativeXComponent_KeyAction action;
    OH_NativeXComponent_KeyCode code;
    if (OH_NativeXComponent_GetKeyEventAction(keyEvent, &action) != 0) return;
    if (OH_NativeXComponent_GetKeyEventCode(keyEvent, &code) != 0) return;

    if (action != OH_NATIVEXCOMPONENT_KEY_ACTION_DOWN) return;

    // Map HarmonyOS key codes to Scintilla virtual key codes
    int sciKeyCode = 0;
    switch (code) {
        case KEY_BACK:          sciKeyCode = 8;  break;   // Backspace
        case KEY_ENTER:         sciKeyCode = 13; break;   // Enter
        case KEY_TAB:           sciKeyCode = 9;  break;   // Tab
        case KEY_ESCAPE:        sciKeyCode = 27; break;   // Escape
        case KEY_DEL:           sciKeyCode = 46; break;   // Delete
        case KEY_FORWARD_DEL:   sciKeyCode = 46; break;   // Forward Delete
        default: break;
    }

    if (sciKeyCode > 0) {
        MYLOGI("OnKeyEvent: code=%{public}d sciKeyCode=%{public}d", (int)code, sciKeyCode);
        BN_Sci_OnKeyDown(g_editor, sciKeyCode, false, false, false, false);
    }
}

// ============================================================================
// UI input event callback (API 12+) — soft keyboard IME input
// ============================================================================

static void OnUIInputEvent(OH_NativeXComponent *component, ArkUI_UIInputEvent *event,
                           ArkUI_UIInputEvent_Type type) {
    if (!g_editor || !event || type != ARKUI_UIINPUTEVENT_TYPE_KEY) return;

    // Get key event type (DOWN=0, UP=1, LONG_PRESS=2, CLICK=3)
    ArkUI_KeyEventType keyType = OH_ArkUI_KeyEvent_GetType(event);
    int32_t keyCode = OH_ArkUI_KeyEvent_GetKeyCode(event);
    uint32_t unicode = OH_ArkUI_KeyEvent_GetUnicode(event);

    MYLOGI("OnUIInput: type=%{public}d keyCode=%{public}d unicode=0x%{public}x",
           (int)keyType, keyCode, unicode);

    // Process on DOWN or CLICK
    if (keyType != ARKUI_KEY_EVENT_DOWN && keyType != ARKUI_KEY_EVENT_CLICK) return;

    // Send printable characters via unicode
    if (unicode > 0) {
        char utf8[8] = {};
        int utf8len = 0;
        if (unicode < 0x80) {
            utf8[0] = (char)unicode;
            utf8len = 1;
        } else if (unicode < 0x800) {
            utf8[0] = 0xC0 | (unicode >> 6);
            utf8[1] = 0x80 | (unicode & 0x3F);
            utf8len = 2;
        } else if (unicode < 0x10000) {
            utf8[0] = 0xE0 | (unicode >> 12);
            utf8[1] = 0x80 | ((unicode >> 6) & 0x3F);
            utf8[2] = 0x80 | (unicode & 0x3F);
            utf8len = 3;
        } else {
            utf8[0] = 0xF0 | (unicode >> 18);
            utf8[1] = 0x80 | ((unicode >> 12) & 0x3F);
            utf8[2] = 0x80 | ((unicode >> 6) & 0x3F);
            utf8[3] = 0x80 | (unicode & 0x3F);
            utf8len = 4;
        }
        BN_Sci_OnChar(g_editor, utf8, utf8len);
        MYLOGI("OnUIInput: sent char U+%{public}x len=%{public}d", unicode, utf8len);
    } else {
        // No unicode — handle special keys by ArkUI keyCode
        int sciKey = 0;
        switch (keyCode) {
            case 2055: sciKey = 8;  break;  // ARKUI_KEYCODE_DEL -> Backspace
            case 2054: sciKey = 13; break;  // ARKUI_KEYCODE_ENTER -> Enter
            case 2049: sciKey = 9;  break;  // ARKUI_KEYCODE_TAB -> Tab
            case 2070: sciKey = 27; break;  // ARKUI_KEYCODE_ESCAPE -> Escape
        }
        if (sciKey > 0) {
            MYLOGI("OnUIInput: special key keyCode=%{public}d -> sciKey=%{public}d", keyCode, sciKey);
            BN_Sci_OnKeyDown(g_editor, sciKey, false, false, false, false);
        }
    }
}

static void OnDispatchTouchEvent(OH_NativeXComponent *component, void *window) {
    if (!g_editor) return;
    OH_NativeXComponent_TouchEvent touchEvent;
    if (OH_NativeXComponent_GetTouchEvent(component, window, &touchEvent) != 0) return;
    for (uint32_t i = 0; i < touchEvent.numPoints; i++) {
        const auto &pt = touchEvent.touchPoints[i];
        switch (pt.type) {
            case OH_NATIVEXCOMPONENT_DOWN: BN_Sci_OnTouchDown(g_editor, pt.x, pt.y, pt.timeStamp); break;
            case OH_NATIVEXCOMPONENT_MOVE: BN_Sci_OnTouchMove(g_editor, pt.x, pt.y, pt.timeStamp); break;
            case OH_NATIVEXCOMPONENT_UP: BN_Sci_OnTouchUp(g_editor, pt.x, pt.y, pt.timeStamp); break;
            default: break;
        }
    }
    RenderFrame();
}

// ============================================================================
// NAPI wrappers
// ============================================================================

static napi_value SciCreate(napi_env env, napi_callback_info info) {
    MYLOGI("SciCreate called");
    g_editor = BN_Sci_Create();
    MYLOGI("SciCreate done, editor=%{public}p", g_editor);
    // Register redraw callback so InvalidateAll/Rectangle triggers display refresh
    BN_Sci_SetRedrawCallback(RequestRedraw);
    MYLOGI("SciCreate: redraw callback registered");
    return PointerToNapi(env, g_editor);
}

static napi_value SciDestroy(napi_env env, napi_callback_info info) {
    size_t argc = 1;
    napi_value args[1];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    BN_Sci_Destroy(editor);
    if (editor == g_editor) g_editor = nullptr;
    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

static napi_value SciSetText(napi_env env, napi_callback_info info) {
    size_t argc = 2;
    napi_value args[2];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    char text[65536];
    size_t len = 0;
    napi_get_value_string_utf8(env, args[1], text, sizeof(text), &len);
    text[len] = '\0';
    BN_Sci_SetText(editor, text);
    RequestRedraw();
    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

static napi_value SciGetText(napi_env env, napi_callback_info info) {
    size_t argc = 1;
    napi_value args[1];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    int length = 0;
    const char *text = BN_Sci_GetText(editor, &length);
    napi_value result;
    if (text && length > 0) {
        napi_create_string_utf8(env, text, length, &result);
    } else {
        napi_create_string_utf8(env, "", 0, &result);
    }
    return result;
}

static napi_value SciGetLength(napi_env env, napi_callback_info info) {
    size_t argc = 1;
    napi_value args[1];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    int len = BN_Sci_GetLength(editor);
    napi_value result;
    napi_create_int32(env, len, &result);
    return result;
}

static napi_value SciGetLineCount(napi_env env, napi_callback_info info) {
    size_t argc = 1;
    napi_value args[1];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    int count = BN_Sci_GetLineCount(editor);
    napi_value result;
    napi_create_int32(env, count, &result);
    return result;
}

static napi_value SciSetFont(napi_env env, napi_callback_info info) {
    size_t argc = 3;
    napi_value args[3];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    char fontName[256];
    napi_get_value_string_utf8(env, args[1], fontName, sizeof(fontName), nullptr);
    int size = 14;
    napi_get_value_int32(env, args[2], &size);
    BN_Sci_SetFont(editor, fontName, size);
    RequestRedraw();
    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

static napi_value SciOnChar(napi_env env, napi_callback_info info) {
    size_t argc = 2;
    napi_value args[2];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    char buf[16] = {};
    size_t len = 0;
    napi_get_value_string_utf8(env, args[1], buf, sizeof(buf), &len);
    if (len > 0) {
        BN_Sci_OnChar(editor, buf, (int)len);
    }
    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

static napi_value SciOnKeyDown(napi_env env, napi_callback_info info) {
    size_t argc = 6;
    napi_value args[6];
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    void *editor = NapiToPointer(env, args[0]);
    int keyCode = 0, shift = 0, ctrl = 0, alt = 0, meta = 0;
    if (argc > 1) napi_get_value_int32(env, args[1], &keyCode);
    if (argc > 2) napi_get_value_int32(env, args[2], &shift);
    if (argc > 3) napi_get_value_int32(env, args[3], &ctrl);
    if (argc > 4) napi_get_value_int32(env, args[4], &alt);
    if (argc > 5) napi_get_value_int32(env, args[5], &meta);
    BN_Sci_OnKeyDown(editor, keyCode, shift, ctrl, alt, meta);
    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

// Touch event forwarding from ArkTS (bypasses XComponent inputMode issue on 2in1 devices)
// type: 0=Down, 1=Up, 2=Move, 3=Cancel
static napi_value SciOnTouch(napi_env env, napi_callback_info info) {
    size_t argc = 5;
    napi_value args[5] = {nullptr};
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    if (argc < 4 || !g_editor) {
        napi_value undef;
        napi_get_undefined(env, &undef);
        return undef;
    }
    // args[0] = editor (bigint), args[1] = type (int), args[2] = x (float), args[3] = y (float)
    double type = 0, x = 0, y = 0;
    napi_get_value_double(env, args[1], &type);
    napi_get_value_double(env, args[2], &x);
    napi_get_value_double(env, args[3], &y);
    double timestamp = 0;
    if (argc > 4) napi_get_value_double(env, args[4], &timestamp);

    MYLOGI("SciOnTouch: type=%{public}d x=%.1f y=%.1f", (int)type, x, y);

    // Restore BN_Sci touch handling (was disabled due to crash caused by synchronous redraw re-entrancy)
    // Now safe because RenderFrame() has re-entrancy guard
    switch ((int)type) {
        case 0: BN_Sci_OnTouchDown(g_editor, (float)x, (float)y, (uint32_t)timestamp); break;
        case 1: BN_Sci_OnTouchUp(g_editor, (float)x, (float)y, (uint32_t)timestamp); break;
        case 2: BN_Sci_OnTouchMove(g_editor, (float)x, (float)y, (uint32_t)timestamp); break;
        default: break;
    }

    // Note: Do NOT call RequestRedraw() here synchronously.
    // BN_Sci_OnTouch* may have already triggered InvalidateAll → RequestRedraw → RenderFrame
    // via the registered callback. The ArkTS caller (.onTouch handler) will call
    // sciRequestRedraw() afterwards to ensure the frame is flushed to screen.
    g_needsRedraw.store(1);

    napi_value undef;
    napi_get_undefined(env, &undef);
    return undef;
}

// Called from ArkTS via setInterval to drive caret blink timer
static napi_value SciTick(napi_env env, napi_callback_info info) {
    size_t argc = 1;
    napi_value args[1] = {nullptr};
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    if (argc > 0 && g_editor) {
        BN_Sci_Tick(g_editor);
    }
    // After tick, check if redraw is needed and render
    if (g_needsRedraw.load() && !g_rendering.load()) {
        RenderFrame();
    }
    napi_value undef;
    napi_get_undefined(env, &undef);
    return undef;
}

// Called from ArkTS onSurfaceChanged - update surface size and re-init if needed
static napi_value SciOnSurfaceChanged(napi_env env, napi_callback_info info) {
    size_t argc = 2;
    napi_value args[2] = {nullptr};
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
    if (argc < 2) {
        napi_value undef;
        napi_get_undefined(env, &undef);
        return undef;
    }
    double w = 0, h = 0;
    napi_get_value_double(env, args[0], &w);
    napi_get_value_double(env, args[1], &h);
    MYLOGI("SciOnSurfaceChanged: %{public}.0fx%{public}.0f (editor=%{public}p, nw=%{public}p)",
           w, h, (void*)g_editor, (void*)g_nativeWindow);
    g_surfaceWidth = (uint64_t)w;
    g_surfaceHeight = (uint64_t)h;
    if (g_editor && w > 0 && h > 0) {
        BN_Sci_SetSize(g_editor, (int)w, (int)h);
        // If not yet initialized (size was 0 during onSurfaceCreated), init now
        if (!g_nativeWindow) {
            MYLOGW("SciOnSurfaceChanged: no nativeWindow yet, cannot render");
        } else {
            BN_Sci_Init(g_editor, (int)w, (int)h);
            RenderFrame();
            MYLOGI("SciOnSurfaceChanged: rendered");
        }
    }
    napi_value undef;
    napi_get_undefined(env, &undef);
    return undef;
}

// Request a redraw from ArkTS side
static napi_value SciRequestRedraw(napi_env env, napi_callback_info info) {
    RequestRedraw();
    napi_value undef;
    napi_get_undefined(env, &undef);
    return undef;
}

// Called from ArkTS onLoad - register callbacks and init rendering via surfaceId
static napi_value SciRegisterXComponent(napi_env env, napi_callback_info info) {
    MYLOGI("SciRegisterXComponent: g_nativeXComponent=%{public}p, registered=%{public}d",
           g_nativeXComponent, (int)g_callbacksRegistered);

    size_t argc = 1;
    napi_value args[1] = {nullptr};
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

    char surfaceId[256] = {0};
    if (argc > 0 && args[0] != nullptr) {
        napi_valuetype t;
        napi_typeof(env, args[0], &t);
        if (t == napi_string) {
            size_t len = 0;
            napi_get_value_string_utf8(env, args[0], surfaceId, sizeof(surfaceId), &len);
            MYLOGI("SciRegisterXComponent: surfaceId='%{public}s'", surfaceId);
        }
    }

    // Register callbacks (safe here, not during Init)
    if (g_nativeXComponent && !g_callbacksRegistered) {
        RegisterXComponentCallbacks(g_nativeXComponent);
        g_callbacksRegistered = true;
        MYLOGI("SciRegisterXComponent: callbacks registered");
    }

    // Create NativeWindow from surfaceId
    if (surfaceId[0] != '\0') {
        uint64_t sid = strtoull(surfaceId, nullptr, 10);
        OHNativeWindow *nw = nullptr;
        int wret = OH_NativeWindow_CreateNativeWindowFromSurfaceId(sid, &nw);
        MYLOGI("SciRegisterXComponent: CreateNW ret=%{public}d nw=%{public}p", wret, nw);
        if (wret == 0 && nw) {
            g_nativeWindow = nw;
            // Get size from NativeWindow directly (not OH_NativeXComponent_GetXComponentSize
            // since g_nativeXComponent is nullptr without libraryname)
            int32_t nw_w = 0, nw_h = 0;
            OH_NativeWindow_NativeWindowHandleOpt(nw, GET_BUFFER_GEOMETRY, &nw_w, &nw_h);
            g_surfaceWidth = (uint64_t)nw_w;
            g_surfaceHeight = (uint64_t)nw_h;
            MYLOGI("SciRegisterXComponent: NativeWindow size=%{public}dx%{public}d", nw_w, nw_h);
            if (g_editor && nw_w > 0 && nw_h > 0) {
                BN_Sci_Init(g_editor, nw_w, nw_h);
                RenderFrame();
            } else if (g_editor) {
                MYLOGW("SciRegisterXComponent: size is 0x0, deferring init to onSurfaceChanged");
            }
            MYLOGI("SciRegisterXComponent: init done");
        }
    }

    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

static napi_value SciUnregisterXComponent(napi_env env, napi_callback_info info) {
    MYLOGI("SciUnregisterXComponent");
    g_nativeXComponent = nullptr;
    napi_value undefined;
    napi_get_undefined(env, &undefined);
    return undefined;
}

// ============================================================================
// OH_ArkUI_SurfaceHolder based binding (no libraryname)
// ============================================================================

// Forward declarations
static void OnSurfaceCreatedNative(OH_ArkUI_SurfaceHolder *holder);
static void OnSurfaceChangedNative(OH_ArkUI_SurfaceHolder *holder, uint64_t width, uint64_t height);
static void OnSurfaceDestroyedNative(OH_ArkUI_SurfaceHolder *holder);
static void OnNodeEvent(ArkUI_NodeEvent *event);

static napi_value SciBindNode(napi_env env, napi_callback_info info) {
    MYLOGI("SciBindNode: called");
    size_t argc = 2;
    napi_value args[2] = {nullptr};
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

    // args[0] = id string, args[1] = FrameNode object
    char nodeId[256] = {0};
    size_t idLen = 0;
    napi_get_value_string_utf8(env, args[0], nodeId, sizeof(nodeId), &idLen);
    MYLOGI("SciBindNode: nodeId='%{public}s'", nodeId);

    // Get ArkUI_NodeHandle from FrameNode
    ArkUI_NodeHandle handle = nullptr;
    int32_t ret = OH_ArkUI_GetNodeHandleFromNapiValue(env, args[1], &handle);
    MYLOGI("SciBindNode: GetNodeHandle ret=%{public}d handle=%{public}p", ret, handle);
    if (ret != 0 || !handle) {
        MYLOGE("SciBindNode: failed to get node handle");
        napi_value undef;
        napi_get_undefined(env, &undef);
        return undef;
    }

    g_nodeHandle = handle;

    // Get nodeAPI for event registration
    g_nodeAPI = reinterpret_cast<ArkUI_NativeNodeAPI_1 *>(
        OH_ArkUI_QueryModuleInterfaceByName(ARKUI_NATIVE_NODE, "ArkUI_NativeNodeAPI_1"));
    MYLOGI("SciBindNode: nodeAPI=%{public}p", (void*)g_nodeAPI);

    // Create SurfaceHolder
    g_surfaceHolder = OH_ArkUI_SurfaceHolder_Create(handle);
    MYLOGI("SciBindNode: SurfaceHolder=%{public}p", (void*)g_surfaceHolder);

    if (g_surfaceHolder) {
        // Create and register Surface callbacks
        g_surfaceCallback = OH_ArkUI_SurfaceCallback_Create();
        if (g_surfaceCallback) {
            OH_ArkUI_SurfaceCallback_SetSurfaceCreatedEvent(g_surfaceCallback, OnSurfaceCreatedNative);
            OH_ArkUI_SurfaceCallback_SetSurfaceChangedEvent(g_surfaceCallback, OnSurfaceChangedNative);
            OH_ArkUI_SurfaceCallback_SetSurfaceDestroyedEvent(g_surfaceCallback, OnSurfaceDestroyedNative);
            OH_ArkUI_SurfaceHolder_AddSurfaceCallback(g_surfaceHolder, g_surfaceCallback);
            MYLOGI("SciBindNode: Surface callbacks registered");
        }

        // Set up editor and initial text now that we have the handle
        if (g_editor) {
            BN_Sci_SetRedrawCallback(RequestRedraw);
            MYLOGI("SciBindNode: redraw callback set");
        }
    }

    // Register NDK event listeners
    if (g_nodeAPI) {
        // Add node event receiver
        int32_t addRet = g_nodeAPI->addNodeEventReceiver(handle, OnNodeEvent);
        MYLOGI("SciBindNode: addNodeEventReceiver ret=%{public}d", addRet);

        // Register touch event
        int32_t touchRet = g_nodeAPI->registerNodeEvent(handle, NODE_TOUCH_EVENT, 0, nullptr);
        MYLOGI("SciBindNode: registerNodeEvent TOUCH ret=%{public}d", touchRet);

        // Register key event
        int32_t keyRet = g_nodeAPI->registerNodeEvent(handle, NODE_ON_KEY_EVENT, 1, nullptr);
        MYLOGI("SciBindNode: registerNodeEvent KEY ret=%{public}d", keyRet);
    }

    napi_value undef;
    napi_get_undefined(env, &undef);
    return undef;
}

static napi_value SciUnbindNode(napi_env env, napi_callback_info info) {
    MYLOGI("SciUnbindNode: called");
    size_t argc = 1;
    napi_value args[1] = {nullptr};
    napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

    if (g_nodeAPI && g_nodeHandle) {
        g_nodeAPI->unregisterNodeEvent(g_nodeHandle, NODE_TOUCH_EVENT);
        g_nodeAPI->unregisterNodeEvent(g_nodeHandle, NODE_ON_KEY_EVENT);
    }

    if (g_surfaceHolder && g_surfaceCallback) {
        OH_ArkUI_SurfaceHolder_RemoveSurfaceCallback(g_surfaceHolder, g_surfaceCallback);
        OH_ArkUI_SurfaceCallback_Dispose(g_surfaceCallback);
        g_surfaceCallback = nullptr;
    }

    if (g_surfaceHolder) {
        OH_ArkUI_SurfaceHolder_Dispose(g_surfaceHolder);
        g_surfaceHolder = nullptr;
    }

    g_nodeHandle = nullptr;
    g_nativeWindow = nullptr;

    napi_value undef;
    napi_get_undefined(env, &undef);
    return undef;
}

// ============================================================================
// SurfaceHolder lifecycle callbacks
// ============================================================================

static void OnSurfaceCreatedNative(OH_ArkUI_SurfaceHolder *holder) {
    MYLOGI("OnSurfaceCreatedNative: holder=%{public}p", (void*)holder);
    if (!holder) return;

    OHNativeWindow *window = OH_ArkUI_XComponent_GetNativeWindow(holder);
    MYLOGI("OnSurfaceCreatedNative: nativeWindow=%{public}p", (void*)window);
    if (!window) { MYLOGE("OnSurfaceCreatedNative: window is NULL"); return; }

    g_nativeWindow = window;

    // Get surface size from NativeWindow
    int32_t w = 0, h = 0;
    OH_NativeWindow_NativeWindowHandleOpt(g_nativeWindow, GET_BUFFER_GEOMETRY, &w, &h);
    g_surfaceWidth = (uint64_t)w;
    g_surfaceHeight = (uint64_t)h;
    MYLOGI("OnSurfaceCreatedNative: size=%{public}dx%{public}d", w, h);

    if (g_editor) {
        BN_Sci_Init(g_editor, w, h);
        MYLOGI("OnSurfaceCreatedNative: BN_Sci_Init done");

        // Set font and sample text
        BN_Sci_SetFont(g_editor, "HarmonyOS Sans", 16);

        const char *sampleText =
            "Hello HarmonyOS!\n\n"
            "欢迎使用 MyNotePad\n"
            "基于 Scintilla 5.6.1 的原生文本编辑器\n\n"
            "Features:\n"
            "  - Scintilla 5.6.1 editor core\n"
            "  - HarmonyOS Native Drawing API\n"
            "  - NAPI bridge\n"
            "  - XComponent integration\n\n"
            "function hello() {\n  console.log(\"Hello World!\");\n}\n";
        BN_Sci_SetText(g_editor, sampleText);
    }
    RenderFrame();
}

static void OnSurfaceChangedNative(OH_ArkUI_SurfaceHolder *holder, uint64_t width, uint64_t height) {
    MYLOGI("OnSurfaceChangedNative: %{public}lux%{public}lu", (unsigned long)width, (unsigned long)height);
    g_surfaceWidth = width;
    g_surfaceHeight = height;
    if (g_editor) { BN_Sci_SetSize(g_editor, (int)width, (int)height); }
    if (g_needsRedraw.load()) { RenderFrame(); }
}

static void OnSurfaceDestroyedNative(OH_ArkUI_SurfaceHolder *holder) {
    MYLOGI("OnSurfaceDestroyedNative");
    g_nativeWindow = nullptr;
    g_surfaceWidth = 0;
    g_surfaceHeight = 0;
}

// ============================================================================
// NDK node event callback (touch, key, mouse)
// ============================================================================

static void OnNodeEvent(ArkUI_NodeEvent *event) {
    if (!event) return;

    auto eventType = OH_ArkUI_NodeEvent_GetEventType(event);
    MYLOGI("OnNodeEvent: type=%{public}d", (int)eventType);

    if (eventType == NODE_TOUCH_EVENT) {
        if (!g_editor) return;
        ArkUI_UIInputEvent *inputEvent = OH_ArkUI_NodeEvent_GetInputEvent(event);
        if (!inputEvent) { MYLOGW("OnNodeEvent: TOUCH but no inputEvent"); return; }

        int32_t action = OH_ArkUI_UIInputEvent_GetAction(inputEvent);
        float x = OH_ArkUI_PointerEvent_GetX(inputEvent);
        float y = OH_ArkUI_PointerEvent_GetY(inputEvent);
        uint32_t timestamp = (uint32_t)(OH_ArkUI_UIInputEvent_GetEventTime(inputEvent) / 1000000); // ns -> ms

        MYLOGI("OnNodeEvent: TOUCH action=%{public}d x=%.1f y=%.1f ts=%{public}u", action, x, y, timestamp);

        switch (action) {
            case UI_TOUCH_EVENT_ACTION_DOWN:
                BN_Sci_OnTouchDown(g_editor, x, y, timestamp);
                break;
            case UI_TOUCH_EVENT_ACTION_MOVE:
                BN_Sci_OnTouchMove(g_editor, x, y, timestamp);
                break;
            case UI_TOUCH_EVENT_ACTION_UP:
                BN_Sci_OnTouchUp(g_editor, x, y, timestamp);
                break;
            default:
                break;
        }
        RequestRedraw();
    } else if (eventType == NODE_ON_KEY_EVENT) {
        if (!g_editor) return;
        ArkUI_UIInputEvent *inputEvent = OH_ArkUI_NodeEvent_GetInputEvent(event);
        if (!inputEvent) { MYLOGW("OnNodeEvent: KEY but no inputEvent"); return; }

        ArkUI_KeyEventType keyType = OH_ArkUI_KeyEvent_GetType(inputEvent);
        int32_t keyCode = OH_ArkUI_KeyEvent_GetKeyCode(inputEvent);
        uint32_t unicode = OH_ArkUI_KeyEvent_GetUnicode(inputEvent);

        MYLOGI("OnNodeEvent: KEY type=%{public}d code=%{public}d unicode=0x%{public}x",
               (int)keyType, keyCode, unicode);

        if (keyType != ARKUI_KEY_EVENT_DOWN) return;

        if (unicode > 0) {
            char utf8[8] = {};
            int utf8len = 0;
            if (unicode < 0x80) {
                utf8[0] = (char)unicode; utf8len = 1;
            } else if (unicode < 0x800) {
                utf8[0] = 0xC0 | (unicode >> 6);
                utf8[1] = 0x80 | (unicode & 0x3F); utf8len = 2;
            } else if (unicode < 0x10000) {
                utf8[0] = 0xE0 | (unicode >> 12);
                utf8[1] = 0x80 | ((unicode >> 6) & 0x3F);
                utf8[2] = 0x80 | (unicode & 0x3F); utf8len = 3;
            }
            BN_Sci_OnChar(g_editor, utf8, utf8len);
            RequestRedraw();
        } else {
            int sciKey = 0;
            switch (keyCode) {
                case 2055: sciKey = 8;  break; // DEL -> Backspace
                case 2054: sciKey = 13; break; // ENTER
                case 2049: sciKey = 9;  break; // TAB
                case 2070: sciKey = 27; break; // ESCAPE
            }
            if (sciKey > 0) {
                BN_Sci_OnKeyDown(g_editor, sciKey, false, false, false, false);
                RequestRedraw();
            }
        }
    } else if (eventType == NODE_ON_HOVER_EVENT || eventType == NODE_ON_CLICK_EVENT) {
        // Mouse hover/click events
        if (!g_editor) return;
        ArkUI_UIInputEvent *inputEvent = OH_ArkUI_NodeEvent_GetInputEvent(event);
        if (!inputEvent) return;

        float x = OH_ArkUI_PointerEvent_GetX(inputEvent);
        float y = OH_ArkUI_PointerEvent_GetY(inputEvent);
        MYLOGI("OnNodeEvent: HOVER/CLICK type=%{public}d x=%.1f y=%.1f", (int)eventType, x, y);
    }
}

// ============================================================================
// NAPI module registration (Init)
// ============================================================================

EXTERN_C_START
static napi_value Init(napi_env env, napi_value exports) {
    MYLOGI("Init: looking for OH_NATIVE_XCOMPONENT_OBJ on exports");

    // Check if XComponent object exists and register callbacks immediately.
    // The previous crash was caused by napi_get_property_names, NOT by
    // RegisterCallback itself. Registering here ensures callbacks are ready
    // before the framework calls OnSurfaceCreated.
    napi_value exportInstance = nullptr;
    napi_status s = napi_get_named_property(env, exports, OH_NATIVE_XCOMPONENT_OBJ, &exportInstance);
    if (s == napi_ok && exportInstance != nullptr) {
        OH_NativeXComponent *nativeXComponent = nullptr;
        s = napi_unwrap(env, exportInstance, reinterpret_cast<void**>(&nativeXComponent));
        if (s == napi_ok && nativeXComponent != nullptr) {
            g_nativeXComponent = nativeXComponent;
            char idBuf[128] = {0};
            uint64_t idLen = sizeof(idBuf);
            OH_NativeXComponent_GetXComponentId(nativeXComponent, idBuf, &idLen);

            char initDbg[256];
            snprintf(initDbg, sizeof(initDbg), "Init: got NativeXComponent=%p, id='%s', saved for later",
                     nativeXComponent, idBuf);
            MYLOGI("%{public}s", initDbg);
        } else {
            MYLOGW("Init: napi_unwrap failed, status=%{public}d (XComponent not ready yet)", (int)s);
        }
    } else {
        MYLOGW("Init: OH_NATIVE_XCOMPONENT_OBJ not on exports (status=%{public}d)", (int)s);
    }

    napi_property_descriptor desc[] = {
        { "sciCreate", nullptr, SciCreate, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciDestroy", nullptr, SciDestroy, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciSetText", nullptr, SciSetText, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciGetText", nullptr, SciGetText, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciGetLength", nullptr, SciGetLength, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciGetLineCount", nullptr, SciGetLineCount, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciSetFont", nullptr, SciSetFont, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciOnChar", nullptr, SciOnChar, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciOnKeyDown", nullptr, SciOnKeyDown, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciRegisterXComponent", nullptr, SciRegisterXComponent, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciUnregisterXComponent", nullptr, SciUnregisterXComponent, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciBindNode", nullptr, SciBindNode, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciUnbindNode", nullptr, SciUnbindNode, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciOnTouch", nullptr, SciOnTouch, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciRequestRedraw", nullptr, SciRequestRedraw, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciOnSurfaceChanged", nullptr, SciOnSurfaceChanged, nullptr, nullptr, nullptr, napi_default, nullptr },
        { "sciTick", nullptr, SciTick, nullptr, nullptr, nullptr, napi_default, nullptr },
    };
    napi_define_properties(env, exports, sizeof(desc) / sizeof(desc[0]), desc);
    return exports;
}
EXTERN_C_END

// ============================================================================
// Module entry point
// ============================================================================

static napi_module mynotepadModule = {
    .nm_version = 1,
    .nm_flags = 0,
    .nm_filename = nullptr,
    .nm_register_func = Init,
    .nm_modname = "entry",
    .nm_priv = ((void*)0),
    .reserved = { 0 },
};

extern "C" __attribute__((constructor)) void RegisterEntryModule(void) {
    napi_module_register(&mynotepadModule);
}
