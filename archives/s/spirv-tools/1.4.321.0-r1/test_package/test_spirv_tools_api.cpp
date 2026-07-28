#include <cstring>
#include <iostream>
#include <spirv-tools/libspirv.h>

int main() {
    const char *assembly =
        "OpCapability Shader\n"
        "OpMemoryModel Logical GLSL450\n"
        "OpEntryPoint Fragment %main \"main\"\n"
        "OpExecutionMode %main OriginUpperLeft\n"
        "%void = OpTypeVoid\n"
        "%fn = OpTypeFunction %void\n"
        "%main = OpFunction %void None %fn\n"
        "%entry = OpLabel\n"
        "OpReturn\n"
        "OpFunctionEnd\n";

    spv_context context = spvContextCreate(SPV_ENV_UNIVERSAL_1_5);
    if (!context) {
        std::cerr << "failed to create SPIR-V context\n";
        return 1;
    }

    spv_binary binary = nullptr;
    spv_diagnostic diagnostic = nullptr;
    spv_result_t result = spvTextToBinary(
        context,
        assembly,
        std::strlen(assembly),
        &binary,
        &diagnostic
    );
    if (result != SPV_SUCCESS) {
        if (diagnostic) {
            std::cerr << diagnostic->error << "\n";
            spvDiagnosticDestroy(diagnostic);
        }
        spvContextDestroy(context);
        return 1;
    }

    spv_validator_options options = spvValidatorOptionsCreate();
    if (!options) {
        std::cerr << "failed to create SPIR-V validator options\n";
        spvBinaryDestroy(binary);
        spvContextDestroy(context);
        return 1;
    }
    spv_const_binary_t const_binary = {
        binary->code,
        binary->wordCount,
    };
    diagnostic = nullptr;
    result = spvValidateWithOptions(context, options, &const_binary, &diagnostic);
    spvValidatorOptionsDestroy(options);
    spvBinaryDestroy(binary);
    if (result != SPV_SUCCESS) {
        if (diagnostic) {
            std::cerr << diagnostic->error << "\n";
            spvDiagnosticDestroy(diagnostic);
        }
        std::cerr << "SPIR-V validation failed\n";
        spvContextDestroy(context);
        return 1;
    }
    if (diagnostic) {
        spvDiagnosticDestroy(diagnostic);
    }
    spvContextDestroy(context);

    std::cout << "PASS: SPIRV-Tools assembled and validated a SPIR-V module\n";
    return 0;
}
