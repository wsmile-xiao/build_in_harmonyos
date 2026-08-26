/*
 * lib3ds 1.3.0 consumer test.
 *
 * Verifies the core 3DS API by constructing objects in memory — no .3ds
 * file on disk, no GUI/OpenGL dependency — so it runs headless on OHOS.
 *
 * Every numbered CHECK that passes is tallied and printed at the end as
 * "CHECK passed: <N>", which the CI L1 gate parses.
 */
#include <lib3ds/file.h>
#include <lib3ds/mesh.h>
#include <lib3ds/material.h>
#include <lib3ds/node.h>
#include <lib3ds/vector.h>
#include <lib3ds/matrix.h>
#include <lib3ds/quat.h>
#include <stdio.h>
#include <string.h>

static int g_checks = 0;
#define CHECK(cond, msg)                                       \
    do {                                                       \
        if (cond) {                                            \
            g_checks++;                                        \
            printf("[CHECK %02d] PASS: %s\n", g_checks, msg);  \
        } else {                                               \
            printf("[CHECK %02d] FAIL: %s\n", g_checks, msg);  \
            return 1;                                          \
        }                                                      \
    } while (0)

int main(void)
{
    /* --- 1. File lifecycle + empty-state invariants ---------------- */
    Lib3dsFile *file = lib3ds_file_new();
    CHECK(file != NULL, "lib3ds_file_new returns non-NULL");

    CHECK(file->materials == NULL, "new file has no materials");
    CHECK(file->meshes == NULL, "new file has no meshes");
    CHECK(file->cameras == NULL, "new file has no cameras");
    CHECK(file->lights == NULL, "new file has no lights");
    CHECK(file->nodes == NULL, "new file has no nodes");
    CHECK(file->frames == 100, "new file frames == 100");

    /* --- 2. Material create + insert + lookup ---------------------- */
    Lib3dsMaterial *mat = lib3ds_material_new();
    CHECK(mat != NULL, "lib3ds_material_new returns non-NULL");
    strncpy(mat->name, "RedPlastic", sizeof(mat->name) - 1);
    mat->name[sizeof(mat->name) - 1] = '\0';
    mat->ambient[0] = 0.2f; mat->ambient[1] = 0.0f; mat->ambient[2] = 0.0f;
    mat->diffuse[0] = 0.8f; mat->diffuse[1] = 0.1f; mat->diffuse[2] = 0.1f;

    lib3ds_file_insert_material(file, mat);
    CHECK(file->materials == mat, "inserted material is head of list");

    Lib3dsMaterial *found = lib3ds_file_material_by_name(file, "RedPlastic");
    CHECK(found == mat, "material_by_name finds inserted material");

    Lib3dsMaterial *missing = lib3ds_file_material_by_name(file, "NoSuchMat");
    CHECK(missing == NULL, "material_by_name returns NULL for unknown name");

    /* --- 3. Mesh create + point/face lists + insert --------------- */
    Lib3dsMesh *mesh = lib3ds_mesh_new("Cube");
    CHECK(mesh != NULL, "lib3ds_mesh_new returns non-NULL");
    CHECK(strcmp(mesh->name, "Cube") == 0, "mesh name set to 'Cube'");

    /* A unit cube: 8 vertices, 12 triangles. */
    Lib3dsBool ok = lib3ds_mesh_new_point_list(mesh, 8);
    CHECK(ok, "allocate 8-point list");
    static Lib3dsVector pts[8] = {
        {0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0},
        {0, 0, 1}, {1, 0, 1}, {1, 1, 1}, {0, 1, 1},
    };
    for (int i = 0; i < 8; i++) {
        lib3ds_vector_copy(mesh->pointL[i].pos, pts[i]);
    }
    CHECK(mesh->points == 8, "mesh reports 8 points");

    ok = lib3ds_mesh_new_face_list(mesh, 12);
    CHECK(ok, "allocate 12-face list");
    /* 2 triangles per cube face. */
    static const Lib3dsWord faces[12][3] = {
        {0, 2, 1}, {0, 3, 2},   /* -Z */
        {4, 5, 6}, {4, 6, 7},   /* +Z */
        {0, 1, 5}, {0, 5, 4},   /* -Y */
        {3, 7, 6}, {3, 6, 2},   /* +Y */
        {0, 4, 7}, {0, 7, 3},   /* -X */
        {1, 2, 6}, {1, 6, 5},   /* +X */
    };
    for (int i = 0; i < 12; i++) {
        mesh->faceL[i].points[0] = faces[i][0];
        mesh->faceL[i].points[1] = faces[i][1];
        mesh->faceL[i].points[2] = faces[i][2];
    }
    CHECK(mesh->faces == 12, "mesh reports 12 faces");

    lib3ds_file_insert_mesh(file, mesh);
    CHECK(file->meshes == mesh, "inserted mesh is head of list");

    Lib3dsMesh *mfound = lib3ds_file_mesh_by_name(file, "Cube");
    CHECK(mfound == mesh, "mesh_by_name finds inserted mesh");

    /* --- 4. Bounding box of the cube ------------------------------- */
    Lib3dsVector bmin, bmax;
    lib3ds_mesh_bounding_box(mesh, bmin, bmax);
    CHECK(bmax[0] == 1.0f && bmax[1] == 1.0f && bmax[2] == 1.0f,
          "bounding box max == (1,1,1)");
    CHECK(bmin[0] == 0.0f && bmin[1] == 0.0f && bmin[2] == 0.0f,
          "bounding box min == (0,0,0)");

    /* --- 5. Vector math sanity ------------------------------------- */
    Lib3dsVector a = {1, 2, 2}, b = {0, 0, 0};
    Lib3dsFloat len = lib3ds_vector_length(a);
    CHECK(len == 3.0f, "vector_length((1,2,2)) == 3");

    lib3ds_vector_cross(b, (Lib3dsVector){1, 0, 0}, (Lib3dsVector){0, 1, 0});
    CHECK(b[0] == 0.0f && b[1] == 0.0f && b[2] == 1.0f,
          "cross(X, Y) == Z");

    Lib3dsFloat dot = lib3ds_vector_dot((Lib3dsVector){1, 0, 0},
                                        (Lib3dsVector){0, 1, 0});
    CHECK(dot == 0.0f, "dot(X, Y) == 0");

    /* --- 6. Save + reload round-trip ------------------------------- */
    const char *tmp = "lib3ds_consumer_test.3ds";
    Lib3dsBool saved = lib3ds_file_save(file, tmp);
    CHECK(saved, "lib3ds_file_save writes a .3ds file");

    Lib3dsFile *file2 = lib3ds_file_load(tmp);
    CHECK(file2 != NULL, "lib3ds_file_load reads it back");

    Lib3dsMesh *rmesh = lib3ds_file_mesh_by_name(file2, "Cube");
    CHECK(rmesh != NULL, "reloaded file contains mesh 'Cube'");
    if (rmesh) {
        CHECK(rmesh->points == 8, "reloaded mesh has 8 points");
        CHECK(rmesh->faces == 12, "reloaded mesh has 12 faces");
    }

    Lib3dsMaterial *rmat = lib3ds_file_material_by_name(file2, "RedPlastic");
    CHECK(rmat != NULL, "reloaded file contains material 'RedPlastic'");

    /* --- 7. Node API ---------------------------------------------- */
    Lib3dsNode *node = lib3ds_node_new_object();
    CHECK(node != NULL, "lib3ds_node_new_object returns non-NULL");
    CHECK(node->type == LIB3DS_OBJECT_NODE,
          "node type is OBJECT_NODE");

    strncpy(node->name, mesh->name, sizeof(node->name) - 1);
    node->name[sizeof(node->name) - 1] = '\0';
    node->parent_id = LIB3DS_NO_PARENT;

    lib3ds_file_insert_node(file, node);

    CHECK(file->nodes == node, "inserted node is head of list");
    lib3ds_file_remove_node(file, node);
    CHECK(file->nodes == NULL, "removed node leaves empty list");
    lib3ds_node_free(node);

    /* --- 8. Cleanup ----------------------------------------------- */
    lib3ds_file_free(file2);
    lib3ds_file_free(file);
    remove(tmp);

    printf("\nCHECK passed: %d\n", g_checks);
    printf("lib3ds 1.3.0 consumer test: OK\n");
    return 0;
}
