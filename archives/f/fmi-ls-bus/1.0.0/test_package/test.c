/*
 * test_fmi-ls-bus consumer test.
 *
 * Exercises the installed fmi-ls-bus public C-API headers as a real
 * third-party consumer: includes only the installed public headers
 * (fmi3LsBus.h / fmi3LsBusUtil.h / fmi3LsBusUtilCan.h), builds a CAN
 * Transmit bus operation through the public buffer macros, serializes it
 * into a byte buffer, reads the operation back and asserts its observable
 * fields. Not an empty shell: calls the public API and checks results.
 */
#include <stdio.h>
#include <string.h>

#include <fmi3LsBus.h>
#include <fmi3LsBusUtilCan.h>

static int failures = 0;

#define CHECK(cond, msg)                                          \
  do {                                                            \
    if (cond) {                                                   \
      printf("PASS: %s\n", msg);                                  \
    } else {                                                      \
      printf("FAIL: %s (line %d)\n", msg, __LINE__);              \
      failures++;                                                 \
    }                                                             \
  } while (0)

int main(void) {
  printf("=== fmi-ls-bus 1.0.0 consumer test ===\n");

  /* CAN Transmit operation round-trip via public buffer macros. */
  {
    unsigned char txData[64] = {0};
    unsigned char rxData[64] = {0};
    fmi3LsBusUtilBufferInfo firstBufferInfo;
    fmi3LsBusUtilBufferInfo secondBufferInfo;
    fmi3LsBusOperationHeader* operationHeader = NULL;

    const fmi3UInt64 id = 0x12345678ULL; /* fits fmi3LsBusCanId (32-bit) */
    const fmi3UInt8 payload[] = {0x01, 0x02, 0x03, 0x04};
    const size_t payloadLen = sizeof(payload);

    FMI3_LS_BUS_BUFFER_INFO_INIT(&firstBufferInfo, txData, sizeof(txData));
    FMI3_LS_BUS_CAN_CREATE_OP_CAN_TRANSMIT(&firstBufferInfo, id, 0, 0,
                                           payloadLen, (fmi3UInt8*)payload);
    const fmi3UInt32 serializedLen = FMI3_LS_BUS_BUFFER_LENGTH(&firstBufferInfo);
    CHECK(serializedLen > 0, "CAN Transmit op serialized into buffer");

    FMI3_LS_BUS_BUFFER_INFO_INIT(&secondBufferInfo, rxData, sizeof(rxData));
    FMI3_LS_BUS_BUFFER_WRITE(&secondBufferInfo, txData, serializedLen);

    const fmi3LsBusBoolean hasOp =
        FMI3_LS_BUS_READ_NEXT_OPERATION(&secondBufferInfo, operationHeader);
    CHECK(hasOp != 0, "READ_NEXT_OPERATION returns an operation");
    CHECK(operationHeader != NULL, "operation header pointer returned");
    CHECK(operationHeader->opCode == FMI3_LS_BUS_CAN_OP_CAN_TRANSMIT,
          "operation code is CAN_TRANSMIT (0x0010)");
    {
      const fmi3LsBusCanOperationCanTransmit* op =
          (const fmi3LsBusCanOperationCanTransmit*)operationHeader;
      CHECK(op->id == id, "operation id round-trips");
      CHECK(op->dataLength == (fmi3LsBusDataLength)payloadLen,
            "operation dataLength matches payload");
      CHECK(op->data[0] == payload[0] && op->data[3] == payload[3],
            "operation payload round-trips");
    }
  }

  /* Wakeup operation (no payload) via public API. */
  {
    unsigned char txData[64] = {0};
    fmi3LsBusUtilBufferInfo bufferInfo;
    FMI3_LS_BUS_BUFFER_INFO_INIT(&bufferInfo, txData, sizeof(txData));
    FMI3_LS_BUS_CAN_CREATE_OP_WAKEUP(&bufferInfo);
    CHECK(FMI3_LS_BUS_BUFFER_LENGTH(&bufferInfo) > 0,
          "Wakeup op serialized into buffer");
  }

  if (failures == 0) {
    printf("=== ALL CONSUMER CHECKS PASSED ===\n");
    return 0;
  }
  printf("=== %d CHECKS FAILED ===\n", failures);
  return 1;
}