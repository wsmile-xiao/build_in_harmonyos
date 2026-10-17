// Qt 6.5+ keeps the RHI headers (QShader/QShaderBaker/QShaderDescription) in
// the versioned per-module include directories; include them through the
// canonical <rhi/...> paths.
#include <rhi/qshader.h>
#include <rhi/qshaderbaker.h>
#include <rhi/qshaderdescription.h>
#include <QString>

#include <cstdio>

/*
 * Substantive smoke test for the Qt Shader Tools package on HarmonyOS PC.
 *
 * Exercises the real QShaderBaker/QShader pipeline: it bakes a tiny GLSL
 * fragment shader to SPIR-V through the bundled glslang/SPIRV-Cross stack and
 * verifies the produced QShader carries valid SPIR-V data.
 */
int main()
{
    QShaderBaker baker;

    const QString fragmentSource = QStringLiteral(
        "#version 450\n"
        "layout(location = 0) in vec2 v_texcoord;\n"
        "layout(location = 0) out vec4 fragColor;\n"
        "void main() {\n"
        "    fragColor = vec4(v_texcoord, 0.0, 1.0);\n"
        "}\n");

    baker.setSourceString(fragmentSource.toUtf8(), QShader::FragmentStage);
    baker.setGeneratedShaders(
        {{QShader::SpirvShader, QShaderVersion(100)}});

    // Mirror the options the bundled qsb tool uses: without an explicit
    // SpirvOptions the bake fails on HarmonyOS (empty error message), and the
    // StandardShader variant must be requested explicitly.
    QShaderBaker::SpirvOptions spirvOptions;
    spirvOptions |= QShaderBaker::SpirvOption::StripDebugAndVarInfo;
    baker.setSpirvOptions(spirvOptions);
    baker.setGeneratedShaderVariants({QShader::StandardShader});

    QShader shader = baker.bake();
    if (!shader.isValid()) {
        std::fprintf(stderr, "QShaderBaker::bake() failed: %s\n",
                     qPrintable(baker.errorMessage()));
        return 1;
    }

    const QShaderKey spirvKey(QShader::SpirvShader, QShaderVersion(100));
    if (shader.shader(spirvKey).shader().isEmpty()) {
        std::fprintf(stderr, "Baked shader carries no SPIR-V payload\n");
        return 2;
    }

    const QShaderDescription description = shader.description();
    if (description.inputVariables().isEmpty()) {
        std::fprintf(stderr, "Baked shader reports no input variables\n");
        return 3;
    }

    std::printf("QShader bake OK: SPIR-V %d bytes, %d input variables\n",
                int(shader.shader(spirvKey).shader().size()),
                int(description.inputVariables().size()));
    return 0;
}
