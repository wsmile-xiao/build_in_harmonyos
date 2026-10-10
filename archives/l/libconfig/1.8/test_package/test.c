#include <stdio.h>
#include <string.h>

#include <libconfig.h>

int main(int argc, char **argv)
{
    config_t cfg;
    const char *host = NULL;
    int port = 0;
    int enabled = 0;
    int ok;

    if(argc != 2)
    {
        fprintf(stderr, "usage: %s <consumer.cfg>\n", argv[0]);
        return 2;
    }

    config_init(&cfg);
    if(!config_read_file(&cfg, argv[1]))
    {
        fprintf(stderr, "config_read_file: %s:%d\n",
                config_error_text(&cfg), config_error_line(&cfg));
        config_destroy(&cfg);
        return 1;
    }

    ok = config_lookup_string(&cfg, "server.host", &host)
         && config_lookup_int(&cfg, "server.port", &port)
         && config_lookup_bool(&cfg, "enabled", &enabled);

    if(ok)
    {
        printf("server.host=%s server.port=%d enabled=%d\n",
               host, port, enabled);
        ok = strcmp(host, "localhost") == 0 && port == 8080 && enabled == 1;
    }

    config_destroy(&cfg);

    if(ok)
    {
        printf("test libconfig 1.8 consumer: OK\n");
        return 0;
    }

    fprintf(stderr, "libconfig consumer assertions failed\n");
    return 1;
}
