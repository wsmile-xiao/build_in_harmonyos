/* libxfixes/6.1.0 consumer link + API smoke test.
 *
 * 符号验证（dlopen/dlsym）始终执行；有 X server 时进一步实际调用 API。
 */

#include <stdio.h>
#include <dlfcn.h>

#include <X11/Xlib.h>
#include <X11/extensions/Xfixes.h>

int main(void)
{
    /* R34 强化：dlopen+dlsym 符号验证——真实判别（符号存在、库可加载）——鸿蒙可运行 */
    void *handle = dlopen("libXfixes.so", RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen libXfixes.so failed\n");
        return 1;
    }
    void *sym = dlsym(handle, "XFixesCreateRegion");
    if (!sym) {
        fprintf(stderr, "FAIL: dlsym XFixesCreateRegion failed\n");
        dlclose(handle);
        return 1;
    }
    printf("libxfixes dlsym OK: XFixesCreateRegion=%p\n", sym);

    /* R34 闭环：实际调用被测 API。XOpenDisplay(NULL) 使用 DISPLAY 环境变量——
     * CI 提供 Xvfb 虚拟显示时连接成功、API 实际调用可达；
     * 鸿蒙无 X server/Xvfb 时返回 NULL——明确 SKIP（不静默通过）。 */
    Display *dpy = XOpenDisplay(NULL);
    if (!dpy) {
        printf("SKIP: no X display (鸿蒙无 X server)——符号验证通过\n");
        dlclose(handle);
        return 0;
    }
    {
        XRectangle rect = {0, 0, 10, 10};
        XserverRegion region = XFixesCreateRegion(dpy, &rect, 1);
        if (region == 0) {
            fprintf(stderr, "FAIL: XFixesCreateRegion returned NULL\n");
            XCloseDisplay(dpy);
            dlclose(handle);
            return 1;
        }
        printf("libxfixes API call OK: XFixesCreateRegion=%lu\n", (unsigned long)region);
        XFixesDestroyRegion(dpy, region);
        XCloseDisplay(dpy);
    }
    dlclose(handle);
    return 0;
}
