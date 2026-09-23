#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include <linux/netfilter.h>
#include <libnftnl/common.h>
#include <libnftnl/table.h>

int main(void)
{
    struct nftnl_table *table = nftnl_table_alloc();
    const char *name;

    if (table == NULL)
        return 1;
    nftnl_table_set_str(table, NFTNL_TABLE_NAME, "consumer-table");
    name = nftnl_table_get_str(table, NFTNL_TABLE_NAME);
    if (name == NULL || name[0] != 'c')
        return 2;
    nftnl_table_set_u32(table, NFTNL_TABLE_FAMILY, NFPROTO_INET);
    if (nftnl_table_get_u32(table, NFTNL_TABLE_FAMILY) != NFPROTO_INET)
        return 3;
    nftnl_table_free(table);
    puts("libnftnl consumer API test: OK");
    return 0;
}
