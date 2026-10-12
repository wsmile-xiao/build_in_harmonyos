#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shapefil.h"

/* L1 consumer test: exercise the shapelib API end-to-end.
 * 1. Create a point shapefile + attribute DBF, write 3 records.
 * 2. Reopen and read back, verify counts/coordinates/attributes.
 */
#define NPTS 3
static const double xs[NPTS] = {116.391, 121.474, 113.264};
static const double ys[NPTS] = {39.907, 31.230, 23.129};
static const char *names[NPTS] = {"Beijing", "Shanghai", "Guangzhou"};

int fail(const char *msg) {
    fprintf(stderr, "FAIL: %s\n", msg);
    return 1;
}

int main(int argc, char *argv[]) {
    const char *dir = (argc > 1) ? argv[1] : ".";
    char shp_path[1024], dbf_path[1024];
    snprintf(shp_path, sizeof(shp_path), "%s/testpoint.shp", dir);
    snprintf(dbf_path, sizeof(dbf_path), "%s/testpoint.dbf", dir);

    /* --- write phase --- */
    SHPHandle hSHP = SHPCreate(shp_path, SHPT_POINT);
    if (hSHP == NULL) return fail("SHPCreate");
    DBFHandle hDBF = DBFCreate(dbf_path);
    if (hDBF == NULL) return fail("DBFCreate");
    if (DBFAddField(hDBF, "name", FTString, 32, 0) < 0)
        return fail("DBFAddField");

    for (int i = 0; i < NPTS; i++) {
        double x = xs[i], y = ys[i];
        SHPObject *obj = SHPCreateSimpleObject(SHPT_POINT, 1, &x, &y, NULL);
        if (obj == NULL) return fail("SHPCreateSimpleObject");
        if (SHPWriteObject(hSHP, -1, obj) < 0) return fail("SHPWriteObject");
        SHPDestroyObject(obj);
        DBFWriteStringAttribute(hDBF, i, 0, names[i]);
    }
    SHPClose(hSHP);
    DBFClose(hDBF);

    /* --- read-back phase --- */
    int nEntities, nShapeType;
    hSHP = SHPOpen(shp_path, "rb");
    if (hSHP == NULL) return fail("SHPOpen");
    SHPGetInfo(hSHP, &nEntities, &nShapeType, NULL, NULL);
    if (nEntities != NPTS || nShapeType != SHPT_POINT)
        return fail("SHPGetInfo count/type mismatch");

    hDBF = DBFOpen(dbf_path, "rb");
    if (hDBF == NULL) return fail("DBFOpen");
    if (DBFGetRecordCount(hDBF) != NPTS) return fail("DBF record count");
    if (DBFGetFieldCount(hDBF) != 1) return fail("DBF field count");

    for (int i = 0; i < NPTS; i++) {
        SHPObject *obj = SHPReadObject(hSHP, i);
        if (obj == NULL) return fail("SHPReadObject");
        if (obj->nSHPType != SHPT_POINT || obj->nVertices != 1)
            return fail("object type/vertices");
        if (obj->padfX[0] != xs[i] || obj->padfY[0] != ys[i])
            return fail("coordinate mismatch");
        SHPDestroyObject(obj);
        char name[64];
        if (DBFReadStringAttribute(hDBF, i, 0) == NULL) return fail("DBF read");
        snprintf(name, sizeof(name), "%s", DBFReadStringAttribute(hDBF, i, 0));
        if (strcmp(name, names[i]) != 0) return fail("attribute mismatch");
    }
    SHPClose(hSHP);
    DBFClose(hDBF);

    printf("test shapelib 1.5.0: OK (wrote and read back %d points with attributes)\n", NPTS);
    return 0;
}
