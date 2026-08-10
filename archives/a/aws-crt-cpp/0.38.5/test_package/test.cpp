#include <aws/crt/Api.h>
#include <cstdio>

int main(int argc, char *argv[]) {
    (void)argc;
    (void)argv;

    /* Initialize the AWS CRT C++ runtime - RAII handle */
    Aws::Crt::ApiHandle apiHandle;

    /* Verify the library is properly linked by checking the version */
    auto version = apiHandle.GetCrtVersion();
    if (version.major == 0 && version.minor == 0 && version.patch == 0) {
        fprintf(stderr, "Invalid AWS CRT C++ version\n");
        return 1;
    }
    printf("AWS CRT C++ version: %d.%d.%d\n", version.major, version.minor, version.patch);

    return 0;
}
