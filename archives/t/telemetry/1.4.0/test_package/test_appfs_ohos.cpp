/**
 * @file
 * @brief HarmonyOS specific consumer test of the packaged telemetry libraries.
 *
 * Validates the two HarmonyOS specific contracts of this package:
 *
 *  1. The appFs target publishes the FUSE 3.0 ABI and a 64-bit off_t to every
 *     consumer (upstream: target_compile_definitions(appFs PUBLIC
 *     FUSE_USE_VERSION=30 _FILE_OFFSET_BITS=64)) and the fuse3 headers of the
 *     libfuse package reach the consumer through include/appFs.hpp.
 *  2. The packaged shared libraries carry a real DT_SONAME (libtelemetry.so.1 /
 *     libappFs.so.1) and are self-contained: libappFs.so must be loadable on
 *     OHOS without any libfuse3.so, because the static libfuse3.a of the
 *     dependency is absorbed at link time.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <appFs.hpp>
#include <telemetry.hpp>

#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <cstdio>
#include <memory>
#include <string>

/** The published FUSE ABI of appFs must reach the consumer. */
#if FUSE_USE_VERSION != 30
#error "appFs must publish FUSE_USE_VERSION=30 to its consumers"
#endif

/** appFs must publish a 64-bit off_t to its consumers. */
#if _FILE_OFFSET_BITS != 64
#error "appFs must publish _FILE_OFFSET_BITS=64 to its consumers"
#endif

static_assert(sizeof(off_t) == 8, "OHOS/aarch64 must use a 64-bit off_t");
static_assert(FUSE_MAJOR_VERSION == 3, "appFs requires the FUSE 3.x API");

int g_failures = 0;

#define CHECK(condition)                                                                           \
	do {                                                                                           \
		if (!(condition)) {                                                                        \
			std::fprintf(                                                                          \
				stderr, "CHECK failed: %s (%s:%d)\n", #condition, __FILE__, __LINE__);            \
			++g_failures;                                                                          \
		}                                                                                          \
	} while (false)

namespace {

/** Runtime check of the SONAME versioned libraries of the package. */
void testVersionedSharedLibraries()
{
	void* telemetryHandle = dlopen("libtelemetry.so.1", RTLD_NOW | RTLD_LOCAL);
	if (telemetryHandle == nullptr) {
		std::fprintf(stderr, "dlopen(libtelemetry.so.1): %s\n", dlerror());
	}
	CHECK(telemetryHandle != nullptr);

	// The static libfuse3.a is linked into libappFs.so; loading it must therefore
	// not require a libfuse3.so at runtime on OHOS.
	void* appFsHandle = dlopen("libappFs.so.1", RTLD_NOW | RTLD_LOCAL);
	if (appFsHandle == nullptr) {
		std::fprintf(stderr, "dlopen(libappFs.so.1): %s\n", dlerror());
	}
	CHECK(appFsHandle != nullptr);

	if (telemetryHandle != nullptr) {
		CHECK(dlclose(telemetryHandle) == 0);
	}
	if (appFsHandle != nullptr) {
		CHECK(dlclose(appFsHandle) == 0);
	}
}

/** The telemetry API must work through the linked (SONAME versioned) library. */
void testTelemetryApiFromSharedLibrary()
{
	auto root = telemetry::Directory::create();
	auto subDir = root->addDirs("ohos/telemetry");

	telemetry::FileOps ops {};
	ops.read = []() { return telemetry::Scalar {std::string {"harmonyos"}}; };
	auto file = subDir->addFile("platform", ops);

	CHECK(file->getFullPath() == "/ohos/telemetry/platform");
	CHECK(file->read() == telemetry::Content {telemetry::Scalar {std::string {"harmonyos"}}});
}

/** The appFs header type is complete for consumers (fuse3 headers resolved). */
void testAppFsTypeIsUsable()
{
	using MountFunction = void (telemetry::appFs::AppFsFuse::*)();
	CHECK(sizeof(telemetry::appFs::AppFsFuse*) > 0);
	CHECK(static_cast<MountFunction>(&telemetry::appFs::AppFsFuse::start) != nullptr);
}

/** /dev/fuse is a runtime platform capability, not a build dependency. */
void reportFuseDeviceAvailability()
{
	struct stat info {};
	if (stat("/dev/fuse", &info) == 0) {
		std::puts("OHOS note: /dev/fuse is available, appFs mounts can be started");
	} else {
		std::puts("OHOS note: /dev/fuse is not available, appFs mounting stays unavailable");
	}
}

} // namespace

int main()
{
	testVersionedSharedLibraries();
	testTelemetryApiFromSharedLibrary();
	testAppFsTypeIsUsable();
	reportFuseDeviceAvailability();

	if (g_failures != 0) {
		std::fprintf(stderr, "test_appfs_ohos: %d check(s) failed\n", g_failures);
		return 1;
	}

	std::puts("test_appfs_ohos: HarmonyOS FUSE/off_t contracts and SONAME loading passed");
	return 0;
}
