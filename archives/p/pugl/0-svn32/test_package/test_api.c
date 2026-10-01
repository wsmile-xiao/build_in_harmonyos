#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include <GLES3/gl3.h>

#include "pugl/pugl.h"

static int checks;
static int failures;
static int reshapes;
static int displays;

#define CHECK(condition, message)                       \
    do {                                                \
        ++checks;                                       \
        if (!(condition)) {                             \
            ++failures;                                 \
            fprintf(stderr, "FAIL: %s\n", message);   \
        }                                               \
    } while (0)

static void
on_reshape(PuglView* view, int width, int height)
{
    (void)view;
    glViewport(0, 0, width, height);
    ++reshapes;
}

static void
on_display(PuglView* view)
{
    (void)view;
    glClearColor(0.125f, 0.25f, 0.5f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    ++displays;
}

int
main(void)
{
    int handle_value = 42;
    PuglView* view = puglCreate(0, "pugl-api-test", 32, 24, false);
    CHECK(view != NULL, "puglCreate creates an offscreen EGL view");
    if (!view) {
        return 1;
    }

    puglSetHandle(view, &handle_value);
    CHECK(puglGetHandle(view) == &handle_value, "handle round trip");
    puglIgnoreKeyRepeat(view, true);
    puglSetReshapeFunc(view, on_reshape);
    puglSetDisplayFunc(view, on_display);

    CHECK(puglProcessEvents(view) == PUGL_SUCCESS, "initial event pass");
    CHECK(reshapes == 1, "initial reshape callback");
    CHECK(displays == 1, "initial display callback");
    CHECK(glGetString(GL_VERSION) != NULL, "OpenGL ES context is current");
    CHECK(glGetError() == GL_NO_ERROR, "initial frame has no GL error");

    puglPostRedisplay(view);
    CHECK(puglProcessEvents(view) == PUGL_SUCCESS, "redisplay event pass");
    CHECK(reshapes == 1, "redisplay does not spuriously reshape");
    CHECK(displays == 2, "redisplay callback");

    puglDestroy(view);
    printf("pugl public API: %d checks, %d failures\n", checks, failures);
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
