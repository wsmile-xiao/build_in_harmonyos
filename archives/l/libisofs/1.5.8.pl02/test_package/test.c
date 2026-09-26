/*
 * libisofs 1.5.8.pl02 consumer test — real ISO 9660 image generation
 * and read-back verification.
 *
 * Flow (all through the public libisofs API, no stubs):
 *   1. init + runtime version compatibility check
 *   2. build an in-memory tree: sub-directory, regular file from a memory
 *      stream (deterministic content), symlink, special (fifo) node,
 *      with explicit mtime/permissions on the file node
 *   3. attach an AAIP xattr to the file node (system adapter =
 *      aaip-os-linux.c on OHOS, the __linux__ code path selected at
 *      build time — HarmonyOS-specific coverage)
 *   4. write the image via burn_source->read_xt into a file under the
 *      test build directory (writable, never a hardcoded /tmp)
 *   5. import the image back with iso_data_source_new_from_file +
 *      iso_image_import and verify: block count, volume id, tree shape,
 *      file size and full content, mtime/permissions round trip,
 *      symlink destination, special node type, AAIP xattr round trip
 *   6. emit HMBS_TEST_PACKAGE_RESULT JSON marker
 *
 * Any failed check exits non-zero immediately (no fake pass).
 */

#define _GNU_SOURCE 1

/* The application provides no libburn.h: make the burn_source struct
 * definition available (same pattern as upstream demo/demo.c). */
#define LIBISOFS_WITHOUT_LIBBURN yes

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#include <libisofs/libisofs.h>

#define CHECK(cond, msg)                                       \
    do {                                                       \
        checks_total++;                                        \
        if (cond) {                                            \
            checks_passed++;                                   \
            printf("[PASS] %s\n", msg);                        \
        } else {                                               \
            printf("[FAIL] %s (line %d)\n", msg, __LINE__);    \
            fflush(stdout);                                    \
            exit(1);                                           \
        }                                                      \
    } while (0)

static int checks_total = 0;
static int checks_passed = 0;

static const char *VOLUME_ID = "HMBS_TEST_VOL";

/* deterministic file content: 8192 bytes 'A'..'P' repeating */
#define FILE_DATA_SIZE 8192
static unsigned char file_data[FILE_DATA_SIZE];

static void fill_file_data(void)
{
    for (size_t i = 0; i < FILE_DATA_SIZE; i++)
        file_data[i] = (unsigned char)('A' + (i % 16));
}

#define FIXED_MTIME ((time_t)1725000000) /* 2024-08-30T06:40:00Z */

/* iso_memory_stream_new takes ownership of buf and free()s it, so it
 * must receive a malloc()ed copy, never the static array. */
static int write_image(const char *path)
{
    int result;
    IsoImage *image = NULL;
    IsoDir *root, *sub;
    IsoStream *stream = NULL;
    IsoFile *file;
    IsoWriteOpts *opts = NULL;
    struct burn_source *burn_src = NULL;
    FILE *fp = NULL;
    unsigned char buf[2048];
    unsigned char *owned = NULL;
    int blocks = 0;

    result = iso_init();
    if (result < 0) {
        printf("iso_init failed: %d\n", result);
        goto fail;
    }
    iso_set_msgs_severities("NEVER", "FATAL", "");

    result = iso_image_new(VOLUME_ID, &image);
    if (result < 0) {
        printf("iso_image_new failed: %d\n", result);
        goto fail;
    }
    root = iso_image_get_root(image);

    result = iso_tree_add_new_dir(root, "data", &sub);
    if (result < 0) {
        printf("iso_tree_add_new_dir failed: %d\n", result);
        goto fail;
    }

    owned = malloc(FILE_DATA_SIZE);
    if (owned == NULL)
        goto fail;
    memcpy(owned, file_data, FILE_DATA_SIZE);
    result = iso_memory_stream_new(owned, FILE_DATA_SIZE, &stream);
    if (result < 0) {
        printf("iso_memory_stream_new failed: %d\n", result);
        free(owned);
        goto fail;
    }
    /* stream owns <owned> from here on */

    result = iso_tree_add_new_file(sub, "hello.txt", stream, &file);
    if (result < 0) {
        printf("iso_tree_add_new_file failed: %d\n", result);
        goto fail;
    }
    iso_node_set_mtime((IsoNode *)file, FIXED_MTIME);
    iso_node_set_permissions((IsoNode *)file,
                             S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);

    result = iso_tree_add_new_symlink(root, "readme", "data/hello.txt", NULL);
    if (result < 0) {
        printf("iso_tree_add_new_symlink failed: %d\n", result);
        goto fail;
    }

    /* special (fifo) node — Rock Ridge only, metadata only */
    result = iso_tree_add_new_special(root, "event-pipe", S_IFIFO, 0, NULL);
    if (result < 0) {
        printf("iso_tree_add_new_special failed: %d\n", result);
        goto fail;
    }

    /* AAIP xattr on the file node: exercises aaip-os-linux.c on OHOS.
     * flag bit1 = merge (set this one xattr, keep any others). */
    {
        char *names[1];
        size_t value_lengths[1];
        char *values[1];
        names[0] = (char *)"user.hmbs_test";
        values[0] = (char *)"ohos-aarch64";
        value_lengths[0] = strlen(values[0]);
        result = iso_node_set_attrs((IsoNode *)file, 1, names,
                                    value_lengths, values, 2);
        if (result < 0) {
            printf("iso_node_set_attrs failed: %d\n", result);
            goto fail;
        }
    }

    /* profile 1 = Rock Ridge + ISO level 3; enable AAIP recording */
    result = iso_write_opts_new(&opts, 1);
    if (result < 0) {
        printf("iso_write_opts_new failed: %d\n", result);
        goto fail;
    }
    result = iso_write_opts_set_aaip(opts, 1);
    if (result < 0) {
        printf("iso_write_opts_set_aaip failed: %d\n", result);
        goto fail;
    }

    result = iso_image_create_burn_source(image, opts, &burn_src);
    iso_write_opts_free(opts);
    if (result < 0) {
        printf("iso_image_create_burn_source failed: %d\n", result);
        goto fail;
    }

    fp = fopen(path, "wb");
    if (fp == NULL) {
        printf("fopen(%s) failed: %s\n", path, strerror(errno));
        goto fail;
    }

    while (burn_src->read_xt(burn_src, buf, 2048) == 2048) {
        if (fwrite(buf, 1, 2048, fp) != 2048) {
            printf("fwrite failed: %s\n", strerror(errno));
            goto fail;
        }
        blocks++;
    }
    fclose(fp);
    fp = NULL;

    burn_src->free_data(burn_src);
    free(burn_src);
    iso_image_unref(image);
    iso_finish();
    printf("image written: %d blocks (%d bytes)\n", blocks, blocks * 2048);
    return blocks > 0 ? blocks : -1;

fail:
    if (fp != NULL)
        fclose(fp);
    if (burn_src != NULL) {
        burn_src->free_data(burn_src);
        free(burn_src);
    }
    if (image != NULL)
        iso_image_unref(image);
    iso_finish();
    return -1;
}

static int verify_image(const char *path, int expected_blocks)
{
    int result;
    IsoImage *image = NULL;
    IsoDataSource *src = NULL;
    IsoReadOpts *ropts = NULL;
    IsoReadImageFeatures *features = NULL;
    IsoNode *node = NULL;
    IsoFile *file;
    IsoStream *stream;

    result = iso_init();
    if (result < 0)
        return -1;
    iso_set_msgs_severities("NEVER", "FATAL", "");

    result = iso_data_source_new_from_file(path, &src);
    if (result < 0) {
        printf("iso_data_source_new_from_file failed: %d\n", result);
        goto fail;
    }

    result = iso_image_new(VOLUME_ID, &image);
    if (result < 0) {
        printf("iso_image_new failed: %d\n", result);
        goto fail;
    }

    result = iso_read_opts_new(&ropts, 0);
    if (result < 0) {
        printf("iso_read_opts_new failed: %d\n", result);
        goto fail;
    }
    /* iso_read_opts_new() defaults noaaip=1: loading AAIP must be enabled
     * explicitly or imported nodes lose their xattr. */
    result = iso_read_opts_set_no_aaip(ropts, 0);
    if (result < 0) {
        printf("iso_read_opts_set_no_aaip failed: %d\n", result);
        goto fail;
    }

    result = iso_image_import(image, src, ropts, &features);
    iso_read_opts_free(ropts);
    ropts = NULL;
    iso_data_source_unref(src);
    src = NULL;
    if (result < 0) {
        printf("iso_image_import failed: %d\n", result);
        goto fail;
    }

    /* 1. image size matches the block count written */
    uint32_t import_size = iso_read_image_features_get_size(features);
    CHECK(import_size == (uint32_t)expected_blocks,
          "imported image size matches written block count");

    /* 2. volume id */
    const char *vid = iso_image_get_volume_id(image);
    CHECK(vid != NULL && strcmp(vid, VOLUME_ID) == 0,
          "volume id round trip");

    /* 3. tree shape: /data/hello.txt */
    result = iso_tree_path_to_node(image, "/data/hello.txt", &node);
    CHECK(result == 1 && node != NULL, "path /data/hello.txt resolves");
    if (node != NULL) {
        CHECK(iso_node_get_type(node) == LIBISO_FILE,
              "/data/hello.txt is LIBISO_FILE");
        file = (IsoFile *)node;
        CHECK(iso_file_get_size(file) == FILE_DATA_SIZE,
              "file size round trip");
        CHECK(iso_node_get_mtime(node) == FIXED_MTIME,
              "mtime round trip (RRIP TF)");
        CHECK(iso_node_get_permissions(node) ==
                  (S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH),
              "permissions round trip (RRIP PX)");

        /* 4. full content round trip through the stream */
        stream = iso_file_get_stream(file);
        CHECK(stream != NULL, "iso_file_get_stream returns stream");
        if (stream != NULL) {
            result = iso_stream_open(stream);
            CHECK(result >= 0, "iso_stream_open");
            if (result >= 0) {
                unsigned char *round = malloc(FILE_DATA_SIZE);
                size_t got = 0;
                int r;
                if (round == NULL) {
                    printf("out of memory\n");
                    goto fail;
                }
                while (got < FILE_DATA_SIZE) {
                    r = iso_stream_read(stream, round + got,
                                        FILE_DATA_SIZE - got);
                    if (r <= 0)
                        break;
                    got += (size_t)r;
                }
                iso_stream_close(stream);
                CHECK(got == FILE_DATA_SIZE, "stream read full size");
                CHECK(memcmp(round, file_data, FILE_DATA_SIZE) == 0,
                      "file content round trip (stream)");
                free(round);
            }
        }

        /* 5. AAIP xattr round trip */
        {
            size_t num_attrs = 0;
            char **names = NULL;
            size_t *value_lengths = NULL;
            char **values = NULL;
            result = iso_node_get_attrs(node, &num_attrs, &names,
                                        &value_lengths, &values, 0);
            CHECK(result == 1 && num_attrs >= 1,
                  "AAIP xattr present after import");
            if (result == 1 && num_attrs >= 1) {
                int found = 0;
                for (size_t i = 0; i < num_attrs; i++) {
                    if (names[i] != NULL &&
                        strcmp(names[i], "user.hmbs_test") == 0 &&
                        value_lengths[i] == strlen("ohos-aarch64") &&
                        values[i] != NULL &&
                        memcmp(values[i], "ohos-aarch64",
                               value_lengths[i]) == 0)
                        found = 1;
                }
                CHECK(found, "AAIP xattr name+value round trip");
            }
            if (result == 1) {
                /* flag bit15 = dispose the returned arrays */
                size_t n = num_attrs;
                iso_node_get_attrs(NULL, &n, &names, &value_lengths,
                                   &values, 1 << 15);
            }
        }
    }

    /* 6. symlink round trip */
    result = iso_tree_path_to_node(image, "/readme", &node);
    CHECK(result == 1 && node != NULL, "path /readme resolves");
    if (node != NULL) {
        CHECK(iso_node_get_type(node) == LIBISO_SYMLINK,
              "/readme is LIBISO_SYMLINK");
        const char *dest = iso_symlink_get_dest((IsoSymlink *)node);
        CHECK(dest != NULL && strcmp(dest, "data/hello.txt") == 0,
              "symlink destination round trip");
    }

    /* 7. special (fifo) node round trip */
    result = iso_tree_path_to_node(image, "/event-pipe", &node);
    CHECK(result == 1 && node != NULL, "path /event-pipe resolves");
    if (node != NULL) {
        CHECK(iso_node_get_type(node) == LIBISO_SPECIAL,
              "/event-pipe is LIBISO_SPECIAL");
        CHECK((iso_node_get_mode(node) & S_IFMT) == S_IFIFO,
              "special node keeps S_IFIFO type");
    }

    iso_read_image_features_destroy(features);
    iso_image_unref(image);
    iso_finish();
    return 0;

fail:
    if (ropts != NULL)
        iso_read_opts_free(ropts);
    if (src != NULL)
        iso_data_source_unref(src);
    if (image != NULL)
        iso_image_unref(image);
    iso_finish();
    return -1;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <output-dir>\n", argv[0]);
        return 2;
    }

    fill_file_data();

    /* runtime version compatibility (allowed before iso_init) */
    int major = 0, minor = 0, micro = 0;
    iso_lib_version(&major, &minor, &micro);
    CHECK(major == 1 && minor == 5, "runtime version is 1.5.x");
    CHECK(iso_lib_is_compatible(1, 5, 0) == 1,
          "iso_lib_is_compatible(1,5,0)");

    char path[4096];
    snprintf(path, sizeof(path), "%s/test.iso", argv[1]);

    int blocks = write_image(path);
    CHECK(blocks > 0, "image generated with >0 blocks");
    if (blocks <= 0)
        return 1;

    if (verify_image(path, blocks) != 0) {
        printf("[FAIL] image verification failed\n");
        return 1;
    }

    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
           "\"checks\":%d,\"passed\":%d}\n",
           checks_total, checks_passed);
    return 0;
}
