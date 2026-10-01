#include <stdio.h>
#include <stdlib.h>

#include <EGL/egl.h>
#include <GLES3/gl3.h>

#include "pugl/pugl_ohos.h"

static int checks;
static int failures;
static int motion_count;
static int mouse_count;
static int scroll_count;
static int special_count;
static int keyboard_count;
static int close_count;

#define CHECK(condition, message)                       \
    do {                                                \
        ++checks;                                       \
        if (!(condition)) {                             \
            ++failures;                                 \
            fprintf(stderr, "FAIL: %s\n", message);   \
        }                                               \
    } while (0)

static void on_motion(PuglView* v, int x, int y)
{
    (void)v; (void)x; (void)y; ++motion_count;
}

static void on_mouse(PuglView* v, int b, bool p, int x, int y)
{
    (void)v; (void)b; (void)p; (void)x; (void)y; ++mouse_count;
}

static void on_scroll(PuglView* v, float dx, float dy)
{
    (void)v; (void)dx; (void)dy; ++scroll_count;
}

static void on_special(PuglView* v, bool p, PuglKey key)
{
    (void)v; (void)p; (void)key; ++special_count;
}

static void on_keyboard(PuglView* v, bool p, uint32_t key)
{
    (void)v; (void)p; (void)key; ++keyboard_count;
}

static void on_close(PuglView* v)
{
    (void)v; ++close_count;
}

static void on_display(PuglView* v)
{
    (void)v;
    glClearColor(0.25f, 0.5f, 0.75f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
}

int
main(void)
{
    PuglView* view = puglCreate(0, "pugl-ohos-test", 16, 12, false);
    CHECK(view != NULL, "offscreen HarmonyOS view");
    if (!view) {
        return 1;
    }
    CHECK(puglGetNativeWindow(view) == 0, "pbuffer has no native window");

    puglSetDisplayFunc(view, on_display);
    puglSetMotionFunc(view, on_motion);
    puglSetMouseFunc(view, on_mouse);
    puglSetScrollFunc(view, on_scroll);
    puglSetSpecialFunc(view, on_special);
    puglSetKeyboardFunc(view, on_keyboard);
    puglSetCloseFunc(view, on_close);
    puglProcessEvents(view);

    unsigned char* pixels = (unsigned char*)calloc(16U * 12U * 4U, 1U);
    int width = 0;
    int height = 0;
    CHECK(pixels != NULL, "frame allocation");
    CHECK(puglGrabFrame(view, &width, &height, pixels) == 0, "frame readback");
    CHECK(width == 16 && height == 12, "frame dimensions");
    CHECK(pixels[0] >= 62 && pixels[0] <= 66, "red channel");
    CHECK(pixels[1] >= 126 && pixels[1] <= 130, "green channel");
    CHECK(pixels[2] >= 189 && pixels[2] <= 193, "blue channel");

    puglSendMotion(view, 3, 4, PUGL_MOD_SHIFT);
    puglSendMouse(view, 1, true, 3, 4, PUGL_MOD_CTRL);
    puglSendScroll(view, 0.0f, 1.0f, PUGL_MOD_ALT);
    puglSendSpecial(view, true, PUGL_KEY_F1, PUGL_MOD_SUPER);
    puglSendKeyboard(view, true, 'A', PUGL_MOD_SHIFT);
    puglSendClose(view);
    CHECK(motion_count == 0, "events remain queued");
    CHECK(puglProcessEvents(view) == PUGL_SUCCESS, "event dispatch");
    CHECK(motion_count == 1, "motion callback");
    CHECK(mouse_count == 1, "mouse callback");
    CHECK(scroll_count == 1, "scroll callback");
    CHECK(special_count == 1, "special callback");
    CHECK(keyboard_count == 1, "keyboard callback");
    CHECK(close_count == 1, "close callback");

    puglSendMotion(view, 7, 9, PUGL_MOD_CTRL | PUGL_MOD_ALT);
    puglProcessEvents(view);
    CHECK(puglGetModifiers(view) == (PUGL_MOD_CTRL | PUGL_MOD_ALT),
          "modifier state");
    CHECK(puglSetNativeWindow(view, 0) == PUGL_SUCCESS, "pbuffer recreation");

    CHECK(eglGetCurrentContext() != EGL_NO_CONTEXT, "context is current");
    puglDestroy(view);
    CHECK(eglGetCurrentContext() == EGL_NO_CONTEXT, "context is released");
    free(pixels);

    printf("pugl HarmonyOS backend: %d checks, %d failures\n",
           checks, failures);
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
