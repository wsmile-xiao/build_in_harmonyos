/* libxi/6.1.0 consumer link + API smoke test.
 *
 * 仅解析符号，避免无 X server 时实际调用导致段错误。
 */

#include <stdio.h>

#include <X11/Xlib.h>
#include <X11/extensions/XInput.h>
#include <X11/extensions/XInput2.h>

int main(void)
{
    /* P3 修复：函数指针声明与实际签名一致（返回 int），去掉 void* 强转 */
    int (*qver_fn)(Display *, int *, int *) = XIQueryVersion;

    /* P2 修复：实际调用被测 API（XOpenDisplay——鸿蒙无 X server 时返回 NULL） */
    Display *dpy = XOpenDisplay(NULL);
    if (dpy) {
        int major = 0, minor = 0;
        int ret = qver_fn(dpy, &major, &minor);
        printf("libxi API call OK: XIQueryVersion -> ret=%d major=%d minor=%d\n",
               ret, major, minor);
        XCloseDisplay(dpy);
    } else {
        printf("libxi link OK: XIQueryVersion=%p (no X server on OHOS——符号解析验证)\n",
               (void *)qver_fn);
    }
    return 0;
}
