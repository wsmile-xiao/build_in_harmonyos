#include <cstring>
#include <iostream>

#include <imgui.h>
#include "test_imgui_platform.h"

int main(int argc, char** argv) {
    const bool fault_mode = argc == 2 &&
                            std::strcmp(argv[1], "--fault-version") == 0;
    const bool ohos_headless_mode = argc == 2 &&
                                    std::strcmp(
                                        argv[1],
                                        "--ohos-headless") == 0;
    if (fault_mode) {
        const bool accepted = ImGui::DebugCheckVersionAndDataLayout(
            "intentionally-invalid-version",
            sizeof(ImGuiIO),
            sizeof(ImGuiStyle),
            sizeof(ImVec2),
            sizeof(ImVec4),
            sizeof(ImDrawVert),
            sizeof(ImDrawIdx));
        if (accepted) {
            std::cerr << "fault injection failed: mismatched version accepted\n";
            return 20;
        }
        std::cout << "fault injection passed: mismatched version rejected\n";
        return 0;
    }

    if (std::strcmp(ImGui::GetVersion(), IMGUI_VERSION) != 0) {
        std::cerr << "runtime/header version mismatch\n";
        return 1;
    }
    if (!IMGUI_CHECKVERSION()) {
        std::cerr << "version/layout check failed\n";
        return 2;
    }

    ImGuiContext* context = ImGui::CreateContext();
    if (context == nullptr || ImGui::GetCurrentContext() != context) {
        std::cerr << "context creation failed\n";
        return 3;
    }

    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2(640.0f, 480.0f);
    io.DeltaTime = 1.0f / 60.0f;
    if (io.DisplaySize.x != 640.0f || io.DisplaySize.y != 480.0f ||
        io.DeltaTime <= 0.0f) {
        std::cerr << "IO state update failed\n";
        ImGui::DestroyContext();
        return 4;
    }
    ImGuiStyle& style = ImGui::GetStyle();
    if (style.Alpha <= 0.0f || style.Alpha > 1.0f) {
        std::cerr << "unexpected default style alpha\n";
        ImGui::DestroyContext();
        return 5;
    }

    if (!CheckPlatformBackends(ohos_headless_mode)) {
        ImGui::DestroyContext();
        return 7;
    }

    ImGui::DestroyContext();
    if (ImGui::GetCurrentContext() != nullptr) {
        std::cerr << "context destruction failed\n";
        return 6;
    }
    std::cout << "imgui consumer checks passed\n";
    return 0;
}
