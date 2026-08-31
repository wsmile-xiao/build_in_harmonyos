#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    char command[1024];
    int i;

    if (argc < 3) {
        return 2;
    }
    for (i = 1; i < argc; ++i) {
        int status;
        if (snprintf(command, sizeof(command), "\"%s\" --help", argv[i]) < 0) {
            return 1;
        }
        status = system(command);
        if (status != 0 && status != 256) {
            return 1;
        }
    }
    puts("consumer awesfx tools test passed");
    return 0;
}
