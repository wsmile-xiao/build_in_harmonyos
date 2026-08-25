#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo '### Test of #! --shebang'
cat >/tmp/shebang <<EOF
#!/usr/local/bin/parallel --shebang -rk echo
A
B
C
EOF
chmod 755 /tmp/shebang
/tmp/shebang

echo '### Test of #! --hashbang'
cat >/tmp/shebang <<EOF
#!/usr/local/bin/parallel --hashbang -rk echo
A
B
C
EOF
chmod 755 /tmp/shebang
/tmp/shebang

echo '### Test of #! with 2 files as input (2 columns)'
cat >'/tmp/she <bang>"' <<EOF
#!/usr/local/bin/parallel --shebang -rk --xapply -a /tmp/123 echo
A
B
C
EOF
chmod 755 '/tmp/she <bang>"'
seq 1 3 >/tmp/123
'/tmp/she <bang>"'
