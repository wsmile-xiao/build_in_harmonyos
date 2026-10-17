#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wasmedge/wasmedge.h>

static const uint8_t wasm_add_module[] = {
    0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x07, 0x01, 0x60, 0x02, 0x7f, 0x7f, 0x01,
    0x7f, 0x03, 0x02, 0x01, 0x00, 0x07, 0x07, 0x01,
    0x03, 0x61, 0x64, 0x64, 0x00, 0x00, 0x0a, 0x09,
    0x01, 0x07, 0x00, 0x20, 0x00, 0x20, 0x01, 0x6a,
    0x0b,
};

static const uint8_t invalid_wasm_module[] = {
    0x00, 0x61, 0x73, 0x6d, 0x00, 0x00, 0x00, 0x00,
};

static int check_version_api(void) {
    const char *version = WasmEdge_VersionGet();
    if (version == NULL || version[0] == '\0') {
        return 1;
    }
    if (strcmp(version, WASMEDGE_VERSION) != 0) {
        return 1;
    }
    if (WasmEdge_VersionGetMajor() != WASMEDGE_VERSION_MAJOR ||
        WasmEdge_VersionGetMinor() != WASMEDGE_VERSION_MINOR ||
        WasmEdge_VersionGetPatch() != WASMEDGE_VERSION_PATCH) {
        return 1;
    }
    return 0;
}

static int check_configure_and_vm_lifecycle(void) {
    WasmEdge_ConfigureContext *conf = WasmEdge_ConfigureCreate();
    if (conf == NULL) {
        return 1;
    }
    WasmEdge_VMContext *vm = WasmEdge_VMCreate(conf, NULL);
    if (vm == NULL) {
        WasmEdge_ConfigureDelete(conf);
        return 1;
    }
    WasmEdge_VMDelete(vm);
    WasmEdge_ConfigureDelete(conf);
    return 0;
}

static int run_add_once(int lhs, int rhs, int expected) {
    WasmEdge_ConfigureContext *conf = WasmEdge_ConfigureCreate();
    if (conf == NULL) {
        return 1;
    }
    WasmEdge_VMContext *vm = WasmEdge_VMCreate(conf, NULL);
    if (vm == NULL) {
        WasmEdge_ConfigureDelete(conf);
        return 1;
    }

    WasmEdge_String func = WasmEdge_StringCreateByCString("add");
    WasmEdge_Value params[2] = {WasmEdge_ValueGenI32(lhs), WasmEdge_ValueGenI32(rhs)};
    WasmEdge_Value returns[1];
    WasmEdge_Result result = WasmEdge_VMRunWasmFromBuffer(
        vm, wasm_add_module, sizeof(wasm_add_module), func, params, 2, returns, 1);
    WasmEdge_StringDelete(func);

    int failed = 0;
    if (!WasmEdge_ResultOK(result)) {
        failed = 1;
    } else if (WasmEdge_ValueGetI32(returns[0]) != expected) {
        failed = 1;
    }

    WasmEdge_VMDelete(vm);
    WasmEdge_ConfigureDelete(conf);
    return failed;
}

static int check_vm_execution(void) {
    return run_add_once(20, 22, 42);
}

static int check_repeated_execution(void) {
    if (run_add_once(1, 2, 3) != 0) {
        return 1;
    }
    return run_add_once(123, 456, 579);
}

static int check_invalid_module_is_rejected(void) {
    WasmEdge_ConfigureContext *conf = WasmEdge_ConfigureCreate();
    if (conf == NULL) {
        return 1;
    }
    WasmEdge_VMContext *vm = WasmEdge_VMCreate(conf, NULL);
    if (vm == NULL) {
        WasmEdge_ConfigureDelete(conf);
        return 1;
    }

    WasmEdge_String func = WasmEdge_StringCreateByCString("missing");
    WasmEdge_Result result = WasmEdge_VMRunWasmFromBuffer(
        vm, invalid_wasm_module, sizeof(invalid_wasm_module), func, NULL, 0, NULL, 0);
    WasmEdge_StringDelete(func);

    int failed = WasmEdge_ResultOK(result) ? 1 : 0;
    WasmEdge_VMDelete(vm);
    WasmEdge_ConfigureDelete(conf);
    return failed;
}

static int check_missing_function_is_rejected(void) {
    WasmEdge_ConfigureContext *conf = WasmEdge_ConfigureCreate();
    if (conf == NULL) {
        return 1;
    }
    WasmEdge_VMContext *vm = WasmEdge_VMCreate(conf, NULL);
    if (vm == NULL) {
        WasmEdge_ConfigureDelete(conf);
        return 1;
    }

    WasmEdge_String func = WasmEdge_StringCreateByCString("missing");
    WasmEdge_Result result = WasmEdge_VMRunWasmFromBuffer(
        vm, wasm_add_module, sizeof(wasm_add_module), func, NULL, 0, NULL, 0);
    WasmEdge_StringDelete(func);

    int failed = WasmEdge_ResultOK(result) ? 1 : 0;
    WasmEdge_VMDelete(vm);
    WasmEdge_ConfigureDelete(conf);
    return failed;
}

static int run_named_test(const char *name) {
    if (strcmp(name, "--version-api") == 0) {
        return check_version_api();
    }
    if (strcmp(name, "--vm-lifecycle") == 0) {
        return check_configure_and_vm_lifecycle();
    }
    if (strcmp(name, "--vm-execute-add") == 0) {
        return check_vm_execution();
    }
    if (strcmp(name, "--vm-repeat-execute") == 0) {
        return check_repeated_execution();
    }
    if (strcmp(name, "--reject-invalid-module") == 0) {
        return check_invalid_module_is_rejected();
    }
    if (strcmp(name, "--reject-missing-function") == 0) {
        return check_missing_function_is_rejected();
    }
    fprintf(stderr, "unknown test mode: %s\n", name);
    return 1;
}

int main(int argc, char **argv) {
    if (argc == 2) {
        return run_named_test(argv[1]);
    }

    if (check_version_api() != 0) {
        return 1;
    }
    if (check_configure_and_vm_lifecycle() != 0) {
        return 1;
    }
    if (check_vm_execution() != 0) {
        return 1;
    }
    if (check_repeated_execution() != 0) {
        return 1;
    }
    if (check_invalid_module_is_rejected() != 0) {
        return 1;
    }
    if (check_missing_function_is_rejected() != 0) {
        return 1;
    }
    return 0;
}
