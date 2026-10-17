#include <gtk/gtkversion.h>
#include <stdio.h>

/* gtk_check_version 的声明在 gtk/gtk.h 内;而 gtk.h 会传递包含 pango
 * 头(pango-coverage.h → hb.h),消费方需要 harfbuzz 的包含路径才能
 * 编译。为让冒烟测试只依赖 gtk2 自身头文件,这里手动声明原型,
 * 版本宏取自 gtkversion.h(无传递包含)。 */

extern const char *gtk_check_version(unsigned int required_major,
                                     unsigned int required_minor,
                                     unsigned int required_micro);

/* 覆盖范围(R40 人工确认):本测试覆盖链接级验证与版本 API 兼容;
 * GTK x11 后端的运行时初始化需图形环境,不在 CI/无显示验证范围内。 */
int main(void)
{
    /* 库版本必须兼容请求的 2.24.33（同 major 且不低于请求版本） */
    const char *incompat = gtk_check_version(2, 24, 33);
    if (incompat != NULL) {
        fprintf(stderr, "gtk_check_version(2,24,33) failed: %s\n", incompat);
        return 1;
    }
    if (GTK_MAJOR_VERSION != 2) {
        fprintf(stderr, "GTK_MAJOR_VERSION is %d, expected 2\n", GTK_MAJOR_VERSION);
        return 1;
    }
    printf("gtk2 %u.%u.%u consumer check ok\n",
           (unsigned)GTK_MAJOR_VERSION, (unsigned)GTK_MINOR_VERSION,
           (unsigned)GTK_MICRO_VERSION);
    return 0;
}
