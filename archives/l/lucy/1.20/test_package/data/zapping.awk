#!/usr/bin/awk -f

/^>/ {
    if (collect) {
	print name;
	seq=substr(seq, left, right-left+1);
	for (i=1; i<right-left+1; i+=60)
	    printf("%s\n", substr(seq, i, 60));
    }
    name=$1; left=$5; right=$6; collect=1; seq=""; next;
}

// {
    if (collect)
	seq = seq $1;
}

END {
    if (collect) {
	print name;
	seq=substr(seq, left, right-left+1);
	for (i=1; i<right-left+1; i+=60)
	    printf("%s\n", substr(seq, i, 60));
    }
}
    
