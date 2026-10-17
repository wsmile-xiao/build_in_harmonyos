#include <stdio.h>
#include <string.h>

#include <vorbis/codec.h>
#include <vorbis/vorbisenc.h>
#include <vorbis/vorbisfile.h>

int main(void)
{
    const char *version = vorbis_version_string();
    int (*clear_fn)(OggVorbis_File *) = ov_clear;
    vorbis_info info;
    vorbis_comment comment;
    int rc;

    if (version == NULL || strstr(version, "Vorbis") == NULL) {
        fprintf(stderr, "unexpected Vorbis version string\n");
        return 1;
    }

    vorbis_info_init(&info);
    rc = vorbis_encode_init_vbr(&info, 2, 44100, 0.4f);
    if (rc != 0) {
        fprintf(stderr, "vorbis_encode_init_vbr failed: %d\n", rc);
        vorbis_info_clear(&info);
        return 2;
    }

    vorbis_comment_init(&comment);
    vorbis_comment_add_tag(&comment, "ENCODER", "conan-test-package");
    if (comment.comments != 1 || comment.user_comments == NULL) {
        fprintf(stderr, "vorbis_comment_add_tag failed\n");
        vorbis_comment_clear(&comment);
        vorbis_info_clear(&info);
        return 3;
    }

    if (clear_fn == NULL) {
        fprintf(stderr, "vorbisfile symbol not linked\n");
        vorbis_comment_clear(&comment);
        vorbis_info_clear(&info);
        return 4;
    }

    printf("libvorbis consumer smoke passed: %s\n", version);
    vorbis_comment_clear(&comment);
    vorbis_info_clear(&info);
    return 0;
}
