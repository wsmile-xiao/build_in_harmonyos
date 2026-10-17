/* test_form_api.c — libformw test_package.
 *
 * 端到端驱动 form 库公开 API：字段创建、缓冲区写入/读回、字段状态、
 * 表单组装（以 NULL 结尾的字段数组）、字段计数、当前字段设置与查询、
 * 表单与字段销毁。
 *
 * 终端上下文：宽字符 form 库的字段缓冲与表单对象绑定 SCREEN（set_field_buffer
 * 经内部 pad、new_form 取 SCREEN 的 stdscr），必须先建立屏幕。本测试用
 * newterm("dumb") 显式建立最小屏幕（TERM 强制为 dumb，TERMINFO 由依赖包
 * ncurses/6.6 的 conanrun 环境提供），不用 initscr 的全屏初始化路径，也不
 * 刷新屏幕，输出保持干净、可在无 tty 的自动化环境复现。
 * 静态链接 libformw.a + 父包 libncursesw.a：链接成功本身即证明同源 ABI。
 */
#include <curses.h>
#include <eti.h>
#include <form.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static int g_checks = 0;

#define CHECK(cond, name)                                        \
    do {                                                         \
        g_checks++;                                              \
        if (!(cond)) {                                           \
            fprintf(stderr, "FAIL %s (check #%d)\n", name, g_checks); \
            return 1;                                            \
        }                                                        \
    } while (0)

int main(void)
{
    setenv("TERM", "dumb", 1);
    SCREEN *scr = newterm("dumb", stdout, stdin);
    CHECK(scr != NULL, "newterm(dumb), TERMINFO from ncurses/6.6 conanrun env");

    FIELD *field = new_field(1, 20, 0, 0, 0, 0);
    CHECK(field != NULL, "new_field");

    CHECK(set_field_buffer(field, 0, "libformw-ok") == E_OK, "set_field_buffer");

    char *buf = field_buffer(field, 0);
    CHECK(buf != NULL, "field_buffer");
    CHECK(strncmp(buf, "libformw-ok", 11) == 0, "field_buffer content");

    CHECK(set_field_status(field, TRUE) == E_OK, "set_field_status");
    CHECK(field_status(field) == TRUE, "field_status");

    FIELD *fields[2];
    fields[0] = field;
    fields[1] = NULL;
    FORM *form = new_form(fields);
    CHECK(form != NULL, "new_form");
    CHECK(field_count(form) == 1, "field_count");
    CHECK(set_current_field(form, field) == E_OK, "set_current_field");
    CHECK(current_field(form) == field, "current_field");

    CHECK(free_form(form) == E_OK, "free_form");
    CHECK(free_field(field) == E_OK, "free_field");

    endwin();
    printf("LIBFORMW_FORM_TEST_OK checks=%d\n", g_checks);
    return 0;
}
