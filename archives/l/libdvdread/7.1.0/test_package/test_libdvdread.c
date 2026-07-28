#include <dvdread/dvd_reader.h>
#include <dvdread/version.h>

#include <stdio.h>
#include <string.h>

int main(int argc, char** argv)
{
    if (argc == 2 && strcmp(argv[1], "--missing-path") == 0)
    {
        dvd_reader_t* missing =
            DVDOpen("./this-path-must-not-exist-libdvdread-test");
        if (missing != NULL)
        {
            DVDClose(missing);
            fprintf(stderr, "nonexistent DVD path unexpectedly opened\n");
            return 1;
        }
        puts("nonexistent DVD path rejected");
        return 0;
    }
    if (argc != 1)
    {
        fprintf(stderr, "usage: test_libdvdread [--missing-path]\n");
        return 2;
    }

    if (DVDREAD_VERSION_MAJOR != 7 || DVDREAD_VERSION_MINOR != 1 ||
        DVDREAD_VERSION_MICRO != 0)
    {
        fprintf(stderr, "unexpected libdvdread version macros\n");
        return 3;
    }
    if (DVD_VIDEO_LB_LEN != 2048)
    {
        fprintf(stderr, "unexpected logical-block size\n");
        return 4;
    }

    dvd_reader_t* reader = DVDOpen(".");
    if (reader == NULL)
    {
        fprintf(stderr, "existing directory could not be opened\n");
        return 5;
    }

    dvd_stat_t stat_buffer;
    if (DVDFileStat(reader, 99, DVD_READ_INFO_FILE, &stat_buffer) != -1)
    {
        DVDClose(reader);
        fprintf(stderr, "missing title did not return -1\n");
        return 6;
    }
    DVDClose(reader);

    puts("libdvdread consumer checks passed");
    return 0;
}
