// Consumer test for collada-dom 2.5.0 — exercises the DOM API in memory.
// Builds a minimal COLLADA 1.5 document via DAE::load() and verifies the
// parsed root, proving header + lib linkage works.
#include <cstdio>

#include <dae.h>

static const char* kMinimalCollada =
    "<?xml version=\"1.0\"?>\n"
    "<COLLADA xmlns=\"http://www.collada.org/2008/03/COLLADASchema\" "
    "version=\"1.5.0\">\n"
    "  <asset>\n"
    "    <contributor><author>conan-test</author></contributor>\n"
    "    <created>2026-08-28T00:00:00Z</created>\n"
    "    <modified>2026-08-28T00:00:00Z</modified>\n"
    "    <unit name=\"meter\" meter=\"1\"/>\n"
    "    <up_axis>Y_UP</up_axis>\n"
    "  </asset>\n"
    "  <library_geometries id=\"geoLib\">\n"
    "    <geometry id=\"box\" name=\"box\">\n"
    "      <mesh/>\n"
    "    </geometry>\n"
    "  </library_geometries>\n"
    "</COLLADA>\n";

int main() {
    DAE dae;

    // load() accepts an in-memory document through the "mem://" scheme; the
    // XML buffer is parsed directly without touching the filesystem.
    daeInt rc = dae.load("mem://conan-test/test-1.5.dae", kMinimalCollada);
    if (rc != DAE_OK) {
        std::fprintf(stderr, "FAIL: DAE::load returned %d (expected DAE_OK=%d)\n",
                     rc, DAE_OK);
        return 1;
    }

    // getRoot() returns the generic root proxy (daeElement) for the document.
    daeElement* root = dae.getRoot("mem://conan-test/test-1.5.dae");
    if (!root) {
        std::fprintf(stderr, "FAIL: root document is null after load\n");
        return 1;
    }

    // Verify the in-memory document exists in the database and is queryable.
    daeDatabase* db = dae.getDatabase();
    if (!db) {
        std::fprintf(stderr, "FAIL: database handle is null\n");
        return 1;
    }
    daeUInt elementCount = db->getElementCount();
    if (elementCount == 0) {
        std::fprintf(stderr, "FAIL: parsed document contains no elements\n");
        return 1;
    }

    std::printf("PASS: collada-dom 2.5.0 parsed COLLADA 1.5 doc (elements=%u)\n",
                static_cast<unsigned>(elementCount));
    return 0;
}
