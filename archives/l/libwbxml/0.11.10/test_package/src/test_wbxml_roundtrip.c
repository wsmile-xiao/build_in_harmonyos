/* test_package — real WBXML round-trip via libwbxml core API.
 *
 * Encodes a small XML document to WBXML (wbxml_conv_xml2wbxml_*),
 * decodes the WBXML back to XML (wbxml_conv_wbxml2xml_*),
 * and asserts the round-trip is non-empty + semantically equivalent.
 * This exercises the public conversion API end-to-end — not a macro check.
 *
 * API signatures (from src/wbxml_conv.h):
 *   WBXMLError wbxml_conv_xml2wbxml_create(WBXMLConvXML2WBXML **conv);
 *   WBXMLError wbxml_conv_xml2wbxml_run(WBXMLConvXML2WBXML *conv,
 *                                      WB_UTINY *xml, WB_ULONG xml_len,
 *                                      WB_UTINY **wbxml, WB_ULONG *wbxml_len);
 *   void       wbxml_conv_xml2wbxml_destroy(WBXMLConvXML2WBXML *conv);
 *   WBXMLError wbxml_conv_wbxml2xml_create(WBXMLConvWBXML2XML **conv);
 *   WBXMLError wbxml_conv_wbxml2xml_run(WBXMLConvWBXML2XML *conv,
 *                                      WB_UTINY *wbxml, WB_ULONG wbxml_len,
 *                                      WB_UTINY **xml, WB_ULONG *xml_len);
 *   void       wbxml_conv_wbxml2xml_destroy(WBXMLConvWBXML2XML *conv);
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wbxml/wbxml.h>

/* WAP provisioning doc — WBXML_LANG_PROV10 is available because
 * WBXML_SUPPORT_PROV is defined in wbxml_config.h. */
static const char *XML_IN =
    "<?xml version=\"1.0\"?>\n"
    "<!DOCTYPE wap-provisioningdoc PUBLIC \"-//WAPFORUM//DTD PROV 1.0//EN\""
    " \"http://www.wapforum.org/DTD/prov.dtd\">\n"
    "<wap-provisioningdoc version=\"1.0\">\n"
    "  <characteristic type=\"ADDRESS\">\n"
    "    <parm name=\"BEARER\" value=\"GSM/CSD\"/>\n"
    "    <parm name=\"PORT\" value=\"9201\"/>\n"
    "  </characteristic>\n"
    "</wap-provisioningdoc>\n";

int main(void) {
    WBXMLError ret;
    WB_UTINY *wbxml_out = NULL;
    WB_ULONG  wbxml_len = 0;
    WB_UTINY *xml_back  = NULL;
    WB_ULONG  xml_back_len = 0;
    int failures = 0;

    /* ── Encode: XML → WBXML ── */
    WBXMLConvXML2WBXML *enc = NULL;
    ret = wbxml_conv_xml2wbxml_create(&enc);
    if (ret != WBXML_OK || enc == NULL) {
        fprintf(stderr, "FAIL: wbxml_conv_xml2wbxml_create: ret=%d %s\n",
                (int)ret, enc == NULL ? "(null conv)" : "");
        return 1;
    }
    ret = wbxml_conv_xml2wbxml_run(enc,
                                   (WB_UTINY *)XML_IN,
                                   (WB_ULONG)strlen(XML_IN),
                                   &wbxml_out, &wbxml_len);
    wbxml_conv_xml2wbxml_destroy(enc);
    if (ret != WBXML_OK) {
        fprintf(stderr, "FAIL: wbxml_conv_xml2wbxml_run: ret=%d\n", (int)ret);
        return 1;
    }
    if (wbxml_out == NULL || wbxml_len == 0) {
        fprintf(stderr, "FAIL: xml2wbxml produced empty WBXML\n");
        return 1;
    }
    /* Guard the diagnostic print: WBXML header is >= 3 bytes (version +
     * publicid + charset), so only index [0..2] when we actually have that
     * many. A truncated 1-2 byte buffer would otherwise read out of bounds
     * just to print a hex dump. */
    if (wbxml_len < 3) {
        fprintf(stderr,
                "FAIL: xml2wbxml produced truncated WBXML (%lu bytes, need >=3)\n",
                (unsigned long)wbxml_len);
        free(wbxml_out);
        return 1;
    }
    printf("OK encode: XML(%zuB) -> WBXML(%luB)\n", strlen(XML_IN),
           (unsigned long)wbxml_len);
    printf("   WBXML[0..3]=%02x %02x %02x %02x\n",
           wbxml_out[0], wbxml_out[1], wbxml_out[2],
           wbxml_len > 3 ? wbxml_out[3] : 0);

    /* ── Decode: WBXML → XML ── */
    WBXMLConvWBXML2XML *dec = NULL;
    ret = wbxml_conv_wbxml2xml_create(&dec);
    if (ret != WBXML_OK || dec == NULL) {
        fprintf(stderr, "FAIL: wbxml_conv_wbxml2xml_create: ret=%d %s\n",
                (int)ret, dec == NULL ? "(null conv)" : "");
        free(wbxml_out);
        return 1;
    }
    ret = wbxml_conv_wbxml2xml_run(dec,
                                    wbxml_out, wbxml_len,
                                    &xml_back, &xml_back_len);
    wbxml_conv_wbxml2xml_destroy(dec);
    if (ret != WBXML_OK) {
        fprintf(stderr, "FAIL: wbxml_conv_wbxml2xml_run: ret=%d\n", (int)ret);
        free(wbxml_out);
        return 1;
    }
    if (xml_back == NULL || xml_back_len == 0) {
        fprintf(stderr, "FAIL: wbxml2xml produced empty XML\n");
        free(wbxml_out);
        return 1;
    }
    printf("OK decode: WBXML(%luB) -> XML(%luB)\n",
           (unsigned long)wbxml_len, (unsigned long)xml_back_len);

    /* ── Round-trip semantic check ──
     * WBXML→XML may reflow whitespace/indentation, so compare key tokens. */
    const char *needles[] = {
        "wap-provisioningdoc", "characteristic", "BEARER", "GSM/CSD", "9201"};
    size_t n = sizeof(needles) / sizeof(needles[0]);
    for (size_t i = 0; i < n; i++) {
        if (!strstr((const char *)xml_back, needles[i])) {
            fprintf(stderr, "FAIL: round-trip XML missing token \"%s\"\n",
                    needles[i]);
            failures++;
        }
    }
    free(xml_back);
    free(wbxml_out);

    if (failures) {
        fprintf(stderr, "FAIL: %d token mismatch(es)\n", failures);
        return 1;
    }
    printf("OK round-trip: %zu/%zu tokens present\n", n, n);
    printf("ALL OK\n");
    return 0;
}
