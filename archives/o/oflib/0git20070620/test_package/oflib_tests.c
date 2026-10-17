#include <ofapi/of_api.h>

#include <errno.h>
#include <stdio.h>
#include <sys/stat.h>

#define CHECK(condition, message)                                               \
    do {                                                                        \
        if (!(condition)) {                                                     \
            fprintf(stderr, "FAIL: %s (line %d)\n", (message), __LINE__);       \
            return 1;                                                           \
        }                                                                       \
    } while (0)

static int write_bytes(const char *path, const void *data, size_t size)
{
    FILE *stream = fopen(path, "wb");
    if (stream == NULL)
        return 0;
    if (fwrite(data, 1, size, stream) != size) {
        fclose(stream);
        return 0;
    }
    return fclose(stream) == 0;
}

static int test_uint32(void)
{
    uint8_t data[] = {0x12, 0x34, 0x56, 0x78, 0x01, 0x02, 0x03, 0x04};
    uint32_t value = 0;

    CHECK(of_property_to_uint32(&value, data, 4) == 1,
          "a four-byte property must decode");
    CHECK(value == UINT32_C(0x12345678), "uint32 decoding must be big-endian");
    CHECK(of_property_to_uint32(&value, data, 3) == 0,
          "a non-four-byte scalar property must be rejected");
    CHECK(of_property_to_n_uint32(&value, data, sizeof(data), 2) == 1,
          "the second uint32 element must decode");
    CHECK(value == UINT32_C(0x01020304), "indexed uint32 decoding must be exact");
    CHECK(of_property_to_n_uint32(&value, data, sizeof(data), 0) == 0,
          "uint32 index zero must be rejected");
    puts("oflib uint32 tests passed (6 assertions)");
    return 0;
}

static int test_uint64(void)
{
    uint8_t data[] = {
        0x01, 0x23, 0x45, 0x67, 0x10, 0x20, 0x30, 0x40,
        0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x78,
    };
    uint64_t value = 0;

    CHECK(of_property_to_n_uint64(&value, data, sizeof(data), 1) == 1,
          "the first uint64 element must decode");
    CHECK(value == UINT64_C(0x0123456710203040),
          "the first uint64 value must be big-endian");
    CHECK(of_property_to_n_uint64(&value, data, sizeof(data), 2) == 1,
          "the second uint64 element must decode");
    CHECK(value == UINT64_C(0x1122334455667778),
          "the second uint64 value must be exact");
    CHECK(of_property_to_n_uint64(&value, data, sizeof(data), 3) == 0,
          "an out-of-range uint64 element must be rejected");
    puts("oflib uint64 tests passed (5 assertions)");
    return 0;
}

static int test_device_tree(void)
{
    char root[PATH_MAX];
    char node_dir[PATH_MAX];
    char path[PATH_MAX];
    const uint8_t root_name[] = "root";
    const uint8_t node_name[] = "serial";
    const uint8_t node_type[] = "uart";
    const uint8_t property[] = {0xde, 0xad, 0xbe, 0xef};
    struct device_node *node;
    void *loaded;
    int length = 0;

    CHECK(getcwd(root, sizeof(root)) != NULL, "the test working directory is readable");
    CHECK(snprintf(node_dir, sizeof(node_dir), "%s/oflib-device-tree", root) > 0,
          "the fixture directory path must fit");
    if (mkdir(node_dir, 0700) != 0 && errno != EEXIST) {
        perror("mkdir");
        return 1;
    }
    CHECK(snprintf(path, sizeof(path), "%s/name", node_dir) > 0,
          "the root name path must fit");
    CHECK(write_bytes(path, root_name, sizeof(root_name)), "the root name is writable");

    CHECK(snprintf(path, sizeof(path), "%s/serial@1000", node_dir) > 0,
          "the child path must fit");
    CHECK(mkdir(path, 0700) == 0 || errno == EEXIST, "the child fixture is writable");
    CHECK(snprintf(path, sizeof(path), "%s/serial@1000/name", node_dir) > 0,
          "the child name path must fit");
    CHECK(write_bytes(path, node_name, sizeof(node_name)), "the child name is writable");
    CHECK(snprintf(path, sizeof(path), "%s/serial@1000/device_type", node_dir) > 0,
          "the child type path must fit");
    CHECK(write_bytes(path, node_type, sizeof(node_type)), "the child type is writable");
    CHECK(snprintf(path, sizeof(path), "%s/serial@1000/reg", node_dir) > 0,
          "the property path must fit");
    CHECK(write_bytes(path, property, sizeof(property)), "the property is writable");

    CHECK(snprintf(path, sizeof(path), "%s/", node_dir) > 0,
          "the OF root path must fit");
    of_init_root(path);
    CHECK(strcmp(OF_ROOT, node_dir) == 0, "of_init_root must trim a trailing slash");

    node = of_find_node_by_path("/serial@1000");
    CHECK(node != NULL, "a fixture node must be found by path");
    CHECK(node->path != NULL && strcmp(node->path, "/serial@1000/") == 0,
          "the node path must be relative to the configured OF root");
    CHECK(node->name != NULL && strcmp(node->name, "serial") == 0,
          "the node name property must be loaded");
    CHECK(node->type != NULL && strcmp(node->type, "uart") == 0,
          "the node device_type property must be loaded");
    CHECK(of_test_property(node, "reg") == 1, "the reg property must exist");
    loaded = of_find_property(node, "reg", &length);
    CHECK(loaded != NULL && length == 4, "the reg property must be readable");
    CHECK(memcmp(loaded, property, sizeof(property)) == 0,
          "the property bytes must be preserved");

    free(loaded);
    of_free_node(node);
    puts("oflib device-tree tests passed (21 assertions)");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s uint32|uint64|device-tree\n", argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "uint32") == 0)
        return test_uint32();
    if (strcmp(argv[1], "uint64") == 0)
        return test_uint64();
    if (strcmp(argv[1], "device-tree") == 0)
        return test_device_tree();
    fprintf(stderr, "unknown test scenario: %s\n", argv[1]);
    return 2;
}
