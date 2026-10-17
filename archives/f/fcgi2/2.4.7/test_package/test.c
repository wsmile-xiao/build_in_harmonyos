/*
 * test_package/test.c — 消费者测试程序 (R34)
 *
 * 以第三方使用者身份，仅通过已安装的公开头文件 (fcgi_stdio.h) 与公开 API
 * (FCGI_Accept/FCGI_printf) 调用 libfcgi，验证编译、链接与运行：
 *   - CGI 回退模式：无 web server 派生时 FCGI_Accept 服务 stdin 单次请求
 *   - 输出 "fcgi-ok" 标记供 test.sh 断言
 */
#include <fcgi_stdio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    int count = 0;
    while (FCGI_Accept() >= 0) {
        char *method = getenv("REQUEST_METHOD");
        if (method == NULL) {
            method = "UNKNOWN";
        }
        FCGI_printf("Content-type: text/plain\r\n\r\n"
                    "fcgi-ok method=%s count=%d pid=%ld\n",
                    method, ++count, (long)getpid());
        break; /* 单请求验证 */
    }
    return 0;
}
