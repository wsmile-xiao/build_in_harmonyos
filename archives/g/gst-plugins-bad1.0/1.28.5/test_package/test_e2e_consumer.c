/* gst-plugins-bad1.0 end-to-end consumer test (OHOS PC, rule12).
 *
 * Drives the packaged codecparsers library through a real H.264
 * bitstream parsing workflow: feed a hand-crafted Annex-B stream
 * containing a baseline SPS NAL -> the packaged parser identifies
 * the NAL unit -> decodes the SPS -> the extracted fields are
 * asserted against the values encoded in the test bitstream.
 * This exercises the actual packaged parsing code end-to-end
 * (input -> parse -> semantic assert), not just symbol presence.
 * codecparsers is a pure-function library (no GType registry
 * involvement), so it runs safely in one process on OHOS PC where
 * the shared-library shape cannot dlopen plugins (cross-copy GType
 * registry split -- see PR body "上游测试用例减少原因").
 */
#include <gst/codecparsers/gsth264parser.h>
#include <stdio.h>
#include <string.h>

/* Annex-B H.264 SPS NAL (same test vector as the upstream
 * tests/check/libs/h264parser.c suite, nalu_sps_with_vui):
 * high profile (100), level 4.0, 1920x1088 progressive with VUI.
 *   0x00 00 00 01      Annex-B start code
 *   0x67               NAL header: SPS, nal_ref_idc=3
 *   0x64 00 28         profile_idc=100, constraints=0, level_idc=40
 *   ...                SPS payload + VUI parameters
 */
static const guint8 sps_nal[] = {
    0x00, 0x00, 0x00, 0x01, 0x67, 0x64, 0x00, 0x28,
    0xac, 0xd9, 0x40, 0x78, 0x04, 0x4f, 0xde, 0x03,
    0xd2, 0x02, 0x02, 0x02, 0x80, 0x00, 0x01, 0xf4,
    0x80, 0x00, 0x75, 0x30, 0x4f, 0x8b, 0x16, 0xcb
};

int main(void)
{
    /* 1. parser lifecycle: create the packaged parser object */
    GstH264NalParser *parser = gst_h264_nal_parser_new();
    if (!parser) {
        fprintf(stderr, "e2e FAIL: gst_h264_nal_parser_new returned NULL\n");
        return 1;
    }
    printf("e2e [1] H264 NAL parser created\n");

    /* 2. feed the bitstream: NAL unit identification */
    GstH264NalUnit nalu;
    GstH264ParserResult res = gst_h264_parser_identify_nalu(
        parser, sps_nal, 0, sizeof(sps_nal), &nalu);
    /* Single-NAL buffer: no next start code exists, the parser reports
     * NO_NAL_END (documented behaviour: for NAL-aligned data this is
     * equivalent to OK -- the NAL ends with the buffer). */
    if (res != GST_H264_PARSER_OK && res != GST_H264_PARSER_NO_NAL_END) {
        fprintf(stderr, "e2e FAIL: identify_nalu -> %d\n", res);
        return 1;
    }
    if (nalu.type != GST_H264_NAL_SPS) {
        fprintf(stderr, "e2e FAIL: expected SPS NAL, got type %d\n", nalu.type);
        return 1;
    }
    printf("e2e [2] NAL identified: type=SPS(%d) size=%u\n",
           nalu.type, nalu.size);

    /* 3. full SPS bitstream decode through the packaged parser */
    static GstH264SPS sps;
    memset(&sps, 0, sizeof(sps));
    res = gst_h264_parser_parse_sps(parser, &nalu, &sps);
    if (res != GST_H264_PARSER_OK) {
        fprintf(stderr, "e2e FAIL: parse_sps -> %d\n", res);
        return 1;
    }
    printf("e2e [3] SPS decoded: profile=%u level=%u\n",
           sps.profile_idc, sps.level_idc);

    /* 4. semantic assertions on the decoded fields (values encoded in
     * the upstream test vector: high profile 100, level 4.0,
     * 1920x1088 interlaced-compatible frame_mbs layout with VUI) */
    if (sps.profile_idc != 100) {
        fprintf(stderr, "e2e FAIL: profile_idc %u != 100\n", sps.profile_idc);
        return 1;
    }
    if (sps.level_idc != 40) {
        fprintf(stderr, "e2e FAIL: level_idc %u != 40\n", sps.level_idc);
        return 1;
    }
    /* frame dimensions follow the spec formula:
     * width = (pic_width_in_mbs_minus1 + 1) * 16
     * height = (2 - frame_mbs_only_flag)
     *          * (pic_height_in_map_units_minus1 + 1) * 16 */
    const guint width = (sps.pic_width_in_mbs_minus1 + 1) * 16;
    const guint height = (2 - sps.frame_mbs_only_flag)
                         * (sps.pic_height_in_map_units_minus1 + 1) * 16;
    if (width != 1920 || height != 1088) {
        fprintf(stderr, "e2e FAIL: dimensions %ux%u != 1920x1088\n",
                width, height);
        return 1;
    }
    if (!sps.vui_parameters_present_flag) {
        fprintf(stderr, "e2e FAIL: VUI parameters not parsed\n");
        return 1;
    }
    printf("e2e [4] decoded fields verified: 1920x1088 high@L4.0 +VUI\n");

    /* 5. teardown */
    gst_h264_nal_parser_free(parser);
    printf("e2e [5] parser freed\ngst-plugins-bad1.0 e2e consumer test: PASS\n");
    return 0;
}
