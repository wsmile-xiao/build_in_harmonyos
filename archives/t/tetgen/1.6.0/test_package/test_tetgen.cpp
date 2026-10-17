#include <tetgen.h>

#include <cstdio>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main() {
    int failures = 0;

    // Four points forming a unit tetrahedron (origin + three unit axes).
    tetgenio in;
    in.firstnumber = 0;
    in.numberofpoints = 4;
    in.pointlist = new REAL[12];
    in.pointlist[0] = 0.0; in.pointlist[1]  = 0.0; in.pointlist[2]  = 0.0;
    in.pointlist[3] = 1.0; in.pointlist[4]  = 0.0; in.pointlist[5]  = 0.0;
    in.pointlist[6] = 0.0; in.pointlist[7]  = 1.0; in.pointlist[8]  = 0.0;
    in.pointlist[9] = 0.0; in.pointlist[10] = 0.0; in.pointlist[11] = 1.0;

    // Drive TetGen through its public library interface (tetgenbehavior overload).
    // parse_commandline takes a non-const char* (upstream API), so pass a mutable
    // buffer to avoid a -Wwritable-strings warning.
    char switches[] = "Q";
    tetgenbehavior behavior;
    behavior.parse_commandline(switches);

    tetgenio out;
    tetrahedralize(&behavior, &in, &out);

    CHECK(out.numberofpoints >= 4,
          "tetrahedralization keeps at least the 4 input points");
    CHECK(out.numberoftetrahedra >= 1,
          "tetrahedralization produces at least one tetrahedron");
    CHECK(out.pointlist != nullptr,
          "tetrahedralization allocates the output point list");

    if (failures != 0) {
        std::fprintf(stderr, "TetGen consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    std::printf("TetGen consumer test passed: %d points, %d tetrahedra\n",
                out.numberofpoints, out.numberoftetrahedra);
    return 0;
}
