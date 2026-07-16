#include <wasmedge/wasmedge.h>

int main(void) {
    WasmEdge_ConfigureContext *conf = WasmEdge_ConfigureCreate();
    if (conf == NULL) {
        return 1;
    }
    WasmEdge_ConfigureDelete(conf);
    return 0;
}
