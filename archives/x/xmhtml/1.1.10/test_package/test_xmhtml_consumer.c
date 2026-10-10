/* XmHTML 1.1.10 消费者冒烟用例（鸿蒙特有，headless —— 无需 X 显示）
 *
 * 覆盖目的：证明本包投递的**头文件**可编译、导出的**符号**可链接、动态库可被
 * 加载器解析并调用，且 Motif widget 类已随库完成注册。
 *
 * 上游测试清点（R51）：XmHTML 1.1.10 源码树无 tests/ 目录，Makefile 目标为
 * all/lib/http/examples/tools/contrib/book/depend/clean/distclean，无 check/test。
 */
#include <stdio.h>
#include <string.h>

#include <XmHTML/XmHTML.h>

int main(void)
{
    const char *version;
    int api_version;

    /* 1. 公共 API：版本字符串（include/XmHTML/XmHTML.h:466） */
    version = XmHTMLGetVersionString();
    if (version == NULL || version[0] == '\0') {
        fprintf(stderr, "FAIL: XmHTMLGetVersionString() returned empty\n");
        return 1;
    }
    printf("XmHTMLGetVersionString() = %s\n", version);
    if (strstr(version, "1.1.10") == NULL) {
        fprintf(stderr, "FAIL: version string does not carry 1.1.10: %s\n", version);
        return 1;
    }

    /* 2. 公共 API：数值版本（include/XmHTML/XmHTML.h:463） */
    api_version = XmHTMLGetVersion();
    printf("XmHTMLGetVersion() = %d\n", api_version);
    if (api_version <= 0) {
        fprintf(stderr, "FAIL: XmHTMLGetVersion() returned %d\n", api_version);
        return 1;
    }

    /* 3. 库导出的 Motif widget 类数据符号（XmHTML.h:150）：非 NULL 证明库
     *    已加载且类注册结构可访问（同时覆盖 Xm/Xt/X11 依赖链解析）。 */
    if (xmHTMLWidgetClass == NULL) {
        fprintf(stderr, "FAIL: xmHTMLWidgetClass is NULL\n");
        return 1;
    }
    printf("xmHTMLWidgetClass = %p (Motif class linked)\n",
           (void *)xmHTMLWidgetClass);

    /* 4. 头文件另一公共入口（HTML 子头，验证 include 布局） */
    printf("XmHTMLVERSION_STRING = %s\n", XmHTMLVERSION_STRING);

    printf("PASS: XmHTML consumer OK (compile + link + load + API call)\n");
    return 0;
}
