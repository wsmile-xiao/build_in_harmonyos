#include <stdio.h>
#include <stdlib.h>
#include <gts.h>

/* 消费者冒烟测试：实际调用 libgts 的公开 API。
 * 1. gts_surface_class()/gts_face_class() 等类 getter（OOC 类注册表）
 * 2. gts_surface_new 创建表面对象
 * 3. gts_surface_foreach_face 遍历（空表面应安全返回）
 * 4. gts_object_destroy 销毁对象（触发对象释放路径）
 */
int main(void) {
    GtsSurfaceClass *sclass = gts_surface_class();
    if (sclass == NULL) {
        fprintf(stderr, "FAIL: gts_surface_class() 返回 NULL\n");
        return 1;
    }

    GtsSurface *surface = gts_surface_new(
        sclass, gts_face_class(), gts_edge_class(), gts_vertex_class());
    if (surface == NULL) {
        fprintf(stderr, "FAIL: gts_surface_new 返回 NULL\n");
        return 1;
    }

    /* 遍历空表面：应安全地返回（无面片） */
    gts_surface_foreach_face(surface, NULL, NULL);

    gts_object_destroy(GTS_OBJECT(surface));
    printf("PASS: gts 0.7.6 API 冒烟测试通过 (GtsSurface 创建/遍历/销毁)\n");
    return 0;
}
