// Compare identical scenes at different viewport origins without image baselines.
#include "vtkActor.h"
#include "vtkCamera.h"
#include "vtkDepthPeelingPass.h"
#include "vtkGeoProjection.h"
#include "vtkNew.h"
#include "vtkOpenGLFluidMapper.h"
#include "vtkOpenGLFramebufferObject.h"
#include "vtkOpenGLRenderer.h"
#include "vtkOpenGLRenderWindow.h"
#include "vtkOpenGLShaderCache.h"
#include "vtkOpenGLState.h"
#include "vtkPoints.h"
#include "vtkPolyData.h"
#include "vtkPolyDataMapper.h"
#include "vtkProperty.h"
#include "vtkRenderStepsPass.h"
#include "vtkResourceFileLocator.h"
#include "vtkShaderProgram.h"
#include "vtkSphereSource.h"
#include "vtkUnsignedCharArray.h"
#include "vtkVersion.h"
#include "vtkVolume.h"
#include "vtk_glew.h"

#ifdef VTK_TEST_EGL
#include "vtkEGLRenderWindow.h"
using TestWindow = vtkEGLRenderWindow;
#else
#include "vtkRenderWindow.h"
using TestWindow = vtkRenderWindow;
#endif

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include <vtksys/SystemTools.hxx>

static int checkRuntimeResources()
{
    const std::string library = vtkGetLibraryPathForSymbol(GetVTKVersion);
    vtkNew<vtkResourceFileLocator> locator;
    const std::string landmark = "share/vtk-9.3/proj/proj.db";
    const std::string prefix = locator->Locate(
        vtksys::SystemTools::GetFilenamePath(library), landmark);
    char header[16] = {};
    std::ifstream database(prefix + "/" + landmark, std::ios::binary);
    database.read(header, sizeof(header));
    const bool located = !library.empty() && !prefix.empty() &&
        database.gcount() == sizeof(header) && std::memcmp(header, "SQLite format 3\0", 16) == 0;
    std::printf("[%s] runtime resource locator reads the PROJ database\n", located ? "PASS" : "FAIL");

    vtkNew<vtkGeoProjection> projection;
    projection->SetPROJ4String("EPSG:3978");
    const bool initialized = projection->GetProjection() != nullptr;
    std::printf("[%s] EPSG:3978 projection initializes from runtime data\n", initialized ? "PASS" : "FAIL");
    return int(!located) + int(!initialized);
}

static int checkViewport(bool fluid)
{
    constexpr int size = 128;
    std::vector<unsigned char> images[2];
    for (int side = 0; side < 2; ++side) {
    vtkNew<TestWindow> window;
    window->SetOffScreenRendering(1);
    window->SetMultiSamples(0);
    window->SetAlphaBitPlanes(1);
    window->SetSize(2 * size, size);
    vtkNew<vtkOpenGLRenderer> renderer;
    renderer->SetBackground(0.1, 0.2, 0.3);
    window->AddRenderer(renderer);
    renderer->SetViewport(side * 0.5, 0, (side + 1) * 0.5, 1);

    vtkNew<vtkSphereSource> sphere;
    sphere->SetRadius(0.5);
    sphere->SetThetaResolution(24);
    sphere->SetPhiResolution(24);
    vtkNew<vtkPolyDataMapper> mapper;
    mapper->SetInputConnection(sphere->GetOutputPort());
    vtkNew<vtkActor> opaque;
    opaque->SetMapper(mapper);
    opaque->SetPosition(-0.25, 0, 0.1);
    opaque->GetProperty()->SetColor(1.0, 0.3, 0.1);
    renderer->AddActor(opaque);

    vtkNew<vtkActor> translucent;
    vtkNew<vtkDepthPeelingPass> peeling;
    vtkNew<vtkRenderStepsPass> steps;
    vtkNew<vtkPoints> points;
    vtkNew<vtkPolyData> particles;
    vtkNew<vtkOpenGLFluidMapper> fluidMapper;
    vtkNew<vtkVolume> volume;
    if (fluid) {
        for (int z = 0; z < 5; ++z) {
            for (int y = 0; y < 7; ++y) {
                for (int x = 0; x < 7; ++x) {
                    points->InsertNextPoint(x * 0.12 - 0.2, y * 0.12 - 0.36, z * 0.12 - 0.24);
                }
            }
        }
        particles->SetPoints(points);
        fluidMapper->SetInputData(particles);
        fluidMapper->SetParticleRadius(0.11);
        fluidMapper->SetSurfaceFilterIterations(2);
        fluidMapper->SetSurfaceFilterRadius(3);
        fluidMapper->SetDisplayMode(vtkOpenGLFluidMapper::FluidDisplayMode::TransparentFluidVolume);
        fluidMapper->SetAttenuationColor(0.8f, 0.2f, 0.15f);
        fluidMapper->SetRefractionScale(0.07f);
        volume->SetMapper(fluidMapper);
        renderer->AddVolume(volume);
    } else {
        translucent->SetMapper(mapper);
        translucent->SetPosition(0.3, 0, 0);
        translucent->GetProperty()->SetColor(0.1, 0.7, 1.0);
        translucent->GetProperty()->SetOpacity(0.35);
        renderer->AddActor(translucent);
        peeling->SetMaximumNumberOfPeels(8);
        peeling->SetOcclusionRatio(0.0);
        peeling->SetTranslucentPass(steps->GetTranslucentPass());
        steps->SetTranslucentPass(peeling);
        renderer->SetPass(steps);
    }
    renderer->GetActiveCamera()->SetPosition(0, 0, 4);
    renderer->GetActiveCamera()->SetFocalPoint(0, 0, 0);
    renderer->ResetCamera();
    renderer->ResetCameraClippingRange();

        // Each viewport uses fresh textures so stale depth cannot match the reference.
        window->Render();
        vtkNew<vtkUnsignedCharArray> rgba;
        if (window->GetRGBACharPixelData(side * size, 0, (side + 1) * size - 1,
                                         size - 1, 0, rgba) != VTK_OK) {
            std::fprintf(stderr, "[FAIL] viewport pixel readback\n");
            return 1;
        }
        images[side].assign(rgba->GetPointer(0), rgba->GetPointer(0) + rgba->GetNumberOfValues());
    }
    size_t changed = 0;
    unsigned long long difference = 0;
    int maximum = 0;
    for (size_t i = 0; i < images[0].size(); i += 4) {
        if (images[0][i] != images[0][0] || images[0][i + 1] != images[0][1] ||
            images[0][i + 2] != images[0][2]) {
            ++changed;
        }
        for (int channel = 0; channel < 3; ++channel) {
            int delta = std::abs(int(images[0][i + channel]) - int(images[1][i + channel]));
            difference += delta;
            maximum = std::max(maximum, delta);
        }
    }
    const double average = double(difference) / (size * size * 3);
    const bool ok = changed > 100 && maximum <= 2 && average <= 0.05;
    std::printf("[%s] %s shifted viewport: scene_pixels=%zu max_delta=%d mean_delta=%.8f\n",
                ok ? "PASS" : "FAIL", fluid ? "fluid" : "legacy depth peeling", changed,
                maximum, average);
    return ok ? 0 : 1;
}

static int checkSamplerTypes()
{
    vtkNew<TestWindow> window;
    window->SetOffScreenRendering(1);
    window->SetMultiSamples(0);
    window->SetSize(16, 16);
    vtkNew<vtkOpenGLRenderer> renderer;
    window->AddRenderer(renderer);
    window->Render();
    const char* vertex = "//VTK::System::Dec\nvoid main(){gl_Position=vec4(0.0,0.0,0.0,1.0);}";
    bool ok = true;
    for (const char* type : {"samplerBuffer", "isamplerBuffer", "usamplerBuffer"}) {
        for (const char* precision : {"", "highp "}) {
            std::string fragment = "//VTK::System::Dec\nuniform ";
            fragment += precision;
            fragment += type;
            fragment += " values;\nout vec4 color;\nvoid main(){color=vec4(texelFetchBuffer(values,0));}";
            auto program = vtkOpenGLRenderWindow::SafeDownCast(window)->GetShaderCache()->
                ReadyShaderProgram(vertex, fragment.c_str(), "");
            ok = ok && program && program->GetCompiled();
        }
    }
    std::printf("[%s] floating/signed/unsigned buffer samplers with optional precision\n",
                ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

static int checkBlitState()
{
    vtkNew<TestWindow> window;
    window->SetOffScreenRendering(1);
    window->SetMultiSamples(4);
    window->SetStencilCapable(1);
    window->SetSize(16, 16);
    vtkNew<vtkOpenGLRenderer> renderer;
    window->AddRenderer(renderer);
    window->Render();
    auto glWindow = vtkOpenGLRenderWindow::SafeDownCast(window);
    auto state = glWindow->GetState();
    state->Push();
    vtkNew<vtkOpenGLFramebufferObject> source;
    source->SetContext(glWindow);
    bool ok = source->PopulateFramebuffer(16, 16, true, 1, VTK_UNSIGNED_CHAR, true, 32, 0);
    source->Bind();
    state->vtkglViewport(0, 0, 16, 16);
    state->vtkglDisable(GL_SCISSOR_TEST);
    state->vtkglDisable(GL_STENCIL_TEST);
    state->vtkglColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    state->vtkglDepthMask(GL_TRUE);
    state->vtkglClearColor(0.25, 0.5, 0.75, 1.0);
    state->vtkglClearDepth(0.4);
    state->vtkglClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    state->vtkglColorMask(GL_TRUE, GL_FALSE, GL_FALSE, GL_FALSE);
    state->vtkglEnable(GL_STENCIL_TEST);
    state->vtkglStencilFunc(GL_NEVER, 1, 0xff);
    glWindow->BlitToRenderFramebuffer(true);
    GLboolean mask[4] = {};
    glGetBooleanv(GL_COLOR_WRITEMASK, mask);
    const bool restored = mask[0] && !mask[1] && !mask[2] && !mask[3] && glIsEnabled(GL_STENCIL_TEST);
    state->vtkglDisable(GL_STENCIL_TEST);
    state->vtkglColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    vtkNew<vtkUnsignedCharArray> pixels;
    ok = ok && window->GetRGBACharPixelData(0, 0, 15, 15, 0, pixels) == VTK_OK;
    for (vtkIdType i = 0; i < pixels->GetNumberOfValues() && ok; i += 4) {
        const unsigned char* value = pixels->GetPointer(i);
        ok = std::abs(int(value[0]) - 64) <= 1 && std::abs(int(value[1]) - 128) <= 1 &&
             std::abs(int(value[2]) - 191) <= 1;
    }
    float depth[256] = {};
    ok = ok && glWindow->GetZbufferData(0, 0, 15, 15, depth) == VTK_OK;
    for (float value : depth) {
        ok = ok && std::abs(value - 0.4f) < 1.e-5f;
    }
    state->Pop();
    ok = ok && restored;
    std::printf("[%s] MSAA blit ignores and restores stencil/color-mask state\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

int main()
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    int failures = checkRuntimeResources();
    failures += checkViewport(false);
    failures += checkViewport(true);
    failures += checkSamplerTypes();
    failures += checkBlitState();
    return failures ? 1 : 0;
}
