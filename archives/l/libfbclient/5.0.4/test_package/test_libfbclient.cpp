// test_package for libfbclient/5.0.4 — consumer view.
//
// Really exercises the packaged client library (R34): the shared object is
// loaded, the Y-Valve master interface is obtained, the legacy C API version
// entry point is called, ICU-backed time zone conversion is executed, and a
// real attach attempt is made so that the remote (inet) provider and the
// status/error machinery run. No database server is required.
//
// HarmonyOS specific cases (>= 1):
//   OHOS-1  the test itself is compiled for HarmonyOS/aarch64 with the OHOS
//           toolchain (__OHOS__ / __aarch64__ / __LP64__).
//   OHOS-2  the artifact that got packaged really is an aarch64 HarmonyOS
//           shared object: the ELF header of the library file resolved at
//           runtime (dladdr) is parsed and checked (ELF64, little endian,
//           EM_AARCH64, ET_DYN).
//   OHOS-3  the ICU code path works on HarmonyOS with the ICU shipped by the
//           Conan package (icu4c/78) instead of a system ICU.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <unistd.h>

#include <firebird/Interface.h>
#include <firebird/ibase.h>

using namespace Firebird;

static int failures = 0;

static void check(bool ok, const char* what)
{
	std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok)
		++failures;
}

// ── OHOS-1: compile-time platform check ────────────────────────────────────
static void test_ohos_toolchain()
{
#if !defined(__OHOS__)
	check(false, "[OHOS-1] test compiled with the HarmonyOS toolchain (__OHOS__)");
#else
	const bool ok = (sizeof(void*) == 8)
#if defined(__aarch64__)
		&& true
#else
		&& false
#endif
		;
	check(ok, "[OHOS-1] compiled for HarmonyOS/aarch64 (__OHOS__, __aarch64__, 64-bit)");
#endif
}

// ── OHOS-2: packaged artifact is an aarch64 OHOS shared object ─────────────
static void test_ohos_elf(const char* what)
{
	// Resolve the packaged library at runtime and locate the file it was
	// loaded from (dlsym + dladdr give the real path inside the package).
	void* handle = dlopen("libfbclient.so.2", RTLD_NOW | RTLD_GLOBAL);
	if (!handle)
		handle = dlopen("libfbclient.so", RTLD_NOW | RTLD_GLOBAL);
	if (!handle)
	{
		check(false, "[OHOS-2] dlopen('libfbclient.so.2') succeeds");
		return;
	}
	Dl_info info;
	if (!dlsym(handle, "fb_get_master_interface") ||
		!dladdr(dlsym(handle, "fb_get_master_interface"), &info) || !info.dli_fname)
	{
		check(false, "[OHOS-2] dladdr() resolved the library path");
		return;
	}
	std::printf("  library path: %s\n", info.dli_fname);

	FILE* f = std::fopen(info.dli_fname, "rb");
	if (!f)
	{
		check(false, "[OHOS-2] library file is readable");
		return;
	}
	unsigned char hdr[20] = {0};
	const size_t got = std::fread(hdr, 1, sizeof(hdr), f);
	std::fclose(f);
	if (got < sizeof(hdr))
	{
		check(false, "[OHOS-2] ELF header readable");
		return;
	}

	const bool magic = hdr[0] == 0x7f && hdr[1] == 'E' && hdr[2] == 'L' && hdr[3] == 'F';
	const bool elf64 = hdr[4] == 2;          // ELFCLASS64
	const bool le    = hdr[5] == 1;          // ELFDATA2LSB
	const bool dyn   = hdr[16] == 3 && hdr[17] == 0;   // ET_DYN
	const unsigned machine = (unsigned) hdr[18] | ((unsigned) hdr[19] << 8);
	const bool aarch64 = machine == 183;     // EM_AARCH64

	std::printf("  ELF magic=%d class64=%d little_endian=%d machine=%u type=%s\n",
		(int) magic, (int) elf64, (int) le, machine, dyn ? "DYN" : "other");
	check(magic && elf64 && le && dyn && aarch64, what);
}

// ── OHOS-3 + library functionality ────────────────────────────────────────
static void test_client_library()
{
	IMaster* master = fb_get_master_interface();
	check(master != nullptr, "fb_get_master_interface() returns the Y-Valve master interface");
	if (!master)
		return;

	IUtil* util = master->getUtilInterface();
	check(util != nullptr, "IMaster::getUtilInterface()");
	if (!util)
		return;

	check(util->getClientVersion() == 5 * 256 + 0,
		"IUtil::getClientVersion() == 1280 (Firebird 5.0)");

	// Legacy C API: reports the ISC/InterBase API level plus the product string.
	const int major = isc_get_client_major_version();
	const int minor = isc_get_client_minor_version();
	char version[128] = {0};
	isc_get_client_version(version);
	std::printf("  isc_get_client_version(): '%s' -> major=%d minor=%d\n",
		version, major, minor);
	int versionMajor = 0, versionMinor = 0;
	std::sscanf(version, "LI-V%d.%d.", &versionMajor, &versionMinor);
	check(major == versionMajor && minor == versionMinor,
		"isc_get_client_major/minor_version() consistent with isc_get_client_version()");
	check(std::strstr(version, "Firebird 5.0") != nullptr,
		"isc_get_client_version() reports 'Firebird 5.0'");

	// Client-side common code (date codec).
	const ISC_DATE date = util->encodeDate(2026, 9, 21);
	unsigned year = 0, month = 0, day = 0;
	util->decodeDate(date, &year, &month, &day);
	check(year == 2026 && month == 9 && day == 21,
		"IUtil::encodeDate()/decodeDate() round trip");

	// OHOS-3: time zone conversion goes through ICU (TimeZoneUtil), which on
	// HarmonyOS comes from the icu4c/78 Conan package.
	CheckStatusWrapper status(master->getStatus());
	ISC_TIMESTAMP_TZ ts;
	std::memset(&ts, 0, sizeof(ts));
	char tzbuf[64] = {0};
	util->encodeTimeStampTz(&status, &ts, 2026, 9, 21, 12, 0, 0, 0, "UTC");
	unsigned y = 0, mo = 0, d = 0, h = 0, mi = 0, s = 0, fr = 0;
	util->decodeTimeStampTz(&status, &ts, &y, &mo, &d, &h, &mi, &s, &fr,
		sizeof(tzbuf), tzbuf);
	std::printf("  decodeTimeStampTz(UTC) = %04u-%02u-%02u %02u:%02u:%02u\n", y, mo, d, h, mi, s);
	check(y == 2026 && mo == 9 && d == 21 && h == 12,
		"[OHOS-3] ICU time zone codec works (encode/decodeTimeStampTz)");

	// Remote provider + status/error machinery: no server is running, so a
	// real Firebird network error must come back and be interpretable.
	IProvider* provider = master->getDispatcher();
	check(provider != nullptr, "IMaster::getDispatcher()");
	if (!provider)
		return;

	char dpb[64];
	unsigned dpbLen = 0;
	dpb[dpbLen++] = isc_dpb_version1;
	dpb[dpbLen++] = isc_dpb_user_name;
	dpb[dpbLen++] = 6;
	std::memcpy(dpb + dpbLen, "sysdba", 6);
	dpbLen += 6;
	dpb[dpbLen++] = isc_dpb_password;
	dpb[dpbLen++] = 9;
	std::memcpy(dpb + dpbLen, "masterkey", 9);
	dpbLen += 9;

	ISC_STATUS_ARRAY statusVector;
	isc_db_handle db = 0;
	isc_attach_database(statusVector, 0, "inet://127.0.0.1/nonexistent.fdb", &db,
		(short) dpbLen, dpb);
	check(statusVector[1] != 0, "isc_attach_database() to an absent server returns an error");

	char text[512] = {0};
	if (statusVector[1] != 0)
	{
		const ISC_STATUS* p = statusVector;
		fb_interpret(text, sizeof(text), &p);
	}
	std::printf("  error text: %s\n", text);
	check(std::strstr(text, "network") != nullptr || std::strstr(text, "connect") != nullptr,
		"error is produced by the remote/inet provider (client networking path)");
}

int main()
{
	std::printf("=== libfbclient/5.0.4 test_package ===\n");
	test_ohos_toolchain();
	test_client_library();
	test_ohos_elf("[OHOS-2] packaged library is an aarch64 OHOS shared object (ELF64/LSB/EM_AARCH64/ET_DYN)");
	std::printf("=== %s (%d failure(s)) ===\n", failures == 0 ? "ALL PASSED" : "FAILED", failures);
	return failures == 0 ? 0 : 1;
}
