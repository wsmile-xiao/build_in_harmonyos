#include <ffi.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct pair_value {
    int32_t number;
    double fraction;
};

static int add_numbers(int left, int right) {
    return left + right;
}

static struct pair_value make_pair(int32_t number, double fraction) {
    struct pair_value value = {number, fraction};
    return value;
}

static void closure_add(
    ffi_cif *cif,
    void *result,
    void **arguments,
    void *user_data
) {
    const int bias = *(const int *)user_data;
    (void)cif;
    *(int *)result =
        *(const int *)arguments[0] + *(const int *)arguments[1] + bias;
}

static int test_ordinary_call(void) {
    ffi_cif cif;
    ffi_type *argument_types[] = {&ffi_type_sint, &ffi_type_sint};
    int left = 19;
    int right = 23;
    int result = 0;
    void *argument_values[] = {&left, &right};

    if (ffi_prep_cif(
            &cif,
            FFI_DEFAULT_ABI,
            2,
            &ffi_type_sint,
            argument_types
        ) != FFI_OK) {
        return 1;
    }
    ffi_call(&cif, FFI_FN(add_numbers), &result, argument_values);
    return result == 42 ? 0 : 1;
}

static int test_struct_abi(void) {
    ffi_cif cif;
    ffi_type *pair_elements[] = {
        &ffi_type_sint32,
        &ffi_type_double,
        NULL,
    };
    ffi_type pair_type = {0, 0, FFI_TYPE_STRUCT, pair_elements};
    ffi_type *argument_types[] = {&ffi_type_sint32, &ffi_type_double};
    int32_t number = 17;
    double fraction = 3.25;
    struct pair_value result = {0, 0.0};
    void *argument_values[] = {&number, &fraction};

    if (ffi_prep_cif(
            &cif,
            FFI_DEFAULT_ABI,
            2,
            &pair_type,
            argument_types
        ) != FFI_OK) {
        return 1;
    }
    ffi_call(&cif, FFI_FN(make_pair), &result, argument_values);
    return result.number == number && result.fraction == fraction ? 0 : 1;
}

static int test_closure_callback(void) {
    typedef int (*closure_function)(int, int);

    ffi_cif cif;
    ffi_type *argument_types[] = {&ffi_type_sint, &ffi_type_sint};
    ffi_closure *closure;
    closure_function function = NULL;
    void *code = NULL;
    int bias = 5;
    int result;

    closure = ffi_closure_alloc(sizeof(*closure), &code);
    if (closure == NULL) {
        return 77;
    }
    if (code == NULL || sizeof(function) != sizeof(code)) {
        if (closure != NULL) {
            ffi_closure_free(closure);
        }
        return 1;
    }
    if (ffi_prep_cif(
            &cif,
            FFI_DEFAULT_ABI,
            2,
            &ffi_type_sint,
            argument_types
        ) != FFI_OK) {
        ffi_closure_free(closure);
        return 1;
    }
    if (ffi_prep_closure_loc(
            closure,
            &cif,
            closure_add,
            &bias,
            code
        ) != FFI_OK) {
        ffi_closure_free(closure);
        return 1;
    }

    memcpy(&function, &code, sizeof(function));
    result = function(11, 13);
    ffi_closure_free(closure);
    return result == 29 ? 0 : 1;
}

int main(void) {
    int closure_status;

    if (test_ordinary_call() != 0) {
        fprintf(stderr, "FAIL: ffi_call integer flow\n");
        return 1;
    }
    if (test_struct_abi() != 0) {
        fprintf(stderr, "FAIL: ffi_call struct ABI flow\n");
        return 1;
    }

    puts("PASS consumer_call call=42 struct=17/3.25");
    closure_status = test_closure_callback();
    if (closure_status == 0) {
        puts("PASS consumer_closure closure=29");
        return 0;
    }
    if (closure_status == 77) {
        puts("UNSUPPORTED consumer_closure ffi_closure_alloc");
        return 77;
    }

    fprintf(stderr, "FAIL: ffi_closure callback flow\n");
    return 1;
}
