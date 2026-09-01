#include <embree4/rtcore.h>
#include <stdio.h>

int main(void) {
    /* Initialize embree device */
    RTCDevice device = rtcNewDevice(NULL);
    if (device == NULL) {
        enum RTCError err = rtcGetDeviceError(NULL);
        printf("Failed to create embree device: error %d\n", (int)err);
        return 1;
    }

    /* Verify device version property */
    ssize_t version = (ssize_t)rtcGetDeviceProperty(device, RTC_DEVICE_PROPERTY_VERSION);
    if (version == 0) {
        printf("Invalid device version property\n");
        rtcReleaseDevice(device);
        return 1;
    }

    /* Create a simple scene with a triangle */
    RTCScene scene = rtcNewScene(device);
    RTCGeometry geom = rtcNewGeometry(device, RTC_GEOMETRY_TYPE_TRIANGLE);

    float* vertices = (float*)rtcSetNewGeometryBuffer(
        geom, RTC_BUFFER_TYPE_VERTEX, 0, RTC_FORMAT_FLOAT3, 3 * sizeof(float), 3);
    vertices[0] = 0.0f; vertices[1] = 0.0f; vertices[2] = 0.0f;
    vertices[3] = 1.0f; vertices[4] = 0.0f; vertices[5] = 0.0f;
    vertices[6] = 0.0f; vertices[7] = 1.0f; vertices[8] = 0.0f;

    unsigned int* indices = (unsigned int*)rtcSetNewGeometryBuffer(
        geom, RTC_BUFFER_TYPE_INDEX, 0, RTC_FORMAT_UINT3, 3 * sizeof(unsigned int), 1);
    indices[0] = 0; indices[1] = 1; indices[2] = 2;

    rtcCommitGeometry(geom);
    rtcAttachGeometry(scene, geom);
    rtcReleaseGeometry(geom);
    rtcCommitScene(scene);

    /* Cast a ray and check intersection */
    struct RTCRayHit rayhit;
    rayhit.ray.org_x = 0.3f; rayhit.ray.org_y = 0.3f; rayhit.ray.org_z = -1.0f;
    rayhit.ray.dir_x = 0.0f; rayhit.ray.dir_y = 0.0f; rayhit.ray.dir_z = 1.0f;
    rayhit.ray.tnear = 0.0f;
    rayhit.ray.tfar = 100.0f;
    rayhit.ray.flags = 0;
    rayhit.hit.geomID = RTC_INVALID_GEOMETRY_ID;
    rayhit.hit.instID[0] = RTC_INVALID_GEOMETRY_ID;

    struct RTCIntersectArguments args;
    rtcInitIntersectArguments(&args);
    rtcIntersect1(scene, &rayhit, &args);

    if (rayhit.hit.geomID == RTC_INVALID_GEOMETRY_ID) {
        printf("Ray intersection test failed: no hit\n");
        rtcReleaseScene(scene);
        rtcReleaseDevice(device);
        return 1;
    }

    printf("Embree 4.4.1 test passed: ray hit geometry %u at tfar=%f\n",
           rayhit.hit.geomID, rayhit.ray.tfar);

    rtcReleaseScene(scene);
    rtcReleaseDevice(device);
    return 0;
}
