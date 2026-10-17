#include <cmath>
#include <cstdio>
#include <fstream>

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
    const char* path = "cubelib_write_contract.cube";
    const char* path2 = "cubelib_write_contract2.cube";
    try {
        {
            cube::Cube cube;
            cube::Metric* met = cube.def_met("Time", "time", "FLOAT", "sec", "",
                "https://example.invalid/metric", "root metric", nullptr);
            std::string mod = "test_cube_write.cpp";
            cube::Region* regn = cube.def_region("foo", "foo", "mpi", "barrier", 1, 10, "", "test region", mod);
            cube::Cnode* cnode = cube.def_cnode(regn, mod, 1, nullptr);
            cube::Machine* mach = cube.def_mach("M", "");
            cube::Node* node = cube.def_node("N", mach);
            cube::Process* proc = cube.def_proc("P0", 0, node);
            cube::Thread* thrd = cube.def_thrd("T0", 0, proc);
            cube.initialize();
            cube.set_sev(met, cnode, thrd, 7.25);
            std::ofstream out(path);
            CHECK(out.good(), "open cube file for writing");
            out << cube;
            out.close();
            CHECK(out.good(), "cube written to file");
        }
        {
            std::ifstream in(path);
            CHECK(in.good(), "open cube file for reading");
            cube::Cube cube2;
            in >> cube2;
            CHECK(cube2.get_metv().size() == 1, "reread metric count");
            CHECK(cube2.get_cnodev().size() == 1, "reread cnode count");
            const cube::Metric* met = cube2.get_metv().front();
            const cube::Cnode* cnode = cube2.get_cnodev().front();
            const cube::Thread* thrd = cube2.get_thrdv().front();
            double v = cube2.get_sev(const_cast<cube::Metric*>(met), cnode, thrd);
            CHECK(std::fabs(v - 7.25) < 1e-9, "reread severity matches");
            std::ofstream out2(path2);
            out2 << cube2;
            out2.close();
            CHECK(out2.good(), "second write succeeds");
        }
        if (failures == 0) {
            std::printf("CUBELIB_WRITE_CONTRACT PASS\n");
            return 0;
        }
        std::printf("CUBELIB_WRITE_CONTRACT FAIL (%d)\n", failures);
        return 1;
    } catch (const std::exception& ex) {
        std::printf("FAIL: exception %s\n", ex.what());
        return 1;
    }
}
