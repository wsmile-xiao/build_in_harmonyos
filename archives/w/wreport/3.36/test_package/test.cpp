#include <wreport/var.h>
#include <wreport/vartable.h>

#include <string>

int main()
{
    const auto* table = wreport::Vartable::get_bufr("B0000000000000014000");
    const auto info = table->query(WR_VAR(0, 1, 15));
    if (!table->contains(WR_VAR(0, 1, 15))) return 1;

    wreport::Var site(info);
    site.setc("HarmonyOS");
    if (!site.isset() || site.enqs() != "HarmonyOS") return 2;

    const wreport::Var copy(site);
    if (copy.enqs() != "HarmonyOS" || !(copy == site)) return 3;
    return 0;
}
