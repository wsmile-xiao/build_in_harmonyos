#include <minidjvu/minidjvu.h>

#include <cstdio>
#include <cstring>

namespace {

int failures = 0;

void check(bool condition, const char *message)
{
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", message);
        ++failures;
    }
}

} // namespace

int main()
{
    check(mdjvu_check_sanity() == nullptr, "fixed-width integer ABI sanity");

    mdjvu_bitmap_t bitmap = mdjvu_bitmap_create(13, 3);
    check(bitmap != nullptr, "bitmap creation");
    if (!bitmap) {
        return 1;
    }

    check(mdjvu_bitmap_get_width(bitmap) == 13, "bitmap width");
    check(mdjvu_bitmap_get_height(bitmap) == 3, "bitmap height");
    check(mdjvu_bitmap_get_packed_row_size(bitmap) == 2, "packed row size");
    check(mdjvu_bitmap_get_index(bitmap) == -1, "detached bitmap index");

    unsigned char input[13] = {1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1};
    unsigned char output[13] = {};
    mdjvu_bitmap_pack_row(bitmap, input, 1);
    mdjvu_bitmap_unpack_row_0_or_1(bitmap, output, 1);
    check(std::memcmp(input, output, sizeof(input)) == 0, "row pack/unpack round trip");
    check(mdjvu_bitmap_get_mass(bitmap) == 6, "black pixel mass");

    mdjvu_bitmap_t clone = mdjvu_bitmap_clone(bitmap);
    check(clone != nullptr, "bitmap clone");
    check(clone && mdjvu_bitmap_get_mass(clone) == 6, "clone preserves pixels");
    if (clone) {
        mdjvu_bitmap_clear(clone);
        check(mdjvu_bitmap_get_mass(clone) == 0, "bitmap clear");
        check(mdjvu_bitmap_get_mass(bitmap) == 6, "clone is independent");
    }

    const char *pbm_path = "minidjvu-test.pbm";
    mdjvu_error_t error = nullptr;
    check(mdjvu_save_pbm(bitmap, pbm_path, &error) == 1, "save PBM");
    mdjvu_bitmap_t loaded = mdjvu_load_pbm(pbm_path, &error);
    check(loaded != nullptr, "load PBM");
    if (loaded) {
        check(mdjvu_bitmap_get_width(loaded) == 13, "loaded PBM width");
        check(mdjvu_bitmap_get_height(loaded) == 3, "loaded PBM height");
        check(mdjvu_bitmap_get_mass(loaded) == 6, "loaded PBM pixels");
    }

    check(mdjvu_have_tiff_support() == 1, "libtiff support is enabled");
    const char *tiff_path = "minidjvu-test.tiff";
    check(mdjvu_save_tiff(bitmap, tiff_path, &error) == 1, "save TIFF");
    check(mdjvu_get_tiff_page_count(tiff_path) == 1, "TIFF page count");
    int32 resolution = 0;
    mdjvu_bitmap_t loaded_tiff = mdjvu_load_tiff(tiff_path, &resolution, &error, 0);
    check(loaded_tiff != nullptr, "load TIFF");
    if (loaded_tiff) {
        check(mdjvu_bitmap_get_width(loaded_tiff) == 13, "loaded TIFF width");
        check(mdjvu_bitmap_get_height(loaded_tiff) == 3, "loaded TIFF height");
        check(mdjvu_bitmap_get_mass(loaded_tiff) == 6, "loaded TIFF pixels");
    }
    check(mdjvu_get_version() != nullptr && mdjvu_get_version()[0] != '\0',
          "library version is available");

    if (loaded_tiff) {
        mdjvu_bitmap_destroy(loaded_tiff);
    }
    if (loaded) {
        mdjvu_bitmap_destroy(loaded);
    }
    if (clone) {
        mdjvu_bitmap_destroy(clone);
    }
    mdjvu_bitmap_destroy(bitmap);
    std::remove(pbm_path);
    std::remove(tiff_path);

    if (failures != 0) {
        std::fprintf(stderr, "%d minidjvu checks failed\n", failures);
        return 1;
    }
    std::puts("minidjvu public API checks passed");
    return 0;
}
