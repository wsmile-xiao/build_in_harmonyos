#include <stdio.h>
#include <string.h>
#include "generated_fastq.h"

int main(void) {
    const char expected[] = "@good\nACGTACGT\n+\nIIII!!!!\n";
    if (strcmp((const char *)fastq_result, expected) != 0) {
        fprintf(stderr, "Sickle gzip FASTQ filtering produced unexpected reads\n");
        return 1;
    }
    puts("OHOS consumer: gzip FASTQ processed; 1 good read kept, 1 poor read removed");
    return 0;
}
