#include <cmath>
#include <cstdio>

#include "Cube.h"
#include "CubeCnode.h"
#include "CubeMetric.h"
#include "CubeRegion.h"
#include "CubeMachine.h"
#include "CubeNode.h"
#include "CubeProcess.h"
#include "CubeThread.h"

static int failures = 0;

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            std::printf("FAIL: %s\n", msg); \
            ++failures; \
        } else { \
            std::printf("ok: %s\n", msg); \
        } \
    } while (0)

int main() {
    try {
        cube::Cube cube;
        cube.def_mirror("https://scalasca.org/software/cube-4.x/download.html");
        cube.def_attr("test", "cubelib-api-contract");

        cube::Metric* met = cube.def_met("Time", "time", "FLOAT", "sec", "",
            "https://example.invalid/metric", "root metric", nullptr);
        CHECK(met != nullptr, "def_met returns metric");

        std::string mod = "test_cube_api.cpp";
        cube::Region* regn = cube.def_region("main", "main", "mpi", "barrier", 1, 10, "", "test region", mod);
        CHECK(regn != nullptr, "def_region returns region");

        cube::Cnode* cnode = cube.def_cnode(regn, mod, 1, nullptr);
        CHECK(cnode != nullptr, "def_cnode returns cnode");

        cube::Machine* mach = cube.def_mach("TestMachine", "");
        cube::Node* node = cube.def_node("TestNode", mach);
        cube::Process* proc = cube.def_proc("Process 0", 0, node);
        cube::Thread* thrd = cube.def_thrd("Thread 0", 0, proc);
        CHECK(thrd != nullptr, "location tree built");

        cube.initialize();
        cube.set_sev(met, cnode, thrd, 12.5);
        double v = cube.get_sev(met, cnode, thrd);
        CHECK(std::fabs(v - 12.5) < 1e-9, "set/get severity roundtrip");

        cube.add_sev(met, cnode, thrd, 2.5);
        double v2 = cube.get_sev(met, cnode, thrd);
        CHECK(std::fabs(v2 - 15.0) < 1e-9, "add severity accumulates");

        double saved = cube.get_saved_sev(met, cnode, thrd);
        CHECK(std::fabs(saved - 15.0) < 1e-9, "saved severity matches");

        const std::vector<cube::Metric*>& mets = cube.get_metv();
        CHECK(mets.size() >= 1, "metric vector non-empty");
        CHECK(cube.get_cnodev().size() >= 1, "cnode vector non-empty");

        if (failures == 0) {
            std::printf("CUBELIB_API_CONTRACT PASS\n");
            return 0;
        }
        std::printf("CUBELIB_API_CONTRACT FAIL (%d)\n", failures);
        return 1;
    } catch (const std::exception& ex) {
        std::printf("FAIL: exception %s\n", ex.what());
        return 1;
    }
}
