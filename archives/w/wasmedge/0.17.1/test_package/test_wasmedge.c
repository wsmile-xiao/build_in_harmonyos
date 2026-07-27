#include <stdint.h>
#include <string.h>
#include <wasmedge/wasmedge.h>

static int check_version_api(void) {
    const char *version = WasmEdge_VersionGet();
    if (version == NULL || strstr(version, "0.17.1") == NULL) {
        return 1;
    }
    if (WasmEdge_VersionGetMajor() != 0 || WasmEdge_VersionGetMinor() != 17 ||
        WasmEdge_VersionGetPatch() != 1) {
        return 1;
    }
    return 0;
}

static int check_vm_lifecycle_and_execution(void) {
    static const uint8_t wasm_add_module[] = {
        0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
        0x01, 0x07, 0x01, 0x60, 0x02, 0x7f, 0x7f, 0x01,
        0x7f, 0x03, 0x02, 0x01, 0x00, 0x07, 0x07, 0x01,
        0x03, 0x61, 0x64, 0x64, 0x00, 0x00, 0x0a, 0x09,
        0x01, 0x07, 0x00, 0x20, 0x00, 0x20, 0x01, 0x6a,
        0x0b,
    };

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
    WasmEdge_Value params[2] = {WasmEdge_ValueGenI32(20), WasmEdge_ValueGenI32(22)};
    WasmEdge_Value returns[1];
    WasmEdge_Result result = WasmEdge_VMRunWasmFromBuffer(
        vm, wasm_add_module, sizeof(wasm_add_module), func, params, 2, returns, 1);
    WasmEdge_StringDelete(func);

    int failed = 0;
    if (!WasmEdge_ResultOK(result)) {
        failed = 1;
    } else if (WasmEdge_ValueGetI32(returns[0]) != 42) {
        failed = 1;
    }

    WasmEdge_VMDelete(vm);
    WasmEdge_ConfigureDelete(conf);
    return failed;
}

int main(void) {
    if (check_version_api() != 0) {
        return 1;
    }
    if (check_vm_lifecycle_and_execution() != 0) {
        return 1;
    }
    return 0;
}
