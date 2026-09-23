#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <colr.h>

int main(void) {
    char *colored = colr("colrc", fore(BLUE));
    if (colored == NULL) {
        fprintf(stderr, "colr() returned NULL\n");
        return 1;
    }
    if (strstr(colored, "colrc") == NULL) {
        fprintf(stderr, "colr() output does not contain the input text\n");
        free(colored);
        return 1;
    }
    free(colored);
    return 0;
}
