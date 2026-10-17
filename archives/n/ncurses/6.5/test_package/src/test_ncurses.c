#include <ncurses.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

int main(void) {
    /* 验证 ncurses 宽字符版本 API 可用（不依赖终端/terminfo）：
       1. curses_version() 返回库版本
       2. setcchar/getcchar 宽字符串往返 */
    const char *version = curses_version();
    if (version == NULL || strstr(version, "6.5") == NULL) {
        printf("FAIL: curses_version() = %s\n", version ? version : "(null)");
        return 1;
    }

    /* 宽字符 API：setcchar/getcchar 往返（纯库函数，无需终端）。
       ncurses 的 cchar_t 语义：只保留首个 spacing 字符 + 后续 combining
       字符，因此用单字符验证往返；getcchar 要求 attrs/pair_arg 为
       非 NULL 输出指针 */
    wchar_t msg[] = L"\u00e9";  /* é — 单宽字符 */
    cchar_t wide_char;
    wchar_t wide_str[64];
    attr_t attrs = 0;
    short pair = 0;
    memset(wide_str, 0, sizeof(wide_str));
    if (setcchar(&wide_char, msg, A_NORMAL, 0, NULL) != OK) {
        printf("FAIL: setcchar failed\n");
        return 1;
    }
    if (getcchar(&wide_char, wide_str, &attrs, &pair, NULL) != OK) {
        printf("FAIL: getcchar failed\n");
        return 1;
    }

    if (wcscmp(wide_str, msg) != 0) {
        printf("FAIL: wide-char roundtrip mismatch\n");
        return 1;
    }

    printf("ncurses %s: wide-char roundtrip ok\n", version);
    return 0;
}
