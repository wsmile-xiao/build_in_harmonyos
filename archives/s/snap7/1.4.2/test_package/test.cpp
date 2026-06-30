#include <stdio.h>
#include "snap7.h"

int main(void) {
    printf("snap7 test: creating client...\n");
    S7Object client = Cli_Create();
    if (client != 0) {
        printf("Cli_Create succeeded\n");
        Cli_Destroy(&client);
        printf("Cli_Destroy succeeded\n");
        printf("snap7 1.4.2: OK\n");
        return 0;
    } else {
        printf("Cli_Create failed\n");
        return 1;
    }
}
