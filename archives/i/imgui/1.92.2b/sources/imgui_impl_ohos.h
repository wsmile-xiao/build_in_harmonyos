// dear imgui: Platform Backend for OpenHarmony/HarmonyOS Native XComponent
#pragma once

#include "imgui.h"
#include <ace/xcomponent/native_interface_xcomponent.h>

IMGUI_IMPL_API bool ImGui_ImplOHOS_Init(
    OH_NativeXComponent* component);
IMGUI_IMPL_API void ImGui_ImplOHOS_Shutdown();
IMGUI_IMPL_API void ImGui_ImplOHOS_NewFrame();

// Public event entry points are useful when an application receives input
// through ArkUI APIs other than the callbacks registered by Init().
IMGUI_IMPL_API void ImGui_ImplOHOS_HandleTouch(
    float x, float y, bool pressed);
IMGUI_IMPL_API void ImGui_ImplOHOS_HandleMouse(
    float x, float y, int button, bool pressed);
IMGUI_IMPL_API void ImGui_ImplOHOS_HandleKey(
    int key_code, bool pressed);
IMGUI_IMPL_API void ImGui_ImplOHOS_HandleUnicode(
    unsigned int codepoint);
IMGUI_IMPL_API bool ImGui_ImplOHOS_HasSurface();
