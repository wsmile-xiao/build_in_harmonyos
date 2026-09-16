/* test_package/test.c — consumer of libfcgi (FastCGI 2.x).
 * Exercises the documented FCGI_Accept loop in CGI fallback mode:
 * when the process is not spawned by a web server, libfcgi serves a
 * single CGI request, so the program must print once and exit 0. */
#include <fcgi_stdio.h>

int main(void)
{
    while (FCGI_Accept() >= 0) {
        printf("Content-Type: text/plain\r\n\r\n");
        printf("fcgi-ok\n");
    }
    return 0;
}
