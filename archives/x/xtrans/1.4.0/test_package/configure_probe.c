#include <arpa/inet.h>
#include <netdb.h>
#include <stddef.h>
#include <sys/socket.h>

int main(void)
{
    socklen_t length = 0;
    struct sockaddr_storage storage;
    size_t interface_size = sizeof(length) + sizeof(storage);

    interface_size += sizeof(&getaddrinfo);
    interface_size += sizeof(&inet_ntop);
    return interface_size == 0;
}
