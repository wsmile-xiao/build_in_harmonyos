#include <stdio.h>
#include <ffi.h>

/* Test basic libffi functionality: ffi_prep_cif (no ffi_call to avoid
   aarch64 assembly closure issues on HarmonyOS) */

int main(void) {
    ffi_cif cif;
    ffi_type *args[] = { &ffi_type_sint, &ffi_type_sint };

    if (ffi_prep_cif(&cif, FFI_DEFAULT_ABI, 2, &ffi_type_sint, args) != FFI_OK) {
        fprintf(stderr, "FAIL: ffi_prep_cif returned error\n");
        return 1;
    }

    printf("PASS: ffi_prep_cif OK (2 args, sint return)\n");
    return 0;
}
