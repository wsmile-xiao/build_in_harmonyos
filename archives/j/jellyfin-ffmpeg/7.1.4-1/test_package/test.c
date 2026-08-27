#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/frame.h>
#include <libavutil/imgutils.h>
#include <libavfilter/avfilter.h>
#include <stdio.h>
#include <string.h>
#define W 320
#define H 240
static int encode_one(const char *enc_name) {
    const AVCodec *codec = avcodec_find_encoder_by_name(enc_name);
    if (!codec) return -1;
    AVCodecContext *ctx = avcodec_alloc_context3(codec);
    if (!ctx) return -1;
    ctx->width = W; ctx->height = H; ctx->pix_fmt = AV_PIX_FMT_YUV420P;
    ctx->time_base = (AVRational){1, 25}; ctx->framerate = (AVRational){25, 1};
    ctx->bit_rate = 200000; ctx->max_b_frames = 0; ctx->gop_size = 1;
    if (avcodec_open2(ctx, codec, NULL) < 0) { avcodec_free_context(&ctx); return -1; }
    AVFrame *frame = av_frame_alloc();
    if (!frame) { avcodec_free_context(&ctx); return -1; }
    frame->format = ctx->pix_fmt; frame->width = W; frame->height = H;
    if (av_frame_get_buffer(frame, 0) < 0) { av_frame_free(&frame); avcodec_free_context(&ctx); return -1; }
    for (int y = 0; y < H; y++) memset(frame->data[0] + y * frame->linesize[0], y & 0xFF, W);
    memset(frame->data[1], 0x80, (H/2) * frame->linesize[1]);
    memset(frame->data[2], 0x40, (H/2) * frame->linesize[2]);
    frame->pts = 0;
    int total = 0;
    AVPacket *pkt = av_packet_alloc();
    if (!pkt) { av_frame_free(&frame); avcodec_free_context(&ctx); return -1; }
    if (avcodec_send_frame(ctx, frame) >= 0 && avcodec_send_frame(ctx, NULL) >= 0)
        while (avcodec_receive_packet(ctx, pkt) >= 0) { total += pkt->size; av_packet_unref(pkt); }
    av_packet_free(&pkt); av_frame_free(&frame); avcodec_free_context(&ctx);
    return total;
}
int main(void) {
    int rc = 0;
    printf("jellyfin-ffmpeg: libavcodec %u.%u.%u\n", AV_VERSION_MAJOR(avcodec_version()), AV_VERSION_MINOR(avcodec_version()), AV_VERSION_MICRO(avcodec_version()));
    int n = encode_one("mpeg4");
    if (n <= 0) return 1;
    printf("  mpeg4: %d bytes OK\n", n);
    const char *ext[] = {"libopenh264", "libvpx", "libopus", "libmp3lame", "libfdk_aac", "libvorbis"};
    for (unsigned i = 0; i < sizeof(ext)/sizeof(ext[0]); i++) {
        if (!avcodec_find_encoder_by_name(ext[i])) { fprintf(stderr, "MISSING: %s\n", ext[i]); rc = 1; }
        else printf("  %-12s present\n", ext[i]);
    }
    n = encode_one("libopenh264");
    if (n <= 0) rc = 1; else printf("  libopenh264: %d bytes OK\n", n);
    { int found = 0; void *opaque = NULL; const char *name;
      while ((name = avio_enum_protocols(&opaque, 0)) != NULL) { if (strcmp(name, "https") == 0) { found = 1; break; } }
      if (!found) rc = 1; else printf("  https: OK\n"); }
    if (!avfilter_get_by_name("drawtext")) rc = 1; else printf("  drawtext: OK\n");
    if (!avfilter_get_by_name("zscale")) rc = 1; else printf("  zscale: OK\n");
    if (!avcodec_find_decoder_by_name("libdav1d")) rc = 1; else printf("  libdav1d: OK\n");
    return rc;
}
