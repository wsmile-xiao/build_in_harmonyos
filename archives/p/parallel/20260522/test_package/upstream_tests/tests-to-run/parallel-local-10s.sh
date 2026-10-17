#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Simple jobs that never fails
# Each should be taking 10-30s and be possible to run in parallel
# I.e.: No race conditions, no logins

par__zextract() {
    # Generate /tmp/zextract.{bz2,gz,zst,raw}
    seq 1000000 |
	parallel -j0 --pipe --tee '{1} > /tmp/zextract.{2}' \
		 ::: 'bzip2 -1' 'gzip -1' 'zstd -1' cat :::+ bz2 gz zst raw
    # Here with wrong extension to test 4CC detection
    parallel cp {} {}.bin ::: /tmp/zextract.{bz2,gz,zst,raw}
    doit() {
	parallel -k --block -1 --tagstring "$1-$2" $2 -j4 --pipepart -a $1 wc
    }
    export -f doit
    stdout parallel -j 25% -k doit ::: /tmp/zextract.{bz2,gz,zst,raw}{,.bin} \
	   ::: '' -L100000 "-L100000 -N3"
}
 
par_shard() {
    echo '### --shard'
    # Each of the 5 lines should match:
    #   ##### ##### ######
    seq 100000 | parallel --pipe --shard 1 -j5  wc |
	perl -pe 's/(.*\d{5,}){3}/OK/'
    # Data should be sharded to all processes
    shard_on_col() {
	col=$1
	seq 10 99 | shuf | perl -pe 's/(.)/$1\t/g' |
	    parallel --pipe --shard $col -j2 --colsep "\t" sort -k$col |
	    field $col | sort | uniq -c
    }
    shard_on_col 1
    shard_on_col 2

    echo '### --shard'
    shard_on_col_name() {
	colname=$1
	col=$2
	(echo AB; seq 10 99 | shuf) | perl -pe 's/(.)/$1\t/g' |
	    parallel --header : --pipe --shard $colname -j2 --colsep "\t" sort -k$col |
	    field $col | sort | uniq -c
    }
    shard_on_col_name A 1
    shard_on_col_name B 2

    echo '### --shard'
    shard_on_col_expr() {
	colexpr="$1"
	col=$2
	(seq 10 99 | shuf) | perl -pe 's/(.)/$1\t/g' |
	    parallel --pipe --shard "$colexpr" -j2 --colsep "\t" "sort -k$col; echo c1 c2" |
	    field $col | sort | uniq -c
    }
    shard_on_col_expr '1 $_%=3' 1
    shard_on_col_expr '2 $_%=3' 2

    shard_on_col_name_expr() {
	colexpr="$1"
	col=$2
	(echo AB; seq 10 99 | shuf) | perl -pe 's/(.)/$1\t/g' |
	    parallel --header : --pipe --shard "$colexpr" -j2 --colsep "\t" "sort -k$col; echo c1 c2" |
	    field $col | sort | uniq -c
    }
    shard_on_col_name_expr 'A $_%=3' 1
    shard_on_col_name_expr 'B $_%=3' 2
    
    echo '*** broken'
    # Should be shorthand for --pipe -j+0
    #seq 200000 | parallel --pipe --shard 1 wc |
    #	perl -pe 's/(.*\d{5,}){3}/OK/'
    # Combine with arguments (should compute -j10 given args)
    seq 200000 | parallel --pipe --shard 1 echo {}\;wc ::: {1..10} ::: a b |
	perl -pe 's/(.*\d{5,}){3}/OK/'
}

par_bin() {
    echo '### Test --bin'
    seq 10 | parallel --pipe --bin 1 -j4 wc | sort
    paste <(seq 10) <(seq 10 -1 1) |
	parallel --pipe --colsep '\t' --bin 2 -j4 wc | sort
    echo '### Test --bin with expression that gives 1..n'
    paste <(seq 10) <(seq 10 -1 1) |
	parallel --pipe --colsep '\t' --bin '2 $_=$_%2+1' -j4 wc | sort
    echo '### Test --bin with expression that gives 0..n-1'
    paste <(seq 10) <(seq 10 -1 1) |
	parallel --pipe --colsep '\t' --bin '2 $_%=2' -j4 wc | sort
    echo '### Blocks in version 20220122'
    echo 10 | parallel --pipe --bin 1 -j100% cat | sort
    paste <(seq 10) <(seq 10 -1 1) |
	parallel --pipe --colsep '\t' --bin 2 cat | sort
}

par_--round-robin_blocks() {
    echo "bug #49664: --round-robin does not complete"
    seq 20000000 | parallel -j8 --block 10M --round-robin --pipe wc -c | wc -l
}

par_no_newline_compress() {
    echo 'bug #41613: --compress --line-buffer - no newline';
    pipe_doit() {
	tagstring="$1"
	compress="$2"
	echo tagstring="$tagstring" compress="$compress"
	perl -e 'print "O"'|
	    parallel "$compress" $tagstring --pipe --line-buffer cat
	echo "K"
    }
    export -f pipe_doit
    nopipe_doit() {
	tagstring="$1"
	compress="$2"
	echo tagstring="$tagstring" compress="$compress"
	parallel "$compress" $tagstring --line-buffer echo {} O ::: -n
	echo "K"
    }
    export -f nopipe_doit
    parallel -j1 -qk --header : {pipe}_doit {tagstring} {compress} \
	     ::: tagstring '--tagstring {#}' -k \
	     ::: compress --compress -k \
	     ::: pipe pipe nopipe
}

par_retries_lb_jl() {
    echo Broken in 20240522
    # Ignore --unsafe
    unset PARALLEL
    tmp=$(mktemp)
    export tmp
    parallel-20240522 --_unsafe --lb --jl /dev/null --timeout 0.3 --retries 5 'echo should be 5 lines >> "$tmp";sleep {}' ::: 20
    cat "$tmp"
    > "$tmp"
    parallel --unsafe --lb --jl /dev/null --timeout 0.3 --retries 5 'echo 5 lines >> "$tmp";sleep {}' ::: 20
    cat "$tmp"
    rm "$tmp"
}

par_--match() {
    export PARALLEL="$PARALLEL -k"
    echo Basic match
    parallel --match '(.*)/([a-zA-Z]+)' echo {1.2} {1.1} \
	     ::: works/This "works, too"/This

    echo Simple CSV-parsing
    echo https://gnu.org/s/parallel,myfile |
	parallel --match '(.*),(.*)' echo url={1.1} filename={1.2}

    echo Dummy --match for input source 1, real --match for input source 2
    parallel --match '' --match '(.*)/([A-Z]+)' echo {2.1} {1} ::: works ::: This/SKIP

    echo Reuse --match
    parallel --match +2 --match '([A-Z]+)' echo {2.1} {1.1} \
	     ::: ignoreOK ::: ignoreALL

    echo With --header :
    parallel --header : --match +2 --match '([A-Z]+)' echo {B.1} {A.1} \
	     ::: A ignoreOK ::: B ignoreALL

    echo Failure to match/Partial match
    parallel --match '([a-z]+)' echo {1.1} ::: matches FAILS MATCHESpartly
    
    echo Test error: missing --match
    parallel --match 'dummy' echo {2.1} ::: should fail

    echo 'Test error: \001 in match'
    ctrl_a=$(perl -e 'printf "%c",1')
    parallel --match "$ctrl_a" echo {1.1} ::: fail

    echo From man parallel_examples
    parallel --match '(.)' --dr 'mkdir -p {1.1} && mv {} {1.1}' ::: afile bfile adir
    parallel --match '(.).* (.*)' echo {1.1}. {1.2} \
	     ::: "Arthur Dent" "Ford Prefect" "Tricia McMillan" "Zaphod Beeblebrox"
    parallel --match '(.*)/(.*)/(.*)' echo {1.3}-{1.1}-{1.2} \
	     ::: 12/31/1969 01/19/2038 06/01/2002
    parallel --match 'https://(.*?)/(.*)' echo Domain: {1.1} Path: {1.2} \
	     ::: https://example.com/dir/page https://gnu.org/s/parallel
    parallel --match '(.*),(.*)' echo Second: {1.2}, First: {1.1} \
	     ::: "Arthur,Babel fish" "Adams,Betelgeuse" "Arcturan,Bistro"
    parallel --match '([a-z])([a-z]*) ([a-z])([a-z]*)' \
	     echo '{=1.1 $_=uc($_) =}{1.2} {=1.3 $_=uc($_) =}{1.4}' \
	     ::: "pan galactic" "gargle blaster"
    dial=(
	"DK(Denmark) 00,45"
	"US(United States) 011,1"
	"JP(Japan) 010,81"
	"AU(Australia) 0011,61"
	"CA(Canada) 011,1"
	"RU(Russia) 810,7"
	"TH(Thailand) 001,66"
	"TW(Taiwan) 002,886"
    )
    parallel --match '(.*)\((.*)\) (.*),(.*)' --match +1 \
	     echo From {1.1}/{1.2} to {2.1}/{2.2} dial {1.3}-{2.4} \
	     ::: "${dial[@]}" ::: "${dial[@]}"
    
    echo Capture groups CSV-parsing - not implemented
    echo https://gnu.org/s/parallel,myfile |
	parallel --match '(?<url>.*),(?<file>.*)' echo url={url} filename={file}

    echo Non posistional replacement fields - not implemented
    parallel --match '(.*),(.*)_(.*)' echo {.2} {.3} {.1} ::: Gold,Heart_of

    echo TODO Ignore case?
}

par_--tee_too_many_args() {
    echo '### Fail if there are more arguments than --jobs'
    ulimit -n 1000
    seq 11 | stdout parallel -k --tag --pipe -j4 --tee grep {} ::: {1..4}
    tmp=`mktemp`
    seq 11 | parallel -k --tag --pipe -j0 --tee grep {} ::: {1..10000} 2> "$tmp"
    cat "$tmp" | perl -pe 's/\d+/999/g' |
	grep -v 'Warning: Starting' |
	grep -v 'Warning: Consider'
    rm "$tmp"
}

par_retries_0() {
    echo '--retries 0 = inf'
    echo this wraps at 256 and should retry until it wraps
    tmp=$(mktemp)
    qtmp=$(parallel -0 --shellquote ::: "$tmp")
    parallel --retries 0 -u 'printf {} >> '"$qtmp"';a=$(stat -c %s '"$qtmp"'); echo -n " $a";  exit $a' ::: a
    echo
    rm -f "$tmp"
}

par_seqreplace_long_line() {
    echo '### Test --seqreplace and line too long'
    seq 1 1000 |
	stdout parallel -j1 -s 210 -k --seqreplace I echo IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII \|wc |
	uniq -c
}

par__quote_special_results() {
    echo "### Test --results on file systems with limited UTF8 support"
    export LC_ALL=C
    doit() {
	mkfs=$1
	img=$(mktemp /dev/shm/par-test-loop-XXXX.img)
	dir=$(mktemp -d /tmp/par-test-loop-XXXX)
	dd if=/dev/zero bs=1024k count=301 > "$img"
	# Use the mkfs.$filesystem
	$mkfs "$img"
	sudo mount "$img" "$dir" -oloop,uid=`id -u` 2>/dev/null ||
	    sudo mount "$img" "$dir" -oloop
	cd "$dir"
	sudo chown `id -u` .
	df "$dir"
	printf "%s\0" '' +m . +_ .. +__ ,. ,.. + ++ / +z |
	    parallel -0 --results a echo
	(cd a/1 && find . -type d | sort | fmt -2000)
	seq 128 | perl -ne 'printf "%c\0",$_' |
	    parallel -0 --results b128 echo
	(cd b128/1 && find . -type d | sort | fmt -2000)
	seq 128 255 | perl -ne 'printf "%c\0",$_' |
	    parallel -0 --results b255 echo
	(cd b255/1 && find . -type d | sort | fmt -2000)
	cd
	sudo umount "$dir"
	rmdir "$dir"/
	rm "$img"
    }
    export -f doit
    stdout parallel --timeout 1000% -k --tag --plus doit ::: \
	   mkfs.btrfs mkfs.exfat mkfs.ext2 mkfs.ext3 mkfs.ext4 \
           "mkfs.ntfs -F" "mkfs.xfs -f" mkfs.minix \
	   mkfs.fat mkfs.vfat mkfs.msdos mkfs.f2fs |
	perl -pe 's:(/dev/loop|par-test-loop)\S+:$1:g;s/ +/ /g' |
	G -v MB/s -v GB/s -v UUID -v Binutils -v 150000 -v exfatprogs |
	G -v ID.SIZE.PATH |
	# mkfs.xfs -f      = crc=1 finobt=1, sparse=1, rmapbt=0
	# mkfs.xfs -f      = reflink=1 bigtime=0 inobtcount=0
	G -v crc=..finobt=...sparse=...rmapbt= -v reflink=..bigtime=..inobtcount= |
	# mkfs.xfs -f     log =internal log bsize=4096 blocks=16384, version=2
	G -v log.=internal.log.bsize= |
	# mkfs.btrfs Incompat features: extref, skinny-metadata, no-holes
	# mke2fs 1.46.5 (30-Dec-2021)
	# btrfs-progs v6.6.3
 	G -vP Incompat.features -vP mke2fs.[.0-9]{5} -vP btrfs-progs.v[.0-9]{5} |
	# F2FS-tools: mkfs.f2fs Ver: 1.14.0 (2020-08-24)
 	G -vP mkfs.f2fs.Ver:.[.0-9]{5} |
	# See https://btrfs.readthedocs.io for more
	# mkfs.f2fs Info: Overprovision segments = 27 (GC reserved = 18)
	G -v 'See http' -v Overprovision |
	# mkfs.f2fs /dev/loop 147952 70136 77816 48% /tmp/par-test-loop
	perl -pe 's:/dev/loop \d+ \d+ \d+ \d+:/dev/loop 999999 99999 99999 9:'
    # Skip:
    #   mkfs.bfs - ro
    #   mkfs.cramfs - ro
}

par_totaljobs() {
    . `which env_parallel.bash`
    myrun() {
	total="$@"
	slowseq() { seq "$@" | pv -qL 3; }
	elapsed() { /usr/bin/time -f %e stdout "$@" 2>&1 >/dev/null; }
	slowseq 5 | elapsed parallel -j 1 $total --bar 'sleep 1; true'
    }
    export -f myrun
    parset mytime myrun ::: '' '--total 5'
    # --total should run > 2 sec faster
    perl -E 'say ((2+shift) < (shift) ? "Error: --total should be faster" : "OK")' ${mytime[0]} ${mytime[1]}
}

par_load_blocks() {
    echo "### Test if --load blocks. Bug.";
    export PARALLEL="$PARALLEL --load 300%"
    (seq 1 1000 |
	 parallel -kj2 --load 300% --recend "\n" --spreadstdin gzip -1 |
	 zcat | sort -n | md5sum
     seq 1 1000 |
	 parallel -kj200 --load 300% --recend "\n" --spreadstdin gzip -1 |
	 zcat | sort -n | md5sum) 2>&1 |
	grep -Ev 'processes took|Consider adjusting -j'
}

par_dryrun_timeout_ungroup() {
    echo 'bug #51039: --dry-run --timeout 1.4m -u breaks'
    seq 1000 | stdout parallel --dry-run --timeout 1.4m -u --jobs 10 echo | wc
}

par_opt_arg_eaten() {
    echo 'bug #31716: Options with optional arguments may eat next argument'
    echo '### Test https://savannah.gnu.org/bugs/index.php?31716'
    seq 1 5 | stdout parallel -k -l echo {} OK
    seq 1 5 | stdout parallel -k -l 1 echo {} OK

    echo '### -k -l -0'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -l -0 echo {} OK

    echo '### -k -0 -l'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -l echo {} OK

    echo '### -k -0 -l 1'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -l 1 echo {} OK

    echo '### -k -0 -l 0'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -l 0 echo {} OK

    echo '### -k -0 -L -0 - -0 is argument for -L'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -L -0 echo {} OK

    echo '### -k -0 -L 0 - -L always takes arg'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -L 0 echo {} OK

    echo '### -k -0 -L 0 - -L always takes arg'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -L 0 -0 echo {} OK

    echo '### -k -e -0'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -e -0 echo {} OK

    echo '### -k -0 -e eof'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -e eof echo {} OK

    echo '### -k -i -0'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -i -0 echo {} OK

    echo '### -k -0 -i repl'
    printf '1\0002\0003\0004\0005\000' | stdout parallel -k -0 -i repl echo repl OK
}

par__--nice() {
    echo 'Check that --nice works'
    # parallel-20160422 OK
    check_for_2_bzip2s() {
	perl -e '
	for(1..5) {
	       # Try 5 times if the machine is slow starting bzip2
	       sleep(1);
	       @out = qx{ps -eo "%c %n" | grep 18 | grep bzip2};
	       if($#out == 1) {
		     # Should find 2 lines
		     print @out;
		     exit 0;
	       }
           }
	   print "failed\n@out";
	   '
    }
    # wait for load < 8
    parallel --load 8 echo ::: load_10
    parallel -j0 --timeout 10 --nice 18 bzip2 '<' ::: /dev/zero /dev/zero &
    pid=$!
    check_for_2_bzip2s
    parallel --retries 10 '! kill -TERM' ::: $pid 2>/dev/null
}

par_colsep() {
    echo '### Test of --colsep'
    echo 'a%c%b' | parallel --colsep % echo {1} {3} {2}
    (echo 'a%c%b'; echo a%c%b%d) | parallel -k --colsep % echo {1} {3} {2} {4}
    (echo a%c%b; echo d%f%e) | parallel -k --colsep % echo {1} {3} {2}
    parallel -k --colsep % echo {1} {3} {2} ::: a%c%b d%f%e
    parallel -k --colsep % echo {1} {3} {2} ::: a%c%b
    parallel -k --colsep % echo {1} {3} {2} {4} ::: a%c%b a%c%b%d


    echo '### Test of tab as colsep'
    printf 'def\tabc\njkl\tghi' | parallel -k --colsep '\t' echo {2} {1}
    parallel -k -a <(printf 'def\tabc\njkl\tghi') --colsep '\t' echo {2} {1}

    echo '### Test of multiple -a plus colsep'
    parallel --xapply -k -a <(printf 'def\njkl\n') -a <(printf 'abc\tghi\nmno\tpqr') --colsep '\t' echo {2} {1}

    echo '### Test of multiple -a no colsep'
    parallel --xapply -k -a <(printf 'ghi\npqr\n') -a <(printf 'abc\tdef\njkl\tmno') echo {2} {1}

    echo '### Test of quoting after colsplit'
    parallel --colsep % echo {2} {1} ::: '>/dev/null%>/tmp/null'

    echo '### Test of --colsep as regexp'
    (echo 'a%c%%b'; echo a%c%b%d) | parallel -k --colsep %+ echo {1} {3} {2} {4}
    parallel -k --colsep %+ echo {1} {3} {2} {4} ::: a%c%%b a%c%b%d
    (echo 'a% c %%b'; echo a%c% b %d) | parallel -k --colsep %+ echo {1} {3} {2} {4}
    (echo 'a% c %%b'; echo a%c% b %d) | parallel -k --colsep %+ echo '"{1}_{3}_{2}_{4}"'

    echo '### Test of -C'
    (echo 'a% c %%b'; echo a%c% b %d) | parallel -k -C %+ echo '"{1}_{3}_{2}_{4}"'

    echo '### Test of --trim n'
    (echo 'a% c %%b'; echo a%c% b %d) | parallel -k --trim n --colsep %+ echo '"{1}_{3}_{2}_{4}"'
    parallel -k -C %+ echo '"{1}_{3}_{2}_{4}"' ::: 'a% c %%b' 'a%c% b %d'

    echo '### Test of bug: If input is empty string'
    (echo ; echo abcbdbebf;echo abc) | parallel -k --colsep b -v echo {1}{2}
}

par_failing_compressor() {
    echo 'Compress with failing (de)compressor'
    echo 'Test --tag/--line-buffer/--files in all combinations'
    echo 'Test working/failing compressor/decompressor in all combinations'
    echo '(-k is used as a dummy argument)'
    doit() {
	# Print something to stdout/stderr
	echo "$@"
	echo "$@" >&2
    }
    export -f doit
    stdout parallel -vk --header : --argsep ,,, \
	   stdout parallel -k {tag} {lb} {files} --compress \
	   --compress-program {comp} --decompress-program {decomp} doit \
	   ::: C={comp},D={decomp} \
	     ,,, tag --tag -k \
	     ,,, lb --line-buffer -k \
	     ,,, files --files0 -k \
	     ,,, comp 'cat;true' 'cat;false' \
	     ,,, decomp 'cat;true' 'cat;false' |
	replace_tmpdir |
	perl -pe 's:/par......par:/tmpfile:'
}


par_END() {
    echo '### Test -i and --replace: Replace with argument'
    (echo a; echo END; echo b) | parallel -k -i -eEND echo repl{}ce
    (echo a; echo END; echo b) | parallel -k --replace -eEND echo repl{}ce
    (echo a; echo END; echo b) | parallel -k -i+ -eEND echo repl+ce
    (echo e; echo END; echo b) | parallel -k -i'*' -eEND echo r'*'plac'*'
    (echo a; echo END; echo b) | parallel -k --replace + -eEND echo repl+ce
    (echo a; echo END; echo b) | parallel -k --replace== -eEND echo repl=ce
    (echo a; echo END; echo b) | parallel -k --replace = -eEND echo repl=ce
    (echo a; echo END; echo b) | parallel -k --replace=^ -eEND echo repl^ce
    (echo a; echo END; echo b) | parallel -k -I^ -eEND echo repl^ce

    echo '### Test -E: Artificial end-of-file'
    (echo include this; echo END; echo not this) | parallel -k -E END echo
    (echo include this; echo END; echo not this) | parallel -k -EEND echo

    echo '### Test -e and --eof: Artificial end-of-file'
    (echo include this; echo END; echo not this) | parallel -k -e END echo
    (echo include this; echo END; echo not this) | parallel -k -eEND echo
    (echo include this; echo END; echo not this) | parallel -k --eof=END echo
    (echo include this; echo END; echo not this) | parallel -k --eof END echo
}

par__xargs_compat() {
    echo xargs compatibility
    a_b-c() { echo a_b; echo c; }
    a_b_-c-d() { echo a_b' '; echo c; echo d; }
    a_b_-c-d-e() { echo a_b' '; echo c; echo d; echo e; }
    one_mb_line() { perl -e 'print "z"x1000000'; }
    stdsort() { stdout "$@" | LC_ALL=C sort; }

    echo '### Test -L -l and --max-lines'
    a_b-c | parallel -km -L2 echo
    a_b-c | parallel -k -L2 echo
    a_b-c | xargs -L2 echo

    echo '### xargs -L1 echo'
    a_b-c | parallel -km -L1 echo
    a_b-c | parallel -k -L1 echo
    a_b-c | xargs -L1 echo

    echo 'Lines ending in space should continue on next line'
    echo '### xargs -L1 echo'
    a_b_-c-d | parallel -km -L1 echo
    a_b_-c-d | parallel -k -L1 echo
    a_b_-c-d | xargs -L1 echo

    echo '### xargs -L2 echo'
    a_b_-c-d-e | parallel -km -L2 echo
    a_b_-c-d-e | parallel -k -L2 echo
    a_b_-c-d-e | xargs -L2 echo

    echo '### xargs -l echo'
    a_b_-c-d-e | parallel -l -km echo # This behaves wrong
    a_b_-c-d-e | parallel -l -k echo # This behaves wrong
    a_b_-c-d-e | xargs -l echo

    echo '### xargs -l2 echo'
    a_b_-c-d-e | parallel -km -l2 echo
    a_b_-c-d-e | parallel -k -l2 echo
    a_b_-c-d-e | xargs -l2 echo

    echo '### xargs -l1 echo'
    a_b_-c-d-e | parallel -km -l1 echo
    a_b_-c-d-e | parallel -k -l1 echo
    a_b_-c-d-e | xargs -l1 echo

    echo '### xargs --max-lines=2 echo'
    a_b_-c-d-e | parallel -km --max-lines 2 echo
    a_b_-c-d-e | parallel -k --max-lines 2 echo
    a_b_-c-d-e | xargs --max-lines=2 echo

    echo '### xargs --max-lines echo'
    a_b_-c-d-e | parallel --max-lines -km echo # This behaves wrong
    a_b_-c-d-e | parallel --max-lines -k echo # This behaves wrong
    a_b_-c-d-e | xargs --max-lines echo

    echo '### test too long args'
    (
	one_mb_line | parallel echo 2>&1
	one_mb_line | xargs echo 2>&1
	(seq 1 10; one_mb_line; seq 12 15) | stdsort parallel -j1 -km -s 10 echo
	(seq 1 10; one_mb_line; seq 12 15) | stdsort xargs -s 10 echo
	(seq 1 10; one_mb_line; seq 12 15) | stdsort parallel -j1 -kX -s 10 echo
    ) | perl -pe 's/(\d+)\d\d\d(\D)/${1}999$2/g'

    echo '### Test -x'
    echo '-km'
    (seq 1 10; echo 12345; seq 12 15) | stdsort parallel -j1 -km -s 10 -x echo
    echo '-kX'
    (seq 1 10; echo 12345; seq 12 15) | stdsort parallel -j1 -kX -s 10 -x echo
    echo '-x'
    (seq 1 10; echo 12345; seq 12 15) | stdsort xargs -s 10 -x echo
    echo '-km -x'
    (seq 1 10; echo 1234;  seq 12 15) | stdsort parallel -j1 -km -s 10 -x echo
    echo '-kX -x'
    (seq 1 10; echo 1234;  seq 12 15) | stdsort parallel -j1 -kX -s 10 -x echo
    echo '-x'
    (seq 1 10; echo 1234;  seq 12 15) | stdsort xargs -s 10 -x echo
}

par_line_buffer() {
    echo "### --line-buffer"
    tmp1=$(mktemp)
    tmp2=$(mktemp)

    seq 10 | parallel -j20 --line-buffer  'seq {} 10 | pv -qL 10' > "$tmp1"
    seq 10 | parallel -j20                'seq {} 10 | pv -qL 10' > "$tmp2"
    cat "$tmp1" | wc
    diff "$tmp1" "$tmp2" >/dev/null
    echo These must diff: $?
    rm "$tmp1" "$tmp2"
}

par_pipe_line_buffer() {
    echo "### --pipe --line-buffer"
    tmp1=$(mktemp)
    tmp2=$(mktemp)

    nowarn() {
	# Ignore certain warnings
	# parallel: Warning: Starting 11 processes took > 2 sec.
	# parallel: Warning: Consider adjusting -j. Press CTRL-C to stop.
	grep -v '^parallel: Warning: (Starting|Consider)'
    }

    export PARALLEL="$PARALLEL -N10 -L1 --pipe  -j20 --tagstring {#}"
    seq 200| parallel --line-buffer pv -qL 10 > "$tmp1" 2> >(nowarn)
    seq 200| parallel               pv -qL 10 > "$tmp2" 2> >(nowarn)
    cat "$tmp1" | wc
    diff "$tmp1" "$tmp2" >/dev/null
    echo These must diff: $?
    rm "$tmp1" "$tmp2"
}

par_pipe_line_buffer_compress() {
    echo "### --pipe --line-buffer --compress"
    seq 200 |
	parallel -N10 -L1 --pipe  -j20 --line-buffer --compress --tagstring {#} pv -qL 10 |
	wc
}

par__pipepart_spawn() {
    echo '### bug #46214: Using --pipepart doesnt spawn multiple jobs in version 20150922'
    seq 1000000 > /tmp/num1000000
    stdout parallel --pipepart --progress -a /tmp/num1000000 --block 10k -j0 true |
	grep 1:local | perl -pe 's/\d\d\d/999/g; s/\d\d+|[2-9]/2+/g;'
}

par_pipe_tee() {
    echo 'bug #45479: --pipe/--pipepart --tee'
    echo '--pipe --tee'

    random100M() {
	< /dev/zero openssl enc -aes-128-ctr -K 1234 -iv 1234 2>/dev/null |
	    head -c 100M;
    }
    random100M | parallel --pipe --tee cat ::: {1..3} | LC_ALL=C wc -c
}

par_pipepart_tee() {
    echo 'bug #45479: --pipe/--pipepart --tee'
    echo '--pipepart --tee'

    export TMPDIR=/dev/shm/parallel
    mkdir -p $TMPDIR
    random100M() {
	< /dev/zero openssl enc -aes-128-ctr -K 1234 -iv 1234 2>/dev/null |
	    head -c 100M;
    }
    tmp=$(mktemp)
    random100M >"$tmp"
    parallel --pipepart --tee -a $tmp cat ::: {1..3} | LC_ALL=C wc -c
    rm "$tmp"
}

par_k() {
    echo '### Test -k'
    ulimit -n 50
    (echo "sleep 3; echo begin";
     seq 1 30 |
	 parallel -j1 -kq echo "sleep 1; echo {}";
     echo "echo end") |
	stdout nice parallel -k -j0 |
	grep -Ev 'Try running|or increasing|No more file handles.' |
	perl -pe '/parallel:/ and s/\d/X/g'
}

par_k_linebuffer() {
    echo '### bug #47750: -k --line-buffer should give current job up to now'

    parallel --line-buffer --tag -k 'seq {} | pv -qL 10' ::: {10..20}
    parallel --line-buffer -k 'echo stdout top;sleep 1;echo stderr in the middle >&2; sleep 1;echo stdout' ::: end 2>&1
}

par_results_csv() {
    echo "bug #: --results csv"

    doit() {
	parallel -k $@ --results -.csv echo ::: H2 22 23 ::: H1 11 12 \
		 2> >(grep -v TMPDIR) |
	    replace_tmpdir
    }
    export -f doit
    parallel -k --tag doit ::: '--header :' '' \
	::: --tag '' ::: --files0 '' ::: --compress '' |
	perl -pe 's:/par......par:/tmpfile:g;s/\d+\.\d+/999.999/g'
}

par_kill_children_timeout() {
    echo '### Test killing children with --timeout and exit value (failed if timed out)'
    pstree $$ | grep sleep | grep -v anacron | grep -v screensave | wc
    doit() {
	for i in `seq 100 120`; do
	    bash -c "(sleep $i)" &
	    sleep $i &
	done;
	wait;
	echo No good;
    }
    export -f doit
    parallel --timeout 3 doit ::: 1000000000 1000000001
    echo $?;
    sleep 2;
    pstree $$ | grep sleep | grep -v anacron | grep -v screensave | wc
}

par_tmux_fg() {
    echo 'bug #50107: --tmux --fg should also write how to access it'
    stdout parallel --tmux --fg sleep ::: 3 |
	replace_tmpdir |
	perl -pe 's:/tms.....:tmpfile:'
}


par_retries_all_fail() {
    echo "bug #53748: -k --retries 10 + out of filehandles = blocking"
    ulimit -n 30
    seq 8 |
	parallel -k -j0 --retries 2 --timeout 0.1 'echo {}; sleep {}; false' 2>/dev/null
}

par_long_line_remote() {
    echo '### Deal with long command lines on remote servers'
    perl -e "print(((\"'\"x5000).\"\\n\")x6)" |
	parallel -j1 -S lo -N 10000 echo {} |wc
    perl -e 'print((("\$"x5000)."\n")x50)' |
	parallel -j1 -S lo -N 10000 echo {} |wc
}

par_shellquote() {
    echo '### Test --shellquote in all shells'
    doit() {
	# Run --shellquote for ascii 1..255 in a shell
	shell="$1"
	"$shell" -c perl\ -e\ \'print\ pack\(\"c\*\",1..255\)\'\ \|\ parallel\ -0\ --shellquote
    }
    export -f doit
    parallel --tag -q -k doit {} ::: bash csh dash fish fizsh ksh2020 ksh93 lksh mksh posh rzsh sash sh static-sh tcsh yash zsh csh tcsh
}

par_tmp_full() {
    # Assume /tmp/shm is easy to fill up
    export SHM=/tmp/shm/parallel
    mkdir -p $SHM
    sudo umount -l $SHM 2>/dev/null
    sudo mount -t tmpfs -o size=10% none $SHM

    echo "### Test --tmpdir running full. bug #40733 was caused by this"
    stdout parallel -j1 --tmpdir $SHM cat /dev/zero ::: dummy |
	grep -v 'Warning:.*No space left on device during global destruction'
}

par_jobs_file() {
    echo '### Test of -j filename'
    echo 3 >/tmp/jobs_to_run1
    parallel -j /tmp/jobs_to_run1 -v sleep {} ::: 10 8 6 5 4
    # Should give 6 8 10 5 4
}

par_filter_no_delay() {
    echo '### --filter + --delay: filtered jobs must not consume delay slots'
    start=$SECONDS
    parallel --delay 1 -j1 --filter '{} > 4' echo ::: {1..8}
    elapsed=$((SECONDS - start))
    [ "$elapsed" -lt 7 ] && echo "FAST: filtered jobs skipped delay" || echo "SLOW: $elapsed s"
}

par_skip_no_delay() {
    echo '### skip() must not consume --delay slot'
    start=$SECONDS
    parallel --delay 1 -j1 echo '{= 2 < seq and seq() < 10 and skip(); =}' ::: {1..11}
    elapsed=$((SECONDS - start))
    [ "$elapsed" -lt 10 ] && echo "FAST: skipped jobs skipped delay" || echo "SLOW: $elapsed s (should be <10, unfixed would be ~11)"
}

export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 1000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's/,31,0/,15,0/' |
    # Replace $PWD with . even if given as ~/...
    perl -pe 's:~:'"$HOME"':g' |
    perl -pe 's:'"$HOME"':~:g'
