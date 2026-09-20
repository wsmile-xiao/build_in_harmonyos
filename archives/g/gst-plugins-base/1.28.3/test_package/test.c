#include <gst/gst.h>
#include <gst/pbutils/pbutils.h>
#include <gst/audio/audio.h>
#include <gst/video/video.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    const gchar *version = gst_version_string();
    printf("gstreamer version: %s\n", version);
    g_assert(version != NULL);

    /* pbutils library from gst-plugins-base */
    gst_pb_utils_init();

    /* audio library from gst-plugins-base */
    const GstAudioFormatInfo *fmt_info = gst_audio_format_get_info(GST_AUDIO_FORMAT_S16);
    g_assert(fmt_info != NULL);
    printf("audio format S16 depth: %d\n", fmt_info->depth);

    /* video library from gst-plugins-base */
    const GstVideoFormatInfo *vfmt_info = gst_video_format_get_info(GST_VIDEO_FORMAT_I420);
    g_assert(vfmt_info != NULL);
    printf("video format I420 bits: %d\n", vfmt_info->bits);

    printf("gst-plugins-base test: PASS\n");
    return 0;
}
