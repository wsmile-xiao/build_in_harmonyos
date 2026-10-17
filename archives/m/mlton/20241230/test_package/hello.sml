val answer = List.foldl op+ 0 [1, 2, 3, 4];
val _ = if answer = 10 then print "MLTON_CONSUMER_OK\n" else raise Fail "bad sum";
