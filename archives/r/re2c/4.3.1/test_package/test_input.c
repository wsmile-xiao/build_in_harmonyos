/* re2c test input — simple lexer that recognizes numbers */
#include <stdio.h>

int scan(const char *str) {
    /* re2c default simple API modifies YYCURSOR, so use non-const */
    char *YYCURSOR = (char *)str;
    char *YYMARKER;
    /*!re2c
        re2c:yyfill:enable = 0;
        re2c:define:YYCTYPE = "char";

        [0-9]+  { return 1; }
        .       { return 0; }
    */
}

int main(void) {
    int result = scan("12345");
    printf("re2c test: scan result=%d (expected 1)\n", result);
    return result == 1 ? 0 : 1;
}
