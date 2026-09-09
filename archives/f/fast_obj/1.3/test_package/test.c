#include <stdio.h>
#include <stdlib.h>
#include "fast_obj.h"

/* Consumer test: parse a small embedded OBJ and verify counts. */
int main(void)
{
    fastObjMesh* mesh = fast_obj_read("cube.obj");
    if (!mesh)
    {
        fprintf(stderr, "FAIL: fast_obj_read returned NULL\n");
        return 1;
    }

    /* cube.obj: 8 vertices -> position_count=9 (fast_obj keeps a dummy
       entry at index 0 for missing data; indices are 1-based), 6 faces. */
    int ok = 1;
    if (mesh->position_count != 9)
    {
        fprintf(stderr, "FAIL: position_count=%u, expected 9\n", mesh->position_count);
        ok = 0;
    }
    if (mesh->face_count != 6)
    {
        fprintf(stderr, "FAIL: face_count=%u, expected 6\n", mesh->face_count);
        ok = 0;
    }
    if (mesh->group_count != 1)
    {
        fprintf(stderr, "FAIL: group_count=%u, expected 1\n", mesh->group_count);
        ok = 0;
    }
    if (!mesh->positions || !mesh->indices)
    {
        fprintf(stderr, "FAIL: positions/indices missing\n");
        ok = 0;
    }

    fast_obj_destroy(mesh);

    if (ok)
    {
        printf("test fast_obj 1.3: OK (8 verts, 6 faces)\n");
        return 0;
    }
    return 1;
}
