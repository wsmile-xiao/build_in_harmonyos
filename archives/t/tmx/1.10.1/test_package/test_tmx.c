/* Consumer test for tmx/1.10.1: load real Tiled maps through the
   packaged static library and assert parsed values (15 checks).
   Exercises the libxml2 XML path, the zlib decompression path
   (WANT_ZLIB=ON), the find helpers, the buffer loader, the error
   reporting (tmx_errno/tmx_strerr) and the color conversion API.
   A stub library (or a broken zlib linkage) fails these checks
   instead of silently passing. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <tmx.h>

static int g_total = 0;
static int g_passed = 0;

#define CHECK(cond, desc)                                                     \
    do {                                                                      \
        ++g_total;                                                            \
        if (cond) {                                                           \
            ++g_passed;                                                       \
            printf("ok %d - %s\n", g_total, desc);                            \
        } else {                                                              \
            printf("FAIL %d - %s\n", g_total, desc);                          \
        }                                                                     \
    } while (0)

/* 4x3 orthogonal map, CSV layer data, gids 1..12. */
static const char *kCsvMap =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<map version=\"1.10\" tiledversion=\"1.10.1\" orientation=\"orthogonal\" "
    "renderorder=\"right-down\" width=\"4\" height=\"3\" tilewidth=\"16\" "
    "tileheight=\"16\" infinite=\"0\" nextlayerid=\"8\" nextobjectid=\"1\">\n"
    " <tileset firstgid=\"1\" name=\"demo\" tilewidth=\"16\" "
    "tileheight=\"16\" tilecount=\"12\" columns=\"4\">\n"
    "  <image source=\"tiles.png\" width=\"64\" height=\"48\"/>\n"
    " </tileset>\n"
    " <layer id=\"7\" name=\"ground\" width=\"4\" height=\"3\">\n"
    "  <data encoding=\"csv\">\n"
    "1,2,3,4,5,6,7,8,9,10,11,12\n"
    "</data>\n"
    " </layer>\n"
    "</map>\n";

/* Same map, base64+zlib layer data (zlib(compress(u32le 1..12))). */
static const char *kZlibMap =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<map version=\"1.10\" tiledversion=\"1.10.1\" orientation=\"orthogonal\" "
    "renderorder=\"right-down\" width=\"4\" height=\"3\" tilewidth=\"16\" "
    "tileheight=\"16\" infinite=\"0\" nextlayerid=\"8\" nextobjectid=\"1\">\n"
    " <tileset firstgid=\"1\" name=\"demo\" tilewidth=\"16\" "
    "tileheight=\"16\" tilecount=\"12\" columns=\"4\">\n"
    "  <image source=\"tiles.png\" width=\"64\" height=\"48\"/>\n"
    " </tileset>\n"
    " <layer id=\"7\" name=\"ground\" width=\"4\" height=\"3\">\n"
    "  <data encoding=\"base64\" compression=\"zlib\">\n"
    "eNoNw4cNACAMAKA66/r/XiGhRES12R1O0+X2eH1+BeAATw==\n"
    "</data>\n"
    " </layer>\n"
    "</map>\n";

static const char *kBrokenMap = "<map><oops";

static int write_file(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    size_t len;
    size_t wrote;
    if (!f) {
        return 0;
    }
    len = strlen(content);
    wrote = fwrite(content, 1, len, f);
    fclose(f);
    return wrote == len;
}

int main(int argc, char **argv) {
    tmx_map *map = NULL;
    tmx_map *buf_map = NULL;
    tmx_map *z_map = NULL;
    tmx_map *missing = NULL;
    tmx_map *broken = NULL;
    tmx_layer *layer = NULL;
    tmx_layer *layer_by_id = NULL;
    tmx_tileset_list *ts = NULL;
    tmx_col_bytes col;

    (void)argc;
    (void)argv;

    /* 1: file loader parses a real map (libxml2 path). */
    CHECK(write_file("hmbs_tmx_csv.tmx", kCsvMap) != 0,
          "fixture map written to disk");
    map = tmx_load("hmbs_tmx_csv.tmx");
    CHECK(map != NULL, "tmx_load parses the CSV fixture map");

    /* 2-3: header dimensions. */
    CHECK(map && map->width == 4 && map->height == 3,
          "map dimensions are 4x3");
    CHECK(map && map->tile_width == 16 && map->tile_height == 16,
          "tile size is 16x16");

    /* 4: embedded tileset list head. */
    CHECK(map && map->ts_head && map->ts_head->tileset &&
              map->ts_head->tileset->name &&
              strcmp(map->ts_head->tileset->name, "demo") == 0,
          "tileset head is named demo");

    /* 5-6: layer lookup and tile gids. */
    layer = map ? tmx_find_layer_by_name(map, "ground") : NULL;
    CHECK(layer && layer->id == 7, "layer ground found with id 7");
    CHECK(layer && layer->content.gids && layer->content.gids[0] == 1 &&
              layer->content.gids[11] == 12,
          "layer gids span 1..12");

    /* 7-8: tileset lookup and GID-indexed tile array. */
    ts = map ? tmx_find_tileset_by_name(map, "demo") : NULL;
    CHECK(ts && ts->firstgid == 1 && ts->tileset &&
              ts->tileset->tilecount == 12,
          "tileset demo has firstgid 1 and 12 tiles");
    CHECK(map && map->tilecount > 12 && map->tiles && map->tiles[12] &&
              map->tiles[12]->id == 11,
          "gid 12 resolves to tile id 11");

    /* 9: in-memory loader covers the same document. */
    buf_map = tmx_load_buffer(kCsvMap, (int)strlen(kCsvMap));
    CHECK(buf_map && buf_map->width == 4 && buf_map->height == 3,
          "tmx_load_buffer parses the same document");

    /* 10-11: error paths fail closed with a usable diagnostic.
       Upstream parse_xml() reports a missing file as E_UNKN
       ("xml parser: unable to open ...", see src/tmx_xml.c), never
       E_NOENT, so assert non-zero errno plus message instead of a
       specific code that upstream never emits. */
    missing = tmx_load("hmbs_tmx_no_such_file.tmx");
    CHECK(missing == NULL && tmx_errno != E_NONE &&
              tmx_strerr() != NULL,
          "missing file fails closed with a non-zero errno and a message");
    broken = tmx_load_buffer(kBrokenMap, (int)strlen(kBrokenMap));
    CHECK(broken == NULL && tmx_errno != E_NONE,
          "malformed XML fails with a non-zero tmx_errno");

    /* 12: zlib-compressed layer data decodes (WANT_ZLIB linkage). */
    z_map = tmx_load_buffer(kZlibMap, (int)strlen(kZlibMap));
    layer_by_id = z_map ? tmx_find_layer_by_name(z_map, "ground") : NULL;
    CHECK(layer_by_id && layer_by_id->content.gids &&
              layer_by_id->content.gids[5] == 6,
          "base64+zlib layer decodes to matching gids");

    /* 13: color conversion API. */
    col = tmx_col_to_bytes(0xFF112233u);
    CHECK(col.r == 0x11 && col.g == 0x22 && col.b == 0x33 &&
              col.a == 0xFF,
          "tmx_col_to_bytes splits ARGB correctly");

    /* 14: id lookup agrees with name lookup. */
    layer_by_id = map ? tmx_find_layer_by_id(map, 7) : NULL;
    CHECK(layer_by_id != NULL && layer_by_id == layer,
          "find_layer_by_id(7) matches find_layer_by_name");

    if (map) {
        tmx_map_free(map);
    }
    if (buf_map) {
        tmx_map_free(buf_map);
    }
    if (z_map) {
        tmx_map_free(z_map);
    }
    remove("hmbs_tmx_csv.tmx");

    printf("PASSED %d/%d\n", g_passed, g_total);
    return g_passed == g_total ? 0 : 1;
}
