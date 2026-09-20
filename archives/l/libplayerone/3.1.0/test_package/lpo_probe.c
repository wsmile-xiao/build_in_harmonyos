/* Downstream-consumption probe for libplayerone 3.1.0.
 *
 * Includes the packaged PlayerOneCamera.h, references the core public API
 * (POAGetAPIVersion / POAGetCameraCount / POAOpenCamera /
 * POAGetCameraProperties) and links against the vendor prebuilt
 * libPlayerOneCamera.so — proving the header and the packaged vendor .so
 * are usable by a real OHOS aarch64 build.
 *
 * Not executed on the host: the vendor .so needs a connected POA camera
 * over USB and the CI sandbox does not allow dlopen of foreign .so files.
 * The link step is the downstream-usability proof (R34).
 */
#include <PlayerOneCamera.h>

int lpo_probe_version(void)
{
	return POAGetAPIVersion();
}

int lpo_probe_camera_count(void)
{
	return POAGetCameraCount();
}

POAErrors lpo_probe_open(int camera_id)
{
	return POAOpenCamera(camera_id);
}

POAErrors lpo_probe_properties(int camera_id, POACameraProperties *props)
{
	return POAGetCameraProperties(camera_id, props);
}
