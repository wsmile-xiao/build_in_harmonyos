#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "vamp/vamp.h"

int main(void) {
    /* Check that the Vamp SDK header is accessible and basic types are defined */
    VampPluginDescriptor descriptor;
    memset(&descriptor, 0, sizeof(descriptor));
    descriptor.vampApiVersion = 2;
    if (descriptor.vampApiVersion != 2) {
        fprintf(stderr, "VampPluginDescriptor struct not usable\n");
        return 2;
    }
    puts("vamp-plugin-sdk header assertions: 1 passed");
    return 0;
}