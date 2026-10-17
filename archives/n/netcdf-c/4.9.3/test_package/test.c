#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <netcdf.h>

/* Consumer test: create a small netCDF-4 file via the public API,
 * write one variable, reopen it and verify the round-trip value. */
int main(void) {
    const char *path = "consumer_test.nc";
    int ncid, dimid, varid;
    float in[4] = {1.5f, -2.0f, 3.25f, 42.0f};
    float out[4] = {0};
    int ret;

    ret = nc_create(path, NC_CLOBBER | NC_NETCDF4, &ncid);
    if (ret != NC_NOERR) {
        fprintf(stderr, "nc_create failed: %s\n", nc_strerror(ret));
        return 1;
    }
    if ((ret = nc_def_dim(ncid, "n", 4, &dimid)) != NC_NOERR) goto fail;
    if ((ret = nc_def_var(ncid, "data", NC_FLOAT, 1, &dimid, &varid)) != NC_NOERR)
        goto fail;
    if ((ret = nc_enddef(ncid)) != NC_NOERR) goto fail;
    if ((ret = nc_put_var_float(ncid, varid, in)) != NC_NOERR) goto fail;
    if ((ret = nc_close(ncid)) != NC_NOERR) goto fail;

    ret = nc_open(path, NC_NOWRITE, &ncid);
    if (ret != NC_NOERR) {
        fprintf(stderr, "nc_open failed: %s\n", nc_strerror(ret));
        return 1;
    }
    if ((ret = nc_inq_varid(ncid, "data", &varid)) != NC_NOERR) goto fail;
    if ((ret = nc_get_var_float(ncid, varid, out)) != NC_NOERR) goto fail;
    if ((ret = nc_close(ncid)) != NC_NOERR) goto fail;

    if (memcmp(in, out, sizeof(in)) != 0) {
        fprintf(stderr, "round-trip mismatch: got %f,%f,%f,%f\n",
                out[0], out[1], out[2], out[3]);
        return 1;
    }
    printf("consumer round-trip OK: %g %g %g %g\n", out[0], out[1], out[2], out[3]);
    remove(path);
    return 0;

fail:
    fprintf(stderr, "netCDF API error: %s\n", nc_strerror(ret));
    nc_close(ncid);
    return 1;
}