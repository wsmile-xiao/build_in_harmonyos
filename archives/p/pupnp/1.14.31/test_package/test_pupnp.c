#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <upnp/ixml.h>
#include <upnp/upnp.h>
#include <upnp/upnptools.h>

/* Self-contained check macro: the condition must always be evaluated, even
 * in Release builds where CMake adds -DNDEBUG and assert() compiles to
 * nothing. Callers keep side effects out of CHECK conditions. */
static int g_assertions = 0;

#define CHECK(cond)                                                   \
    do {                                                              \
        if (!(cond)) {                                                \
            fprintf(stderr, "CHECK failed at %s:%d: %s\n",            \
                    __FILE__, __LINE__, #cond);                       \
            abort();                                                  \
        }                                                             \
        g_assertions++;                                               \
    } while (0)

static const char *kDeviceDesc =
    "<?xml version=\"1.0\"?>"
    "<root xmlns=\"urn:schemas-upnp-org:device-1-0\">"
    "<specVersion><major>1</major><minor>0</minor></specVersion>"
    "<device>"
    "<deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>"
    "<friendlyName>HarmonyTest</friendlyName>"
    "<manufacturer>OHOS</manufacturer>"
    "<modelName>UT</modelName>"
    "<UDN>uuid:12345678-1234-1234-1234-123456789abc</UDN>"
    "</device>"
    "</root>";

static void scenario_ixml_dom(void)
{
    IXML_Document *doc = ixmlParseBuffer(kDeviceDesc);
    CHECK(doc != NULL);
    IXML_NodeList *types =
        ixmlDocument_getElementsByTagName(doc, "deviceType");
    CHECK(types != NULL);
    CHECK(ixmlNodeList_length(types) == 1);
    IXML_Node *typeElem = ixmlNodeList_item(types, 0);
    CHECK(typeElem != NULL);
    IXML_Node *typeText = ixmlNode_getFirstChild(typeElem);
    CHECK(typeText != NULL);
    const DOMString typeVal = ixmlNode_getNodeValue(typeText);
    CHECK(typeVal != NULL);
    CHECK(strcmp(typeVal,
                 "urn:schemas-upnp-org:device:MediaServer:1") == 0);
    IXML_NodeList *names =
        ixmlDocument_getElementsByTagName(doc, "friendlyName");
    CHECK(names != NULL);
    CHECK(ixmlNodeList_length(names) == 1);
    IXML_Node *nameElem = ixmlNodeList_item(names, 0);
    CHECK(nameElem != NULL);
    const DOMString nameVal =
        ixmlNode_getNodeValue(ixmlNode_getFirstChild(nameElem));
    CHECK(nameVal != NULL);
    CHECK(strcmp(nameVal, "HarmonyTest") == 0);
    DOMString xml = ixmlDocumenttoString(doc);
    CHECK(xml != NULL);
    CHECK(strstr(xml, "HarmonyTest") != NULL);
    ixmlFreeDOMString(xml);
    ixmlNodeList_free(types);
    ixmlNodeList_free(names);
    ixmlDocument_free(doc);
    printf("SCENARIO ixml_dom PASS\n");
}

static void scenario_upnp_preinit(void)
{
    /* Before any successful init the server accessors report empty. */
    CHECK(UpnpGetServerPort() == 0);
    CHECK(UpnpGetServerIpAddress() == NULL);
    const char *msg = UpnpGetErrorMessage(UPNP_E_SUCCESS);
    CHECK(msg != NULL);
    CHECK(strlen(msg) > 0);
    printf("SCENARIO upnp_preinit PASS\n");
}

static void scenario_upnp_init(void)
{
    /* Full SDK lifecycle on the default interface (mirrors upstream
     * test_init, which requires UpnpInit2 success on the test host). */
    int rc = UpnpInit2(NULL, 0);
    CHECK(rc == UPNP_E_SUCCESS);
    {
        unsigned short port = UpnpGetServerPort();
        CHECK(port != 0);
        char *ip = UpnpGetServerIpAddress();
        CHECK(ip != NULL);
        CHECK(strlen(ip) > 0);
        printf("UPNP bound ip=%s port=%u\n", ip, (unsigned)port);
    }
    CHECK(UpnpFinish() == UPNP_E_SUCCESS);
    CHECK(UpnpGetServerPort() == 0);
    printf("SCENARIO upnp_init PASS\n");
}

int main(void)
{
    scenario_ixml_dom();
    scenario_upnp_preinit();
    scenario_upnp_init();
    printf("PUPNP_CONSUMER_TEST PASS assertions=%d\n", g_assertions);
    return 0;
}
