package sample

import "core:fmt"
import "core:math"

Point    ::  struct{
        x:int,
        y : int,
}

add :: proc( a,b:int )->int{
    return a+b
}

norm :: proc( p : Point ) -> f64 {
    return math.sqrt( f64( p.x*p.x + p.y*p.y ) )
}

main :: proc( ) {
        p := Point{ x=1, y = 2 }
    sum := add( p.x, p.y )
        fmt.println( "sum =", sum )
        if sum > 0 {
        fmt.println( "norm =", norm( p ) )
        } else {
                fmt.println( "non-positive" )
        }
}
