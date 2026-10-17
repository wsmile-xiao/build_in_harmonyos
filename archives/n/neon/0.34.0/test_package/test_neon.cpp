// neon consumer test (L0c + R34): standalone test source executed
// via self.run (clang++ link) from conanfile.py test().
// R34: actually call the tested API — ne_sock_init() +
// ne_uri_parse() (pure user-space, no network required).
#include <neon/ne_uri.h>
#include <neon/ne_socket.h>
#include <cstdio>

int main() {
    if (ne_sock_init() != 0) {
        std::fprintf(stderr, "ne_sock_init failed\n");
        return 1;
    }
    ne_uri uri;
    if (ne_uri_parse("https://example.com:443/path", &uri) != 0) {
        std::fprintf(stderr, "ne_uri_parse failed\n");
        return 1;
    }
    if (uri.scheme == NULL || uri.host == NULL) {
        std::fprintf(stderr, "uri parse incomplete\n");
        return 1;
    }
    std::printf("OK: neon 0.34.0 (sock_init + uri_parse ok: %s://%s)\n",
                uri.scheme, uri.host);
    ne_sock_exit();
    return 0;
}
