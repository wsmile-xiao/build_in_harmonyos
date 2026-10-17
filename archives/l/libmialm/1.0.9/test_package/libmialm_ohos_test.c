#include <mialm.h>

#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "check failed at line %d: %s\n",                 \
                    __LINE__, #condition);                                     \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    struct utsname platform;
    MiaVector3d *vector;

    CHECK(uname(&platform) == 0);
    CHECK(strcmp(platform.sysname, "HarmonyOS") == 0);
    CHECK(strcmp(platform.machine, "aarch64") == 0);

    vector = mia_vector3d_new(3.0f, 4.0f, 0.0f);
    CHECK(vector != NULL && mia_vector3d_get_norm(vector) == 5.0f);
    g_object_unref(vector);
    return 0;
}
