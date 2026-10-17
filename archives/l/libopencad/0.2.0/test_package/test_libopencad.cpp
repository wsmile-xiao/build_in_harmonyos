// Consumer test for libopencad 0.2.0 — really exercises the public C API
// by opening a DWG sample file and verifying layers/geometry parsing.
//
// Mirrors upstream test "reading_geometries.1arc" (tests/data/r2000/1arc.dwg):
//   - OpenCADFile succeeds
//   - exactly 1 layer
//   - exactly 1 ARC geometry
//
// Exit code 0 on success, non-zero on failure.

#include <cstdio>
#include <cstdlib>

#include "opencad/opencad_api.h"
#include "opencad/cadgeometry.h"

int main()
{
    // 1. Version API sanity check. GetVersion() returns
    //    major*10000 + minor*100 + rev, i.e. 200 for 0.2.0.
    if (GetVersion() != 200)
    {
        std::fprintf(stderr, "unexpected version: %d\n", GetVersion());
        return 1;
    }
    std::printf("libopencad version: %s (format support: %s)\n",
                GetVersionString(), GetCADFormats());

    // 2. Open a real DWG (R2000) sample shipped in the package res/ dir
    //    (taken from the upstream source tarball; run from that directory).
    CADFile *pFile = OpenCADFile("./r2000/1arc.dwg",
                                 CADFile::OpenOptions::READ_FAST);
    if (pFile == nullptr)
    {
        std::fprintf(stderr, "OpenCADFile failed, error=%d\n", GetLastErrorCode());
        return 1;
    }

    // 3. Verify layer table.
    if (pFile->GetLayersCount() != 1)
    {
        std::fprintf(stderr, "expected 1 layer, got %zu\n",
                     pFile->GetLayersCount());
        delete pFile;
        return 1;
    }

    // 4. Verify geometry: exactly one ARC.
    CADLayer &layer = pFile->GetLayer(0);
    size_t arcs = 0;
    for (size_t i = 0; i < layer.getGeometryCount(); ++i)
    {
        CADGeometry *pGeom = layer.getGeometry(i);
        if (pGeom != nullptr && pGeom->getType() == CADGeometry::ARC)
        {
            ++arcs;
        }
        delete pGeom;
    }

    std::printf("layers=%zu geometry=%zu arcs=%zu\n",
                pFile->GetLayersCount(), layer.getGeometryCount(), arcs);

    delete pFile;

    if (arcs != 1)
    {
        std::fprintf(stderr, "expected 1 ARC geometry, got %zu\n", arcs);
        return 1;
    }

    std::printf("test_libopencad PASS\n");
    return 0;
}
