// dear imgui: Platform Backend for OpenHarmony/HarmonyOS Native XComponent

#include "imgui.h"
#ifndef IMGUI_DISABLE
#include "imgui_impl_ohos.h"

#include <ace/xcomponent/native_interface_xcomponent.h>
#include <ace/xcomponent/native_xcomponent_key_event.h>
#include <time.h>

struct ImGui_ImplOHOS_Data {
    OH_NativeXComponent* Component;
    void* Window;
    uint64_t Width;
    uint64_t Height;
    double Time;
    OH_NativeXComponent_Callback SurfaceCallbacks;
    OH_NativeXComponent_MouseEvent_Callback MouseCallbacks;
};

static ImGui_ImplOHOS_Data* g_Data = nullptr;

static ImGuiKey ImGui_ImplOHOS_KeyCodeToImGuiKey(int key_code)
{
    switch (key_code)
    {
        case KEY_TAB: return ImGuiKey_Tab;
        case KEY_DPAD_LEFT: return ImGuiKey_LeftArrow;
        case KEY_DPAD_RIGHT: return ImGuiKey_RightArrow;
        case KEY_DPAD_UP: return ImGuiKey_UpArrow;
        case KEY_DPAD_DOWN: return ImGuiKey_DownArrow;
        case KEY_PAGE_UP: return ImGuiKey_PageUp;
        case KEY_PAGE_DOWN: return ImGuiKey_PageDown;
        case KEY_HOME: return ImGuiKey_Home;
        case KEY_FORWARD_DEL: return ImGuiKey_Delete;
        case KEY_DEL: return ImGuiKey_Backspace;
        case KEY_SPACE: return ImGuiKey_Space;
        case KEY_ENTER: return ImGuiKey_Enter;
        case KEY_ESCAPE: return ImGuiKey_Escape;
        case KEY_APOSTROPHE: return ImGuiKey_Apostrophe;
        case KEY_COMMA: return ImGuiKey_Comma;
        case KEY_MINUS: return ImGuiKey_Minus;
        case KEY_PERIOD: return ImGuiKey_Period;
        case KEY_SLASH: return ImGuiKey_Slash;
        case KEY_SEMICOLON: return ImGuiKey_Semicolon;
        case KEY_EQUALS: return ImGuiKey_Equal;
        case KEY_LEFT_BRACKET: return ImGuiKey_LeftBracket;
        case KEY_BACKSLASH: return ImGuiKey_Backslash;
        case KEY_RIGHT_BRACKET: return ImGuiKey_RightBracket;
        case KEY_GRAVE: return ImGuiKey_GraveAccent;
        case KEY_CAPS_LOCK: return ImGuiKey_CapsLock;
        case KEY_SCROLL_LOCK: return ImGuiKey_ScrollLock;
        case KEY_CTRL_LEFT: return ImGuiKey_LeftCtrl;
        case KEY_CTRL_RIGHT: return ImGuiKey_RightCtrl;
        case KEY_SHIFT_LEFT: return ImGuiKey_LeftShift;
        case KEY_SHIFT_RIGHT: return ImGuiKey_RightShift;
        case KEY_ALT_LEFT: return ImGuiKey_LeftAlt;
        case KEY_ALT_RIGHT: return ImGuiKey_RightAlt;
        case KEY_META_LEFT: return ImGuiKey_LeftSuper;
        case KEY_META_RIGHT: return ImGuiKey_RightSuper;
        case KEY_MENU: return ImGuiKey_Menu;
        default:
            if (key_code >= KEY_A && key_code <= KEY_Z)
                return static_cast<ImGuiKey>(
                    ImGuiKey_A + key_code - KEY_A);
            return ImGuiKey_None;
    }
}

void ImGui_ImplOHOS_HandleTouch(float x, float y, bool pressed)
{
    ImGuiIO& io = ImGui::GetIO();
    io.AddMouseSourceEvent(ImGuiMouseSource_TouchScreen);
    io.AddMousePosEvent(x, y);
    io.AddMouseButtonEvent(0, pressed);
}

void ImGui_ImplOHOS_HandleMouse(
    float x, float y, int button, bool pressed)
{
    ImGuiIO& io = ImGui::GetIO();
    io.AddMouseSourceEvent(ImGuiMouseSource_Mouse);
    io.AddMousePosEvent(x, y);
    if (button >= 0 && button < ImGuiMouseButton_COUNT)
        io.AddMouseButtonEvent(button, pressed);
}

void ImGui_ImplOHOS_HandleKey(int key_code, bool pressed)
{
    ImGuiIO& io = ImGui::GetIO();
    const ImGuiKey key = ImGui_ImplOHOS_KeyCodeToImGuiKey(key_code);
    if (key != ImGuiKey_None)
    {
        io.AddKeyEvent(key, pressed);
        io.SetKeyEventNativeData(key, key_code, key_code);
    }
}

void ImGui_ImplOHOS_HandleUnicode(unsigned int codepoint)
{
    ImGui::GetIO().AddInputCharacter(codepoint);
}

static void ImGui_ImplOHOS_OnSurfaceCreated(
    OH_NativeXComponent* component, void* window)
{
    if (g_Data == nullptr)
        return;
    g_Data->Window = window;
    OH_NativeXComponent_GetXComponentSize(
        component, window, &g_Data->Width, &g_Data->Height);
}

static void ImGui_ImplOHOS_OnSurfaceChanged(
    OH_NativeXComponent* component, void* window)
{
    if (g_Data == nullptr)
        return;
    g_Data->Window = window;
    OH_NativeXComponent_GetXComponentSize(
        component, window, &g_Data->Width, &g_Data->Height);
}

static void ImGui_ImplOHOS_OnSurfaceDestroyed(
    OH_NativeXComponent*, void*)
{
    if (g_Data == nullptr)
        return;
    g_Data->Window = nullptr;
    g_Data->Width = 0;
    g_Data->Height = 0;
}

static void ImGui_ImplOHOS_OnTouch(
    OH_NativeXComponent* component, void* window)
{
    OH_NativeXComponent_TouchEvent event = {};
    if (OH_NativeXComponent_GetTouchEvent(
            component, window, &event) != 0)
        return;
    ImGuiIO& io = ImGui::GetIO();
    for (uint32_t index = 0; index < event.numPoints; ++index)
    {
        const OH_NativeXComponent_TouchPoint& point =
            event.touchPoints[index];
        io.AddMouseSourceEvent(ImGuiMouseSource_TouchScreen);
        io.AddMousePosEvent(point.x, point.y);
        if (point.type == OH_NATIVEXCOMPONENT_DOWN)
            io.AddMouseButtonEvent(0, true);
        else if (point.type == OH_NATIVEXCOMPONENT_UP)
            io.AddMouseButtonEvent(0, false);
    }
}

static int ImGui_ImplOHOS_MouseButton(
    OH_NativeXComponent_MouseEventButton button)
{
    switch (button)
    {
        case OH_NATIVEXCOMPONENT_LEFT_BUTTON: return 0;
        case OH_NATIVEXCOMPONENT_RIGHT_BUTTON: return 1;
        case OH_NATIVEXCOMPONENT_MIDDLE_BUTTON: return 2;
        default: return -1;
    }
}

static void ImGui_ImplOHOS_OnMouse(
    OH_NativeXComponent* component, void* window)
{
    OH_NativeXComponent_MouseEvent event = {};
    if (OH_NativeXComponent_GetMouseEvent(
            component, window, &event) != 0)
        return;
    ImGuiIO& io = ImGui::GetIO();
    io.AddMouseSourceEvent(ImGuiMouseSource_Mouse);
    io.AddMousePosEvent(event.x, event.y);
    const int button = ImGui_ImplOHOS_MouseButton(event.button);
    if (button >= 0 &&
        event.action == OH_NATIVEXCOMPONENT_MOUSE_PRESS)
        io.AddMouseButtonEvent(button, true);
    else if (button >= 0 &&
             event.action == OH_NATIVEXCOMPONENT_MOUSE_RELEASE)
        io.AddMouseButtonEvent(button, false);
}

static void ImGui_ImplOHOS_OnHover(
    OH_NativeXComponent*, bool)
{
}

static void ImGui_ImplOHOS_OnKey(
    OH_NativeXComponent* component, void*)
{
    OH_NativeXComponent_KeyEvent* event = nullptr;
    OH_NativeXComponent_KeyAction action;
    OH_NativeXComponent_KeyCode code;
    if (OH_NativeXComponent_GetKeyEvent(component, &event) != 0 ||
        event == nullptr ||
        OH_NativeXComponent_GetKeyEventAction(event, &action) != 0 ||
        OH_NativeXComponent_GetKeyEventCode(event, &code) != 0)
        return;
    if (action == OH_NATIVEXCOMPONENT_KEY_ACTION_DOWN ||
        action == OH_NATIVEXCOMPONENT_KEY_ACTION_UP)
        ImGui_ImplOHOS_HandleKey(
            static_cast<int>(code),
            action == OH_NATIVEXCOMPONENT_KEY_ACTION_DOWN);
}

bool ImGui_ImplOHOS_Init(OH_NativeXComponent* component)
{
    IMGUI_CHECKVERSION();
    ImGuiIO& io = ImGui::GetIO();
    IM_ASSERT(io.BackendPlatformUserData == nullptr);
    if (component == nullptr || g_Data != nullptr)
        return false;

    void* data_memory = IM_ALLOC(sizeof(ImGui_ImplOHOS_Data));
    if (data_memory == nullptr)
        return false;
    ImGui_ImplOHOS_Data* data =
        IM_PLACEMENT_NEW(data_memory) ImGui_ImplOHOS_Data();
    data->Component = component;
    data->SurfaceCallbacks.OnSurfaceCreated =
        ImGui_ImplOHOS_OnSurfaceCreated;
    data->SurfaceCallbacks.OnSurfaceChanged =
        ImGui_ImplOHOS_OnSurfaceChanged;
    data->SurfaceCallbacks.OnSurfaceDestroyed =
        ImGui_ImplOHOS_OnSurfaceDestroyed;
    data->SurfaceCallbacks.DispatchTouchEvent =
        ImGui_ImplOHOS_OnTouch;
    data->MouseCallbacks.DispatchMouseEvent =
        ImGui_ImplOHOS_OnMouse;
    data->MouseCallbacks.DispatchHoverEvent =
        ImGui_ImplOHOS_OnHover;

    g_Data = data;
    io.BackendPlatformUserData = data;
    io.BackendPlatformName = "imgui_impl_ohos";

    const int surface_result =
        OH_NativeXComponent_RegisterCallback(
            component, &data->SurfaceCallbacks);
    const int mouse_result =
        OH_NativeXComponent_RegisterMouseEventCallback(
            component, &data->MouseCallbacks);
    const int key_result =
        OH_NativeXComponent_RegisterKeyEventCallback(
            component, ImGui_ImplOHOS_OnKey);
    OH_NativeXComponent_SetNeedSoftKeyboard(component, true);
    if (surface_result != 0 || mouse_result != 0 ||
        key_result != 0)
    {
        ImGui_ImplOHOS_Shutdown();
        return false;
    }
    return true;
}

void ImGui_ImplOHOS_Shutdown()
{
    if (g_Data == nullptr)
        return;
    ImGuiIO& io = ImGui::GetIO();
    io.BackendPlatformName = nullptr;
    io.BackendPlatformUserData = nullptr;
    IM_DELETE(g_Data);
    g_Data = nullptr;
}

void ImGui_ImplOHOS_NewFrame()
{
    ImGuiIO& io = ImGui::GetIO();
    if (g_Data != nullptr &&
        g_Data->Width > 0 && g_Data->Height > 0)
        io.DisplaySize = ImVec2(
            static_cast<float>(g_Data->Width),
            static_cast<float>(g_Data->Height));

    timespec now = {};
    clock_gettime(CLOCK_MONOTONIC, &now);
    const double current =
        static_cast<double>(now.tv_sec) +
        static_cast<double>(now.tv_nsec) / 1000000000.0;
    io.DeltaTime = (g_Data != nullptr && g_Data->Time > 0.0)
        ? static_cast<float>(current - g_Data->Time)
        : 1.0f / 60.0f;
    if (g_Data != nullptr)
        g_Data->Time = current;
}

bool ImGui_ImplOHOS_HasSurface()
{
    return g_Data != nullptr && g_Data->Window != nullptr &&
           g_Data->Width > 0 && g_Data->Height > 0;
}

#endif
