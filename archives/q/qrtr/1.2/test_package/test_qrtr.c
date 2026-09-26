/* Consumer test for the installed libqrtr.
 *
 * Drives the public QMI encode/decode API from include/libqrtr.h and the
 * validation paths around it. None of these calls need a QRTR kernel device,
 * so the test proves the installed library is both linkable and functional.
 *
 * The descriptor below uses one TLV type per element (0x01 / 0x02). That is
 * required: the shipped qmi_response_type_v01_ei[] tags both of its fields
 * with QMI_COMMON_TLV_TYPE, so it encodes a single common TLV and
 * find_ei() always resolves it to the first element. That is upstream
 * behaviour for the common response header, not something a consumer can
 * round-trip field by field.
 */

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include <libqrtr.h>

static int checks;
static int failures;

#define CHECK(cond, msg)                                          \
	do {                                                      \
		checks++;                                         \
		if (cond) {                                       \
			printf("ok   - %s\n", msg);               \
		} else {                                          \
			printf("FAIL - %s\n", msg);               \
			failures++;                               \
		}                                                 \
	} while (0)

#define QMI_TEST_MSG_ID 0x0026
#define QMI_TEST_TXN_ID 0x1234
#define QMI_TEST_CODE 0x00badd00
#define QMI_TEST_STATUS 0x5aa5

#define TEST_TLV_CODE 0x01
#define TEST_TLV_STATUS 0x02

struct test_payload {
	uint32_t code;
	uint16_t status;
};

/* Explicit element sizes keep the descriptor independent of the ABI of the
 * test struct: the wire format is fixed by the QMI spec, not by the host. */
static struct qmi_elem_info test_payload_ei[] = {
	{
		.data_type	= QMI_UNSIGNED_4_BYTE,
		.elem_len	= 1,
		.elem_size	= 4,
		.array_type	= NO_ARRAY,
		.tlv_type	= TEST_TLV_CODE,
		.offset		= offsetof(struct test_payload, code),
		.ei_array	= NULL,
	},
	{
		.data_type	= QMI_UNSIGNED_2_BYTE,
		.elem_len	= 1,
		.elem_size	= 2,
		.array_type	= NO_ARRAY,
		.tlv_type	= TEST_TLV_STATUS,
		.offset		= offsetof(struct test_payload, status),
		.ei_array	= NULL,
	},
	{
		.data_type	= QMI_EOTI,
		.elem_len	= 0,
		.elem_size	= 0,
		.array_type	= NO_ARRAY,
		.tlv_type	= QMI_COMMON_TLV_TYPE,
		.offset		= 0,
		.ei_array	= NULL,
	},
};

static void test_qmi_roundtrip(void)
{
	DEFINE_QRTR_PACKET(pkt, 256);
	const struct test_payload sent = {
		.code = QMI_TEST_CODE,
		.status = QMI_TEST_STATUS,
	};
	struct test_payload received = { 0 };
	unsigned int msg_id = 0;
	unsigned int txn_id = 0;
	ssize_t encoded;
	int decoded;

	encoded = qmi_encode_message(&pkt, QMI_RESPONSE, QMI_TEST_MSG_ID,
				     QMI_TEST_TXN_ID, &sent, test_payload_ei);
	CHECK(encoded > 0, "qmi_encode_message() encodes a QMI response");
	CHECK((size_t)encoded == pkt.data_len,
	      "encoded length matches the reported packet length");
	CHECK(pkt.type == QRTR_TYPE_DATA,
	      "encoded packet is marked as QRTR_TYPE_DATA");

	CHECK(qmi_decode_header(&pkt, &msg_id) == 0,
	      "qmi_decode_header() accepts the encoded packet");
	CHECK(msg_id == QMI_TEST_MSG_ID, "decoded header keeps the message id");

	decoded = qmi_decode_message(&received, &txn_id, &pkt, QMI_RESPONSE,
				     QMI_TEST_MSG_ID, test_payload_ei);
	CHECK(decoded >= 0, "qmi_decode_message() decodes the packet");
	CHECK(txn_id == QMI_TEST_TXN_ID, "decoded transaction id round-trips");
	CHECK(received.code == sent.code, "decoded first TLV round-trips");
	CHECK(received.status == sent.status, "decoded second TLV round-trips");
}

static void test_qmi_rejects_invalid_input(void)
{
	DEFINE_QRTR_PACKET(pkt, 256);
	const struct test_payload sent = {
		.code = QMI_TEST_CODE,
		.status = QMI_TEST_STATUS,
	};
	struct test_payload received = { 0 };
	unsigned int msg_id = 0;

	CHECK(qmi_encode_message(&pkt, QMI_RESPONSE, QMI_TEST_MSG_ID,
				 QMI_TEST_TXN_ID, &sent,
				 test_payload_ei) > 0,
	      "re-encode succeeds for the validation cases");

	/* Wrong message type must be rejected, not silently accepted. */
	CHECK(qmi_decode_message(&received, NULL, &pkt, QMI_REQUEST,
				 QMI_TEST_MSG_ID, test_payload_ei) == -EINVAL,
	      "qmi_decode_message() rejects a mismatched message type");

	/* Wrong message id must be rejected as well. */
	CHECK(qmi_decode_message(&received, NULL, &pkt, QMI_RESPONSE,
				 QMI_TEST_MSG_ID + 1,
				 test_payload_ei) == -EINVAL,
	      "qmi_decode_message() rejects a mismatched message id");

	/* A NULL structure is only valid for zero-length messages. */
	CHECK(qmi_encode_message(&pkt, QMI_RESPONSE, QMI_TEST_MSG_ID,
				 QMI_TEST_TXN_ID, NULL,
				 test_payload_ei) == -EINVAL,
	      "qmi_encode_message() rejects NULL for a non-empty message");

	/* A NULL destination must be refused instead of dereferenced. */
	CHECK(qmi_decode_message(NULL, NULL, &pkt, QMI_RESPONSE,
				 QMI_TEST_MSG_ID, test_payload_ei) == -EINVAL,
	      "qmi_decode_message() rejects a NULL output structure");

	/* The header carries its own length; a packet whose data_len disagrees
	 * with it must be refused (truncated / trailing-garbage detection). */
	pkt.data_len += 1;
	CHECK(qmi_decode_header(&pkt, &msg_id) == -EINVAL,
	      "qmi_decode_header() rejects an inconsistent message length");
	pkt.data_len -= 1;
}

static void test_uapi_abi(void)
{
	CHECK(AF_QIPCRTR == 42,
	      "AF_QIPCRTR matches the stable Linux UAPI value");
	CHECK(sizeof(((struct sockaddr_qrtr *)0)->sq_family) == 2,
	      "sockaddr_qrtr family keeps its 16-bit UAPI width");
	CHECK(sizeof(struct sockaddr_qrtr) == 12,
	      "sockaddr_qrtr keeps its stable 12-byte ABI");
	CHECK(offsetof(struct sockaddr_qrtr, sq_node) == 4 &&
	      offsetof(struct sockaddr_qrtr, sq_port) == 8,
	      "sockaddr_qrtr fields keep their stable offsets");
	CHECK(sizeof(struct qrtr_ctrl_pkt) == 20,
	      "qrtr_ctrl_pkt remains packed to its 20-byte wire size");
}

int main(void)
{
	test_qmi_roundtrip();
	test_qmi_rejects_invalid_input();
	test_uapi_abi();

	printf("TEST_PACKAGE_RESULT total=%d passed=%d failed=%d\n", checks,
	       checks - failures, failures);

	return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
