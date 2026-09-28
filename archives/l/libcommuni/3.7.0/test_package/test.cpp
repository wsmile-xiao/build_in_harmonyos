#include <cstdio>

#include <IrcCore/IrcConnection>

int main(void)
{
    // R34: exercise the real libcommuni API (static-linked IrcCore/IrcModel/IrcUtil)
    IrcConnection connection;
    connection.setHost("irc.example.com");
    if (connection.host() != "irc.example.com") {
        std::fprintf(stderr, "IrcConnection host roundtrip failed\n");
        return 1;
    }
    std::printf("test libcommuni 3.7.0: OK\n");
    return 0;
}
