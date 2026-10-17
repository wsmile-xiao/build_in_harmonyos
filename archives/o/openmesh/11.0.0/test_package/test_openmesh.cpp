#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <vector>

#include <OpenMesh/Core/IO/MeshIO.hh>
#include <OpenMesh/Core/Mesh/TriMesh_ArrayKernelT.hh>

using Mesh = OpenMesh::TriMesh_ArrayKernelT<>;

int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "--fault-missing-file") == 0) {
        Mesh missing;
        const bool accepted = OpenMesh::IO::read_mesh(
            missing, "ohpcd-intentionally-missing-mesh.off");
        if (accepted) {
            std::cerr << "fault injection failed: missing mesh accepted\n";
            return 20;
        }
        std::cout << "fault injection passed: missing mesh rejected\n";
        return 0;
    }

    Mesh mesh;
    mesh.request_face_normals();
    std::vector<Mesh::VertexHandle> vertices;
    vertices.push_back(mesh.add_vertex(Mesh::Point(0.0f, 0.0f, 0.0f)));
    vertices.push_back(mesh.add_vertex(Mesh::Point(1.0f, 0.0f, 0.0f)));
    vertices.push_back(mesh.add_vertex(Mesh::Point(0.0f, 1.0f, 0.0f)));

    const Mesh::FaceHandle face = mesh.add_face(vertices);
    if (!face.is_valid()) {
        std::cerr << "triangle face creation failed\n";
        return 1;
    }
    if (mesh.n_vertices() != 3 || mesh.n_edges() != 3 ||
        mesh.n_faces() != 1) {
        std::cerr << "unexpected topology counts\n";
        return 2;
    }

    mesh.update_face_normals();
    const Mesh::Normal normal = mesh.normal(face);
    if (std::fabs(normal[0]) > 1.0e-6f ||
        std::fabs(normal[1]) > 1.0e-6f ||
        std::fabs(normal[2] - 1.0f) > 1.0e-6f) {
        std::cerr << "unexpected face normal\n";
        return 3;
    }

    const char* filename = "ohpcd-openmesh-roundtrip.off";
    if (!OpenMesh::IO::write_mesh(mesh, filename)) {
        std::cerr << "OFF write failed\n";
        return 4;
    }
    Mesh loaded;
    if (!OpenMesh::IO::read_mesh(loaded, filename)) {
        std::remove(filename);
        std::cerr << "OFF read failed\n";
        return 5;
    }
    std::remove(filename);
    if (loaded.n_vertices() != 3 || loaded.n_edges() != 3 ||
        loaded.n_faces() != 1) {
        std::cerr << "round-trip topology mismatch\n";
        return 6;
    }

    std::cout << "OpenMesh consumer checks passed\n";
    return 0;
}
