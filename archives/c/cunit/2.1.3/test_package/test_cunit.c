#include <CUnit/Basic.h>
#include <stdio.h>

int main(void) {
    if (CU_initialize_registry() != CUE_SUCCESS) {
        return CU_get_error();
    }
    if (CU_add_suite("test_suite", NULL, NULL) == NULL) {
        CU_cleanup_registry();
        return 1;
    }
    CU_cleanup_registry();
    printf("cunit test passed!\n");
    return 0;
}
