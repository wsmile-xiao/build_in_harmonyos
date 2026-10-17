#include <stdio.h>

#include <SDL.h>
#include <SDL_opengles2.h>

#include "test_native_video.h"

static int close_byte(unsigned char actual, int expected)
{
    return actual >= expected - 2 && actual <= expected + 2;
}

static int renderer_pixel_matches(SDL_Renderer *renderer, int x, int y,
                                  int red, int green, int blue)
{
    SDL_Rect rect;
    Uint8 pixel[4] = {0, 0, 0, 0};

    rect.x = x;
    rect.y = y;
    rect.w = 1;
    rect.h = 1;
    if (SDL_RenderReadPixels(renderer, &rect, SDL_PIXELFORMAT_RGBA32,
                             pixel, (int)sizeof(pixel)) != 0) {
        return 0;
    }
    return close_byte(pixel[0], red) && close_byte(pixel[1], green) &&
           close_byte(pixel[2], blue) && pixel[3] >= 253;
}

int SDL2_RunNativeVideoProbeWithObserver(
    Uint64 surface_id, int width, int height,
    SDL2_NativeVideoPresentationObserver observer, void *observer_userdata)
{
    SDL_Window *window = NULL;
    SDL_GLContext context = NULL;
    SDL_Renderer *renderer = NULL;
    SDL_Texture *texture = NULL;
    SDL_RendererInfo renderer_info;
    PFNGLVIEWPORTPROC gl_viewport = NULL;
    PFNGLCLEARCOLORPROC gl_clear_color = NULL;
    PFNGLCLEARPROC gl_clear = NULL;
    PFNGLFINISHPROC gl_finish = NULL;
    PFNGLREADPIXELSPROC gl_read_pixels = NULL;
    PFNGLGETERRORPROC gl_get_error = NULL;
    unsigned char pixel[4] = {0, 0, 0, 0};
    const Uint8 texture_pixels[16] = {
        255, 0, 0, 255, 0, 255, 0, 255,
        0, 0, 255, 255, 255, 255, 255, 255,
    };
    char surface_text[32];
    char width_text[16];
    char height_text[16];
    int actual_width = 0;
    int actual_height = 0;
    int sample_x_right = 0;
    int sample_y_bottom = 0;
    int renderer_index = -1;
    GLenum graphics_error = GL_NO_ERROR;
    int i;
    int checks = 0;
    int rc = 1;

#define REQUIRE(expr, label)                                                   \
    do {                                                                       \
        if (!(expr)) {                                                         \
            fprintf(stderr, "SDL2_NATIVE_VIDEO_FAIL assertion=%s sdl=%s "     \
                            "graphics=0x%x\n",                                \
                    label, SDL_GetError(), (unsigned int)graphics_error);        \
            goto cleanup;                                                      \
        }                                                                      \
        ++checks;                                                              \
    } while (0)

    REQUIRE(surface_id > 0 && width > 0 && height > 0, "surface_tuple");
    SDL_snprintf(surface_text, sizeof(surface_text), "%" SDL_PRIu64, surface_id);
    SDL_snprintf(width_text, sizeof(width_text), "%d", width);
    SDL_snprintf(height_text, sizeof(height_text), "%d", height);
    REQUIRE(SDL_setenv("SDL_VIDEODRIVER", "nativewindow", 1) == 0 &&
                SDL_SetHint(SDL_HINT_NATIVEWINDOW_SURFACE_ID, surface_text) &&
                SDL_SetHint(SDL_HINT_NATIVEWINDOW_WIDTH, width_text) &&
                SDL_SetHint(SDL_HINT_NATIVEWINDOW_HEIGHT, height_text),
            "nativewindow_hints");
    REQUIRE(SDL_Init(SDL_INIT_VIDEO) == 0, "video_init");
    REQUIRE(SDL_GetCurrentVideoDriver() != NULL &&
                SDL_strcmp(SDL_GetCurrentVideoDriver(), "nativewindow") == 0,
            "driver_selected");

    REQUIRE(SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0"),
            "nearest_texture_scaling");
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    window = SDL_CreateWindow("SDL2 NativeWindow probe", SDL_WINDOWPOS_UNDEFINED,
                              SDL_WINDOWPOS_UNDEFINED, width, height,
                              SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN);
    REQUIRE(window != NULL, "ordinary_create_window");
    SDL_GetWindowSize(window, &actual_width, &actual_height);
    REQUIRE(actual_width == width && actual_height == height, "window_geometry");
    sample_x_right = width - (width / 4) - 1;
    sample_y_bottom = height - (height / 4) - 1;

    for (i = 0; i < SDL_GetNumRenderDrivers(); ++i) {
        SDL_RendererInfo candidate;
        if (SDL_GetRenderDriverInfo(i, &candidate) == 0 && candidate.name &&
            SDL_strcmp(candidate.name, "opengles2") == 0) {
            renderer_index = i;
            break;
        }
    }
    REQUIRE(renderer_index >= 0, "opengles2_renderer_registered");
    renderer = SDL_CreateRenderer(window, renderer_index, SDL_RENDERER_ACCELERATED);
    REQUIRE(renderer != NULL, "opengles2_renderer_create");
    SDL_zero(renderer_info);
    REQUIRE(SDL_GetRendererInfo(renderer, &renderer_info) == 0 &&
                renderer_info.name &&
                SDL_strcmp(renderer_info.name, "opengles2") == 0 &&
                (renderer_info.flags & SDL_RENDERER_ACCELERATED) != 0,
            "opengles2_renderer_selected");
    texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGBA32,
                                SDL_TEXTUREACCESS_STATIC, 2, 2);
    REQUIRE(texture != NULL, "renderer_texture_create");
    REQUIRE(SDL_UpdateTexture(texture, NULL, texture_pixels, 8) == 0 &&
                SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255) == 0 &&
                SDL_RenderClear(renderer) == 0 &&
                SDL_RenderCopy(renderer, texture, NULL, NULL) == 0,
            "renderer_texture_copy");
    REQUIRE(renderer_pixel_matches(renderer, width / 4, height / 4,
                                   255, 0, 0),
            "renderer_readback_red");
    REQUIRE(renderer_pixel_matches(renderer, sample_x_right, height / 4,
                                   0, 255, 0),
            "renderer_readback_green");
    REQUIRE(renderer_pixel_matches(renderer, width / 4, sample_y_bottom,
                                   0, 0, 255),
            "renderer_readback_blue");
    REQUIRE(renderer_pixel_matches(renderer, sample_x_right,
                                   sample_y_bottom, 255, 255, 255),
            "renderer_readback_white");
    SDL_ClearError();
    SDL_RenderPresent(renderer);
    REQUIRE(SDL_GetError()[0] == '\0', "renderer_present");
    SDL_DestroyTexture(texture);
    texture = NULL;
    SDL_DestroyRenderer(renderer);
    renderer = NULL;

    context = SDL_GL_CreateContext(window);
    REQUIRE(context != NULL, "egl_context");
    REQUIRE(SDL_GL_MakeCurrent(window, context) == 0 &&
                SDL_GL_GetCurrentWindow() == window &&
                SDL_GL_GetCurrentContext() == context,
            "egl_current");

    gl_viewport = (PFNGLVIEWPORTPROC)SDL_GL_GetProcAddress("glViewport");
    gl_clear_color =
        (PFNGLCLEARCOLORPROC)SDL_GL_GetProcAddress("glClearColor");
    gl_clear = (PFNGLCLEARPROC)SDL_GL_GetProcAddress("glClear");
    gl_finish = (PFNGLFINISHPROC)SDL_GL_GetProcAddress("glFinish");
    gl_read_pixels =
        (PFNGLREADPIXELSPROC)SDL_GL_GetProcAddress("glReadPixels");
    gl_get_error = (PFNGLGETERRORPROC)SDL_GL_GetProcAddress("glGetError");
    REQUIRE(gl_viewport && gl_clear_color && gl_clear && gl_finish &&
                gl_read_pixels && gl_get_error,
            "gles2_entrypoints");

    (void)gl_get_error();
    gl_viewport(0, 0, width, height);
    gl_clear_color(0.25f, 0.50f, 0.75f, 1.0f);
    gl_clear(GL_COLOR_BUFFER_BIT);
    gl_finish();
    gl_read_pixels(0, 0, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
    graphics_error = gl_get_error();
    REQUIRE(graphics_error == GL_NO_ERROR && close_byte(pixel[0], 64) &&
                close_byte(pixel[1], 128) && close_byte(pixel[2], 191) &&
                pixel[3] >= 253,
            "gles2_readback");

    SDL_ClearError();
    SDL_GL_SwapWindow(window);
    REQUIRE(SDL_GetError()[0] == '\0', "egl_swap");
    if (observer &&
        observer(observer_userdata, pixel[0], pixel[1], pixel[2], pixel[3]) != 0) {
        fprintf(stderr, "SDL2_NATIVE_VIDEO_FAIL assertion=presentation_observer\n");
        goto cleanup;
    }
    if (checks != 22) {
        fprintf(stderr, "SDL2_NATIVE_VIDEO_FAIL assertion_count=%d\n", checks);
        goto cleanup;
    }
    printf("SDL2_NATIVE_VIDEO_PASS assertions=%d driver=nativewindow "
           "surface_id=%" SDL_PRIu64 " size=%dx%d pixel=%u,%u,%u,%u\n",
           checks, surface_id, width, height, pixel[0], pixel[1], pixel[2],
           pixel[3]);
    rc = 0;

cleanup:
    if (texture) {
        SDL_DestroyTexture(texture);
    }
    if (renderer) {
        SDL_DestroyRenderer(renderer);
    }
    if (context) {
        SDL_GL_DeleteContext(context);
    }
    if (window) {
        SDL_DestroyWindow(window);
    }
    SDL_QuitSubSystem(SDL_INIT_VIDEO);
    return rc;
}

int SDL2_RunNativeVideoProbe(Uint64 surface_id, int width, int height)
{
    return SDL2_RunNativeVideoProbeWithObserver(
        surface_id, width, height, NULL, NULL);
}

#ifndef SDL2_NATIVE_VIDEO_NO_MAIN
static int parse_positive(const char *text, Uint64 *value)
{
    const char *cursor;
    Uint64 parsed = 0;

    if (!text || !*text) {
        return 0;
    }
    for (cursor = text; *cursor; ++cursor) {
        const Uint64 digit = (Uint64)(*cursor - '0');
        if (*cursor < '0' || *cursor > '9' ||
            parsed > (SDL_MAX_UINT64 - digit) / 10) {
            return 0;
        }
        parsed = (parsed * 10) + digit;
    }
    if (parsed == 0) {
        return 0;
    }
    *value = parsed;
    return 1;
}

int main(int argc, char **argv)
{
    Uint64 surface_id = 0;
    Uint64 width = 0;
    Uint64 height = 0;
    if (argc != 4 || !parse_positive(argv[1], &surface_id) ||
        !parse_positive(argv[2], &width) || !parse_positive(argv[3], &height) ||
        width > SDL_MAX_SINT32 || height > SDL_MAX_SINT32) {
        fprintf(stderr, "usage: %s SURFACE_ID WIDTH HEIGHT\n", argv[0]);
        return 64;
    }
    return SDL2_RunNativeVideoProbe(surface_id, (int)width, (int)height);
}
#endif
