/* libxtst/1.2.5 consumer link + API smoke test.
 *
 * 实际调用被测 API + 符号验证（X server 可用时实际调用；鸿蒙无 X server 时回退符号验证）。
 */

#include <stdio.h>

#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>

int main(void)
{
    /* 函数指针声明与 XTestQueryExtension 真实签名一致（Bool——5 参数） */
    Bool (*qext_fn)(Display *, int *, int *, int *, int *) = XTestQueryExtension;
    printf("libxtst symbol OK: XTestQueryExtension=%p\n", (void *)qext_fn);

    /* 实际调用被测 API。XOpenDisplay(NULL) 使用 DISPLAY 环境变量——
     * CI 提供 Xvfb 虚拟显示时连接成功、API 实际调用可达；
     * 鸿蒙无 X server/Xvfb 时返回 NULL——回退符号验证。 */
    Display *dpy = XOpenDisplay(NULL);
    if (!dpy) {
        printf("SKIP: no X display (鸿蒙无 X server)——符号验证通过\n");
        return 0;
    }
    if (dpy) {
        int event_base, error_base, major, minor;
        Bool ok = qext_fn(dpy, &event_base, &error_base, &major, &minor);
        if (!ok) {
            fprintf(stderr, "FAIL: XTestQueryExtension returned False\n");
            return 1;
        }
        printf("libxtst API call OK: XTestQueryExtension=%d\n", ok);
        XCloseDisplay(dpy);
    }
    return 0;
}
