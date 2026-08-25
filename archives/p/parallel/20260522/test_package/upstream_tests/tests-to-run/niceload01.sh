#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

forceswap() {
    perl -e '
	my $sleep_after = shift;
	
	# Only output if output is terminal
	my $output = -t STDOUT;
	
	sub freekb {
	    my $free = `free|grep buffers/cache`;
	    my @a=split / +/,$free;
	    if($a[3] > 0) {
		return $a[3];
	    }
	    my $free = `free|grep Mem:`;
	    my @a=split / +/,$free;
	    if($a[6] > 0) {
		return $a[6];
	    }
	    die;
	}
	
	sub swapkb {
	    my $swap = `free|grep Swap:`;
	    my @a=split / +/,$swap;
	    return $a[2];
	}
	
	my $swap = swapkb();
	my $lastswap = $swap;
	my $free = freekb();
	my @children;
	while($lastswap >= $swap) {
	    $output and print "Swap: $swap Free: $free";
	    $lastswap = $swap;
	    $swap = swapkb();
	    $free = freekb();
	    my $pct10 = $free * 1024 * 10/100;
	    my $use = ($pct10 > 2_000_000_000 ? 2_000_000_000 : $pct10);
	    my $used_mem_single = "x"x($use/1000);
	    # Faster for large values
	    my $used_mem = "$used_mem_single"x1000;
	    my $child = fork();
	    if($child) {
		push @children, $child;
	    } else {
	    	sleep 120;
	    	exit();
	    }
	}
	
	$output and print "Swap increased $lastswap -> $swap\n";
	if($sleep_after) {
	    $output and print "Sleep $sleep_after\n";
	    sleep $sleep_after;
	}
	kill "INT", @children;
	' $@
}

echo '### Test niceload -q'
niceload -q perl -e '$a = "works";$b="This $a\n"; print($b);'
echo

# Force swapping
forceswap >/dev/null
forceswap >/dev/null &

cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel -vj0 -k --joblog /tmp/jl-`basename $0` -L1 -r
echo '### --rm and --runmem'
  niceload  -H --rm 1g free -g | perl -ane '/Mem:/ and print $F[5],"\n"' | grep '[1-9]' >/dev/null && echo OK--rm
  niceload  -H --runmem 1g free -g | perl -ane '/Mem:/ and print $F[5],"\n"' | grep '[1-9]' >/dev/null && echo OK--runmem

echo '### -N and --noswap. Must give 0'
  niceload -H -N vmstat 1 2 | tail -n1 | awk '{print "-N " $7*$8}'
  niceload -H --noswap vmstat 1 2 | tail -n1 | awk '{print "--noswap " $7*$8}'
EOF

# force load > 10
while uptime | grep -Ev age:.[1-9][0-9]+.[0-9][0-9] >/dev/null ; do
    (timeout 5 nice perl -e 'while(1){}' 2>/dev/null &)
done

cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel -vj0 --joblog /tmp/jl-`basename $0` -L1
echo '### -H and --hard'
  niceload  -H -l 9.9 uptime | grep ':.[1-9][0-9].[0-9][0-9],' || echo OK-load below 9.9
  niceload  --hard -l 9 uptime | grep ':.[1-9][0-9].[0-9][0-9],' || echo OK-load below 10
EOF

cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel --timeout 300 -vj0 --joblog /tmp/jl-`basename $0` -L1
echo '### -f and --factor'
  niceload -H --factor 30 -l6 echo factor 30 finish last
  niceload -H -f 0.01 -l6 echo f 0.1 finish first
EOF

#echo '### Test niceload -p'
#sleep 3 &
#nice-load -v -p $!
