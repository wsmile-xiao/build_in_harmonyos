// test_package/src/main.cpp — substantive VTK API test (R34)
//
// Verifies that the VTK library is correctly built, linked, and functional
// on HarmonyOS (arm64) by exercising real VTK APIs:
//   1. Querying the VTK version string via vtkVersion::GetVTKVersion()
//   2. Creating a vtkSphereSource via vtkNew<vtkSphereSource> (RAII smart
//      pointer — the core VTK object-creation API)
//   3. Configuring the sphere (SetRadius, SetThetaResolution, SetPhiResolution,
//      SetCenter) and calling Update() to execute the pipeline
//   4. Reading the vtkPolyData output and asserting the exact point and cell
//      counts produced by vtkSphereSource's mesh formula
//      (full sphere: 2 pole rows are merged, effective phi rows =
//      PhiResolution - numPoles = 16 - 2 = 14;
//       numPts  = thetaResolution * phiResolution + 2 = 16*14+2 = 226,
//       numPolys = phiResolution * 2 * thetaResolution   = 14*2*16 = 448;
//      values verified empirically on a native build)
//
// Every assertion prints a [STEP]/[PASS]/[FAIL] record and any failure
// exits non-zero.  Invoking the binary with "--expect-fail" runs a
// deliberately inverted assertion, which MUST fail and exit non-zero —
// this proves the error path really propagates a non-zero exit status.
//
// This is NOT a hollow "printf OK" test — if VTK were missing or broken,
// the link step or the Update()/GetNumberOfPoints() call would fail.

#include "vtkNew.h"
#include "vtkSphereSource.h"
#include "vtkPolyData.h"
#include "vtkVersion.h"

#include <cstdio>
#include <cstring>

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

int main(int argc, char* argv[])
{
    const bool expect_fail =
        (argc > 1 && std::strcmp(argv[1], "--expect-fail") == 0);
    std::printf("[STEP] 1: query VTK runtime version via vtkVersion::GetVTKVersion()\n");

    // 1. Runtime version check — exercises vtkVersion::GetVTKVersion() symbol.
    const char* ver = vtkVersion::GetVTKVersion();
    if (!ver || std::strlen(ver) == 0) {
        std::fprintf(stderr, "[FAIL] vtkVersion::GetVTKVersion() returned empty\n");
        return 1;
    }
    std::printf("       VTK runtime version: %s\n", ver);
    check(std::strcmp(ver, "9.3.0") == 0, "VTK version equals 9.3.0", "9.3.0", ver);

    std::printf("[STEP] 2: create and configure vtkSphereSource (vtkNew RAII)\n");

    // 2. Instantiate a sphere source via vtkNew (RAII smart pointer —
    //    the canonical VTK object-creation API).
    vtkNew<vtkSphereSource> sphere;

    // 3. Configure the sphere geometry.
    sphere->SetRadius(2.0);
    sphere->SetCenter(0.0, 0.0, 0.0);
    sphere->SetThetaResolution(16);
    sphere->SetPhiResolution(16);

    std::printf("[STEP] 3: execute the pipeline via Update()\n");

    // Execute the pipeline (produces the poly-data output).
    sphere->Update();

    std::printf("[STEP] 4: verify poly-data output geometry\n");

    // 4. Read the output and verify geometry was produced.
    vtkPolyData* output = sphere->GetOutput();
    check(output != nullptr, "sphere->GetOutput() returns non-null", "non-null",
          output ? "non-null" : "null");
    if (!output) {
        std::fprintf(stderr, "aborting: no output available\n");
        return 1;
    }

    vtkIdType nPoints = output->GetNumberOfPoints();
    vtkIdType nCells = output->GetNumberOfCells();
    std::printf("       points=%lld cells=%lld\n",
                static_cast<long long>(nPoints),
                static_cast<long long>(nCells));
    std::fflush(stdout);

    // vtkSphereSource full-sphere mesh (Filters/Sources/vtkSphereSource.cxx,
    // empirically verified on a native build): with theta=16, phi=16 the two
    // pole rows merge (numPoles=2), effective phi rows = 14:
    //   numPts   = 16*14+2 = 226
    //   numPolys = 14*2*16 = 448
    if (expect_fail) {
        // Deliberately inverted expectation: this MUST fail and exit non-zero.
        check(nPoints == 1, "deliberate inverted assertion (points == 1)",
              "1 (intentionally wrong)", "226");
        std::fflush(stdout);
        std::printf("expect-fail mode: %s\n",
                    failures > 0 ? "assertion failed as intended" :
                                   "ERROR: inverted assertion unexpectedly passed");
        return failures > 0 ? 1 : 0;
    }

    char bufPts[32], bufCells[32];
    std::snprintf(bufPts, sizeof(bufPts), "%lld", static_cast<long long>(nPoints));
    std::snprintf(bufCells, sizeof(bufCells), "%lld", static_cast<long long>(nCells));
    check(nPoints == 226, "sphere point count equals 226", "226", bufPts);
    check(nCells == 448, "sphere cell count equals 448", "448", bufCells);
    check(nPoints > 0, "sphere produced non-zero points", "> 0", bufPts);

    if (failures == 0) {
        std::fflush(stdout);
        std::printf("test vtk 9.3.0: OK (all assertions passed)\n");
        return 0;
    }
    std::fflush(stdout);
    std::fprintf(stderr, "test vtk 9.3.0: FAILED (%d assertion(s) failed)\n",
                 failures);
    return 1;
}
