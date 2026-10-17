#include "rapidobj/rapidobj.hpp"

#include <iostream>
#include <sstream>
#include <string>

// Test data: upstream tests/data/cube/cube.obj (8 vertices, 12 triangles)
static const char* kCubeObj = R"(# cube.obj
g cube

v  0.0  0.0  0.0
v  0.0  0.0  1.0
v  0.0  1.0  0.0
v  0.0  1.0  1.0
v  1.0  0.0  0.0
v  1.0  0.0  1.0
v  1.0  1.0  0.0
v  1.0  1.0  1.0

f  1 7 5
f  1 3 7
f  1 4 3
f  1 2 4
f  3 8 7
f  3 4 8
f  5 7 8
f  5 8 6
f  1 5 6
f  1 6 2
f  2 6 8
f  2 8 4
)";

int main()
{
    // ParseStream with a real OBJ payload via rapidobj API
    std::istringstream stream(kCubeObj);
    rapidobj::Result result = rapidobj::ParseStream(stream);

    if (result.error) {
        std::cout << "ParseStream failed: " << result.error.code.message() << '\n';
        return 1;
    }

    // positions is a flat std::vector<float> (3 components per vertex)
    if (result.attributes.positions.size() != 24) {
        std::cout << "expected 24 position components (8 vertices x 3), got "
                  << result.attributes.positions.size() << '\n';
        return 1;
    }

    if (result.shapes.size() != 1 || result.shapes[0].mesh.indices.size() != 36) {
        std::cout << "expected 1 shape with 36 indices (12 triangles), got " << result.shapes.size()
                  << " shapes / " << (result.shapes.empty() ? 0 : result.shapes[0].mesh.indices.size())
                  << " indices\n";
        return 1;
    }

    // Triangulate is a no-op on already-triangulated data; verify it stays consistent
    bool ok = rapidobj::Triangulate(result);
    if (!ok || result.shapes[0].mesh.indices.size() != 36) {
        std::cout << "Triangulate failed or changed index count\n";
        return 1;
    }

    std::cout << "rapidobj 1.1 consumer test OK: 8 vertices, 36 indices parsed and triangulated\n";
    return 0;
}
