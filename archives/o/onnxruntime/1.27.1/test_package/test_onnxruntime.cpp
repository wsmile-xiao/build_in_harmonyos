// Smoke test: verify ONNX Runtime C API is accessible
#include <onnxruntime/onnxruntime_c_api.h>
#include <stdio.h>

int main() {
    const OrtApiBase* api_base = OrtGetApiBase();
    if (api_base == nullptr) {
        printf("FAIL: OrtGetApiBase() returned nullptr\n");
        return 1;
    }
    printf("OK: ONNX Runtime version: %s\n", api_base->GetVersionString());
    return 0;
}
