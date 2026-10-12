/*
 * Consumer smoke test for pcsclite 2.5.2 (PC/SC smart-card middleware).
 *
 * Verifies, using ONLY the public installed headers/API:
 *   - <winscard.h> include chain resolves (<pcsclite.h> sits next to it)
 *   - compile + link against the packaged libpcsclite
 *   - SCardEstablishContext/SCardReleaseContext round-trip.  No pcscd daemon
 *     runs on the OHOS CI machine (it is intentionally not shipped), so the
 *     documented daemon-less behaviour is asserted instead: EstablishContext
 *     returns SCARD_E_NO_SERVICE and leaves the context untouched.  If a
 *     daemon IS available (e.g. on a developer machine), the success path is
 *     asserted instead — both are valid outcomes, each checked precisely.
 *   - pcsc_stringify_error() for SUCCESS / NO_SERVICE / INTERNAL_ERROR
 *   - bogus-handle rejection (SCARD_E_INVALID_HANDLE) for
 *     SCardReleaseContext / SCardIsValidContext
 *   - exported protocol-control-information globals (SCARD_PCI_T0/T1/RAW)
 *   - MAX_ATR_SIZE ABI constant
 */
#include <stdio.h>
#include <string.h>
#include <winscard.h>

static int failures = 0;
static int checks = 0;

static void check(int cond, const char *what)
{
	checks++;
	if (cond)
		printf("PASS %2d: %s\n", checks, what);
	else {
		printf("FAIL %2d: %s\n", checks, what);
		failures++;
	}
}

int main(void)
{
	SCARDCONTEXT ctx = 0;
	LONG rv;

	/* 1. ABI constant from <pcsclite.h> */
	check(MAX_ATR_SIZE == 33, "MAX_ATR_SIZE == 33");

	/* 2-4. pcsc_stringify_error() exact upstream strings */
	check(strcmp(pcsc_stringify_error(SCARD_S_SUCCESS),
			"Command successful.") == 0,
		"pcsc_stringify_error(SCARD_S_SUCCESS) == \"Command successful.\"");
	check(strcmp(pcsc_stringify_error(SCARD_E_NO_SERVICE),
			"Service not available.") == 0,
		"pcsc_stringify_error(SCARD_E_NO_SERVICE) == \"Service not available.\"");
	check(strcmp(pcsc_stringify_error(SCARD_F_INTERNAL_ERROR),
			"Internal error.") == 0,
		"pcsc_stringify_error(SCARD_F_INTERNAL_ERROR) == \"Internal error.\"");

	/* 5-7. exported PCI globals (defined in g_defines.c) */
	check(SCARD_PCI_T0 != NULL && SCARD_PCI_T0->dwProtocol == SCARD_PROTOCOL_T0,
		"SCARD_PCI_T0 global exported with T0 protocol");
	check(SCARD_PCI_T1 != NULL && SCARD_PCI_T1->dwProtocol == SCARD_PROTOCOL_T1,
		"SCARD_PCI_T1 global exported with T1 protocol");
	check(SCARD_PCI_RAW != NULL && SCARD_PCI_RAW->dwProtocol == SCARD_PROTOCOL_RAW,
		"SCARD_PCI_RAW global exported with RAW protocol");

	/* 8. SCardEstablishContext round-trip entry */
	rv = SCardEstablishContext(SCARD_SCOPE_SYSTEM, NULL, NULL, &ctx);
	if (rv == SCARD_S_SUCCESS) {
		/* daemon reachable (developer machine): release must succeed */
		check(1, "SCardEstablishContext(SCARD_SCOPE_SYSTEM) succeeded (daemon present)");
		rv = SCardReleaseContext(ctx);
		check(rv == SCARD_S_SUCCESS,
			"SCardReleaseContext(valid ctx) == SCARD_S_SUCCESS");
	} else {
		/* CI / daemon-less machine: documented NO_SERVICE, ctx untouched */
		check(rv == SCARD_E_NO_SERVICE,
			"SCardEstablishContext without daemon == SCARD_E_NO_SERVICE (0x8010001D)");
		check(ctx == 0, "context left untouched when EstablishContext fails");
	}

	/* 11-12. bogus-handle rejection (local, daemon-independent) */
	rv = SCardReleaseContext((SCARDCONTEXT)0xDEADBEEF);
	check(rv == SCARD_E_INVALID_HANDLE,
		"SCardReleaseContext(bogus) == SCARD_E_INVALID_HANDLE (0x80100003)");
	rv = SCardIsValidContext((SCARDCONTEXT)0x1234);
	check(rv == SCARD_E_INVALID_HANDLE,
		"SCardIsValidContext(bogus) == SCARD_E_INVALID_HANDLE");

	printf("\n%d checks, %d failures\n", checks, failures);
	return failures ? 1 : 0;
}
