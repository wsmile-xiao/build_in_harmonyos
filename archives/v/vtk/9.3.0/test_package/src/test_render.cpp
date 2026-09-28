// test_render.cpp — deep-adaptation EGL/GLES offscreen render readback test (R40)
//
// Validates the substantive HarmonyOS graphics backend of the VTK package:
//   1. Create a real vtkEGLRenderWindow (EGL + OpenGL ES — the native
//      HarmonyOS graphics stack) in offscreen mode.
//   2. Build a sphere pipeline (vtkSphereSource -> vtkPolyDataMapper ->
//      vtkActor -> vtkRenderer) and execute a real GPU draw via Render().
//   3. Read the framebuffer back through vtkWindowToImageFilter and assert
//      that non-background pixels were actually produced (a broken EGL/GLES
//      stack or a stub would yield an empty/background-only framebuffer).
//
// Every assertion prints a [STEP]/[PASS]/[FAIL] record and any failure
// exits non-zero.  "--expect-fail" runs a deliberately inverted assertion
// which MUST fail and exit non-zero.

#include "vtkActor.h"
#include "vtkCallbackCommand.h"
#include "vtkCommand.h"
#ifdef VTK_TEST_EGL
#include "vtkEGLRenderWindow.h"
using TestRenderWindow = vtkEGLRenderWindow;
#else
#include "vtkRenderWindow.h"
using TestRenderWindow = vtkRenderWindow;
#endif
#include "vtkImageData.h"
#include "vtkNew.h"
#include "vtkOpenGLFramebufferObject.h"
#include "vtkOpenGLRenderWindow.h"
#include "vtkOpenGLShaderCache.h"
#include "vtkOpenGLState.h"
#include "vtkOpenGLVertexArrayObject.h"
#include "vtkPixelBufferObject.h"
#include "vtkPolyDataMapper.h"
#include "vtkPointData.h"
#include "vtkRenderer.h"
#include "vtkShaderProgram.h"
#include "vtkSphereSource.h"
#include "vtkSmartPointer.h"
#include "vtkTextureObject.h"
#include "vtkUnsignedCharArray.h"
#include "vtkWindowToImageFilter.h"
#include "vtk_glew.h"

#include <cstdio>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <vector>

static int failures = 0;

static void check(int cond, const char* what, const char* expected,
                  const char* actual)
{
    if (cond) {
        std::printf("[PASS] %s (expected %s, got %s)\n", what, expected, actual);
    } else {
        std::printf("[FAIL] %s (expected %s, got %s)\n", what, expected, actual);
        ++failures;
    }
}

static void checkTextureReadback(vtkOpenGLRenderWindow* window)
{
    std::printf("[STEP] 5: repeated RGB float upload and GPU readback\n");
    window->MakeCurrent();
    vtkNew<vtkTextureObject> texture;
    texture->SetContext(window);
    texture->SetMinificationFilter(vtkTextureObject::Nearest);
    texture->SetMagnificationFilter(vtkTextureObject::Nearest);
    for (int pass = 0; pass < 2; ++pass) {
        float expected[18];
        float actual[18] = {};
        for (int i = 0; i < 18; ++i) {
            expected[i] = 10.0f * pass + 0.25f * i;
        }
        bool ok = texture->Create2DFromRaw(3, 2, 3, VTK_FLOAT, expected);
        vtkSmartPointer<vtkPixelBufferObject> pixels;
        if (ok) {
            pixels.TakeReference(texture->Download());
        }
        ok = ok && pixels && pixels->GetComponents() == 3 && pixels->GetType() == VTK_FLOAT;
        if (ok && pass == 0) {
            ok = pixels->Download1D(VTK_FLOAT, actual, 6, 3, 0);
        } else if (ok) {
            const float* mapped = static_cast<const float*>(pixels->MapPackedBuffer());
            ok = mapped != nullptr;
            if (mapped) {
                for (int i = 0; i < 18; ++i) {
                    actual[i] = mapped[i];
                }
                pixels->UnmapPackedBuffer();
            }
        }
        for (int i = 0; i < 18 && ok; ++i) {
            ok = std::isfinite(actual[i]) && std::fabs(actual[i] - expected[i]) < 1.e-5f;
        }
        check(ok, pass == 0 ? "RGB float readback" : "reused texture RGB float readback",
              "18 matching HDR values", ok ? "18 matching HDR values" : "mismatch");
    }

#if VTK_MODULE_vtkglew_GLES3
    int observedErrors = 0;
    vtkNew<vtkCallbackCommand> expectedError;
    expectedError->SetClientData(&observedErrors);
    expectedError->SetCallback([](vtkObject*, unsigned long, void* data, void*) {
        ++*static_cast<int*>(data);
    });
    const unsigned long observer = texture->AddObserver(vtkCommand::ErrorEvent, expectedError);
    vtkSmartPointer<vtkPixelBufferObject> missingLevel;
    missingLevel.TakeReference(texture->Download(texture->GetTarget(), 1));
    texture->RemoveObserver(observer);
    check(!missingLevel && observedErrors > 0, "missing texture level reports failure",
          "null result and error event", !missingLevel && observedErrors > 0 ? "null result and error event" : "unexpected result");

    vtkSmartPointer<vtkPixelBufferObject> recovered;
    recovered.TakeReference(texture->Download());
    float restored[18] = {};
    bool restoredValues = recovered && recovered->Download1D(VTK_FLOAT, restored, 6, 3, 0);
    for (int i = 0; i < 18 && restoredValues; ++i) {
        restoredValues = std::isfinite(restored[i]) && std::fabs(restored[i] - (10.0f + 0.25f * i)) < 1.e-5f;
    }
    check(restoredValues, "readback after missing level", "18 original HDR values",
          restoredValues ? "18 original HDR values" : "mismatch");
#endif
}

static void checkNormalizedTexture(vtkOpenGLRenderWindow* window)
{
    std::printf("[STEP] 6: strided 16-bit volume texture preserves values and unpack state\n");
    unsigned short input[4 * 3 * 2 * 4];
    for (int i = 0; i < 96; ++i) {
        input[i] = static_cast<unsigned short>((i * 1777) % 65536);
    }
    auto state = window->GetState();
    const GLenum names[] = {GL_UNPACK_ROW_LENGTH, GL_UNPACK_IMAGE_HEIGHT,
                            GL_UNPACK_SKIP_ROWS, GL_UNPACK_SKIP_PIXELS};
    const GLint strides[] = {4, 3, 1, 1};
    GLint saved[4];
    for (int i = 0; i < 4; ++i) {
        glGetIntegerv(names[i], &saved[i]);
        state->vtkglPixelStorei(names[i], strides[i]);
    }
    vtkNew<vtkTextureObject> texture;
    texture->SetContext(window);
    texture->SetMinificationFilter(vtkTextureObject::Nearest);
    texture->SetMagnificationFilter(vtkTextureObject::Nearest);
    bool ok = texture->Create3DFromRaw(2, 2, 2, 4, VTK_UNSIGNED_SHORT, input);
    bool statePreserved = true;
    for (int i = 0; i < 4; ++i) {
        GLint actual = 0;
        glGetIntegerv(names[i], &actual);
        statePreserved = statePreserved && actual == strides[i];
        state->vtkglPixelStorei(names[i], saved[i]);
    }
    unsigned short actual[32] = {};
    vtkSmartPointer<vtkPixelBufferObject> pixels;
    if (ok) {
        pixels.TakeReference(texture->Download());
    }
    ok = ok && pixels && pixels->GetType() == VTK_UNSIGNED_SHORT &&
         pixels->Download1D(VTK_UNSIGNED_SHORT, actual, 8, 4, 0);
    for (int z = 0; z < 2 && ok; ++z) {
        for (int y = 0; y < 2 && ok; ++y) {
            for (int x = 0; x < 2 && ok; ++x) {
                for (int c = 0; c < 4; ++c) {
                    const int source = (((z * 3 + y + 1) * 4 + x + 1) * 4 + c);
                    const int target = (((z * 2 + y) * 2 + x) * 4 + c);
                    ok = ok && actual[target] == input[source];
                }
            }
        }
    }
    check(ok, "strided unsigned-short 3D roundtrip", "32 exact values",
          ok ? "32 exact values" : "mismatch");
    check(statePreserved, "unpack state restored", "4 unchanged pixel-store values",
          statePreserved ? "4 unchanged pixel-store values" : "state changed");
}

template <typename Scalar>
static void checkTextureResize(vtkOpenGLRenderWindow* window, int vtkType, int depth)
{
    const int width = 3;
    const int height = 2;
    const int components = 4;
    const int count = width * height * depth * components;
    std::vector<Scalar> original(depth * components, 0);
    vtkNew<vtkTextureObject> texture;
    texture->SetContext(window);
    texture->SetMinificationFilter(vtkTextureObject::Nearest);
    texture->SetMagnificationFilter(vtkTextureObject::Nearest);
    int errors = 0;
    vtkNew<vtkCallbackCommand> observer;
    observer->SetClientData(&errors);
    observer->SetCallback([](vtkObject*, unsigned long, void* data, void*) {
        ++*static_cast<int*>(data);
    });
    texture->AddObserver(vtkCommand::ErrorEvent, observer);
    bool ok = depth == 1
        ? texture->Create2DFromRaw(1, 1, components, vtkType, original.data())
        : texture->Create3DFromRaw(1, 1, depth, components, vtkType, original.data());
    texture->Resize(width, height);
    ok = ok && errors == 0 && glGetError() == GL_NO_ERROR;

    std::vector<Scalar> expected(count);
    std::vector<float> transfer(count);
    for (int i = 0; i < count; ++i) {
        const int value = vtkType == VTK_SHORT ? (i - 24) * 1009 : (i * 1297) % 65536;
        expected[i] = static_cast<Scalar>(value);
        transfer[i] = value / (vtkType == VTK_SHORT ? 32767.0f : 65535.0f);
    }
    if (ok) {
        texture->Activate();
        if (depth == 1) {
            glTexSubImage2D(texture->GetTarget(), 0, 0, 0, width, height,
                            GL_RGBA, GL_FLOAT, transfer.data());
        } else {
            glTexSubImage3D(texture->GetTarget(), 0, 0, 0, 0, width, height, depth,
                            GL_RGBA, GL_FLOAT, transfer.data());
        }
        ok = glGetError() == GL_NO_ERROR;
        texture->Deactivate();
    }
    vtkSmartPointer<vtkPixelBufferObject> pixels;
    if (ok) {
        pixels.TakeReference(texture->Download());
    }
    std::vector<Scalar> actual(count);
    ok = ok && pixels && pixels->GetType() == vtkType &&
        pixels->Download1D(vtkType, actual.data(), width * height * depth, components, 0);
    for (int i = 0; i < count && ok; ++i) {
        ok = actual[i] == expected[i];
    }
    char label[80];
    std::snprintf(label, sizeof(label), "%s %s resize and complete refill",
                  vtkType == VTK_SHORT ? "signed-short" : "unsigned-short",
                  depth == 1 ? "2D" : "3D");
    check(ok, label, "new dimensions and exact logical values",
          ok ? "new dimensions and exact logical values" : "resize or readback mismatch");
}

static void checkDepthCopy(vtkOpenGLRenderWindow* window)
{
    std::printf("[STEP] 7: copy a depth pattern across formats and sample counts\n");
    auto state = window->GetState();
    GLint maxSamples = 0;
    glGetIntegerv(GL_MAX_SAMPLES, &maxSamples);
    const int sampleCounts[] = {0, maxSamples >= 4 ? 4 : maxSamples};
    for (int samples : sampleCounts) {
        state->PushFramebufferBindings();
        vtkOpenGLState::ScopedglViewport viewportSaver(state);
        vtkOpenGLState::ScopedglScissor scissorSaver(state);
        vtkOpenGLState::ScopedglEnableDisable scissorEnableSaver(state, GL_SCISSOR_TEST);
        vtkOpenGLState::ScopedglDepthMask depthMaskSaver(state);
        GLfloat savedClear = 1.0f;
        glGetFloatv(GL_DEPTH_CLEAR_VALUE, &savedClear);
        vtkNew<vtkOpenGLFramebufferObject> source;
        source->SetContext(window);
        bool ok = source->PopulateFramebuffer(4, 2, samples == 0, 1,
                                             VTK_UNSIGNED_CHAR, true, 24, samples);
        source->Bind();
        state->vtkglViewport(0, 0, 4, 2);
        state->vtkglDepthMask(GL_TRUE);
        state->vtkglDisable(GL_SCISSOR_TEST);
        state->vtkglClearDepth(0.25);
        glClear(GL_DEPTH_BUFFER_BIT);
        state->vtkglEnable(GL_SCISSOR_TEST);
        state->vtkglScissor(2, 0, 2, 2);
        state->vtkglClearDepth(0.75);
        glClear(GL_DEPTH_BUFFER_BIT);
        state->vtkglDisable(GL_SCISSOR_TEST);
        vtkNew<vtkTextureObject> copied;
        copied->SetContext(window);
        ok = ok && copied->AllocateDepth(4, 2, vtkTextureObject::Float32);
        copied->CopyFromFrameBuffer(0, 0, 0, 0, 4, 2);
        window->GetRenderFramebuffer()->Bind(GL_DRAW_FRAMEBUFFER);
        state->vtkglViewport(0, 0, 4, 2);
        window->TextureDepthBlit(copied);
        float actual[8] = {};
        ok = ok && window->GetZbufferData(0, 0, 3, 1, actual) == VTK_OK;
        for (int i = 0; i < 8; ++i) {
            const float expected = (i % 4 < 2) ? 0.25f : 0.75f;
            ok = ok && std::isfinite(actual[i]) && std::fabs(actual[i] - expected) < 1.e-5f;
        }
        state->vtkglClearDepth(savedClear);
        state->PopFramebufferBindings();
        check(ok, samples ? "MSAA depth resolve and format conversion" : "depth format conversion",
              "8 matching depth samples", ok ? "8 matching depth samples" : "mismatch");

        // A second viewport starts away from the framebuffer origin. ES MSAA
        // resolve must preserve those coordinates until the subsequent crop.
        state->PushFramebufferBindings();
        source->Bind(GL_READ_FRAMEBUFFER);
        vtkNew<vtkTextureObject> cropped;
        cropped->SetContext(window);
        bool croppedOk = cropped->AllocateDepth(2, 2, vtkTextureObject::Float32);
        cropped->CopyFromFrameBuffer(2, 0, 0, 0, 2, 2);
        cropped->Deactivate();
        window->GetRenderFramebuffer()->Bind(GL_DRAW_FRAMEBUFFER);
        state->vtkglViewport(0, 0, 2, 2);
        window->TextureDepthBlit(cropped);
        float croppedValues[4] = {};
        croppedOk = croppedOk && window->GetZbufferData(0, 0, 1, 1, croppedValues) == VTK_OK;
        for (float value : croppedValues) {
            croppedOk = croppedOk && std::isfinite(value) && std::fabs(value - 0.75f) < 1.e-5f;
        }
        state->PopFramebufferBindings();
        check(croppedOk, samples ? "offset MSAA depth region" : "offset depth region",
              "4 samples at 0.75", croppedOk ? "4 samples at 0.75" : "mismatch");
    }
}

static void checkGeometryDepth(vtkOpenGLRenderWindow* window)
{
    std::printf("[STEP] 8: geometry shader fragment depth with a 32-bit attachment\n");
    const char* vertex = R"(//VTK::System::Dec
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
})";
    const char* geometry = R"(//VTK::System::Dec
layout(triangles) in;
layout(triangle_strip, max_vertices = 3) out;
void main() {
    for (int i = 0; i < 3; ++i) {
        gl_Position = gl_in[i].gl_Position;
        EmitVertex();
    }
    EndPrimitive();
})";
    const char* fragment = R"(//VTK::System::Dec
uniform float expectedDepth;
out vec4 color;
void main() {
    color = vec4(1.0);
    gl_FragDepth = expectedDepth;
})";
    auto state = window->GetState();
    state->PushFramebufferBindings();
    vtkOpenGLState::ScopedglViewport viewportSaver(state);
    vtkOpenGLState::ScopedglEnableDisable scissorSaver(state, GL_SCISSOR_TEST);
    vtkOpenGLState::ScopedglEnableDisable depthSaver(state, GL_DEPTH_TEST);
    vtkOpenGLState::ScopedglDepthFunc depthFuncSaver(state);
    vtkOpenGLState::ScopedglDepthMask depthMaskSaver(state);
    vtkNew<vtkOpenGLFramebufferObject> framebuffer;
    framebuffer->SetContext(window);
    bool ok = framebuffer->PopulateFramebuffer(4, 4, true, 1, VTK_UNSIGNED_CHAR, true, 32, 0);
    framebuffer->Bind();
    state->vtkglViewport(0, 0, 4, 4);
    state->vtkglDisable(GL_SCISSOR_TEST);
    state->vtkglEnable(GL_DEPTH_TEST);
    state->vtkglDepthFunc(GL_ALWAYS);
    state->vtkglDepthMask(GL_TRUE);
    vtkShaderProgram* program = window->GetShaderCache()->ReadyShaderProgram(vertex, fragment, geometry);
    ok = ok && program && program->GetCompiled();
    vtkNew<vtkOpenGLVertexArrayObject> vao;
    const float depths[] = {0.25f, 0.459788588f, 0.510493845f, 0.75f};
    for (float expected : depths) {
        framebuffer->Bind();
        state->vtkglViewport(0, 0, 4, 4);
        if (ok) {
            window->GetShaderCache()->ReadyShaderProgram(program);
            program->SetUniformf("expectedDepth", expected);
            vao->Bind();
            glDrawArrays(GL_TRIANGLES, 0, 3);
            vao->Release();
            ok = glGetError() == GL_NO_ERROR;
        }
        window->GetRenderFramebuffer()->Bind(GL_DRAW_FRAMEBUFFER);
        window->TextureDepthBlit(framebuffer->GetDepthAttachmentAsTextureObject());
        float actual[16] = {};
        ok = ok && window->GetZbufferData(0, 0, 3, 3, actual) == VTK_OK;
        for (float value : actual) {
            ok = ok && std::isfinite(value) && std::fabs(value - expected) < 1.e-5f;
        }
    }
    state->PopFramebufferBindings();
    check(ok, "geometry shader writes precise fragment depth", "64 matching samples",
          ok ? "64 matching samples" : "mismatch");
}

int main(int argc, char* argv[])
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    const bool expect_fail =
        (argc > 1 && std::strcmp(argv[1], "--expect-fail") == 0);

    std::printf("[STEP] 1: create vtkEGLRenderWindow (EGL + OpenGL ES) offscreen\n");
    vtkNew<vtkCallbackCommand> eglError;
    eglError->SetCallback([](vtkObject*, unsigned long, void*, void* message) {
        std::fprintf(stderr, "[FAIL] EGL render window: %s\n",
                     message ? static_cast<const char*>(message) : "initialization error");
        // VTK 9.3 may continue OpenGL initialization after an EGL error.
        // Exit this test immediately; code 2 is distinct from the negative assertion.
        std::exit(2);
    });
    vtkNew<TestRenderWindow> renWin;
    renWin->AddObserver(vtkCommand::ErrorEvent, eglError);
    renWin->OffScreenRenderingOn();
    // These flags control VTK's FBO. EGLConfig selection is handled in patch 0004.
    renWin->SetMultiSamples(0);
    renWin->SetAlphaBitPlanes(0);
    renWin->SetStencilCapable(0);
    renWin->SetSize(64, 64);

    std::printf("[STEP] 2: build sphere rendering pipeline\n");
    vtkNew<vtkRenderer> renderer;
    renderer->SetBackground(0.0, 0.0, 0.0);
    renWin->AddRenderer(renderer);

    vtkNew<vtkSphereSource> sphere;
    sphere->SetThetaResolution(32);
    sphere->SetPhiResolution(32);

    vtkNew<vtkPolyDataMapper> mapper;
    mapper->SetInputConnection(sphere->GetOutputPort());

    vtkNew<vtkActor> actor;
    actor->SetMapper(mapper);
    renderer->AddActor(actor);
    renderer->ResetCamera();
    std::printf("       renderer=%s mapper=%s actor=%s\n",
                renderer->GetClassName(), mapper->GetClassName(), actor->GetClassName());

    std::printf("[STEP] 3: execute a real GPU draw via Render()\n");
    renWin->Render();
    check(renWin->GetNeverRendered() == 0, "render window has been rendered",
          "rendered", renWin->GetNeverRendered() ? "never-rendered" : "rendered");

    std::printf("[STEP] 4: read framebuffer back and verify non-background pixels\n");
    vtkNew<vtkWindowToImageFilter> w2i;
    w2i->SetInput(renWin);
    w2i->SetInputBufferTypeToRGB();
    w2i->ReadFrontBufferOff();
    w2i->ShouldRerenderOff();
    w2i->Update();
    vtkImageData* img = w2i->GetOutput();
    check(img != nullptr, "readback image produced", "non-null",
          img ? "non-null" : "null");
    if (!img) {
        return 1;
    }

    int dims[3];
    img->GetDimensions(dims);
    char bufDims[64];
    std::snprintf(bufDims, sizeof(bufDims), "%dx%dx%d", dims[0], dims[1], dims[2]);
    check(dims[0] == 64 && dims[1] == 64, "readback dimensions 64x64", "64x64",
          bufDims);

    vtkUnsignedCharArray* scalars =
        vtkUnsignedCharArray::SafeDownCast(img->GetPointData()->GetScalars());
    check(scalars != nullptr, "readback pixel buffer present", "non-null",
          scalars ? "non-null" : "null");
    if (!scalars) {
        return 1;
    }

    // The sphere is drawn white on a black background (default actor
    // color).  Count pixels that are not background.
    long long lit = 0;
    const int nc = scalars->GetNumberOfComponents();
    const vtkIdType n = scalars->GetNumberOfTuples();
    for (vtkIdType i = 0; i < n; ++i) {
        double v = 0.0;
        for (int c = 0; c < nc; ++c) {
            v += scalars->GetComponent(i, c);
        }
        if (v > 0.5 * nc) {
            ++lit;
        }
    }
    char bufLit[32];
    std::snprintf(bufLit, sizeof(bufLit), "%lld", lit);
    std::printf("       non-background pixels: %s / %d\n", bufLit, dims[0] * dims[1]);

    if (expect_fail) {
        check(lit == 0, "deliberate inverted assertion (lit == 0)",
              "0 (intentionally wrong)", bufLit);
        std::printf("expect-fail mode: %s\n",
                    failures > 0 ? "assertion failed as intended" :
                                   "ERROR: inverted assertion unexpectedly passed");
        return failures > 0 ? 1 : 0;
    }

    check(lit > 100, "sphere pixels rendered (non-background > 100)", "> 100",
          bufLit);
    checkTextureReadback(vtkOpenGLRenderWindow::SafeDownCast(renWin));
    checkNormalizedTexture(vtkOpenGLRenderWindow::SafeDownCast(renWin));
    checkTextureResize<short>(vtkOpenGLRenderWindow::SafeDownCast(renWin), VTK_SHORT, 1);
    checkTextureResize<unsigned short>(vtkOpenGLRenderWindow::SafeDownCast(renWin), VTK_UNSIGNED_SHORT, 1);
    checkTextureResize<short>(vtkOpenGLRenderWindow::SafeDownCast(renWin), VTK_SHORT, 2);
    checkTextureResize<unsigned short>(vtkOpenGLRenderWindow::SafeDownCast(renWin), VTK_UNSIGNED_SHORT, 2);
    checkDepthCopy(vtkOpenGLRenderWindow::SafeDownCast(renWin));
    checkGeometryDepth(vtkOpenGLRenderWindow::SafeDownCast(renWin));

    if (failures == 0) {
        std::printf("test vtk 9.3.0 render: OK (EGL/GLES offscreen pipeline verified)\n");
        return 0;
    }
    std::fprintf(stderr, "test vtk 9.3.0 render: FAILED (%d assertion(s))\n",
                 failures);
    return 1;
}
