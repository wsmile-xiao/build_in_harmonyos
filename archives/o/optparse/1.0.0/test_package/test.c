#include <stdio.h>
#define OPTPARSE_IMPLEMENTATION
#include "optparse.h"

int main(int argc, char **argv) {
    struct optparse options;
    int option;
    
    /* Initialize with dummy argv for testing */
    char *test_argv[] = {"test", "-a", "-b", "value", NULL};
    optparse_init(&options, test_argv);
    
    /* Parse options */
    while ((option = optparse(&options, "ab:")) != -1) {
        switch (option) {
        case 'a':
            printf("Option -a parsed\n");
            break;
        case 'b':
            printf("Option -b parsed with argument: %s\n", options.optarg);
            break;
        case '?':
            fprintf(stderr, "Error: %s\n", options.errmsg);
            return 1;
        }
    }
    
    printf("optparse test passed\n");
    return 0;
}
