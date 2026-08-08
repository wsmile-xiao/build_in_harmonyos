fun require true _ = ()
  | require false message =
      (TextIO.output (TextIO.stdErr, "FAIL: " ^ message ^ "\n");
       OS.Process.exit OS.Process.failure);

datatype tree = Leaf of int | Node of tree * tree;
fun sum (Leaf n) = n
  | sum (Node (left, right)) = sum left + sum right;

val _ = require (6 * 7 = 42) "integer arithmetic";
val _ = require (sum (Node (Leaf 10, Node (Leaf 20, Leaf 12))) = 42)
                "datatype and pattern matching";
val huge = valOf (IntInf.fromString "123456789012345678901234567890");
val _ = require (huge * 9 = valOf (IntInf.fromString "1111111101111111110111111111010"))
                "IntInf arithmetic";
val _ = require (List.map (fn x => x * x) [1, 2, 3, 4] = [1, 4, 9, 16])
                "higher-order list processing";
val _ = print "POLYML_CONSUMER_TEST_PASS\n";
