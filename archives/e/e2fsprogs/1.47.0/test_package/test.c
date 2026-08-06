#include <stdio.h>
#include <et/com_err.h>

int main(void) {
    /* Call com_err from libcom_err — verifies the library is actually linked */
    com_err("test_e2fsprogs", 0, "e2fsprogs library test OK");
    return 0;
}
