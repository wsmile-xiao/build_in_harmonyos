/* bzrtp test_package — ZRTP context lifecycle consumer checks.
 *
 * Proves, against the packaged libbzrtp (static or shared):
 *  1. bzrtp_createBzrtpContext returns a usable context
 *  2. bzrtp_setCallbacks accepts the client callback table
 *  3. bzrtp_initBzrtpContext + bzrtp_setClientData initialise a channel
 *  4. bzrtp_addChannel adds a second channel; both report
 *     BZRTP_CHANNEL_INITIALISED via bzrtp_getChannelStatus
 *  5. bzrtp_getSupportedCryptoTypes lists hash algos and bzrtp_algoToString
 *     resolves the first one
 *  6. bzrtp_set_MTU/bzrtp_get_MTU round-trip, bzrtp_available_key_agreement
 *     is non-empty, and bzrtp_destroyBzrtpContext tears both channels down
 *     (remaining counts 1 then 0)
 *
 * All calls are local: no network, no sqlite, no engine start (so the
 * sendData stub is never invoked). Each passing check prints one
 * "CHECK-OK: <name>" line; the test_package conanfile counts those lines
 * for the HMBS_TEST_PACKAGE_RESULT marker. Exit code is 0 only if all
 * 6 checks pass (exit-0-alone is not proof).
 */
#include <bzrtp/bzrtp.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define SSRC_ONE 0x12345678u
#define SSRC_TWO 0x23456789u

static int send_data_stub(void *clientData, const uint8_t *packetString, uint16_t packetLength) {
	(void)clientData;
	(void)packetString;
	(void)packetLength;
	return 0;
}

static int status_message_stub(void *clientData, const uint8_t messageLevel,
		const uint8_t messageId, const char *messageString) {
	(void)clientData;
	(void)messageLevel;
	(void)messageId;
	(void)messageString;
	return 0;
}

static int srtp_available_stub(void *clientData, const bzrtpSrtpSecrets_t *srtpSecrets, uint8_t part) {
	(void)clientData;
	(void)srtpSecrets;
	(void)part;
	return 0;
}

static int start_srtp_stub(void *clientData, const bzrtpSrtpSecrets_t *srtpSecrets, int32_t verified) {
	(void)clientData;
	(void)srtpSecrets;
	(void)verified;
	return 0;
}

static int exported_keys_stub(void *clientData, int zuid, uint8_t role) {
	(void)clientData;
	(void)zuid;
	(void)role;
	return 0;
}

int main(void) {
	bzrtpContext_t *ctx;
	bzrtpCallbacks_t cbs;
	uint8_t hashTypes[7];
	uint8_t kaTypes[256];
	uint8_t hashCount;
	uint8_t kaCount;
	const char *algoName;

	memset(&cbs, 0, sizeof(cbs));

	ctx = bzrtp_createBzrtpContext();
	if (ctx == NULL) {
		fprintf(stderr, "FAIL: bzrtp_createBzrtpContext returned NULL\n");
		return 1;
	}
	printf("CHECK-OK: create-context\n");

	cbs.bzrtp_statusMessage = status_message_stub;
	cbs.bzrtp_messageLevel = BZRTP_MESSAGE_ERROR;
	cbs.bzrtp_sendData = send_data_stub;
	cbs.bzrtp_srtpSecretsAvailable = srtp_available_stub;
	cbs.bzrtp_startSrtpSession = start_srtp_stub;
	cbs.bzrtp_contextReadyForExportedKeys = exported_keys_stub;
	if (bzrtp_setCallbacks(ctx, &cbs) != 0) {
		fprintf(stderr, "FAIL: bzrtp_setCallbacks != 0\n");
		return 1;
	}
	printf("CHECK-OK: set-callbacks\n");

	if (bzrtp_initBzrtpContext(ctx, SSRC_ONE) != 0) {
		fprintf(stderr, "FAIL: bzrtp_initBzrtpContext != 0\n");
		return 1;
	}
	if (bzrtp_setClientData(ctx, SSRC_ONE, (void *)0x1) != 0) {
		fprintf(stderr, "FAIL: bzrtp_setClientData != 0\n");
		return 1;
	}
	printf("CHECK-OK: init-channel\n");

	if (bzrtp_addChannel(ctx, SSRC_TWO) != 0) {
		fprintf(stderr, "FAIL: bzrtp_addChannel != 0\n");
		return 1;
	}
	if (bzrtp_getChannelStatus(ctx, SSRC_ONE) != BZRTP_CHANNEL_INITIALISED
			|| bzrtp_getChannelStatus(ctx, SSRC_TWO) != BZRTP_CHANNEL_INITIALISED) {
		fprintf(stderr, "FAIL: channel status not INITIALISED (one=0x%x two=0x%x)\n",
				bzrtp_getChannelStatus(ctx, SSRC_ONE),
				bzrtp_getChannelStatus(ctx, SSRC_TWO));
		return 1;
	}
	printf("CHECK-OK: add-channel\n");

	hashCount = bzrtp_getSupportedCryptoTypes(ctx, ZRTP_HASH_TYPE, hashTypes);
	if (hashCount == 0 || hashCount > 7) {
		fprintf(stderr, "FAIL: hash algo count out of range: %u\n", hashCount);
		return 1;
	}
	algoName = bzrtp_algoToString(hashTypes[0]);
	if (algoName == NULL || algoName[0] == '\0') {
		fprintf(stderr, "FAIL: bzrtp_algoToString empty for hash 0x%02x\n", hashTypes[0]);
		return 1;
	}
	printf("CHECK-OK: crypto-types (hash=%u e.g. %s)\n", hashCount, algoName);

	if (bzrtp_set_MTU(ctx, 1500) != 0 || bzrtp_get_MTU(ctx) != 1500) {
		fprintf(stderr, "FAIL: MTU round-trip broken (got %u)\n",
				(unsigned)bzrtp_get_MTU(ctx));
		return 1;
	}
	kaCount = bzrtp_available_key_agreement(kaTypes);
	if (kaCount == 0) {
		fprintf(stderr, "FAIL: no key agreement algorithm available\n");
		return 1;
	}
	if (bzrtp_destroyBzrtpContext(ctx, SSRC_ONE) != 1) {
		fprintf(stderr, "FAIL: destroying first channel must leave 1 remaining\n");
		return 1;
	}
	if (bzrtp_destroyBzrtpContext(ctx, SSRC_TWO) != 0) {
		fprintf(stderr, "FAIL: destroying last channel must leave 0 remaining\n");
		return 1;
	}
	printf("CHECK-OK: mtu-keyagreement-destroy (ka=%u)\n", kaCount);

	printf("bzrtp consumer test PASS (6/6)\n");
	return 0;
}
