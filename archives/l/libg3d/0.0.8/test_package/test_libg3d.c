#include <stdio.h>
#include <string.h>

#include <g3d/g3d.h>
#include <g3d/primitive.h>
#include <g3d/material.h>
#include <g3d/model.h>
#include <g3d/object.h>

static int failed = 0;
static int checks = 0;

static void check(int cond, const char *label)
{
    checks++;
    if (cond) {
        printf("ok %d - %s\n", checks, label);
    } else {
        printf("not ok %d - %s\n", checks, label);
        failed = 1;
    }
}

int main(void)
{
    G3DContext *context = g3d_context_new();
    check(context != NULL, "g3d_context_new returns valid context");

    G3DMaterial *material = g3d_material_new();
    check(material != NULL, "g3d_material_new returns valid material");

    G3DObject *box = g3d_primitive_box(1.0f, 2.0f, 3.0f, material);
    check(box != NULL, "g3d_primitive_box returns object");
    check(box != NULL && box->vertex_count > 0, "box has vertices");
    check(box != NULL && box->faces != NULL, "box has faces");

    double radius_before = 0.0;
    if (box != NULL) {
        radius_before = g3d_object_radius(box);
        check(radius_before > 0.0, "g3d_object_radius positive");
    } else {
        check(0, "g3d_object_radius positive");
    }

    if (box != NULL) {
        int scaled = g3d_object_scale(box, 2.0f);
        double radius_after = g3d_object_radius(box);
        check(scaled != 0, "g3d_object_scale succeeds");
        check(radius_after > radius_before, "scaled radius grows");
    } else {
        check(0, "g3d_object_scale succeeds");
        check(0, "scaled radius grows");
    }

    G3DObject *sphere = g3d_primitive_sphere(1.0f, 8, 8, material);
    check(sphere != NULL, "g3d_primitive_sphere returns object");
    check(sphere != NULL && sphere->vertex_count > 0, "sphere has vertices");

    G3DModel *model = g3d_model_new();
    check(model != NULL, "g3d_model_new returns valid model");
    check(model != NULL && model->objects == NULL, "fresh model has no objects");

    printf("1..%d\n", checks);
    if (box != NULL)
        g3d_object_free(box);
    if (sphere != NULL)
        g3d_object_free(sphere);
    if (model != NULL)
        g3d_model_free(model);
    if (material != NULL)
        g3d_material_free(material);
    if (context != NULL)
        g3d_context_free(context);
    if (failed) {
        fprintf(stderr, "consumer test FAILED\n");
        return 1;
    }
    printf("libg3d consumer test: OK (%d checks)\n", checks);
    return 0;
}
