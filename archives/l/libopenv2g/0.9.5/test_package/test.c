#include <stdint.h>
#include <stdio.h>

#include "BitInputStream.h"
#include "BitOutputStream.h"
#include "appHandEXIDatatypes.h"
#include "appHandEXIDatatypesDecoder.h"
#include "appHandEXIDatatypesEncoder.h"
#include "v2gtp.h"

#define CHECK(condition, label) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "CHECK-FAIL: %s\n", label); \
            return 1; \
        } \
        printf("CHECK-OK: %s\n", label); \
    } while (0)

static int test_bit_stream(void)
{
    uint8_t bytes[8] = {0};
    size_t write_pos = 0;
    bitstream_t output = {
        sizeof(bytes), bytes, &write_pos, 0, BITS_IN_BYTE
    };
    uint32_t value = 0;

    CHECK(writeBits(&output, 3, 5) == 0, "write three bits");
    CHECK(writeBits(&output, 8, 0xa5) == 0, "write one byte");
    CHECK(flush(&output) == 0 && write_pos == 2, "flush bit stream");

    size_t read_pos = 0;
    bitstream_t input = {write_pos, bytes, &read_pos, 0, 0};
    CHECK(readBits(&input, 3, &value) == 0 && value == 5,
          "read three bits");
    CHECK(readBits(&input, 8, &value) == 0 && value == 0xa5,
          "read one byte");
    return 0;
}

static int test_v2gtp_header(void)
{
    uint8_t packet[16] = {0};
    uint32_t payload_length = 0;

    CHECK(write_v2gtpHeader(packet, 4, V2GTP_EXI_TYPE) == 0,
          "write V2GTP header");
    CHECK(packet[0] == V2GTP_VERSION && packet[1] == V2GTP_VERSION_INV,
          "check V2GTP version bytes");
    CHECK(read_v2gtpHeader(packet, &payload_length) == 0 &&
              payload_length == 4,
          "read V2GTP payload length");
    return 0;
}

static int test_app_handshake_roundtrip(void)
{
    uint8_t bytes[512] = {0};
    size_t position = 0;
    bitstream_t stream = {
        sizeof(bytes), bytes, &position, 0, BITS_IN_BYTE
    };
    struct appHandEXIDocument request;
    struct appHandEXIDocument decoded;

    init_appHandEXIDocument(&request);
    init_appHandEXIDocument(&decoded);
    request.supportedAppProtocolReq_isUsed = 1;
    request.supportedAppProtocolReq.AppProtocol.arrayLen = 1;
    request.supportedAppProtocolReq.AppProtocol.array[0]
        .ProtocolNamespace.charactersLen = 4;
    request.supportedAppProtocolReq.AppProtocol.array[0]
        .ProtocolNamespace.characters[0] = 116;
    request.supportedAppProtocolReq.AppProtocol.array[0]
        .ProtocolNamespace.characters[1] = 101;
    request.supportedAppProtocolReq.AppProtocol.array[0]
        .ProtocolNamespace.characters[2] = 115;
    request.supportedAppProtocolReq.AppProtocol.array[0]
        .ProtocolNamespace.characters[3] = 116;
    request.supportedAppProtocolReq.AppProtocol.array[0].VersionNumberMajor = 1;
    request.supportedAppProtocolReq.AppProtocol.array[0].VersionNumberMinor = 0;
    request.supportedAppProtocolReq.AppProtocol.array[0].SchemaID = 7;
    request.supportedAppProtocolReq.AppProtocol.array[0].Priority = 1;

    CHECK(encode_appHandExiDocument(&stream, &request) == 0,
          "encode application handshake");
    CHECK(position > 0, "application handshake has encoded bytes");

    stream.size = position;
    position = 0;
    stream.pos = &position;
    stream.buffer = 0;
    stream.capacity = 0;
    CHECK(decode_appHandExiDocument(&stream, &decoded) == 0,
          "decode application handshake");
    CHECK(decoded.supportedAppProtocolReq_isUsed == 1 &&
              decoded.supportedAppProtocolReq.AppProtocol.arrayLen == 1,
          "round-trip application protocol count");
    CHECK(decoded.supportedAppProtocolReq.AppProtocol.array[0].SchemaID == 7,
          "round-trip application protocol schema ID");
    return 0;
}

int main(void)
{
    if (test_bit_stream() != 0 ||
        test_v2gtp_header() != 0 ||
        test_app_handshake_roundtrip() != 0) {
        return 1;
    }
    puts("libopenv2g consumer tests passed");
    return 0;
}
