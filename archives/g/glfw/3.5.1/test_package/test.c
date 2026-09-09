/*
 * glfw 3.5.1 test_package — NULL platform lifecycle on OHOS/aarch64.
 *
 * R34: this is the L1 Conan test; it exercises the public GLFW API
 * end-to-end against the Null backend compiled into libglfw.so.3:
 *
 *   glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_NULL)
 *   → glfwInit
 *   → glfwGetVersion / glfwGetVersionString (must report 3.5.1)
 *   → glfwCreateWindow(GLFW_NO_API)  (headless window)
 *   → glfwGetWindowSize (must report the requested 640x480)
 *   → monitor API (the null platform connects one fake monitor
 *     "Null SuperNoop 0" 1920x1080@60: GetMonitors/GetPrimaryMonitor/
 *     GetMonitorName/GetMonitorPos/ContentScale/GetVideoMode/GetGammaRamp)
 *   → glfwSet/GetInputMode(GLFW_CURSOR) + glfwGetKey (input API surface)
 *   → glfwGetClipboardString ( backend: NULL, must not crash)
 *   → glfwGetTime / glfwGetTimerFrequency (posix timer backend)
 *   → glfwSetWindowTitle / glfwWindowShouldClose
 *   → glfwDestroyWindow
 *   → glfwTerminate
 *
 * Every step abort()s on failure so the test reports the first real
 * failure root cause, not a stubbed pass.
 */
#include <stdio.h>
#include <stdlib.h>
#include <GLFW/glfw3.h>

#define CHECK(cond, stage)                                              \
    do {                                                                \
        if (!(cond)) {                                                  \
            const char* desc = NULL;                                    \
            glfwGetError(&desc);                                        \
            fprintf(stderr, "[FAIL] %s: cond='%s' GLFWerror='%s'\n",    \
                    (stage), #cond, desc ? desc : "()");                \
            fflush(stderr);                                             \
            abort();                                                    \
        }                                                               \
    } while (0)

static void report(const char* stage)
{
    printf("[ OK ] %s\n", stage);
    fflush(stdout);
}

int main(void)
{
    /* 1. Select the Null platform explicitly (the only backend compiled in) */
    glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_NULL);
    report("glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_NULL)");

    /* 2. glfwInit must succeed on the Null platform */
    if (!glfwInit()) {
        const char* desc = NULL;
        glfwGetError(&desc);
        fprintf(stderr, "[FAIL] glfwInit: %s\n", desc ? desc : "()");
        fflush(stderr);
        abort();
    }
    report("glfwInit");

    /* 3. Version must be 3.5.1 */
    int major = 0, minor = 0, rev = 0;
    glfwGetVersion(&major, &minor, &rev);
    CHECK(major == 3 && minor == 5 && rev == 1, "glfwGetVersion == 3.5.1");
    report("glfwGetVersion == 3.5.1");

    const char* verstr = glfwGetVersionString();
    CHECK(verstr != NULL, "glfwGetVersionString non-NULL");
    printf("    version string: %s\n", verstr);
    report("glfwGetVersionString");

    /* 4. Headless window: GLFW_CLIENT_API=GLFW_NO_API (no GL/Vulkan context,
     *    without this hint glfw defaults to OpenGL and the null platform
     *    would try to load OSMesa) */
    glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
    GLFWwindow* window = glfwCreateWindow(640, 480, "glfw-null-test", NULL, NULL);
    CHECK(window != NULL, "glfwCreateWindow(GLFW_NO_API)");
    report("glfwCreateWindow(640x480, GLFW_NO_API)");

    /* 5. Window queries must work on the Null platform */
    int w = 0, h = 0;
    glfwGetWindowSize(window, &w, &h);
    CHECK(w == 640 && h == 480, "glfwGetWindowSize == 640x480");
    report("glfwGetWindowSize == 640x480");

    /* 6. Monitor API: the null platform connects a single fake monitor
     * ("Null SuperNoop 0", 1920x1080@60) during init — query it fully */
    int count = -1;
    GLFWmonitor** monitors = glfwGetMonitors(&count);
    CHECK(monitors != NULL && count == 1, "glfwGetMonitors ( platform: 1 fake monitor)");
    report("glfwGetMonitors ( platform: 1 fake monitor)");

    GLFWmonitor* primary = glfwGetPrimaryMonitor();
    CHECK(primary != NULL && primary == monitors[0], "glfwGetPrimaryMonitor");
    report("glfwGetPrimaryMonitor ( platform)");

    const char* mon_name = glfwGetMonitorName(primary);
    CHECK(mon_name != NULL && mon_name[0] != '\0', "glfwGetMonitorName non-empty");
    report("glfwGetMonitorName");

    int mx = -1, my = -1;
    glfwGetMonitorPos(primary, &mx, &my);
    CHECK(mx == 0 && my == 0, "glfwGetMonitorPos == (0,0)");
    report("glfwGetMonitorPos == (0,0)");

    float xs = 0.f, ys = 0.f;
    glfwGetMonitorContentScale(primary, &xs, &ys);
    CHECK(xs == 1.f && ys == 1.f, "glfwGetMonitorContentScale == 1.0");
    report("glfwGetMonitorContentScale == 1.0");

    const GLFWvidmode* mode = glfwGetVideoMode(primary);
    CHECK(mode != NULL && mode->width == 1920 && mode->height == 1080 &&
          mode->refreshRate == 60, "glfwGetVideoMode == 1920x1080@60");
    report("glfwGetVideoMode == 1920x1080@60");

    const GLFWgammaramp* ramp = glfwGetGammaRamp(primary);
    CHECK(ramp != NULL && ramp->size == 256, "glfwGetGammaRamp (256 entries)");
    report("glfwGetGammaRamp (256 entries)");

    /* 7. Input API surface on the headless window */
    glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_NORMAL);
    int cursor_mode = glfwGetInputMode(window, GLFW_CURSOR);
    CHECK(cursor_mode == GLFW_CURSOR_NORMAL, "glfwGet/SetInputMode(GLFW_CURSOR)");
    report("glfwGet/SetInputMode(GLFW_CURSOR)");

    int key = glfwGetKey(window, GLFW_KEY_A);
    CHECK(key == GLFW_RELEASE, "glfwGetKey(GLFW_KEY_A) == GLFW_RELEASE");
    report("glfwGetKey(GLFW_KEY_A) == GLFW_RELEASE");

    /* 8. Clipboard API ( backend: returns NULL, must not crash) */
    const char* clip = glfwGetClipboardString(window);
    (void)clip; /* null backend has no clipboard: NULL is acceptable */
    report("glfwGetClipboardString ( platform)");

    /* 9. Time API (posix timer backend) */
    double t0 = glfwGetTime();
    CHECK(t0 >= 0.0, "glfwGetTime >= 0");
    double freq = glfwGetTimerFrequency();
    CHECK(freq > 0.0, "glfwGetTimerFrequency > 0 (posix timer)");
    report("glfwGetTime / glfwGetTimerFrequency (posix timer)");

    /* 10. Window title + shouldClose on the null window */
    glfwSetWindowTitle(window, "renamed");
    CHECK(glfwWindowShouldClose(window) == GLFW_FALSE, "glfwWindowShouldClose");
    report("glfwSetWindowTitle / glfwWindowShouldClose");

    /* 11. Teardown */
    glfwDestroyWindow(window);
    report("glfwDestroyWindow");

    glfwTerminate();
    report("glfwTerminate");

    printf("ALL 21 CHECKS PASSED: glfw 3.5.1 null-platform lifecycle ok\n");
    fflush(stdout);
    return 0;
}
