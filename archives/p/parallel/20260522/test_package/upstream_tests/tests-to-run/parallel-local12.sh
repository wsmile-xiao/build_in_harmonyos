#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

rm -f ~/.parallel/will-cite

resize=`resize`

# Disabled 2015-06-01
# 
# echo '### Test stdin goes to first command only ("-" as argument)'
# cat >/tmp/parallel-script-for-script <<EOF
# #!/bin/bash
# echo via first cat |parallel --tty -kv cat ::: - -
# EOF
# chmod 755 /tmp/parallel-script-for-script
# echo via pseudotty | script -q -f -c /tmp/parallel-script-for-script /dev/null
# sleep 2
# rm /tmp/parallel-script-for-script

echo '### Test xargs compatibility'

echo /tmp/1 > /tmp/files
echo 1 > /tmp/1

echo 'xargs Expect: 3 1'
echo 3 | xargs -P 1 -n 1 -a /tmp/files cat -
echo 'parallel Expect: 3 1 via psedotty  2'
cat >/tmp/parallel-script-for-script <<EOF
#!/bin/bash
echo 3 | parallel --tty -k -P 1 -n 1 -a /tmp/files cat -
EOF
chmod 755 /tmp/parallel-script-for-script
echo via pseudotty |
    script -q -f -c /tmp/parallel-script-for-script /dev/null |
    perl -ne '/tange|  .*/ or print'
sleep 1

echo 'xargs Expect: 1 3'
echo 3 | xargs -I {} -P 1 -n 1 -a /tmp/files cat {} -
echo 'parallel Expect: 1 3 2 via pseudotty'
cat >/tmp/parallel-script-for-script2 <<EOF
#!/bin/bash
echo 3 | parallel --tty -k -I {} -P 1 -n 1 -a /tmp/files cat {} -
EOF
chmod 755 /tmp/parallel-script-for-script2
echo via pseudotty |
    script -q -f -c /tmp/parallel-script-for-script2 /dev/null |
    perl -ne '/tange|  .*/ or print'
sleep 1

echo '### Test stdin goes to first command only ("cat" as argument)'
cat >/tmp/parallel-script-for-script2 <<EOF
#!/bin/bash
echo no output |parallel --tty -kv ::: 'echo a' 'cat'
EOF
chmod 755 /tmp/parallel-script-for-script2
echo via pseudotty |
    script -q -f -c /tmp/parallel-script-for-script2 /dev/null |
    perl -ne '/tange|  .*/ or print'
sleep 2
rm /tmp/parallel-script-for-script2

echo "### Test stdin as tty input for 'vi'"
echo 'NB: If this changes and the diff is printed to terminal, then'
echo "the terminal settings may be fucked up. Use 'reset' to get back."
cat >/tmp/parallel-script-for-script3 <<EOF
#!/bin/bash
seq 10 | parallel --tty -X vi file{}
EOF
chmod 755 /tmp/parallel-script-for-script3
echo ZZZZ |
    script -q -f -c /tmp/parallel-script-for-script3 /dev/null |
    perl -ne '/tange|  .*/ or print'
sleep 2
rm /tmp/parallel-script-for-script3

stdout parallel --citation < /dev/null |
    perl -ne '/tange|  .*/ or print'

touch ~/.parallel/will-cite
echo 1 > ~/.parallel/runs-without-willing-to-cite
# Clear screen
eval `resize`
seq $LINES | parallel -N0 echo > /dev/tty
reset
