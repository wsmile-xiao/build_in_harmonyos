#include <biolibc/biostring.h>
#include <biolibc/vcf.h>
#include <stdio.h>
#include <string.h>

static int test_vcf_meta_stream(void)
{
    char line[128];
    FILE *input = fopen("biolibc-vcf-smoke.vcf", "w+");
    FILE *meta;

    if (input == NULL) {
        return 10;
    }
    fputs("##fileformat=VCFv4.2\n", input);
    fputs("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n", input);
    fputs("chr1\t13\t.\tA\tG\t.\t.\t.\tGT\t0|1\n", input);
    rewind(input);

    meta = bl_vcf_skip_meta_data(input);
    if (meta == NULL) {
        fclose(input);
        return 11;
    }
    if (fgets(line, sizeof(line), meta) == NULL || strncmp(line, "##fileformat=VCFv4.2", 20) != 0) {
        fclose(meta);
        fclose(input);
        return 12;
    }
    if (getc(input) != '#') {
        fclose(meta);
        fclose(input);
        return 13;
    }
    fclose(meta);
    fclose(input);
    return 0;
}

int main(void)
{
    if (bl_chrom_name_cmp("chr2", "chr10") >= 0) {
        return 1;
    }
    if (bl_chrom_name_cmp("chrX", "chr10") <= 0) {
        return 2;
    }
    if (bl_chrom_name_cmp("chr7", "chr7") != 0) {
        return 3;
    }
    if (test_vcf_meta_stream() != 0) {
        return 4;
    }
    return 0;
}
