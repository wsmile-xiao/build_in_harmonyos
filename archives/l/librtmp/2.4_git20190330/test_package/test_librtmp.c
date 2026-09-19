/* test_librtmp.c — librtmp/2.4_git20190330 consumer test package.
 *
 * Exercises the packaged library through its public API and asserts real
 * behavior: URL parsing (RTMP_ParseURL), AMF encode/decode round trips
 * (AMF_EncodeInt32/AMF_DecodeInt32, AMF_EncodeString/AMF_DecodeString,
 * AMF_EncodeNumber/AMF_DecodeNumber, AMF_EncodeBoolean/AMF_DecodeBoolean),
 * logging level control (RTMP_LogSetLevel/RTMP_LogGetLevel) and the RTMP
 * object lifecycle (RTMP_Init/RTMP_Close with default state checks).
 * No network access is required.
 */
#include <stdio.h>
#include <string.h>

#include "log.h"
#include "rtmp.h"

static int run_checks = 0;
static int failed_checks = 0;

#define CHECK(cond, msg) \
  do { \
    run_checks++; \
    if (!(cond)) { \
      fprintf(stderr, "FAIL: %s\n", (msg)); \
      failed_checks++; \
    } \
  } while (0)

static void
test_log_level(void)
{
  RTMP_LogSetLevel(RTMP_LOGWARNING);
  CHECK(RTMP_LogGetLevel() == RTMP_LOGWARNING, "log level round trip (WARNING)");
  RTMP_LogSetLevel(RTMP_LOGDEBUG2);
  CHECK(RTMP_LogGetLevel() == RTMP_LOGDEBUG2, "log level round trip (DEBUG2)");
  RTMP_LogSetLevel(RTMP_LOGERROR);
  CHECK(RTMP_LogGetLevel() == RTMP_LOGERROR, "log level round trip (ERROR)");
}

static void
test_rtmp_lifecycle(void)
{
  RTMP r;

  RTMP_Init(&r);
  CHECK(r.m_sb.sb_socket == -1, "RTMP_Init sets no socket (sb_socket == -1)");
  CHECK(r.m_inChunkSize == RTMP_DEFAULT_CHUNKSIZE,
        "RTMP_Init sets the default chunk size");
  CHECK(r.m_nBufferMS == 30000, "RTMP_Init sets the default buffer time");
  RTMP_Close(&r);
  CHECK(r.m_sb.sb_socket == -1, "RTMP_Close is safe on a non-connected object");
}

static void
test_parseurl(void)
{
  AVal host = { NULL, 0 }, playpath = { NULL, 0 }, app = { NULL, 0 };
  unsigned int port = 0;
  int protocol = -1;

  CHECK(RTMP_ParseURL("rtmp://example.com:1935/live/stream", &protocol,
                      &host, &port, &playpath, &app) == 1,
        "RTMP_ParseURL accepts a canonical rtmp URL");
  CHECK(protocol == RTMP_PROTOCOL_RTMP, "parsed protocol is RTMP");
  CHECK(port == 1935, "parsed explicit port 1935");
  CHECK(host.av_len == 11 && memcmp(host.av_val, "example.com", 11) == 0,
        "parsed host is example.com");
  CHECK(app.av_len == 4 && memcmp(app.av_val, "live", 4) == 0,
        "parsed app is live");
  CHECK(playpath.av_len == 6 && memcmp(playpath.av_val, "stream", 6) == 0,
        "parsed playpath is stream");

  protocol = -1;
  port = 0;
  CHECK(RTMP_ParseURL("rtmpe://media.example.org:8080/vod2/mp4:file.mp4",
                      &protocol, &host, &port, &playpath, &app) == 1,
        "RTMP_ParseURL accepts an rtmpe URL");
  CHECK(protocol == RTMP_PROTOCOL_RTMPE, "parsed protocol is RTMPE");
  CHECK(port == 8080, "parsed explicit port 8080");
  CHECK(host.av_len == 17 && memcmp(host.av_val, "media.example.org", 17) == 0,
        "parsed host is media.example.org");
  CHECK(app.av_len == 4 && memcmp(app.av_val, "vod2", 4) == 0,
        "parsed app is vod2");
  CHECK(playpath.av_len == 12 && memcmp(playpath.av_val, "mp4:file.mp4", 12) == 0,
        "parsed playpath is mp4:file.mp4");

  CHECK(RTMP_ParseURL("not-a-url", &protocol, &host, &port,
                      &playpath, &app) == 0,
        "RTMP_ParseURL rejects a URL without ://");
  CHECK(RTMP_ParseURL("rtmp://", &protocol, &host, &port,
                      &playpath, &app) == 0,
        "RTMP_ParseURL rejects a URL without a host");
}

static void
test_amf_integer(void)
{
  char buf[16];
  char *end = buf + sizeof(buf);

  CHECK(AMF_EncodeInt32(buf, end, 0x11223344) == buf + 4,
        "AMF_EncodeInt32 returns one past four written bytes");
  CHECK(AMF_DecodeInt32(buf) == 0x11223344,
        "AMF_DecodeInt32 round trip of 0x11223344");

  CHECK(AMF_EncodeInt24(buf, end, 0x445566) == buf + 3,
        "AMF_EncodeInt24 returns one past three written bytes");
  CHECK(AMF_DecodeInt24(buf) == 0x445566,
        "AMF_DecodeInt24 round trip of 0x445566");

  CHECK(AMF_EncodeInt16(buf, end, 0x5566) == buf + 2,
        "AMF_EncodeInt16 returns one past two written bytes");
  CHECK(AMF_DecodeInt16(buf) == 0x5566,
        "AMF_DecodeInt16 round trip of 0x5566");
}

static void
test_amf_number_boolean_string(void)
{
  char buf[64];
  char *end = buf + sizeof(buf);
  char *p;
  AVal out;

  p = AMF_EncodeNumber(buf, end, 3.5);
  CHECK(p == buf + 9, "AMF_EncodeNumber writes marker plus eight bytes");
  CHECK(AMF_DecodeNumber(buf + 1) == 3.5, "AMF number round trip of 3.5");

  p = AMF_EncodeBoolean(buf, end, 1);
  CHECK(p == buf + 2, "AMF_EncodeBoolean writes marker plus one byte");
  CHECK(AMF_DecodeBoolean(buf) == 1, "AMF boolean round trip of true");

  AVal str = AVC("RTMP");
  p = AMF_EncodeString(buf, end, &str);
  CHECK(p == buf + 7, "AMF_EncodeString writes marker, length and bytes");
  AMF_DecodeString(buf + 1, &out);
  CHECK(out.av_len == 4 && memcmp(out.av_val, "RTMP", 4) == 0,
        "AMF string round trip of RTMP");

  /* RTMP protocol constant sanity (defines exercised by every consumer) */
  CHECK(RTMP_PROTOCOL_RTMP == 0 && RTMP_PROTOCOL_RTMPE == RTMP_FEATURE_ENC
        && RTMP_PROTOCOL_RTMPT == RTMP_FEATURE_HTTP,
        "RTMP protocol constants keep upstream values");
}

int
main(void)
{
  test_log_level();
  test_rtmp_lifecycle();
  test_parseurl();
  test_amf_integer();
  test_amf_number_boolean_string();

  printf("librtmp consumer test: %d checks, %d failures\n",
         run_checks, failed_checks);
  return failed_checks == 0 ? 0 : 1;
}
