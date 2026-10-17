#include <mialm.h>

#include <libxml/parser.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "check failed at line %d: %s\n",                 \
                    __LINE__, #condition);                                     \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    const float sqrt14 = sqrtf(14.0f);
    MiaVector3d *first = mia_vector3d_new(1.0f, 2.0f, 3.0f);
    MiaVector3d *second = mia_vector3d_new(2.0f, 5.0f, 7.0f);
    MiaVector3d *duplicate;
    MiaVector3d *sum;
    MiaQuaternion *rotation;
    MiaCamera *camera;
    MiaLandmark *landmark;
    MiaLandmark *loaded_landmark;
    MiaLandmarklist *list;
    MiaLandmarklist *loaded;

    CHECK(first != NULL);
    CHECK(second != NULL);
    CHECK(MIA_IS_VECTOR3D(first));
    CHECK(first->x == 1.0f && first->y == 2.0f && first->z == 3.0f);

    duplicate = mia_vector3d_dup(first);
    CHECK(duplicate != NULL);
    CHECK(mia_vector3d_equal(first, duplicate));

    mia_vector3d_addup(first, second);
    CHECK(first->x == 3.0f && first->y == 7.0f && first->z == 10.0f);
    mia_vector3d_scale(first, 0.5f);
    CHECK(first->x == 1.5f && first->y == 3.5f && first->z == 5.0f);
    CHECK(mia_vector3d_dot(duplicate, second) == 33.0f);
    CHECK(fabsf(mia_vector3d_get_norm(duplicate) - sqrt14) < 1e-5f);

    mia_vector3d_normalize(duplicate);
    CHECK(fabsf(mia_vector3d_get_norm(duplicate) - 1.0f) < 1e-5f);
    CHECK(fabsf(duplicate->x - 1.0f / sqrt14) < 1e-5f &&
          fabsf(duplicate->y - 2.0f / sqrt14) < 1e-5f &&
          fabsf(duplicate->z - 3.0f / sqrt14) < 1e-5f);

    mia_vector3d_copy(duplicate, second);
    CHECK(duplicate->x == 2.0f && duplicate->y == 5.0f && duplicate->z == 7.0f);
    mia_vector3d_add(first, second, duplicate);
    CHECK(duplicate->x == 3.5f && duplicate->y == 8.5f && duplicate->z == 12.0f);
    sum = mia_vector3d_add(first, second, NULL);
    CHECK(sum != NULL);
    CHECK(sum->x == 3.5f && sum->y == 8.5f && sum->z == 12.0f);

    rotation = mia_quaternion_new(0.0f, 0.0f, 0.0f, 1.0f);
    CHECK(rotation != NULL);
    CHECK(MIA_IS_QUATERNION(rotation));
    CHECK(fabsf(mia_quaternion_norm(rotation) - 1.0f) < 1e-5f);

    camera = mia_camera_new(mia_vector3d_new(10.0f, 20.0f, 30.0f),
                            rotation, 2.5f);
    CHECK(camera != NULL);
    CHECK(mia_camera_get_zoom(camera) == 2.5f);
    CHECK(mia_camera_get_location(camera)->z == 30.0f);

    landmark = mia_landmark_new("Harmony landmark",
                                mia_vector3d_new(-1.0f, 4.0f, 9.0f),
                                42.0f, camera, "reference.png");
    CHECK(landmark != NULL);
    CHECK(strcmp(mia_landmark_get_name(landmark), "Harmony landmark") == 0);

    list = mia_landmarklist_new("Harmony list");
    CHECK(list != NULL);
    CHECK(mia_landmarklist_insert(list, landmark));
    CHECK(mia_landmarklist_save(list, "libmialm-test.xml"));
    loaded = mia_landmarklist_new_from_file("libmialm-test.xml");
    CHECK(loaded != NULL);
    CHECK(strcmp(mia_landmarklist_get_name(loaded), "Harmony list") == 0);
    loaded_landmark = mia_landmarklist_get_landmark(loaded, "Harmony landmark");
    CHECK(loaded_landmark != NULL);
    CHECK(strcmp(mia_landmark_get_picfile(loaded_landmark), "reference.png") == 0);

    g_object_unref(loaded);
    g_object_unref(list);
    g_object_unref(sum);
    g_object_unref(duplicate);
    g_object_unref(second);
    g_object_unref(first);
    xmlCleanupParser();
    return 0;
}
