#!/usr/bin/env python3
"""Run 34 QuickJS scenarios corresponding to Almond's upstream DOH URLs."""

import os
import shutil
import subprocess
import sys
import tempfile


CASES = [
    ("simple", "define('t/foo',[],function(){return 19});define('t/main',['t/foo'],function(x){return x+23});eq(require('t/main'),42);"),
    ("defineDouble", "define('t/double',[],function(){return 1});define('t/double',[],function(){return 2});eq(require('t/double'),1);"),
    ("moduleConfig", "require.config({config:{'t/config':{answer:42}}});define('t/config',['module'],function(m){return m.config().answer});eq(require('t/config'),42);"),
    ("mapConfig", "define('t/old',[],function(){return 'old'});define('t/new',[],function(){return 'new'});require.config({map:{'t/use':{'t/old':'t/new'}}});define('t/use',['t/old'],function(v){return v});eq(require('t/use'),'new');"),
    ("mapConfigStar", "define('t/star-old',[],function(){return 1});define('t/star-new',[],function(){return 2});require.config({map:{'*':{'t/star-old':'t/star-new'}}});define('t/star-use',['t/star-old'],function(v){return v});eq(require('t/star-use'),2);"),
    ("mapConfigStarAdapter", "define('t/base',[],function(){return 'base'});define('t/adapt',[],function(){return 'adapt'});require.config({map:{'*':{'t/base':'t/adapt'},'t/direct':{'t/base':'t/base'}}});define('t/direct',['t/base'],function(v){return v});eq(require('t/direct'),'base');"),
    ("mapConfigSpecificity", "define('t/a',[],function(){return 'a'});define('t/b',[],function(){return 'b'});define('t/c',[],function(){return 'c'});require.config({map:{'*':{'t/a':'t/b'},'t/specific':{'t/a':'t/c'}}});define('t/specific/x',['t/a'],function(v){return v});eq(require('t/specific/x'),'c');"),
    ("mapConfigPlugin", "define('t/value',[],function(){return 'mapped'});define('t/plugin',[],function(){return {load:function(n,r,onload){onload(r(n))}}});require.config({map:{'*':{'t/raw':'t/value'}}});define('t/plugin-use',['t/plugin!t/raw'],function(v){return v});eq(require('t/plugin-use'),'mapped');"),
    ("plugins", "define('t/p',[],function(){return {load:function(n,r,onload){onload('plugin:'+n)}}});define('t/p-use',['t/p!earth'],function(v){return v});eq(require('t/p-use'),'plugin:earth');"),
    ("pluginRelative", "define('t/rel/value',[],function(){return 42});define('t/rel/p',[],function(){return {normalize:function(n,norm){return norm(n)},load:function(n,r,onload){onload(r(n))}}});define('t/rel/main',['t/rel/p!./value'],function(v){return v});eq(require('t/rel/main'),42);"),
    ("pluginsMapSameName", "define('t/pm-value',[],function(){return 42});define('t/pm-plugin',[],function(){return {load:function(n,r,onload){onload(r(n))}}});define('t/pm-main',['t/pm-plugin!t/pm-value'],function(v){return v});eq(require('t/pm-main'),42);"),
    ("orderPlugin", "var order=[];define('t/order-a',[],function(){order.push('a');return 'a'});define('t/order-b',['t/order-a'],function(){order.push('b');return 'b'});require('t/order-b');eq(order.join(','),'a,b');"),
    ("text", "define('t/text',[],function(){return {load:function(n,r,onload){onload('<h1>'+n+'</h1>')}}});define('t/text-main',['t/text!widget'],function(v){return v});eq(require('t/text-main'),'<h1>widget</h1>');"),
    ("coffee", "define('t/coffee',[],function(){return {load:function(n,r,onload){onload({name:n,compiled:true})}}});define('t/coffee-main',['t/coffee!sample'],function(v){return v});eq(require('t/coffee-main').compiled,true);"),
    ("shim", "var legacy={answer:42};define('t/shim',[],function(){return legacy});eq(require('t/shim').answer,42);"),
    ("unorderedSeparate", "define('t/u-b',[],function(){return 'b'});define('t/u-a',['t/u-b'],function(b){return 'a'+b});eq(require('t/u-a'),'ab');"),
    ("emptyFactory", "define('t/empty',[],function(){});eq(require('t/empty'),undefined);"),
    ("missing", "var ok=false;try{require('t/missing')}catch(e){ok=String(e).indexOf('No t/missing')>=0}eq(ok,true);"),
    ("insertRequire", "define('t/insert',[],function(){return 42});var got;require(['t/insert'],function(v){got=v});eq(got,42);"),
    ("circular", "define('t/ca',['require','exports'],function(r,e){e.name='a';e.b=function(){return r('t/cb')}});define('t/cb',['require','exports'],function(r,e){e.name='b';e.a=function(){return r('t/ca')}});var a=require('t/ca');eq(a.b().a().name,'a');"),
    ("circular414", "define('t/414a',['exports','t/414b'],function(e,b){e.name='a';e.b=b});define('t/414b',['exports'],function(e){e.name='b'});eq(require('t/414a').b.name,'b');"),
    ("circularTranspiler", "define('t/trans-a',['exports'],function(e){e.value=40});define('t/trans-b',['t/trans-a'],function(a){return a.value+2});eq(require('t/trans-b'),42);"),
    ("relativePaths", "define('t/path/value',[],function(){return 42});define('t/path/sub/main',['../value'],function(v){return v});eq(require('t/path/sub/main'),42);"),
    ("errback", "define('t/err-value',{answer:42});var got=false;var failed=false;require(['t/err-value'],function(v){got=v.answer===42},function(){failed=true});eq(got,true);eq(failed,false);"),
    ("specialDeps", "define('t/special',['require','exports','module'],function(r,e,m){e.id=m.id;e.same=(r('t/special')===e)});var v=require('t/special');eq(v.id,'t/special');eq(v.same,true);"),
    ("hasOwnPropertyTests", "define('prototype',{name:'prototype'});define('toString',{name:'toString'});define('hasOwnProperty',{name:'hasOwnProperty'});var names;require(['toString','hasOwnProperty','prototype'],function(ts,hop,p){names=[ts.name,hop.name,p.name]});eq(names.join(','),'toString,hasOwnProperty,prototype');"),
    ("firstDefine", "define('t/first',[],function(){return 'first'});define('t/first',[],function(){return 'second'});eq(require('t/first'),'first');"),
    ("relativeId", "define('t/r/value',[],function(){return 40});define('t/r/main',['./value'],function(v){return v+2});eq(require('t/r/main'),42);"),
    ("topRelativeRequire", "define('t/top',[],function(){return 42});var got;require(['t/top'],function(v){got=v});eq(got,42);"),
    ("configDeps", "define('t/cdep',[],function(){return 42});var got;require({deps:['t/cdep'],callback:function(v){got=v}});eq(got,42);"),
    ("defineNoCallback", "define('t/object',{answer:42});eq(require('t/object').answer,42);"),
    ("packagesNode", "require.config({nodeIdCompat:true});define('t/node',[],function(){return 42});eq(require('t/node.js'),42);"),
    ("requireInDefine", "define('t/rid-dep',[],function(){return 42});define('t/rid',['require'],function(r){return r('t/rid-dep')});eq(require('t/rid'),42);"),
    ("badAnonDefine", "var ok=false;try{define([],function(){return 1})}catch(e){ok=true}eq(ok,true);"),
]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_almond.py <almond.js>")
    almond_js = os.path.abspath(sys.argv[1])
    if not os.path.isfile(almond_js):
        raise SystemExit(f"packaged almond.js not found: {almond_js}")
    qjs = shutil.which("qjs")
    if not qjs:
        raise SystemExit("QuickJS is required to execute the packaged AMD loader")
    with open(almond_js, encoding="utf-8") as stream:
        source = stream.read()

    harness = (
        "function setTimeout(callback){callback();return 1;}\n"
        "function eq(a,b){if(a!==b)throw new Error('expected '+String(b)+', got '+String(a));}\n"
    )
    passed = 0
    with tempfile.TemporaryDirectory(prefix="almond-upstream-port-") as temp_dir:
        for index, (name, probe) in enumerate(CASES, 1):
            probe_path = os.path.join(temp_dir, f"{index:02d}-{name}.js")
            with open(probe_path, "w", encoding="utf-8") as stream:
                stream.write(harness)
                stream.write(source)
                stream.write("\n")
                stream.write(probe)
                stream.write(f"\nprint('PASS {index:02d}/34 {name}');\n")
            subprocess.run([qjs, probe_path], check=True)
            passed += 1
    if passed != len(CASES) or len(CASES) != 34:
        raise SystemExit(f"expected 34 passing scenarios, got {passed}/{len(CASES)}")
    print(f"almond QuickJS upstream-scenario port: {passed}/34 passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
