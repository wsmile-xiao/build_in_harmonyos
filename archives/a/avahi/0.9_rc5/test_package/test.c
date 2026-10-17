#include <avahi-common/address.h>
#include <avahi-common/malloc.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    AvahiAddress addr;
    char buf[AVAHI_ADDRESS_STR_MAX];
    
    // Test basic address parsing and formatting
    if (avahi_address_parse("127.0.0.1", AVAHI_PROTO_INET, &addr) == NULL) {
        fprintf(stderr, "Address parsing failed\n");
        return 1;
    }
    
    if (avahi_address_snprint(buf, sizeof(buf), &addr) == NULL) {
        fprintf(stderr, "Address formatting failed\n");
        return 1;
    }
    
    printf("Avahi address test: %s\n", buf);
    
    if (strcmp(buf, "127.0.0.1") != 0) {
        fprintf(stderr, "Address formatting mismatch\n");
        return 1;
    }
    
    printf("Avahi test passed\n");
    return 0;
}
