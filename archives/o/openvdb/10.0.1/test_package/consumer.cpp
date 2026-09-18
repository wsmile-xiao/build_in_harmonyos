// 最小 consumer：验证 openvdb 头文件可用 + libopenvdb 可链接
#include <openvdb/openvdb.h>
#include <iostream>

int main() {
    openvdb::initialize();
    openvdb::FloatGrid::Ptr grid = openvdb::FloatGrid::create(1.0f);
    grid->setName("test");
    std::cout << "openvdb consumer ok: " << grid->getName()
              << " activeVoxels=" << grid->activeVoxelCount() << std::endl;
    return 0;
}
