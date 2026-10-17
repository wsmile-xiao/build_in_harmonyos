#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "avtp.h"
#include "avtp_aaf.h"
#include "avtp_crf.h"
#include "avtp_cvf.h"
#include "avtp_ieciidc.h"
#include "avtp_rvf.h"

#define REQUIRE(condition)                                                   \
    do {                                                                      \
        if (!(condition)) {                                                   \
            fprintf(stderr, "FAIL: %s (%s:%d)\n", #condition, __FILE__,   \
                    __LINE__);                                               \
            return 1;                                                         \
        }                                                                     \
    } while (0)

int main(void)
{
    uint32_t common_value = 0;
    uint64_t value = 0;
    struct avtp_common_pdu common;
    struct avtp_stream_pdu stream;
    struct avtp_crf_pdu crf;

    memset(&common, 0, sizeof(common));
    REQUIRE(avtp_pdu_set(&common, AVTP_FIELD_SUBTYPE, AVTP_SUBTYPE_AAF) == 0);
    REQUIRE(avtp_pdu_get(&common, AVTP_FIELD_SUBTYPE, &common_value) == 0);
    REQUIRE(common_value == AVTP_SUBTYPE_AAF);

    REQUIRE(avtp_aaf_pdu_init(&stream) == 0);
    REQUIRE(avtp_aaf_pdu_get(&stream, AVTP_AAF_FIELD_SV, &value) == 0);
    REQUIRE(value == 1);
    REQUIRE(avtp_aaf_pdu_set(&stream, AVTP_AAF_FIELD_STREAM_ID,
                             UINT64_C(0x1122334455667788)) == 0);
    REQUIRE(avtp_aaf_pdu_get(&stream, AVTP_AAF_FIELD_STREAM_ID, &value) == 0);
    REQUIRE(value == UINT64_C(0x1122334455667788));

    REQUIRE(avtp_crf_pdu_init(&crf) == 0);
    REQUIRE(avtp_crf_pdu_get(&crf, AVTP_CRF_FIELD_SV, &value) == 0);
    REQUIRE(value == 1);
    REQUIRE(avtp_crf_pdu_set(&crf, AVTP_CRF_FIELD_BASE_FREQ, 48000) == 0);
    REQUIRE(avtp_crf_pdu_get(&crf, AVTP_CRF_FIELD_BASE_FREQ, &value) == 0);
    REQUIRE(value == 48000);

    REQUIRE(avtp_cvf_pdu_init(&stream, AVTP_CVF_FORMAT_SUBTYPE_H264) == 0);
    REQUIRE(avtp_cvf_pdu_get(&stream, AVTP_CVF_FIELD_FORMAT, &value) == 0);
    REQUIRE(value == AVTP_CVF_FORMAT_RFC);
    REQUIRE(avtp_cvf_pdu_get(&stream, AVTP_CVF_FIELD_FORMAT_SUBTYPE, &value) == 0);
    REQUIRE(value == AVTP_CVF_FORMAT_SUBTYPE_H264);

    REQUIRE(avtp_rvf_pdu_init(&stream) == 0);
    REQUIRE(avtp_rvf_pdu_get(&stream, AVTP_RVF_FIELD_SV, &value) == 0);
    REQUIRE(value == 1);
    REQUIRE(avtp_rvf_pdu_set(&stream, AVTP_RVF_FIELD_ACTIVE_PIXELS, 1920) == 0);
    REQUIRE(avtp_rvf_pdu_get(&stream, AVTP_RVF_FIELD_ACTIVE_PIXELS, &value) == 0);
    REQUIRE(value == 1920);

    REQUIRE(avtp_ieciidc_pdu_init(&stream, AVTP_IECIIDC_TAG_CIP) == 0);
    REQUIRE(avtp_ieciidc_pdu_get(&stream, AVTP_IECIIDC_FIELD_TAG, &value) == 0);
    REQUIRE(value == AVTP_IECIIDC_TAG_CIP);
    REQUIRE(avtp_ieciidc_pdu_set(&stream, AVTP_IECIIDC_FIELD_CHANNEL, 2) == 0);
    REQUIRE(avtp_ieciidc_pdu_get(&stream, AVTP_IECIIDC_FIELD_CHANNEL, &value) == 0);
    REQUIRE(value == 2);

    puts("libavtp consumer API checks passed (32 assertions)");
    return 0;
}
