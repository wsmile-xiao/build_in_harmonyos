/*
 * test_package.c — libtatsu 1.0.5 offline consumer verification.
 *
 * Verifies the installed Conan package from the public API only:
 *   1. C consumer can include <libtatsu/tss.h> and link
 *   2. request object creation / overrides / parameters from manifest
 *   3. request field add + read round-trip (incl. backported dict helpers)
 *   4. request serialization to the exact TSS XML contract
 *   5. successful response parsing (mock server, 127.0.0.1 only)
 *   6. negative paths: HTTP non-2xx, connection refused, malformed body,
 *      missing required fields, NULL/empty inputs
 *   7. response accessors (ticket / path / blob)
 *   8. memory ownership and cleanup
 *
 * The mock HTTP server is an in-process socket listener bound to
 * 127.0.0.1 with a programmatically generated fixture; no public
 * network, real Apple TSS service, device identity or account is used.
 */
#include <libtatsu/tss.h>
#include <libtatsu/tatsu.h>
#include <plist/plist.h>

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/* portable case-insensitive substring search (musl/OHOS has no
 * strcasestr unless _GNU_SOURCE is defined before any header) */
static char *find_ci(const char *haystack, const char *needle)
{
    size_t nlen = strlen(needle);
    if (nlen == 0) return (char*)haystack;
    for (const char *p = haystack; *p; p++) {
        if (strncasecmp(p, needle, nlen) == 0) return (char*)p;
    }
    return NULL;
}

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, name) do { \
    g_checks++; \
    if (cond) { printf("[PASS] %s\n", (name)); } \
    else { g_failed++; printf("[FAIL] %s (line %d)\n", (name), __LINE__); } \
} while (0)

/* ------------------------------------------------------------------ */
/* Minimal in-process HTTP mock server (127.0.0.1 only)                */
/* ------------------------------------------------------------------ */

#define MOCK_HTTP_RESPONSE_HEADER \
    "HTTP/1.1 %d %s\r\n" \
    "Content-Type: text/html\r\n" \
    "Content-Length: %zu\r\n" \
    "Connection: close\r\n" \
    "\r\n"

/* TSS wire contract: status line first, then the XML payload. Response
 * ticket key has NO '@' prefix (matches idevicerestore's response
 * consumption: plist_dict_get_item(tss, "ApImg4Ticket")); the '@' is
 * only used on the request side. */
#define MOCK_TSS_SUCCESS_BODY \
    "STATUS=0&MESSAGE=SUCCESS\n<?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
    "<plist version=\"1.0\"><dict>" \
    "<key>ApImg4Ticket</key><data>AAECAwQFBgcICQ==</data>" \
    "<key>ApBoardID</key><integer>8</integer>" \
    "<key>ApChipID</key><integer>4900</integer>" \
    "<key>ApSecurityDomain</key><integer>1</integer>" \
    "<key>ApECID</key><integer>71324398718</integer>" \
    "<key>KernelCache</key><dict>" \
    "<key>Path</key><string>/usr/standalone/firmware/kernelcache.release.test</string>" \
    "<key>Blob</key><data>AAECAwQFBgcICQ==</data>" \
    "</dict>" \
    "</dict></plist>"

typedef struct {
    int listen_fd;
    int port;
    /* captured request (owned) */
    char *last_request;
    size_t last_request_len;
    /* response to send */
    char *response_body;
    int response_status;
    int response_close_early; /* simulate connection failure after headers */
} mock_server;

static void mock_server_init(mock_server *srv)
{
    memset(srv, 0, sizeof(*srv));
    srv->listen_fd = -1;
}

static int mock_server_start(mock_server *srv)
{
    struct sockaddr_in addr;
    socklen_t addrlen = sizeof(addr);
    int one = 1;

    srv->listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (srv->listen_fd < 0) return -1;
    setsockopt(srv->listen_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    /* bind to loopback ONLY — this test never touches a real network */
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0; /* kernel picks a free port */

    if (bind(srv->listen_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(srv->listen_fd);
        srv->listen_fd = -1;
        return -1;
    }
    if (listen(srv->listen_fd, 4) < 0) {
        close(srv->listen_fd);
        srv->listen_fd = -1;
        return -1;
    }
    if (getsockname(srv->listen_fd, (struct sockaddr*)&addr, &addrlen) < 0) {
        close(srv->listen_fd);
        srv->listen_fd = -1;
        return -1;
    }
    srv->port = ntohs(addr.sin_port);
    return 0;
}

/* Serve exactly one request and capture the raw POST body. */
static int mock_server_serve_once(mock_server *srv)
{
    char buf[8192];
    int client = accept(srv->listen_fd, NULL, NULL);
    size_t body_len = 0;
    char *body = NULL;
    ssize_t n;
    size_t total = 0;
    char header[512];
    int header_len;

    if (client < 0) return -1;

    while ((n = read(client, buf, sizeof(buf))) > 0) {
        char *newbuf = (char*)realloc(body, total + (size_t)n + 1);
        if (!newbuf) { free(body); close(client); return -1; }
        body = newbuf;
        memcpy(body + total, buf, (size_t)n);
        total += (size_t)n;
        body[total] = '\0';
        /* end of request: blank line separator, non-chunked POST */
        char *sep = strstr(body, "\r\n\r\n");
        if (sep && total >= (size_t)(sep - body) + 4) {
            /* content-length based completion check */
            char *cl = find_ci(body, "Content-Length:");
            if (cl) {
                long want = strtol(cl + 15, NULL, 10);
                if ((long)(total - (sep - body) - 4) >= want) break;
            } else {
                break;
            }
        }
    }

    free(srv->last_request);
    srv->last_request = body;
    srv->last_request_len = total;

    if (srv->response_close_early) {
        /* simulate connection failure: close without sending anything */
        close(client);
        return 0;
    }

    body_len = strlen(srv->response_body);
    header_len = snprintf(header, sizeof(header), MOCK_HTTP_RESPONSE_HEADER,
                          srv->response_status,
                          srv->response_status == 200 ? "OK" : "Service Unavailable",
                          body_len);
    write(client, header, (size_t)header_len);
    write(client, srv->response_body, body_len);
    close(client);
    return 0;
}

/* Serve up to max_requests requests (the upstream client retries 15
 * times on unparseable responses, so the mock must keep answering).
 * The listening socket has a 3 s accept timeout, so the serving child
 * exits shortly after the parent stops connecting. */
static int mock_server_serve_loop(mock_server *srv, int max_requests)
{
    struct timeval tv;
    tv.tv_sec = 3;
    tv.tv_usec = 0;
    setsockopt(srv->listen_fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    for (int i = 0; i < max_requests; i++) {
        if (mock_server_serve_once(srv) < 0) {
            /* accept timed out (or error): no more requests coming */
            return (i > 0) ? 0 : -1;
        }
    }
    return 0;
}

static void mock_server_stop(mock_server *srv)
{
    if (srv->listen_fd >= 0) close(srv->listen_fd);
    srv->listen_fd = -1;
    free(srv->last_request);
    srv->last_request = NULL;
    free(srv->response_body);
    srv->response_body = NULL;
}

/* Build a http://127.0.0.1:port URL string (caller frees). */
static char *mock_server_url(mock_server *srv)
{
    char *url = (char*)malloc(64);
    if (url) snprintf(url, 64, "http://127.0.0.1:%d", srv->port);
    return url;
}

/* ------------------------------------------------------------------ */
/* 1-3: offline API tests (no network at all)                          */
/* ------------------------------------------------------------------ */

static void test_version_and_headers(void)
{
    const char *v = libtatsu_version();
    CHECK(v != NULL, "libtatsu_version() returns non-NULL");
    CHECK(strcmp(v, "1.0.5") == 0, "libtatsu_version() == \"1.0.5\"");
}

static void test_request_create_free(void)
{
    plist_t req = tss_request_new(NULL);
    CHECK(req != NULL, "tss_request_new(NULL) creates request");

    /* base fields set by the library itself */
    CHECK(plist_dict_get_item(req, "@HostPlatformInfo") != NULL,
          "request has @HostPlatformInfo");
    CHECK(plist_dict_get_item(req, "@VersionInfo") != NULL,
          "request has @VersionInfo");
    CHECK(plist_dict_get_item(req, "@UUID") != NULL,
          "request has @UUID");

    plist_free(req);
    req = NULL;

    /* overrides path: user-supplied keys must override defaults */
    plist_t overrides = plist_new_dict();
    plist_dict_set_item(overrides, "@HostPlatformInfo", plist_new_string("linux"));
    plist_dict_set_item(overrides, "CustomKey", plist_new_uint(4711));
    req = tss_request_new(overrides);
    CHECK(req != NULL, "tss_request_new(overrides) creates request");
    char *host = NULL;
    plist_t node = plist_dict_get_item(req, "@HostPlatformInfo");
    if (node) plist_get_string_val(node, &host);
    CHECK(host && strcmp(host, "linux") == 0,
          "overrides replace @HostPlatformInfo");
    free(host);
    uint64_t uval = 0;
    node = plist_dict_get_item(req, "CustomKey");
    if (node) plist_get_uint_val(node, &uval);
    CHECK(uval == 4711, "overrides add custom keys");
    plist_free(overrides);
    plist_free(req);
}

static void test_parameters_from_manifest(void)
{
    /* programmatic minimal BuildIdentity fixture (invented values, no real
     * device identity: ECID/chip ids below are made-up small numbers) */
    plist_t manifest = plist_new_dict();
    plist_dict_set_item(manifest, "UniqueBuildID", plist_new_data("\x01\x02\x03\x04", 4));
    plist_dict_set_item(manifest, "Ap,OSLongVersion", plist_new_string("22C150"));
    plist_dict_set_item(manifest, "Ap,OSReleaseType", plist_new_string("Beta"));
    plist_dict_set_item(manifest, "Ap,ProductMarketingVersion", plist_new_string("22.2"));
    plist_dict_set_item(manifest, "Ap,ProductType", plist_new_string("D99AP"));
    plist_dict_set_item(manifest, "Ap,SDKPlatform", plist_new_string("iPhoneOS"));
    plist_dict_set_item(manifest, "Ap,Target", plist_new_string("arm64e"));
    plist_dict_set_item(manifest, "Ap,TargetType", plist_new_string("app"));
    plist_dict_set_item(manifest, "ApChipID", plist_new_uint(0x8000));
    plist_dict_set_item(manifest, "ApBoardID", plist_new_uint(0x0C));
    plist_dict_set_item(manifest, "ApSecurityDomain", plist_new_uint(1));

    plist_t parameters = plist_new_dict();
    int rc = tss_parameters_add_from_manifest(parameters, manifest, false);
    CHECK(rc == 0, "tss_parameters_add_from_manifest returns 0");

    uint64_t chip = 0;
    plist_t node = plist_dict_get_item(parameters, "ApChipID");
    if (node) plist_get_uint_val(node, &chip);
    CHECK(chip == 0x8000, "parameters contain ApChipID (dict_copy_uint path)");

    char *osver = NULL;
    node = plist_dict_get_item(parameters, "Ap,OSLongVersion");
    if (node) plist_get_string_val(node, &osver);
    CHECK(osver && strcmp(osver, "22C150") == 0,
          "parameters contain Ap,OSLongVersion (dict_copy_string path)");
    free(osver);

    uint64_t dlen = 0;
    char *data = NULL;
    node = plist_dict_get_item(parameters, "UniqueBuildID");
    if (node) plist_get_data_val(node, &data, &dlen);
    CHECK(data && dlen == 4 && memcmp(data, "\x01\x02\x03\x04", 4) == 0,
          "parameters contain UniqueBuildID (dict_copy_data path)");
    free(data);

    /* negative: missing UniqueBuildID must fail (fail-closed) */
    plist_t bad = plist_new_dict();
    plist_dict_set_item(bad, "ApChipID", plist_new_uint(1));
    plist_t params2 = plist_new_dict();
    rc = tss_parameters_add_from_manifest(params2, bad, false);
    CHECK(rc == -1, "manifest without UniqueBuildID fails");
    plist_free(bad);
    plist_free(params2);

    plist_free(manifest);
    plist_free(parameters);
}

static void test_request_tag_builders(void)
{
    plist_t parameters = plist_new_dict();
    plist_dict_set_item(parameters, "ApECID", plist_new_uint(12345));
    plist_dict_set_item(parameters, "UniqueBuildID", plist_new_data("\xAA\xBB", 2));
    plist_dict_set_item(parameters, "ApChipID", plist_new_uint(0x8000));
    plist_dict_set_item(parameters, "ApBoardID", plist_new_uint(12));
    plist_dict_set_item(parameters, "ApSecurityDomain", plist_new_uint(1));

    plist_t request = tss_request_new(NULL);

    int rc = tss_request_add_common_tags(request, parameters, NULL);
    CHECK(rc == 0, "tss_request_add_common_tags returns 0");

    uint64_t ecid = 0;
    plist_t node = plist_dict_get_item(request, "ApECID");
    if (node) plist_get_uint_val(node, &ecid);
    CHECK(ecid == 12345, "request contains ApECID after add_common_tags");

    /* negative: img4 tags without ApNonce must fail */
    plist_t minimal = plist_new_dict();
    plist_dict_set_item(minimal, "ApChipID", plist_new_uint(1));
    rc = tss_request_add_ap_img4_tags(request, minimal);
    CHECK(rc == -1, "add_ap_img4_tags without ApNonce fails");

    /* with the required fields present it must succeed */
    plist_dict_set_item(minimal, "ApNonce", plist_new_data("\x11\x22\x33", 3));
    plist_dict_set_item(minimal, "ApSecurityMode", plist_new_bool(1));
    plist_dict_set_item(minimal, "ApProductionMode", plist_new_bool(0));
    rc = tss_request_add_ap_img4_tags(request, minimal);
    CHECK(rc == 0, "add_ap_img4_tags with required fields returns 0");

    uint8_t bval = 2;
    node = plist_dict_get_item(request, "@ApImg4Ticket");
    if (node) plist_get_bool_val(node, &bval);
    CHECK(bval == 1, "@ApImg4Ticket set to true by add_ap_img4_tags");

    /* overrides merged in add_common_tags */
    plist_t request2 = tss_request_new(NULL);
    plist_t ovr = plist_new_dict();
    plist_dict_set_item(ovr, "ApECID", plist_new_uint(999));
    rc = tss_request_add_common_tags(request2, parameters, ovr);
    CHECK(rc == 0, "add_common_tags with overrides returns 0");
    uint64_t ecid2 = 0;
    node = plist_dict_get_item(request2, "ApECID");
    if (node) plist_get_uint_val(node, &ecid2);
    CHECK(ecid2 == 999, "overrides win over parameters in add_common_tags");

    plist_free(ovr);
    plist_free(request2);
    plist_free(minimal);
    plist_free(request);
    plist_free(parameters);
}

static void test_null_and_negative_inputs(void)
{
    /* NULL-tolerant call sites that the API must handle fail-closed */
    plist_t request = tss_request_new(NULL);
    plist_t empty = plist_new_dict();

    int rc = tss_request_add_ap_img4_tags(request, NULL);
    CHECK(rc == -1, "add_ap_img4_tags(NULL parameters) fails");

    rc = tss_request_add_ap_img4_tags(request, empty);
    CHECK(rc == -1, "add_ap_img4_tags(empty parameters) fails");

    rc = tss_request_add_common_tags(request, empty, NULL);
    CHECK(rc == 0, "add_common_tags with empty parameters returns 0 (no required fields)");

    plist_free(empty);
    plist_free(request);
}

/* ------------------------------------------------------------------ */
/* 4: request serialization contract                                   */
/* ------------------------------------------------------------------ */

/* The TSS wire format is a XML plist POST body. We verify the exact
 * serialized shape for a fully controlled request (deterministic fields
 * via overrides, no random UUID by replacing it after creation). */
static void test_request_serialization(void)
{
    plist_t request = tss_request_new(NULL);

    /* pin down the nondeterministic fields for exact matching */
    plist_dict_set_item(request, "@UUID", plist_new_string("00000000-1111-2222-3333-444444444444"));
    plist_dict_set_item(request, "ApECID", plist_new_uint(12345));
    plist_dict_set_item(request, "ApChipID", plist_new_uint(0x8000));
    plist_dict_set_item(request, "@ApImg4Ticket", plist_new_bool(1));

    char *xml = NULL;
    uint32_t size = 0;
    plist_to_xml(request, &xml, &size);
    CHECK(xml != NULL && size > 0, "plist_to_xml serializes request");

    /* exact key/value contracts of the serialized request body */
    CHECK(strstr(xml, "<key>ApECID</key>") != NULL, "serialized body has ApECID key");
    CHECK(strstr(xml, "<integer>12345</integer>") != NULL, "serialized ApECID value");
    CHECK(strstr(xml, "<key>ApChipID</key>") != NULL, "serialized body has ApChipID key");
    CHECK(strstr(xml, "<integer>32768</integer>") != NULL, "serialized ApChipID value (32768)");
    CHECK(strstr(xml, "<key>@ApImg4Ticket</key>") != NULL, "serialized body has @ApImg4Ticket");
    CHECK(strstr(xml, "<true/>") != NULL, "boolean serialized as <true/>");
    CHECK(strstr(xml, "00000000-1111-2222-3333-444444444444") != NULL,
          "serialized @UUID override value");
    CHECK(strncmp(xml, "<?xml", 5) == 0, "serialized body starts with XML declaration");

    /* empty request still serializes to a valid plist root
     * (plist_to_xml requires a non-NULL length out-param) */
    plist_t empty_req = tss_request_new(NULL);
    plist_dict_set_item(empty_req, "@UUID", plist_new_string("00000000-1111-2222-3333-444444444444"));
    char *xml2 = NULL;
    uint32_t size2 = 0;
    plist_to_xml(empty_req, &xml2, &size2);
    CHECK(xml2 != NULL && size2 > 0 && strstr(xml2, "@HostPlatformInfo") != NULL,
          "base request fields survive serialization");
    free(xml2);
    plist_free(empty_req);

    free(xml);
    plist_free(request);
}

/* ------------------------------------------------------------------ */
/* 5-9: mock HTTP server tests (loopback only, no public network)      */
/* ------------------------------------------------------------------ */

/* Serialize a request deterministically the way tss_request_send does,
 * to compare against what the mock server actually received. */
static char *build_deterministic_request_xml(void)
{
    plist_t request = tss_request_new(NULL);
    plist_dict_set_item(request, "@UUID", plist_new_string("00000000-1111-2222-3333-444444444444"));
    plist_dict_set_item(request, "ApECID", plist_new_uint(12345));
    char *xml = NULL;
    uint32_t sz = 0;
    plist_to_xml(request, &xml, &sz);
    plist_free(request);
    return xml;
}

static void test_send_success(void)
{
    mock_server srv;
    mock_server_init(&srv);
    CHECK(mock_server_start(&srv) == 0, "mock server started on 127.0.0.1");

    srv.response_body = strdup(MOCK_TSS_SUCCESS_BODY);
    srv.response_status = 200;

    plist_t request = tss_request_new(NULL);
    plist_dict_set_item(request, "ApECID", plist_new_uint(12345));
    /* pin the random @UUID for exact body comparison */
    plist_dict_set_item(request, "@UUID",
        plist_new_string("00000000-1111-2222-3333-444444444444"));

    /* The mock runs in a forked child so the (blocking) library call can
     * run in the parent concurrently. The captured raw request is shipped
     * back through a pipe: the child owns the capture, the parent owns
     * the verification. */
    int req_pipe[2];
    CHECK(pipe(req_pipe) == 0, "capture pipe created");

    pid_t pid = fork();
    if (pid == 0) {
        /* child: serve requests until the parent's connection attempts
         * stop (upstream breaks the retry loop on MESSAGE=SUCCESS, so
         * exactly one request is expected) */
        close(req_pipe[0]);
        mock_server_serve_loop(&srv, 16);
        if (srv.last_request) {
            uint32_t len = (uint32_t)srv.last_request_len;
            write(req_pipe[1], &len, sizeof(len));
            write(req_pipe[1], srv.last_request, len);
        }
        close(req_pipe[1]);
        _exit(0);
    }
    close(req_pipe[1]);

    char *url = mock_server_url(&srv);
    plist_t response = tss_request_send(request, url);

    int status = 0;
    waitpid(pid, &status, 0);

    /* read back what the server actually received */
    char *captured = NULL;
    uint32_t captured_len = 0;
    if (read(req_pipe[0], &captured_len, sizeof(captured_len)) == (ssize_t)sizeof(captured_len)
        && captured_len > 0 && captured_len < 65536) {
        captured = (char*)calloc(captured_len + 1, 1);
        if (read(req_pipe[0], captured, captured_len) != (ssize_t)captured_len) {
            free(captured); captured = NULL;
        }
    }
    close(req_pipe[0]);

    CHECK(response != NULL, "tss_request_send returns parsed response for SUCCESS");

    if (response) {
        /* ticket accessor: response ticket key (no '@') as data */
        unsigned char *ticket = NULL;
        unsigned int ticket_len = 0;
        int rc = tss_response_get_ap_img4_ticket(response, &ticket, &ticket_len);
        CHECK(rc == 0, "tss_response_get_ap_img4_ticket returns 0");
        /* fixture base64: AAECAwQFBgcICQ== -> 00 01 02 03 04 05 06 07 08 09 */
        CHECK(ticket != NULL && ticket_len == 10,
              "ticket data length is 10 (AAECAwQFBgcICQ==)");
        CHECK(ticket && ticket_len == 10 &&
              memcmp(ticket, "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09", 10) == 0,
              "ticket bytes decode exactly from base64 fixture");
        free(ticket);

        /* path/blob accessors: KernelCache entry has Path + Blob */
        char *path = NULL;
        rc = tss_response_get_path_by_entry(response, "KernelCache", &path);
        CHECK(rc == 0 && path &&
              strcmp(path, "/usr/standalone/firmware/kernelcache.release.test") == 0,
              "tss_response_get_path_by_entry returns exact Path string");
        free(path);

        unsigned char *blob = NULL;
        rc = tss_response_get_blob_by_path(response,
              "/usr/standalone/firmware/kernelcache.release.test", &blob);
        CHECK(rc == 0 && blob != NULL, "tss_response_get_blob_by_path returns blob");
        free(blob);

        rc = tss_response_get_blob_by_entry(response, "KernelCache", &blob);
        CHECK(rc == 0 && blob != NULL, "tss_response_get_blob_by_entry returns blob");
        free(blob);

        plist_free(response);
    }

    /* verify what the server received: request line, headers, exact body */
    CHECK(captured != NULL, "mock server captured the request");
    if (captured) {
        CHECK(strncmp(captured, "POST /", 6) == 0,
              "request uses HTTP POST");
        CHECK(find_ci(captured, "Content-Type: text/xml") != NULL,
              "request Content-Type is text/xml");
        CHECK(find_ci(captured, "User-Agent: InetURL/1.0") != NULL,
              "request User-Agent is InetURL/1.0");
        CHECK(find_ci(captured, "Cache-Control: no-cache") != NULL,
              "request has Cache-Control: no-cache header");
        char *expected = build_deterministic_request_xml();
        /* the body is after the blank line */
        char *body = strstr(captured, "\r\n\r\n");
        if (body) body += 4;
        CHECK(body && expected && strcmp(body, expected) == 0,
              "request body matches the exact serialized plist");
        free(expected);
    }
    free(captured);

    free(url);
    plist_free(request);
    mock_server_stop(&srv);
}

static void test_send_http_error(void)
{
    mock_server srv;
    mock_server_init(&srv);
    CHECK(mock_server_start(&srv) == 0, "mock server started (error case)");

    /* HTTP 503 + STATUS=100: upstream breaks out of the retry loop
     * immediately (status 100 = "server error, most likely the request
     * was malformed") and must fail closed with NULL. */
    srv.response_body = strdup("STATUS=100&MESSAGE=ERROR\n");
    srv.response_status = 503;

    plist_t request = tss_request_new(NULL);
    pid_t pid = fork();
    if (pid == 0) {
        mock_server_serve_loop(&srv, 20);
        _exit(0);
    }
    char *url = mock_server_url(&srv);
    plist_t response = tss_request_send(request, url);
    int status = 0;
    waitpid(pid, &status, 0);

    CHECK(response == NULL,
          "tss_request_send returns NULL for HTTP 503 + STATUS=100");

    free(url);
    plist_free(request);
    mock_server_stop(&srv);
}

static void test_send_connection_failure(void)
{
    /* Connect to a loopback port with no listener: each attempt fails
     * immediately (ECONNREFUSED, no sleep-inducing body). Upstream
     * retries 15 times with sleep(2) between attempts (~30 s) and must
     * end with NULL. This is the documented fail-closed behaviour for
     * an unreachable endpoint. */
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    socklen_t len = sizeof(addr);
    bind(fd, (struct sockaddr*)&addr, sizeof(addr));
    getsockname(fd, (struct sockaddr*)&addr, &len);
    int dead_port = ntohs(addr.sin_port);
    close(fd);

    char url[64];
    snprintf(url, sizeof(url), "http://127.0.0.1:%d", dead_port);

    plist_t request = tss_request_new(NULL);
    plist_t response = tss_request_send(request, url);
    CHECK(response == NULL,
          "tss_request_send returns NULL when connection is refused");
    plist_free(request);
}

static void test_send_malformed_response(void)
{
    mock_server srv;
    mock_server_init(&srv);
    CHECK(mock_server_start(&srv) == 0, "mock server started (malformed case)");

    /* STATUS=0 + MESSAGE=SUCCESS but no XML payload: status_code becomes
     * 0 so the retry loop exits and the "Incorrectly formatted TSS
     * response" path must return NULL without hanging. */
    srv.response_body = strdup("STATUS=0&MESSAGE=SUCCESS\n(garbage, no xml)");
    srv.response_status = 200;

    plist_t request = tss_request_new(NULL);
    pid_t pid = fork();
    if (pid == 0) {
        mock_server_serve_loop(&srv, 20);
        _exit(0);
    }
    char *url = mock_server_url(&srv);
    plist_t response = tss_request_send(request, url);
    int status = 0;
    waitpid(pid, &status, 0);

    CHECK(response == NULL,
          "tss_request_send returns NULL when SUCCESS response lacks XML plist");

    free(url);
    plist_free(request);
    mock_server_stop(&srv);
}

static void test_send_empty_response(void)
{
    mock_server srv;
    mock_server_init(&srv);
    CHECK(mock_server_start(&srv) == 0, "mock server started (empty case)");

    /* Empty 200 body: no STATUS= is parseable, so upstream enters its
     * retry loop (15 attempts, sleep(2) between them, ~30 s) and the
     * server must answer every attempt; the final result is still NULL.
     * This deliberately exercises the documented upstream retry path. */
    srv.response_body = strdup("");
    srv.response_status = 200;

    plist_t request = tss_request_new(NULL);
    pid_t pid = fork();
    if (pid == 0) {
        mock_server_serve_loop(&srv, 20);
        _exit(0);
    }
    char *url = mock_server_url(&srv);
    plist_t response = tss_request_send(request, url);
    int status = 0;
    waitpid(pid, &status, 0);

    CHECK(response == NULL,
          "tss_request_send returns NULL for empty 200 response");

    free(url);
    plist_free(request);
    mock_server_stop(&srv);
}

/* ------------------------------------------------------------------ */
/* 10: response accessors on crafted plist (offline)                   */
/* ------------------------------------------------------------------ */

static void test_response_accessors_offline(void)
{
    /* craft a response plist directly (as tss_request_send would return);
     * response ticket key has no '@' prefix (TSS wire convention) */
    plist_t response = plist_new_dict();
    plist_dict_set_item(response, "ApImg4Ticket", plist_new_data("\xDE\xAD\xBE\xEF", 4));

    unsigned char *ticket = NULL;
    unsigned int tlen = 0;
    int rc = tss_response_get_ap_img4_ticket(response, &ticket, &tlen);
    CHECK(rc == 0 && ticket && tlen == 4 && memcmp(ticket, "\xDE\xAD\xBE\xEF", 4) == 0,
          "ap_img4_ticket accessor round-trips data");
    free(ticket);

    /* ap_ticket reads the APTicket key; response only has ApImg4Ticket, so
     * it must fail WITHOUT touching the caller's out-params (ownership:
     * on failure nothing is allocated, caller frees only on rc == 0) */
    ticket = NULL;
    rc = tss_response_get_ap_ticket(response, &ticket, &tlen);
    CHECK(rc == -1 && ticket == NULL,
          "ap_ticket fails cleanly when response has no APTicket key");

    /* negative: missing entry */
    plist_t empty = plist_new_dict();
    ticket = (unsigned char*)0x1; tlen = 0;
    rc = tss_response_get_ap_ticket(empty, &ticket, &tlen);
    CHECK(rc == -1, "ap_ticket on empty response fails");
    char *no_path = (char*)0x1;
    rc = tss_response_get_path_by_entry(empty, "NoSuchEntry", &no_path);
    CHECK(rc == -1 && no_path == NULL, "get_path_by_entry on missing entry fails");
    unsigned char *blob = NULL;
    rc = tss_response_get_blob_by_path(empty, "NoSuchPath", &blob);
    CHECK(rc == -1, "get_blob_by_path on missing path fails");
    plist_free(empty);

    /* NULL input */
    rc = tss_response_get_ap_ticket(NULL, &ticket, &tlen);
    CHECK(rc == -1, "ap_ticket on NULL response fails");

    plist_free(response);
}

/* ------------------------------------------------------------------ */
/* main                                                                */
/* ------------------------------------------------------------------ */

int main(void)
{
    signal(SIGPIPE, SIG_IGN);

    printf("== libtatsu 1.0.5 test_package (offline, loopback mock) ==\n");

    test_version_and_headers();
    test_request_create_free();
    test_parameters_from_manifest();
    test_request_tag_builders();
    test_null_and_negative_inputs();
    test_request_serialization();
    test_response_accessors_offline();

    test_send_success();
    test_send_http_error();
    test_send_connection_failure();
    test_send_malformed_response();
    test_send_empty_response();

    printf("\nTotal: %d checks, Failed: %d\n", g_checks, g_failed);
    return (g_failed == 0) ? 0 : 1;
}
