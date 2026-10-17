/* test_package consumer test: genuinely exercise the libtasn1 API.
 * Round-trip a minimal ASN.1 INTEGER definition: parser2tree -> der_coding -> der_decoding.
 */
#include <stdio.h>
#include <string.h>
#include <libtasn1.h>

static const char asn1_schema[] =
    "MYINT {iso(1) identified-organization(3) dod(6) internet(1) private(4) 99999}\n"
    "\n"
    "DEFINITIONS IMPLICIT TAGS ::=\n"
    "\n"
    "BEGIN\n"
    "\n"
    "TestValue ::= INTEGER\n"
    "\n"
    "END\n";

int main(void)
{
    asn1_node definitions = NULL, node = NULL;
    char err_desc[256];
    unsigned char der[64];
    int der_len = 0;
    long long value = 0;
    int rc;
    const char *schema_file = "./asn1_test_schema.asn";
    FILE *fp;

    if (!asn1_check_version(ASN1_VERSION)) {
        fprintf(stderr, "version check failed: %s\n", ASN1_VERSION);
        return 1;
    }

    /* asn1_parser2tree() takes a schema FILE path (not inline text). */
    fp = fopen(schema_file, "w");
    if (!fp) {
        fprintf(stderr, "cannot create schema file %s\n", schema_file);
        return 1;
    }
    fputs(asn1_schema, fp);
    fclose(fp);

    err_desc[0] = '\0';
    rc = asn1_parser2tree(schema_file, &definitions, err_desc);
    if (rc != ASN1_SUCCESS) {
        fprintf(stderr, "asn1_parser2tree failed: %s\n",
                err_desc[0] ? err_desc : asn1_strerror(rc));
        return 1;
    }

    rc = asn1_create_element(definitions, "MYINT.TestValue", &node);
    if (rc != ASN1_SUCCESS) {
        fprintf(stderr, "asn1_create_element failed: %s\n", asn1_strerror(rc));
        asn1_delete_structure(&definitions);
        return 1;
    }

    value = 123456;
    rc = asn1_write_value(node, "", &value, 1);
    if (rc != ASN1_SUCCESS) {
        fprintf(stderr, "asn1_write_value failed: %s\n", asn1_strerror(rc));
        asn1_delete_structure(&node);
        asn1_delete_structure(&definitions);
        return 1;
    }

    der_len = sizeof(der);
    err_desc[0] = '\0';
    rc = asn1_der_coding(node, "", der, &der_len, err_desc);
    if (rc != ASN1_SUCCESS) {
        fprintf(stderr, "asn1_der_coding failed: %s\n",
                err_desc[0] ? err_desc : asn1_strerror(rc));
        asn1_delete_structure(&node);
        asn1_delete_structure(&definitions);
        return 1;
    }

    /* Decode the produced DER back into a fresh tree to prove round-trip. */
    rc = asn1_create_element(definitions, "MYINT.TestValue", &node);
    if (rc != ASN1_SUCCESS) {
        fprintf(stderr, "asn1_create_element (decode) failed: %s\n", asn1_strerror(rc));
        asn1_delete_structure(&definitions);
        return 1;
    }
    err_desc[0] = '\0';
    rc = asn1_der_decoding(&node, der, der_len, err_desc);
    if (rc != ASN1_SUCCESS) {
        fprintf(stderr, "asn1_der_decoding failed: %s\n",
                err_desc[0] ? err_desc : asn1_strerror(rc));
        asn1_delete_structure(&node);
        asn1_delete_structure(&definitions);
        return 1;
    }

    printf("libtasn1 %s round-trip test: OK (der_len=%d)\n", ASN1_VERSION, der_len);
    asn1_delete_structure(&node);
    asn1_delete_structure(&definitions);
    return 0;
}
