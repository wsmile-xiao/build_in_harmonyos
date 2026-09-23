#include "implot.h"

#include <cmath>
#include <cstdio>

// Consumer test for implot/0.8 on OHOS: exercises the real plotting API
// headlessly (no platform backend) against the packaged imgui dependency.
// The test asserts observable behaviour, not just successful calls.
static int g_failures = 0;

#define CHECK(cond, name)                                    \
    do {                                                     \
        if (cond) {                                          \
            std::printf("[PASS] %s\n", name);                \
        } else {                                             \
            std::printf("[FAIL] %s\n", name);                \
            ++g_failures;                                    \
        }                                                    \
    } while (0)

int main() {
    // 1. context lifecycle
    ImGui::CreateContext();
    ImPlot::CreateContext();
    CHECK(ImPlot::GetCurrentContext() != nullptr, "implot context created");

    // 2. style push/pop round trip through real ImPlot state
    const float base = ImPlot::GetStyle().LineWeight;
    ImPlot::PushStyleVar(ImPlotStyleVar_LineWeight, 3.0f);
    const float pushed = ImPlot::GetStyle().LineWeight;
    ImPlot::PopStyleVar();
    const float restored = ImPlot::GetStyle().LineWeight;
    CHECK(pushed == 3.0f && restored == base, "style push/pop round trip");

    // 3. input map defaults migrated to ImGui 1.92 key chords
    const ImPlotInputMap& input = ImPlot::GetInputMap();
    CHECK(input.QueryToggleMod == ImGuiMod_Ctrl, "input map key chords valid");

    // 4. headless font atlas prerequisite: without a platform backend the
    // legacy atlas must be built before NewFrame, otherwise imgui 1.92
    // reports "font atlas is not built" and crashes on first glyph use.
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2(800.0f, 600.0f);
    io.DeltaTime = 1.0f / 60.0f;
    const bool atlas_built = io.Fonts->Build();
    CHECK(atlas_built, "font atlas built for headless frame");

    // 5. real plot lifecycle inside a window
    ImGui::NewFrame();
    ImGui::SetNextWindowSize(ImVec2(600.0f, 400.0f));
    ImGui::Begin("win", nullptr, ImGuiWindowFlags_NoCollapse);
    const bool began = ImPlot::BeginPlot("probe");
    CHECK(began, "BeginPlot returns true");
    double xs[16];
    double ys[16];
    for (int i = 0; i < 16; ++i) {
        xs[i] = i;
        ys[i] = std::sin(i * 0.5);
    }
    ImPlot::PlotLine("sin", xs, ys, 16);
    ImPlot::EndPlot();
    ImGui::End();

    // 6. rendered geometry proves the library emitted real draw data
    ImGui::Render();
    ImDrawData* draw_data = ImGui::GetDrawData();
    const bool has_geometry =
        draw_data != nullptr && draw_data->TotalVtxCount > 0 && draw_data->TotalIdxCount > 0;
    CHECK(has_geometry, "plot produced draw geometry");
    if (draw_data != nullptr) {
        std::printf("vtx=%d idx=%d\n", draw_data->TotalVtxCount, draw_data->TotalIdxCount);
    }

    ImPlot::DestroyContext();
    ImGui::DestroyContext();

    if (g_failures != 0) {
        std::printf("FAILED: %d check(s)\n", g_failures);
        return 1;
    }
    std::printf("ALL 6 CHECKS PASSED\n");
    return 0;
}
