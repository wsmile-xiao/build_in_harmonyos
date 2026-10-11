"""OHOS-specific signature/ELF namespace contract, separate from C API consumer."""
import hashlib,json,platform,re,struct,subprocess,sys
from pathlib import Path

def run(package,readelf,native_loader):
    package=Path(package).resolve();lib=(package/'lib/libwebp.so').resolve()
    assert platform.uname().system=='HarmonyOS','NOT_ACTUAL_HARMONYOS'
    assert lib.is_relative_to(package) and lib.is_file()
    data=lib.read_bytes();assert data[:4]==b'\x7fELF' and data[4:6]==b'\x02\x01'
    assert struct.unpack_from('<H',data,18)[0]==183,'NOT_AARCH64'
    sections=subprocess.run([readelf,'-S',str(lib)],capture_output=True,text=True,check=True)
    assert '.codesign' in sections.stdout,'NO_OHOS_CODE_SIGNATURE'
    dynamic=subprocess.run([readelf,'-d',str(lib)],capture_output=True,text=True,check=True)
    needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',dynamic.stdout)
    assert needed and all('/' not in x for x in needed),'PATH_BEARING_DT_NEEDED'
    soname=re.findall(r'\(SONAME\).*?\[(.*?)\]',dynamic.stdout)
    assert len(soname)==1 and '/' not in soname[0]
    assert (package/'lib'/soname[0]).is_file() and (package/'lib'/soname[0]).resolve()==lib,'SONAME_NOT_REAL_INSTALLED_PROVIDER'
    native=Path(native_loader).resolve();assert native.is_file()
    native_sections=subprocess.run([readelf,'-S',str(native)],capture_output=True,text=True,check=True)
    assert native_sections.stdout.count('.codesign')==1,'UNSIGNED_NATIVE_LOADER'
    executed=subprocess.run([str(native),str(package),str(lib)],capture_output=True,text=True,check=True,timeout=120)
    actual=json.loads(executed.stdout)
    assert isinstance(actual,dict) and actual.get('native_loader') is True and actual.get('actual_loader_and_codec_rc')==0
    assert actual.get('width')==actual.get('height')==1 and actual.get('library')==str(lib)
    mapped=set(actual.get('webp_mapping',[]));assert mapped=={str(lib)},'FOREIGN_OR_AMBIGUOUS_WEBP_NAMESPACE'
    sharpyuv=set(actual.get('sharpyuv_mapping',[]))
    assert sharpyuv and all(Path(p).is_relative_to(package) for p in sharpyuv),'FOREIGN_SHARPYUV_PROVIDER'
    result={'name':'harmony_signed_aarch64_codec_namespace','os':platform.uname().system,'library':str(lib),'sha256':hashlib.sha256(data).hexdigest(),'needed':needed,'soname':soname,'codesign_present':True,'actual_loader_and_codec_rc':0,'webp_mapping':sorted(mapped),'sharpyuv_mapping':sorted(sharpyuv)}
    print(json.dumps(result,sort_keys=True));print('HARMONY_TEST_COUNT=1\nHARMONY 1/1 PASS')

if __name__=='__main__':run(sys.argv[1],sys.argv[2],sys.argv[3])
