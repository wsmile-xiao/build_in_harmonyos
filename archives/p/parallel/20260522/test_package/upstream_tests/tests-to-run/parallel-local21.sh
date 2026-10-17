#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

tmp="$(mktemp -d)"
# Test with tmpdir with spaces
TMPDIR="$tmp/   "
export TMPDIR
mkdir -p "$TMPDIR"

par_basic_shebang_wrap() {
    echo "### Test basic --shebang-wrap"
    script="$TMPDIR"/basic--shebang-wrap
    qscript=$(parallel -0 --shellquote ::: "$script")
    cat <<EOF > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/perl

print "Shebang from perl with args @ARGV\n";
EOF

    chmod 755 "$script"
    args() { echo arg1; echo arg2; echo "arg3.1  arg3.2"; }
    "$script" "$(args)"
    echo "### Test basic --shebang-wrap Same as"
    parallel -k /usr/bin/perl "$qscript" ::: "$(args)"
    echo "### Test basic --shebang-wrap stdin"
    args | "$script"
    echo "### Test basic --shebang-wrap Same as"
    args | parallel -k /usr/bin/perl "$qscript"
    rm "$script"
}

par_shebang_with_parser_options() {
    seq 1 2 >/tmp/in12
    seq 4 5 >/tmp/in45
    
    echo "### Test --shebang-wrap with parser options"
    script="$TMPDIR"/with-parser--shebang-wrap
    qscript=$(parallel -0 --shellquote ::: "$script")
    cat <<EOF > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/perl -p

print "Shebang from perl with args @ARGV\n";
EOF

    chmod 755 "$script"
    "$script" /tmp/in12 /tmp/in45
    echo "### Test --shebang-wrap with parser options Same as"
    parallel -k /usr/bin/perl -p "$qscript" ::: /tmp/in12 /tmp/in45
    echo "### Test --shebang-wrap with parser options stdin"
    (echo /tmp/in12; echo /tmp/in45) | "$script"
    echo "### Test --shebang-wrap with parser options Same as"
    (echo /tmp/in12; echo /tmp/in45) | parallel -k /usr/bin/perl "$qscript"
    rm "$script"

    echo "### Test --shebang-wrap --pipe with parser options"
    script="$TMPDIR"/pipe--shebang-wrap
    qscript=$(parallel -0 --shellquote ::: "$script")
    cat <<EOF > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k --pipe /usr/bin/perl -p

print "Shebang from perl with args @ARGV\n";
EOF

    chmod 755 "$script"
    echo "### Test --shebang-wrap --pipe with parser options stdin"
    cat /tmp/in12 /tmp/in45 | "$script"
    echo "### Test --shebang-wrap --pipe with parser options Same as"
    cat /tmp/in12 /tmp/in45 | parallel -k --pipe /usr/bin/perl\ -p "$qscript"
    rm "$script"
    
    rm /tmp/in12
    rm /tmp/in45
}

par_shebang_wrap_perl() {
    script="$TMPDIR"/shebang_wrap_perl
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/perl

print "Arguments @ARGV\n";
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_python() {
    script="$TMPDIR"/shebang_wrap_python
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/python3

import sys
sys.argv.pop(0)
print('Arguments', str(sys.argv))
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_bash() {
    script="$TMPDIR"/shebang_wrap_bash
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /bin/bash

echo Arguments "$@"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_sh() {
    script="$TMPDIR"/shebang_wrap_sh
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /bin/sh

echo Arguments "$@"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_ksh() {
    script="$TMPDIR"/shebang_wrap_ksh
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/ksh

echo Arguments "$@"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_zsh() {
    script="$TMPDIR"/shebang_wrap_zsh
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/zsh

echo Arguments "$@"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_csh() {
    script="$TMPDIR"/shebang_wrap_csh
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /bin/csh

echo Arguments "$argv"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_tcl() {
    script="$TMPDIR"/shebang_wrap_tcl
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/tclsh

puts "Arguments $argv"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_R() {
    # Rscript fucks up if $TMPDIR contains space
    TMPDIR=/tmp
    script="$TMPDIR"/shebang_wrap_R
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/Rscript --vanilla --slave

args <- commandArgs(trailingOnly = TRUE)
print(paste("Arguments ",args))
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}


par_shebang_wrap_gnuplot() {
    script="$TMPDIR"/shebang_wrap_gnuplot
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k ARG={} /usr/bin/gnuplot

print "Arguments ", system('echo "$ARG"')
EOF
    chmod 755 "$script"
    stdout "$script" arg1 arg2 "arg3.1  arg3.2" |
	# Gnuplot 6.0 inserts an extra space
	perl -pe 's/rguments  /rguments /'
    rm "$script"
}

par_shebang_wrap_ruby() {
    script="$TMPDIR"/shebang_wrap_ruby
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/ruby

print "Arguments "
puts ARGV
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_octave() {
    script="$TMPDIR"/shebang_wrap_octave
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/octave

printf ("Arguments");
arg_list = argv ();
for i = 1:nargin
  printf (" %s", arg_list{i});
endfor
printf ("\n");
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_groovy() {
    script="$TMPDIR"/shebang_wrap_groovy
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /snap/bin/groovy

println "Arguments: ${args.join(' ')}"
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_racket() {
    script="$TMPDIR"/shebang_wrap_racket
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/racket
#lang racket

;; Get the command-line arguments, skipping the script name
(define args (vector->list (current-command-line-arguments)))

;; Format the arguments as a string
(define formatted-args (string-join args " "))

;; Print the result
(printf "Arguments: ~a\n" formatted-args)
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_scheme() {
    script="$TMPDIR"/shebang_wrap_scheme
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/env guile
!#

(define (print-arguments args)
  (display "Arguments: ")
  (for-each (lambda (arg)
              (display arg)
              (display " "))
            args)
  (newline))

(print-arguments (cdr (command-line)))
EOF
    chmod 755 "$script"
    stdout "$script" arg1 arg2 "arg3.1  arg3.2" |
	grep -v ';;;' | grep -v shebang_wrap_sche
    rm "$script"
}

par_shebang_wrap_awk() {
    script="$TMPDIR"/shebang_wrap_awk
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/awk -f

BEGIN {
    printf "Arguments: "
    for (i = 1; i < ARGC; i++) {
        printf "%s ", ARGV[i]
    }
    printf "\n"
}
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_fsharp() {
    script="$TMPDIR"/shebang_wrap_fsharp.fsx
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/fsharpi

let args = (System.Environment.GetCommandLineArgs()
  |> Array.tail |> Array.tail |> Array.tail)
printfn "Arguments: %A" args
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_julia() {
    script="$TMPDIR"/shebang_wrap_julia
    unset DISPLAY
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /snap/bin/julia

println("Arguments: ", join(ARGS, " "))
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_clisp() {
    # clisp cannot handle dirs w/ shell wildcards
    TMPDIR=/tmp
    script="$TMPDIR"/shebang_wrap_clisp
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/clisp

(format t "~&~S~&" 'Arguments)
(format t "~&~S~&" *args*)
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_php() {
    script="$TMPDIR"/shebang_wrap_php
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/php
<?php
echo "Arguments";
foreach(array_slice($argv,1) as $v)
{
  echo " $v";
}
echo "\n";
?>
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_nodejs() {
    script="$TMPDIR"/shebang_wrap_nodejs
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/node

var myArgs = process.argv.slice(2);
console.log('Arguments ', myArgs);
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_lua() {
    script="$TMPDIR"/shebang_wrap_lua
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k /usr/bin/lua

io.write "Arguments"
for a = 1, #arg do
  io.write(" ")
  io.write(arg[a])
end
print("")
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

par_shebang_wrap_csharp() {
    script="$TMPDIR"/shebang_wrap_csharp
    cat <<'EOF' > "$script"
#!/usr/local/bin/parallel --shebang-wrap -k ARGV={} /usr/bin/csharp

var argv = Environment.GetEnvironmentVariable("ARGV");
print("Arguments "+argv);
EOF
    chmod 755 "$script"
    "$script" arg1 arg2 "arg3.1  arg3.2"
    rm "$script"
}

export -f $(compgen -A function | grep par_)
# Tested with -j1..8
# -j6 was fastest
#compgen -A function | grep par_ | sort | parallel -j$P --tag -k '{} 2>&1'
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel -j6 --tag -k '{} 2>&1'
rmdir "$TMPDIR" "$tmp"
