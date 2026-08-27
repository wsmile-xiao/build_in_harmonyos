#include <QCoreApplication>
#include <Qt3DCore/QAspectEngine>
#include <Qt3DCore/QEntity>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // Real Qt3D API call: create an aspect engine and a root entity
    Qt3DCore::QAspectEngine engine;
    auto rootEntity = Qt3DCore::QEntityPtr::create();
    if (!rootEntity) {
        std::printf("Qt3D test FAILED: could not create root entity\n");
        return 1;
    }
    engine.setRootEntity(rootEntity);
    std::printf("Qt3D test PASSED\n");
    return 0;
}
