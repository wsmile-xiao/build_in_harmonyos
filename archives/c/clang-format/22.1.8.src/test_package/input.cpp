#include <vector>
#include <map>
using namespace std;
class Foo{public:Foo(int x):x_(x){}int x_;vector<int> v;};
int  main( ){
int   a=1;int b=2;
map<string,int> m;m["a"]=1;
for(int i=0;i<10;++i){a+=i;}
return a+b; }
