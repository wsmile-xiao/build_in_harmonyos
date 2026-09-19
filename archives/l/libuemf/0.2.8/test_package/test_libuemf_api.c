/* Consumer test for libuemf/0.2.8 (Conan L1 test_package).
 *
 * Exercises the installed package end to end through the public API:
 *   1. create a metafile (emf_start, U_EMRHEADER_set, U_EMRSETMAPMODE_set,
 *      createbrushindirect_set, selectobject_set, U_EMRRECTANGLE_set,
 *      U_EMREOF_set, emf_finish),
 *   2. read it back (emf_readdata),
 *   3. walk the record chain and assert the header signature, the record
 *      count, the map mode, the rectangle bounds and the EOF tail.
 * U_emr_names is checked against the record-name table.
 * Any failed check makes the program return non-zero.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "uemf.h"
#include "uemf_print.h"

#define OUT_NAME "test_libuemf_cp.emf"

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", (msg)); } \
    else      { printf("FAIL: %s\n", (msg)); failures++; } \
} while (0)

int main(void){
    EMFTRACK        *et;
    EMFHANDLES      *eht;
    U_RECTL          rclBounds, rclFrame, rclBox;
    U_SIZEL          szlDev, szlMm;
    uint16_t        *Description;
    uint32_t         cbDesc;
    uint32_t         brush = 0;
    U_LOGBRUSH       lb;
    U_COLORREF       cr;
    char            *rec;
    char            *contents = NULL;
    size_t           length = 0;
    int              status;
    PU_ENHMETARECORD pEmr;
    PU_EMRHEADER     pHeader;
    size_t           off;
    int              recnum, last_type, seen_mapmode, seen_rect;

    /* --- 1. create the metafile --- */
    status = emf_start(OUT_NAME, 1000000, 250000, &et);
    CHECK(status == 0, "emf_start opens the metafile for writing");
    status = emf_htable_create(128, 128, &eht);
    CHECK(status == 0, "emf_htable_create initialises the handle table");

    (void) device_size(216, 279, 47.244094, &szlDev, &szlMm);
    (void) drawing_size(297, 210, 47.244094, &rclBounds, &rclFrame);
    Description = U_Utf8ToUtf16le("Conan test\1produced by libuemf test_package\1", 0, NULL);
    CHECK(Description != NULL, "U_Utf8ToUtf16le converts the description string");
    cbDesc = 2 + wchar16len(Description);
    (void) U_Utf16leEdit(Description, U_Utf16le(1), 0);
    rec = U_EMRHEADER_set(rclBounds, rclFrame, NULL, cbDesc, Description, szlDev, szlMm, 0);
    CHECK(rec != NULL, "U_EMRHEADER_set builds the header record");
    (void) emf_append((PU_ENHMETARECORD)rec, et, 1);
    free(Description);

    rec = U_EMRSETMAPMODE_set(U_MM_TEXT);
    CHECK(rec != NULL, "U_EMRSETMAPMODE_set builds the map-mode record");
    (void) emf_append((PU_ENHMETARECORD)rec, et, 1);

    cr = colorref_set(255, 255, 173);
    lb = logbrush_set(U_BS_SOLID, cr, U_HS_SOLIDCLR);
    rec = createbrushindirect_set(&brush, eht, lb);
    CHECK(rec != NULL, "createbrushindirect_set builds a brush record");
    (void) emf_append((PU_ENHMETARECORD)rec, et, 1);
    rec = selectobject_set(brush, eht);
    CHECK(rec != NULL, "selectobject_set builds a select record");
    (void) emf_append((PU_ENHMETARECORD)rec, et, 1);

    rclBox = rectl_set(pointl_set(0, 0), pointl_set(14031, 9921));
    rec = U_EMRRECTANGLE_set(rclBox);
    CHECK(rec != NULL, "U_EMRRECTANGLE_set builds the rectangle record");
    (void) emf_append((PU_ENHMETARECORD)rec, et, 1);

    rec = U_EMREOF_set(0, NULL, et);
    CHECK(rec != NULL, "U_EMREOF_set builds the EOF record");
    (void) emf_append((PU_ENHMETARECORD)rec, et, 1);

    status = emf_finish(et, eht);
    CHECK(status == 0, "emf_finish writes the metafile");
    emf_free(&et);
    emf_htable_free(&eht);

    CHECK(strcmp(U_emr_names(U_EMR_HEADER), "U_EMR_HEADER") == 0,
          "U_emr_names resolves the header record name");

    /* --- 2. read it back --- */
    status = emf_readdata(OUT_NAME, &contents, &length);
    CHECK(status == 0 && contents != NULL && length > 0,
          "emf_readdata reads the metafile back");

    /* --- 3. walk the record chain --- */
    if (contents) {
        pHeader = (PU_EMRHEADER)contents;
        CHECK(pHeader->dSignature == 0x464D4520, "header dSignature is the EMF signature");
        off = 0;
        recnum = 0;
        last_type = -1;
        seen_mapmode = 0;
        seen_rect = 0;
        while (off < length) {
            pEmr = (PU_ENHMETARECORD)(contents + off);
            if (pEmr->iType == U_EMR_SETMAPMODE) {
                PU_EMRSETMAPMODE pMap = (PU_EMRSETMAPMODE)pEmr;
                CHECK(pMap->iMode == U_MM_TEXT, "SETMAPMODE record carries U_MM_TEXT");
                seen_mapmode++;
            }
            if (pEmr->iType == U_EMR_RECTANGLE) {
                PU_EMRRECTANGLE pRect = (PU_EMRRECTANGLE)pEmr;
                CHECK(pRect->rclBox.right == 14031 && pRect->rclBox.bottom == 9921,
                      "RECTANGLE record carries the requested bounds");
                seen_rect++;
            }
            last_type = (int)pEmr->iType;
            recnum++;
            off += pEmr->nSize;
            if (pEmr->iType == U_EMR_EOF) {
                break;
            }
        }
        CHECK(recnum >= 5, "record walk covers header through EOF");
        CHECK(last_type == U_EMR_EOF, "record chain ends at U_EMR_EOF");
        CHECK(seen_mapmode == 1, "exactly one SETMAPMODE record present");
        CHECK(seen_rect == 1, "exactly one RECTANGLE record present");
        CHECK(pHeader->nRecords == (uint32_t)recnum, "header nRecords matches the walk");
        free(contents);
    }
    remove(OUT_NAME);

    if (failures) {
        printf("test_libuemf_api FAILED: %d check(s)\n", failures);
        return 1;
    }
    printf("test_libuemf_api: all checks passed\n");
    return 0;
}
