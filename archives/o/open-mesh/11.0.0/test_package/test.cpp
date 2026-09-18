#include <OpenMesh/Core/IO/MeshIO.hh>
#include <OpenMesh/Core/Mesh/TriMesh_ArrayKernelT.hh>
#include <iostream>
int main() {
    OpenMesh::TriMesh_ArrayKernelT<> mesh;
    std::cout << "openmesh vertices=" << mesh.n_vertices() << std::endl;
    return 0;
}
