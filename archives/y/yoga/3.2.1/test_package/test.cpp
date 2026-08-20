#include <yoga/Yoga.h>
#include <cassert>
#include <cstdio>

int main(void) {
    // Create root node with fixed dimensions
    YGNodeRef root = YGNodeNew();
    YGNodeStyleSetWidth(root, 100);
    YGNodeStyleSetHeight(root, 100);
    YGNodeStyleSetFlexDirection(root, YGFlexDirectionColumn);
    YGNodeStyleSetJustifyContent(root, YGJustifyCenter);
    YGNodeStyleSetAlignItems(root, YGAlignCenter);

    // Create child node with flex grow
    YGNodeRef child = YGNodeNew();
    YGNodeStyleSetWidth(child, 50);
    YGNodeStyleSetHeight(child, 50);
    YGNodeInsertChild(root, child, 0);

    // Calculate layout
    YGNodeCalculateLayout(root, YGUndefined, YGUndefined, YGDirectionLTR);

    // Verify root layout
    assert(YGNodeLayoutGetWidth(root) == 100.0f);
    assert(YGNodeLayoutGetHeight(root) == 100.0f);

    // Verify child layout (centered in 100x100 container with 50x50 child)
    assert(YGNodeLayoutGetLeft(child) == 25.0f);
    assert(YGNodeLayoutGetTop(child) == 25.0f);
    assert(YGNodeLayoutGetWidth(child) == 50.0f);
    assert(YGNodeLayoutGetHeight(child) == 50.0f);

    YGNodeFreeRecursive(root);

    printf("All Yoga layout tests passed!\n");
    return 0;
}
