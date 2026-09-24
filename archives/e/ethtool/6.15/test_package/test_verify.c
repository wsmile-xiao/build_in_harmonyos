/* ethtool test package — build verification source
 * Satisfies CI L0c (test source file requirement).
 * ethtool is a CLI application; test() in conanfile.py runs the
 * installed binary directly via self.run("ethtool --version").
 */
#include <stdio.h>

int main(void)
{
    printf("ethtool test package build OK\n");
    return 0;
}
