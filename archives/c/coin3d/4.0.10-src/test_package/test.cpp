// Coin3D consumer test (headless): exercises the public scene-graph API
// without needing a GL context -- Coin is a rendering library and contexts
// come from the application layer.
//
// 1. Build a small scene graph via public nodes (SoCube).
// 2. Query geometry through SoGetBoundingBoxAction and assert dimensions.
// 3. Write the scene to the .iv format and read it back with SoDB::readAll,
//    asserting the persisted field values survive the round trip.
#include <Inventor/SoDB.h>
#include <Inventor/SoInput.h>
#include <Inventor/SoOutput.h>
#include <Inventor/SbBox.h>
#include <Inventor/SbViewportRegion.h>
#include <Inventor/actions/SoGetBoundingBoxAction.h>
#include <Inventor/actions/SoWriteAction.h>
#include <Inventor/nodes/SoCube.h>
#include <Inventor/nodes/SoGroup.h>
#include <Inventor/nodes/SoSeparator.h>

#include <cmath>
#include <cstdio>

int main() {
    SoDB::init();

    SoCube *cube = new SoCube;
    cube->ref();
    cube->width = 2.0f;
    cube->height = 3.0f;
    cube->depth = 4.0f;

    // 1) geometry through the public action API
    SoGetBoundingBoxAction bbox(SbViewportRegion(100, 100));
    bbox.apply(cube);
    SbVec3f size = bbox.getBoundingBox().getSize();
    std::printf("bbox size: %f %f %f\n", size[0], size[1], size[2]);
    assert(std::fabs(size[0] - 2.0f) < 1e-3f);
    assert(std::fabs(size[1] - 3.0f) < 1e-3f);
    assert(std::fabs(size[2] - 4.0f) < 1e-3f);

    // 2) .iv serialization round trip
    SoOutput out;
    out.openFile("cube.iv");
    SoWriteAction writer(&out);
    writer.apply(cube);
    out.closeFile();
    cube->unref();

    SoInput in;
    if (!in.openFile("cube.iv")) {
        std::printf("FAIL: cannot reopen cube.iv\n");
        return 1;
    }
    // Coin's SoDB::readAll returns the root as SoSeparator*.
    SoSeparator *root = SoDB::readAll(&in);
    if (root == nullptr) {
        std::printf("FAIL: SoDB::readAll returned null\n");
        return 1;
    }

    SoCube *loaded = dynamic_cast<SoCube *>(root);
    if (loaded == nullptr) {
        SoGroup *group = dynamic_cast<SoGroup *>(root);
        if (group != nullptr && group->getNumChildren() > 0) {
            loaded = dynamic_cast<SoCube *>(group->getChild(0));
        }
    }
    if (loaded == nullptr) {
        std::printf("FAIL: round trip did not restore SoCube\n");
        return 1;
    }
    if (loaded->width.getValue() != 2.0f ||
        loaded->height.getValue() != 3.0f ||
        loaded->depth.getValue() != 4.0f) {
        std::printf("FAIL: field values changed across round trip\n");
        return 1;
    }

    std::printf("coin3d consumer test: PASS\n");
    return 0;
}
