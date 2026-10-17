/*
 * Consumer smoke test for libdicom 1.3.0.
 *
 * Parses a real DICOM file (upstream sample data) through the public API:
 *   dcm_filehandle_create_from_file
 *   dcm_filehandle_get_file_meta
 *   dcm_filehandle_get_transfer_syntax_uid
 *   dcm_dataset_get
 *   dcm_element_get_value_string
 *   dcm_dataset_foreach (count elements)
 *   dcm_filehandle_destroy
 *
 * Fails (non-zero exit) when any expected value is missing.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dicom/dicom.h>

static bool count_cb(const DcmElement *element, void *client)
{
    (void) element;
    size_t *n = (size_t *) client;
    (*n)++;
    return true;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "usage: test_libdicom FILE.dcm\n");
        return 2;
    }

    printf("libdicom version: %s\n", dcm_get_version());

    DcmFilehandle *filehandle = dcm_filehandle_create_from_file(NULL, argv[1]);
    if (filehandle == NULL) {
        fprintf(stderr, "FAIL: dcm_filehandle_create_from_file returned NULL\n");
        return 1;
    }

    /* --- File Meta Information: Transfer Syntax UID (0002,0010) --- */
    const DcmDataSet *meta = dcm_filehandle_get_file_meta(NULL, filehandle);
    if (meta == NULL) {
        fprintf(stderr, "FAIL: dcm_filehandle_get_file_meta returned NULL\n");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }

    DcmElement *element = dcm_dataset_get(NULL, meta, 0x00020010);
    if (element == NULL) {
        fprintf(stderr, "FAIL: TransferSyntaxUID element missing\n");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }
    const char *tsuid = NULL;
    if (!dcm_element_get_value_string(NULL, element, 0, &tsuid) ||
        tsuid == NULL) {
        fprintf(stderr, "FAIL: could not read TransferSyntaxUID value\n");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }
    printf("TransferSyntaxUID (0002,0010): %s\n", tsuid);

    /* Cross-check with the convenience accessor. */
    const char *tsuid2 = dcm_filehandle_get_transfer_syntax_uid(filehandle);
    if (tsuid2 == NULL || strcmp(tsuid, tsuid2) != 0) {
        fprintf(stderr, "FAIL: transfer syntax UID mismatch (%s vs %s)\n",
                tsuid, tsuid2 ? tsuid2 : "()");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }

    /* Media Storage SOP Class UID (0002,0002) must be non-empty. */
    element = dcm_dataset_get(NULL, meta, 0x00020002);
    if (element == NULL) {
        fprintf(stderr, "FAIL: MediaStorageSOPClassUID element missing\n");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }
    const char *sopclass = NULL;
    if (!dcm_element_get_value_string(NULL, element, 0, &sopclass) ||
        sopclass == NULL || sopclass[0] == '\0') {
        fprintf(stderr, "FAIL: could not read MediaStorageSOPClassUID\n");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }
    printf("MediaStorageSOPClassUID (0002,0002): %s\n", sopclass);

    /* --- Dataset metadata subset: count elements via foreach --- */
    const DcmDataSet *subset = dcm_filehandle_get_metadata_subset(NULL, filehandle);
    if (subset == NULL) {
        fprintf(stderr, "FAIL: dcm_filehandle_get_metadata_subset returned NULL\n");
        dcm_filehandle_destroy(filehandle);
        return 1;
    }
    size_t n = 0;
    if (!dcm_dataset_foreach(subset, count_cb, &n) || n == 0) {
        fprintf(stderr, "FAIL: metadata subset iteration failed (n=%zu)\n", n);
        dcm_filehandle_destroy(filehandle);
        return 1;
    }
    printf("metadata subset element count: %zu\n", n);

    dcm_filehandle_destroy(filehandle);
    printf("PASS: libdicom parsed the DICOM file successfully\n");
    return 0;
}
