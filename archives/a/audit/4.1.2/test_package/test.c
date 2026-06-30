#include <stdio.h>
#include <stdlib.h>
#include <libaudit.h>

int main(void) {
    /* Verify libaudit is linked by calling a simple function */
    int machine = audit_detect_machine();
    printf("test audit 4.1.2: OK (machine=%d)\n", machine);
    return 0;
}
