#include <tinyframe/tinyframe.h>

#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

int main(void)
{
    struct utsname info;
    unsigned char header[4];
    if (uname(&info) != 0 || strcmp(info.sysname, "HarmonyOS") != 0) {
        fprintf(stderr, "expected HarmonyOS, got %s\n",
                uname(&info) == 0 ? info.sysname : "<uname failed>");
        return 1;
    }
    if (sizeof(void *) != 8 || sysconf(_SC_PAGESIZE) <= 0) {
        fprintf(stderr, "invalid HarmonyOS PC aarch64 runtime model\n");
        return 1;
    }
    tinyframe_set_header(header, 0x484d4f53U);
    if (header[0] != 'H' || header[1] != 'M' ||
        header[2] != 'O' || header[3] != 'S') {
        return 1;
    }
    return 0;
}
