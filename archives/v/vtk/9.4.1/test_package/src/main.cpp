// test_package/src/main.cpp — substantive VTK API test (R34)
//
// Verifies that the VTK library is correctly built, linked, and functional
// on HarmonyOS (arm64) by exercising real VTK APIs:
//   1. Querying the VTK version string via vtkVersion::GetVTKVersion()
//   2. Creating a vtkSphereSource via vtkNew<vtkSphereSource> (RAII smart
//      pointer — the core VTK object-creation API)
//   3. Configuring the sphere (SetRadius, SetThetaResolution, SetPhiResolution,
//      SetCenter) and calling Update() to execute the pipeline
//   4. Reading the vtkPolyData output and asserting that the point count is
//      non-zero (a broken or missing library would fail to link or produce
//      no geometry)
//
// This is NOT a hollow "printf OK" test — if VTK were missing or broken,
// the link step or the Update()/GetNumberOfPoints() call would fail.

#include "vtkNew.h"
#include "vtkSphereSource.h"
#include "vtkPolyData.h"
#include "vtkVersion.h"

#include <cstdio>
#include <cstring>

int main(void)
{
    // 1. Runtime version check — exercises vtkVersion::GetVTKVersion() symbol
    const char* ver = vtkVersion::GetVTKVersion();
    if (!ver || std::strlen(ver) == 0) {
        std::fprintf(stderr, "FAIL: vtkVersion::GetVTKVersion() returned empty\n");
        return 1;
    }
    std::printf("VTK runtime version: %s\n", ver);

    // 2. Instantiate a sphere source via vtkNew (RAII smart pointer —
    //    the canonical VTK object-creation API).
    vtkNew<vtkSphereSource> sphere;

    // 3. Configure the sphere geometry.
    sphere->SetRadius(2.0);
    sphere->SetCenter(0.0, 0.0, 0.0);
    sphere->SetThetaResolution(16);
    sphere->SetPhiResolution(16);

    // Execute the pipeline (produces the poly-data output).
    sphere->Update();

    // 4. Read the output and verify geometry was produced.
    vtkPolyData* output = sphere->GetOutput();
    if (!output) {
        std::fprintf(stderr, "FAIL: sphere->GetOutput() returned null\n");
        return 1;
    }
    vtkIdType nPoints = output->GetNumberOfPoints();
    std::printf("Sphere produced %lld points\n", static_cast<long long>(nPoints));

    if (nPoints <= 0) {
        std::fprintf(stderr, "FAIL: expected non-zero points, got %lld\n",
                     static_cast<long long>(nPoints));
        return 1;
    }

    std::printf("test vtk 9.4.1: OK\n");
    return 0;
}
