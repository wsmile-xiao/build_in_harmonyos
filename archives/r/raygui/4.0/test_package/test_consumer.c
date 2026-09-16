/* Consumer test: compile the raygui implementation with a standalone backend
 * and call real raygui APIs with behavioral assertions.
 * Backend stubs follow raygui.h 4.0 RAYGUI_STANDALONE declaration section. */
#include <stdio.h>
#include <stdlib.h>

/* Forward declarations needed inside raygui.h's implementation section:
 * Fade() is a raylib helper raygui calls, and raygui 4.0 still has one
 * MeasureTextEx() call site (tooltip, line ~4940) despite the changelog
 * removal note. The typedefs here refer to the same structs that
 * raygui.h (RAYGUI_STANDALONE) completes later. */
typedef struct Color Color;
typedef struct Vector2 Vector2;
typedef struct Font Font;
typedef struct Image Image;
typedef struct Texture2D Texture2D;
static Color Fade(Color color, float alpha);
Vector2 MeasureTextEx(Font font, const char *text, float fontSize,
                      float spacing);
void UnloadTexture(Texture2D texture);
int GetGlyphIndex(Font font, int codepoint);
int GetCodepoint(const char *text, int *codepointSize);
void DrawTextCodepoint(Font font, int codepoint, Vector2 position,
                       float fontSize, Color tint);
int GetScreenWidth(void);

/* raygui.h frees glyph arrays through RL_FREE; allocations come from
 * RAYGUI_MALLOC/CALLOC (malloc/calloc by default). */
#define RL_FREE(ptr) free(ptr)

#define RAYGUI_IMPLEMENTATION
#define RAYGUI_STANDALONE

/* Key codes beyond the six that raygui.h's STANDALONE section defines. */
#define KEY_INSERT   260
#define KEY_DELETE   261
#define KEY_HOME     268
#define KEY_END      269
#define KEY_LEFT_SHIFT   340
#define KEY_LEFT_CONTROL 341

/* raygui.h (RAYGUI_STANDALONE) expects these raylib color macros to be
 * provided by the user backend; raygui.h uses them in control drawing. */
#define LIGHTGRAY (Color){ 200, 200, 200, 255 }
#define GRAY      (Color){ 130, 130, 130, 255 }
#define DARKGRAY  (Color){ 80, 80, 80, 255 }
#define YELLOW    (Color){ 253, 249, 0, 255 }
#define GOLD      (Color){ 255, 203, 0, 255 }
#define ORANGE    (Color){ 255, 161, 0, 255 }
#define PINK      (Color){ 255, 109, 194, 255 }
#define RED       (Color){ 230, 41, 55, 255 }
#define MAROON    (Color){ 190, 33, 55, 255 }
#define GREEN     (Color){ 0, 228, 48, 255 }
#define LIME      (Color){ 0, 158, 47, 255 }
#define DARKGREEN (Color){ 0, 117, 44, 255 }
#define SKYBLUE   (Color){ 102, 191, 255, 255 }
#define BLUE      (Color){ 0, 121, 241, 255 }
#define DARKBLUE  (Color){ 0, 82, 172, 255 }
#define PURPLE    (Color){ 200, 122, 255, 255 }
#define VIOLET    (Color){ 135, 60, 190, 255 }
#define DARKPURPLE(Color){ 112, 31, 126, 255 }
#define BEIGE     (Color){ 211, 176, 131, 255 }
#define BROWN     (Color){ 127, 106, 79, 255 }
#define DARKBROWN (Color){ 76, 63, 47, 255 }
#define MAGENTA   (Color){ 255, 0, 255, 255 }
#define RAYWHITE  (Color){ 245, 245, 245, 255 }
#define BLANK     (Color){ 0, 0, 0, 0 }
#define BLACK     (Color){ 0, 0, 0, 255 }
#define WHITE     (Color){ 255, 255, 255, 255 }

#include "raygui.h"

/* ---- Standalone backend: input functions ---- */
static Vector2 GetMousePosition(void)
{
    Vector2 v = {0.0f, 0.0f};
    return v;
}

static float GetMouseWheelMove(void) { return 0.0f; }

static bool IsMouseButtonDown(int button) { (void)button; return false; }

static bool IsMouseButtonPressed(int button) { (void)button; return false; }

static bool IsMouseButtonReleased(int button) { (void)button; return false; }

static bool IsKeyDown(int key) { (void)key; return false; }

static bool IsKeyPressed(int key) { (void)key; return false; }

static int GetCharPressed(void) { return 0; }

/* ---- Standalone backend: drawing functions ---- */
static void DrawRectangle(int x, int y, int width, int height, Color color)
{
    (void)x;
    (void)y;
    (void)width;
    (void)height;
    (void)color;
}

static void DrawRectangleGradientEx(Rectangle rec, Color col1, Color col2,
                                    Color col3, Color col4)
{
    (void)rec;
    (void)col1;
    (void)col2;
    (void)col3;
    (void)col4;
}

/* ---- Standalone backend: text/style functions ---- */
static Font GetFontDefault(void)
{
    Font font = {0};
    return font;
}

static Font LoadFontEx(const char *fileName, int fontSize, int *codepoints,
                       int codepointCount)
{
    (void)fileName;
    (void)fontSize;
    (void)codepoints;
    (void)codepointCount;
    Font font = {0};
    return font;
}

static Texture2D LoadTextureFromImage(Image image)
{
    (void)image;
    Texture2D texture = {0};
    return texture;
}

static void SetShapesTexture(Texture2D tex, Rectangle rec)
{
    (void)tex;
    (void)rec;
}

static char *LoadFileText(const char *fileName)
{
    (void)fileName;
    return NULL;
}

static void UnloadFileText(char *text)
{
    (void)text;
}

static const char *GetDirectoryPath(const char *filePath)
{
    (void)filePath;
    return NULL;
}

static int *LoadCodepoints(const char *text, int *count)
{
    (void)text;
    if (count != NULL) {
        *count = 0;
    }
    return NULL;
}

static void UnloadCodepoints(int *codepoints)
{
    (void)codepoints;
}

static unsigned char *DecompressData(const unsigned char *compData,
                                     int compDataSize, int *dataSize)
{
    (void)compData;
    (void)compDataSize;
    if (dataSize != NULL) {
        *dataSize = 0;
    }
    return NULL;
}

/* raygui.h's implementation calls these raylib text helpers internally;
 * non-static to match the declaration raygui.h emits. */
Vector2 MeasureTextEx(Font font, const char *text, float fontSize,
                      float spacing)
{
    (void)font;
    (void)text;
    (void)fontSize;
    (void)spacing;
    Vector2 size = {0.0f, 0.0f};
    return size;
}

static void DrawTextEx(Font font, const char *text, Vector2 position,
                       float fontSize, float spacing, Color tint)
{
    (void)font;
    (void)text;
    (void)position;
    (void)fontSize;
    (void)spacing;
    (void)tint;
}

static Color Fade(Color color, float alpha)
{
    if (alpha < 0.0f) alpha = 0.0f;
    else if (alpha > 1.0f) alpha = 1.0f;
    Color result = {color.r, color.g, color.b,
                    (unsigned char)(255.0f * ((float)color.a / 255.0f) * alpha)};
    return result;
}

void UnloadTexture(Texture2D texture)
{
    (void)texture;
}

int GetGlyphIndex(Font font, int codepoint)
{
    (void)font;
    (void)codepoint;
    return 0;
}

int GetCodepoint(const char *text, int *codepointSize)
{
    (void)text;
    if (codepointSize != NULL) {
        *codepointSize = 1;
    }
    return 0x3f;
}

void DrawTextCodepoint(Font font, int codepoint, Vector2 position,
                       float fontSize, Color tint)
{
    (void)font;
    (void)codepoint;
    (void)position;
    (void)fontSize;
    (void)tint;
}

int GetScreenWidth(void)
{
    return 0;
}

int main(void)
{
    int failures = 0;

    /* Global state: enable/disable must be observable through GuiGetState(). */
    GuiEnable();
    if (GuiGetState() != STATE_NORMAL) {
        fprintf(stderr, "FAIL: GuiGetState != STATE_NORMAL after GuiEnable\n");
        failures++;
    }
    GuiDisable();
    if (GuiGetState() != STATE_DISABLED) {
        fprintf(stderr, "FAIL: GuiGetState != STATE_DISABLED after GuiDisable\n");
        failures++;
    }
    GuiEnable();

    /* Global lock: GuiLock()/GuiUnlock() observable through GuiIsLocked(). */
    GuiLock();
    if (!GuiIsLocked()) {
        fprintf(stderr, "FAIL: GuiIsLocked false after GuiLock\n");
        failures++;
    }
    GuiUnlock();
    if (GuiIsLocked()) {
        fprintf(stderr, "FAIL: GuiIsLocked true after GuiUnlock\n");
        failures++;
    }

    /* Style store: set then read back through the real style table. */
    int previous = GuiGetStyle(DEFAULT, BORDER_WIDTH);
    GuiSetStyle(DEFAULT, BORDER_WIDTH, previous + 3);
    if (GuiGetStyle(DEFAULT, BORDER_WIDTH) != previous + 3) {
        fprintf(stderr, "FAIL: GuiSetStyle/GuiGetStyle roundtrip\n");
        failures++;
    }
    GuiSetStyle(DEFAULT, BORDER_WIDTH, previous);

    /* GuiIconText must return a non-NULL string. */
    const char *text = GuiIconText(0, "ok");
    if (text == NULL) {
        fprintf(stderr, "FAIL: GuiIconText returned NULL\n");
        failures++;
    }

    if (failures != 0) {
        fprintf(stderr, "test_consumer: %d check(s) failed\n", failures);
        return 1;
    }
    printf("test_consumer PASSED\n");
    return 0;
}
