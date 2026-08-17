#include <xls.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const char *version = xls_getVersion();
    const unsigned char invalid_data[] = {0x00, 0x01, 0x02, 0x03};
    xls_error_t error = LIBXLS_OK;
    xlsWorkBook *workbook = xls_open_buffer(
        invalid_data, sizeof(invalid_data), "UTF-8", &error
    );

    if (version == NULL || strcmp(version, "1.6.3") != 0) {
        fprintf(stderr, "Unexpected libxls version: %s\n", version ? version : "NULL");
        return 1;
    }
    if (workbook != NULL || error == LIBXLS_OK) {
        fprintf(stderr, "Invalid workbook data was not rejected\n");
        if (workbook != NULL) {
            xls_close_WB(workbook);
        }
        return 1;
    }

    printf("libxls %s API and invalid-input handling: PASS (%s)\n",
           version, xls_getError(error));
    return 0;
}
