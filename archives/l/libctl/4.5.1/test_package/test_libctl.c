#include <ctl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    vector3 a = { 1.0, 2.0, 3.0 };
    vector3 b = { 4.0, 5.0, 6.0 };
    char *path;
    scm_init_guile();
    path = ctl_fix_path("/tmp/libctl-consumer");
    if (!path || strcmp(path, "/tmp/libctl-consumer") != 0) {
        free(path);
        return 1;
    }
    free(path);
    if (vector3_dot(a, b) != 32.0)
        return 2;
    puts("LIBCTL_CONSUMER_PASS");
    return 0;
}
