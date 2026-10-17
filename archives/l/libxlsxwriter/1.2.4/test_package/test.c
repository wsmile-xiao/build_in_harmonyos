#include <xlsxwriter.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Consumer smoke test for libxlsxwriter on OHOS aarch64:
// write a small workbook with strings/numbers/formulas, then re-read the
// produced .xlsx as a zip container using zlib's raw inflate API directly
// (the xlsx format is a stored/deflated zip of XML parts; the vendored
// minizip write side is inside the library, so on the consumer side we
// verify the container with zlib itself). This exercises the whole write
// path: zip container (vendored minizip over conan zlib), shared string
// table, worksheet XML, styles, formula parts.
static int read_zip_member(const char *path, const char *member,
                           char *out, size_t outsz);

int main(void) {
    const char *path = "smoke_test.xlsx";
    lxw_workbook *wb = workbook_new(path);
    if (!wb) { fprintf(stderr, "workbook_new failed\n"); return 1; }

    lxw_worksheet *ws = workbook_add_worksheet(wb, NULL);
    lxw_format *bold = workbook_add_format(wb);
    format_set_bold(bold);

    worksheet_write_string(ws, 0, 0, "HelloOHOS", bold);
    worksheet_write_number(ws, 1, 0, 123.45, NULL);
    worksheet_write_formula(ws, 2, 0, "=1+2*3", NULL);

    lxw_error err = workbook_close(wb);
    if (err != LXW_NO_ERROR) {
        fprintf(stderr, "workbook_close failed: %d\n", (int)err);
        return 1;
    }

    char buf[262144];

    // 1) container core parts must exist
    if (read_zip_member(path, "[Content_Types].xml", buf, sizeof(buf)) <= 0) {
        fprintf(stderr, "missing [Content_Types].xml\n"); return 1;
    }
    if (read_zip_member(path, "xl/workbook.xml", buf, sizeof(buf)) <= 0) {
        fprintf(stderr, "missing xl/workbook.xml\n"); return 1;
    }

    // 2) sharedStrings must contain the written string
    int n = read_zip_member(path, "xl/sharedStrings.xml", buf, sizeof(buf));
    if (n <= 0) { fprintf(stderr, "missing sharedStrings.xml\n"); return 1; }
    if (!strstr(buf, "HelloOHOS")) {
        fprintf(stderr, "sharedStrings does not contain written string\n");
        return 1;
    }

    // 3) worksheet XML must carry the number and the formula element
    n = read_zip_member(path, "xl/worksheets/sheet1.xml", buf, sizeof(buf));
    if (n <= 0) { fprintf(stderr, "missing sheet1.xml\n"); return 1; }
    if (!strstr(buf, "123.45") || !strstr(buf, "<f>")) {
        fprintf(stderr, "sheet1.xml missing number/formula\n");
        return 1;
    }

    // 4) styles part must exist (bold format was requested)
    if (read_zip_member(path, "xl/styles.xml", buf, sizeof(buf)) <= 0) {
        fprintf(stderr, "missing styles.xml\n"); return 1;
    }

    printf("libxlsxwriter smoke: PASS (container+sheet+sharedStrings+styles verified)\n");
    return 0;
}

#include <zlib.h>

static uint16_t rd16(const unsigned char *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t rd32(const unsigned char *p) { return (uint32_t)(p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24)); }

static int read_zip_member(const char *path, const char *member,
                           char *out, size_t outsz)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END); long fsz = ftell(f); fseek(f, 0, SEEK_SET);
    if (fsz <= 0 || fsz > 32 * 1024 * 1024) { fclose(f); return -1; }
    unsigned char *data = (unsigned char *)malloc(fsz);
    if (!data || fread(data, 1, fsz, f) != (size_t)fsz) { free(data); fclose(f); return -1; }
    fclose(f);

    // scan local file headers (each starts with PK\x03\x04)
    size_t off = 0;
    while (off + 30 <= (size_t)fsz) {
        if (rd32(data + off) != 0x04034b50) break;
        uint16_t method = rd16(data + off + 8);
        uint32_t csize = rd32(data + off + 18);
        uint32_t usize = rd32(data + off + 22);
        uint16_t nlen = rd16(data + off + 26);
        uint16_t elen = rd16(data + off + 28);
        const char *name = (const char *)(data + off + 30);
        size_t hdr = off;
        off += 30 + nlen + elen;
        if ((size_t)fsz < off + csize) break;
        if (strncmp(name, member, nlen) != 0 || (size_t)nlen != strlen(member)) {
            off += csize;              // skip this member's data, keep scanning
            continue;
        }

        const unsigned char *cdata = data + off;
        int outn = -1;
        if (method == 0) {                     // stored
            if (csize < outsz) { memcpy(out, cdata, csize); out[csize] = 0; outn = (int)csize; }
        } else if (method == 8) {              // deflated
            z_stream zs; memset(&zs, 0, sizeof(zs));
            if (inflateInit2(&zs, -15) == Z_OK) {
                zs.next_in = (Bytef *)cdata; zs.avail_in = csize;
                zs.next_out = (Bytef *)out; zs.avail_out = (uInt)(outsz - 1);
                if (inflate(&zs, Z_FINISH) == Z_STREAM_END || zs.total_out > 0)
                    outn = (int)zs.total_out;
                out[zs.total_out < outsz ? zs.total_out : outsz - 1] = 0;
                inflateEnd(&zs);
            }
        }
        (void)usize; (void)hdr;
        free(data);
        return outn;
    }
    free(data);
    return -1;
}
