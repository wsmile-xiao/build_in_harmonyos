#include "test_imgui_platform.h"

#include <iostream>

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <imgui.h>
#include <imgui_impl_ohos.h>
#include <imgui_impl_opengl3.h>

static bool CheckOHOSHeadlessInput()
{
    ImGuiIO& io = ImGui::GetIO();
    unsigned char* pixels = nullptr;
    int texture_width = 0;
    int texture_height = 0;
    io.Fonts->GetTexDataAsRGBA32(
        &pixels, &texture_width, &texture_height);
    io.Fonts->SetTexID(static_cast<ImTextureID>(1));
    io.ConfigInputTrickleEventQueue = false;
    io.DisplaySize = ImVec2(64.0f, 64.0f);
    ImGui_ImplOHOS_HandleTouch(24.0f, 32.0f, true);
    ImGui_ImplOHOS_HandleKey(2054, true);
    ImGui_ImplOHOS_HandleUnicode('H');
    ImGui_ImplOHOS_NewFrame();
    ImGui::NewFrame();

    const bool touch_ok =
        io.MousePos.x == 24.0f && io.MousePos.y == 32.0f &&
        io.MouseDown[0];
    const bool key_ok = ImGui::IsKeyDown(ImGuiKey_Enter);
    const bool unicode_ok = io.InputQueueCharacters.Size > 0;
    ImGui::SetNextWindowPos(ImVec2(1.0f, 1.0f));
    ImGui::SetNextWindowSize(ImVec2(60.0f, 60.0f));
    ImGui::Begin("OHOS headless input");
    ImGui::TextUnformatted("NativeXComponent input mapping");
    ImGui::End();
    ImGui::Render();
    ImDrawData* draw_data = ImGui::GetDrawData();
    const bool draw_data_ok =
        draw_data != nullptr && draw_data->CmdListsCount > 0;
    const bool font_atlas_ok =
        pixels != nullptr && texture_width > 0 && texture_height > 0;
    if (!font_atlas_ok || !touch_ok || !key_ok ||
        !unicode_ok || !draw_data_ok)
    {
        std::cerr << "OHOS headless input check failed\n";
        return false;
    }
    return true;
}

bool CheckPlatformBackends(bool headless)
{
    if (headless)
        return CheckOHOSHeadlessInput();

    EGLDisplay display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    EGLConfig config = nullptr;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext egl_context = EGL_NO_CONTEXT;
    EGLint config_count = 0;
    const EGLint config_attributes[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    const EGLint surface_attributes[] = {
        EGL_WIDTH, 64,
        EGL_HEIGHT, 64,
        EGL_NONE
    };
    const EGLint context_attributes[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };

    if (display == EGL_NO_DISPLAY ||
        eglInitialize(display, nullptr, nullptr) != EGL_TRUE ||
        eglBindAPI(EGL_OPENGL_ES_API) != EGL_TRUE ||
        eglChooseConfig(
            display, config_attributes, &config, 1,
            &config_count) != EGL_TRUE ||
        config_count != 1)
    {
        std::cerr << "OHOS EGL display/config initialization failed\n";
        return false;
    }
    surface = eglCreatePbufferSurface(
        display, config, surface_attributes);
    egl_context = eglCreateContext(
        display, config, EGL_NO_CONTEXT, context_attributes);
    if (surface == EGL_NO_SURFACE ||
        egl_context == EGL_NO_CONTEXT ||
        eglMakeCurrent(
            display, surface, surface, egl_context) != EGL_TRUE)
    {
        std::cerr << "OHOS EGL context creation failed\n";
        if (egl_context != EGL_NO_CONTEXT)
            eglDestroyContext(display, egl_context);
        if (surface != EGL_NO_SURFACE)
            eglDestroySurface(display, surface);
        eglTerminate(display);
        return false;
    }
    if (!ImGui_ImplOpenGL3_Init("#version 300 es"))
    {
        std::cerr << "OHOS GLES3 renderer initialization failed\n";
        eglMakeCurrent(
            display, EGL_NO_SURFACE, EGL_NO_SURFACE,
            EGL_NO_CONTEXT);
        eglDestroyContext(display, egl_context);
        eglDestroySurface(display, surface);
        eglTerminate(display);
        return false;
    }

    ImGuiIO& io = ImGui::GetIO();
    io.ConfigInputTrickleEventQueue = false;
    io.DisplaySize = ImVec2(64.0f, 64.0f);
    ImGui_ImplOHOS_HandleTouch(24.0f, 32.0f, true);
    ImGui_ImplOHOS_HandleKey(2054, true);
    ImGui_ImplOHOS_HandleUnicode('H');
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplOHOS_NewFrame();
    ImGui::NewFrame();

    const bool touch_ok =
        io.MousePos.x == 24.0f && io.MousePos.y == 32.0f &&
        io.MouseDown[0];
    const bool key_ok = ImGui::IsKeyDown(ImGuiKey_Enter);
    const bool unicode_ok = io.InputQueueCharacters.Size > 0;
    ImGui::SetNextWindowPos(ImVec2(1.0f, 1.0f));
    ImGui::SetNextWindowSize(ImVec2(60.0f, 60.0f));
    ImGui::Begin("OHOS backend");
    ImGui::TextUnformatted("NativeXComponent + GLES3");
    ImGui::End();
    ImGui::Render();
    ImDrawData* draw_data = ImGui::GetDrawData();
    const bool draw_data_ok =
        draw_data != nullptr && draw_data->CmdListsCount > 0;

    bool gl_ok = false;
    if (draw_data_ok)
    {
        glViewport(0, 0, 64, 64);
        glClearColor(0.1f, 0.2f, 0.3f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(draw_data);
        glFinish();
        gl_ok = glGetError() == GL_NO_ERROR;
    }

    ImGui_ImplOpenGL3_Shutdown();
    eglMakeCurrent(
        display, EGL_NO_SURFACE, EGL_NO_SURFACE,
        EGL_NO_CONTEXT);
    eglDestroyContext(display, egl_context);
    eglDestroySurface(display, surface);
    eglTerminate(display);

    if (!touch_ok || !key_ok || !unicode_ok ||
        !draw_data_ok || !gl_ok)
    {
        std::cerr << "OHOS input or GLES3 rendering check failed\n";
        return false;
    }
    return true;
}
