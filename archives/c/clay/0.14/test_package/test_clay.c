/* Consumer test for clay 0.14 — exercises the header-only library the way
 * a downstream project does: initialize arena, declare a nested layout
 * with text + rectangles, run Clay_EndLayout and assert on the generated
 * render commands (rects/text with expected dimensions). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "clay.h"

static void HandleClayErrors_default(Clay_ErrorData err);

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("ok: %s\n", msg); } \
} while (0)

static Clay_Dimensions measureText(Clay_StringSlice text, Clay_TextElementConfig *config, void *userData) {
    (void)userData;
    Clay_Dimensions dims = { (float)text.length * (float)config->fontSize * 0.6f, (float)config->fontSize };
    return dims;
}

int main(void) {
    uint64_t totalMemorySize = Clay_MinMemorySize();
    Clay_Arena clayMemory = Clay_CreateArenaWithCapacityAndMemory(totalMemorySize, (char *)malloc(totalMemorySize));
    CHECK(clayMemory.memory != NULL, "arena created");

    Clay_Initialize(clayMemory, (Clay_Dimensions) {1024, 768},
                    (Clay_ErrorHandler) { HandleClayErrors_default });
    Clay_SetMeasureTextFunction(measureText, NULL);

    Clay_BeginLayout();
    CLAY({ .id = CLAY_ID("outer"),
           .layout = { .padding = {10, 10, 10, 10}, .childGap = 5 },
           .backgroundColor = {200, 200, 200, 255} }) {
        CLAY({ .id = CLAY_ID("sidebar"),
               .layout = { .sizing = { .width = CLAY_SIZING_FIXED(200), .height = CLAY_SIZING_GROW(0) } },
               .backgroundColor = {150, 150, 255, 255} }) {
            CLAY_TEXT(CLAY_STRING("Sidebar"),
                      CLAY_TEXT_CONFIG({ .fontSize = 24, .textColor = {0, 0, 0, 255} }));
        }
        CLAY({ .id = CLAY_ID("content"),
               .layout = { .sizing = { .width = CLAY_SIZING_GROW(0), .height = CLAY_SIZING_GROW(0) } },
               .backgroundColor = {255, 255, 255, 255} }) {
            CLAY_TEXT(CLAY_STRING("Content area"),
                      CLAY_TEXT_CONFIG({ .fontSize = 18, .textColor = {0, 0, 0, 255} }));
        }
    }
    Clay_RenderCommandArray renderCommands = Clay_EndLayout();

    CHECK(renderCommands.length >= 3, "render commands generated (>=3)");
    printf("render command count: %d\n", renderCommands.length);

    /* locate the sidebar rectangle and verify its computed width (200) */
    int foundSidebar = 0;
    float sidebarW = 0;
    for (uint32_t i = 0; i < renderCommands.length; i++) {
        Clay_RenderCommand *cmd = &renderCommands.internalArray[i];
        if (cmd->commandType == CLAY_RENDER_COMMAND_TYPE_RECTANGLE) {
            Clay_BoundingBox bb = cmd->boundingBox;
            if ((int)bb.width == 200) { foundSidebar = 1; sidebarW = bb.width; }
            printf("rect: x=%.1f y=%.1f w=%.1f h=%.1f\n", bb.x, bb.y, bb.width, bb.height);
        } else if (cmd->commandType == CLAY_RENDER_COMMAND_TYPE_TEXT) {
            printf("text: \"%.*s\" w=%.1f\n", (int)cmd->renderData.text.stringContents.length, cmd->renderData.text.stringContents.chars, cmd->boundingBox.width);
        }
    }
    CHECK(foundSidebar, "sidebar rect has fixed width 200");

    /* scrolling: a scrolling container inside a clipped parent must not overflow */
    Clay_BeginLayout();
    CLAY({ .id = CLAY_ID("scrollOuter"),
           .layout = { .sizing = { .width = CLAY_SIZING_FIXED(300), .height = CLAY_SIZING_FIXED(300) } } }) {
        CLAY({ .id = CLAY_ID("scrollInner"),
               .layout = { .sizing = { .width = CLAY_SIZING_GROW(0), .height = CLAY_SIZING_GROW(0) },
                           .childAlignment = { .y = CLAY_ALIGN_Y_TOP },
                           .layoutDirection = CLAY_TOP_TO_BOTTOM },
               .clip = { .horizontal = true, .vertical = true } }) {
            CLAY({ .id = CLAY_ID("scrollContent"),
                   .layout = { .sizing = { .width = CLAY_SIZING_GROW(0), .height = CLAY_SIZING_FIXED(2000) } },
                   .backgroundColor = {100, 200, 100, 255} }) {}
        }
    }
    Clay_RenderCommandArray cmds2 = Clay_EndLayout();
    CHECK(cmds2.length >= 1, "scroll layout commands generated");
    /* scissor clip: content taller than the 300px window must produce a
     * scissor start/end pair (clipping contract) */
    int scissorStart = 0, scissorEnd = 0;
    for (uint32_t i = 0; i < cmds2.length; i++) {
        Clay_RenderCommand *cmd = &cmds2.internalArray[i];
        if (cmd->commandType == CLAY_RENDER_COMMAND_TYPE_SCISSOR_START) scissorStart++;
        if (cmd->commandType == CLAY_RENDER_COMMAND_TYPE_SCISSOR_END) scissorEnd++;
    }
    printf("scissor pairs: start=%d end=%d\n", scissorStart, scissorEnd);
    CHECK(scissorStart >= 1 && scissorEnd >= 1, "clipped scroll produces scissor commands");

    /* arena memory accounting */
    CHECK(Clay_MinMemorySize() > 0, "Clay_MinMemorySize > 0");

    printf("failures=%d\n", failures);
    return failures ? 1 : 0;
}

static void HandleClayErrors_default(Clay_ErrorData err) {
    fprintf(stderr, "clay error: %.*s\n", (int)err.errorText.length, err.errorText.chars);
}
