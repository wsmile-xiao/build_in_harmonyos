#include <gxr.h>

#include <cmath>
#include <cstdio>
#include <cstring>

namespace {
int failures = 0;

#define CHECK(condition)                                                   \
    do {                                                                   \
        if (!(condition)) {                                                \
            std::printf("FAIL: %s (line %d)\n", #condition, __LINE__);    \
            ++failures;                                                    \
        }                                                                  \
    } while (false)
}  // namespace

int main()
{
    timespec newer{9, 100000000};
    timespec older{7, 600000000};
    timespec delta{};
    gxr_time_substract(&newer, &older, &delta);
    CHECK(delta.tv_sec == 1);
    CHECK(delta.tv_nsec == 500000000);
    CHECK(std::fabs(gxr_time_to_double_secs(&delta) - 1.5) < 0.000001);

    timespec converted{};
    gxr_time_float_secs_to_timespec(2.25F, &converted);
    CHECK(converted.tv_sec == 2);
    CHECK(converted.tv_nsec == 250000000);

    GxrDevice *device = gxr_device_new(42, const_cast<char *>("initial"));
    CHECK(device != nullptr);
    CHECK(GXR_IS_DEVICE(device));
    CHECK(gxr_device_get_handle(device) == 42);
    CHECK(std::strcmp(gxr_device_get_model_name(device), "initial") == 0);
    CHECK(!gxr_device_is_pose_valid(device));

    gxr_device_set_handle(device, 84);
    gxr_device_set_model_name(device, const_cast<char *>("updated"));
    gxr_device_set_is_pose_valid(device, true);
    CHECK(gxr_device_get_handle(device) == 84);
    CHECK(std::strcmp(gxr_device_get_model_name(device), "updated") == 0);
    CHECK(gxr_device_is_pose_valid(device));

    graphene_matrix_t input;
    graphene_matrix_t output;
    graphene_point3d_t translation{1.0F, 2.0F, 3.0F};
    graphene_matrix_init_translate(&input, &translation);
    gxr_device_set_transformation_direct(device, &input);
    gxr_device_get_transformation_direct(device, &output);
    CHECK(graphene_matrix_equal(&input, &output));

    GxrDeviceManager *manager = gxr_device_manager_new();
    CHECK(manager != nullptr);
    CHECK(GXR_IS_DEVICE_MANAGER(manager));
    CHECK(gxr_device_manager_get_devices(manager) == nullptr);

    GString *cache = gxr_io_get_cache_path("gxr-conan-test");
    CHECK(cache != nullptr);
    CHECK(cache != nullptr && g_str_has_suffix(cache->str, "gxr-conan-test"));

    if (cache != nullptr) {
        g_string_free(cache, TRUE);
    }
    g_object_unref(manager);
    g_object_unref(device);

    if (failures == 0) {
        std::printf("PASS: gxr C++ consumer exercised time, device, matrix, "
                    "manager and IO APIs\n");
        return 0;
    }
    std::printf("FAILED: %d checks\n", failures);
    return 1;
}
