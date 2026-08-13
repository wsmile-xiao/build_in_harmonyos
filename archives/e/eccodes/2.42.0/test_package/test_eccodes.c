#include <eccodes.h>

#include <stdio.h>

static int check(int condition, const char* message)
{
    if (!condition) {
        fprintf(stderr, "eccodes smoke check failed: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    long api_version = codes_get_api_version();
    if (check(api_version >= 24200, "API version is older than 2.42.0")) {
        return 1;
    }

    codes_handle* handle = codes_handle_new_from_samples(NULL, "GRIB2");
    if (check(handle != NULL, "failed to load GRIB2 sample")) {
        return 1;
    }

    long edition = 0;
    int err = codes_get_long(handle, "edition", &edition);
    if (check(err == 0, "failed to read edition")) {
        codes_handle_delete(handle);
        return 1;
    }
    if (check(edition == 2, "unexpected GRIB edition")) {
        codes_handle_delete(handle);
        return 1;
    }

    err = codes_set_long(handle, "centre", 98);
    if (check(err == 0, "failed to set centre")) {
        codes_handle_delete(handle);
        return 1;
    }

    long centre = 0;
    err = codes_get_long(handle, "centre", &centre);
    if (check(err == 0, "failed to read centre")) {
        codes_handle_delete(handle);
        return 1;
    }
    if (check(centre == 98, "unexpected centre value")) {
        codes_handle_delete(handle);
        return 1;
    }

    codes_handle_delete(handle);
    printf("eccodes consumer smoke passed: %ld\n", api_version);
    return 0;
}
