#include <ladspa.h>
#include <dirent.h>
#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef const LADSPA_Descriptor *(*descriptor_fn)(unsigned long);
static void require(int ok, const char *message) {
  if (!ok) { fprintf(stderr, "FAIL: %s (%s)\n", message, dlerror()); exit(1); }
}
static void pass(const char *label) { printf("CONSUMER_PASS %s\n", label); fflush(stdout); }
static void *load(const char *directory, const char *name) {
  char path[4096];
  require(snprintf(path, sizeof(path), "%s/%s", directory, name) < (int)sizeof(path), "path length");
  void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
  require(handle != NULL, name);
  return handle;
}
int main(int argc, char **argv) {
  require(argc == 2, "plugin directory argument");
  DIR *directory = opendir(argv[1]); require(directory != NULL, "installed plugin directory");
  struct dirent *entry; unsigned modules=0, descriptors=0; unsigned long ids[256];
  while ((entry = readdir(directory))) {
    size_t n = strlen(entry->d_name);
    if (n < 3 || strcmp(entry->d_name+n-3, ".so")) continue;
    void *handle = load(argv[1], entry->d_name);
    descriptor_fn descriptor = (descriptor_fn)dlsym(handle, "ladspa_descriptor");
    require(descriptor != NULL, "descriptor export");
    const LADSPA_Descriptor *d;
    unsigned count=0;
    while ((d=descriptor(count++))) {
      require(descriptors < 256 && d->UniqueID >= 1000 && d->Label && *d->Label && d->Name && d->PortCount,
              "descriptor metadata");
      require(d->instantiate && d->connect_port && d->run && d->cleanup, "processing callbacks");
      for(unsigned j=0;j<descriptors;j++) require(ids[j] != d->UniqueID, "unique plugin ID");
      ids[descriptors++] = d->UniqueID;
    }
    require(count > 1, "nonempty module");
    modules++; dlclose(handle);
  }
  closedir(directory);
  require(modules == 96, "all 96 upstream modules installed"); pass("installed module inventory");
  require(descriptors == 109, "all 109 upstream plugin descriptors"); pass("complete descriptor identity");
  void *amp = load(argv[1], "amp_1181.so");
  const LADSPA_Descriptor *d = ((descriptor_fn)dlsym(amp, "ladspa_descriptor"))(0);
  require(d->UniqueID == 1181 && d->PortCount == 3, "amplifier contract");
  LADSPA_Handle state = d->instantiate(d, 48000); require(state != NULL, "amplifier instance");
  float gain=0, input[64], output[64];
  for(unsigned i=0;i<64;i++){input[i]=(float)i/128.f-0.25f;output[i]=0;}
  d->connect_port(state,0,&gain);d->connect_port(state,1,input);d->connect_port(state,2,output);
  d->run(state,64);
  for(unsigned i=0;i<64;i++)require(fabsf(output[i]-input[i])<1e-6f,"unity samples");
  pass("amplifier unity"); gain=6.0205999f; d->run(state,64);
  for(unsigned i=0;i<64;i++)require(fabsf(output[i]-2*input[i])<1e-5f,"gain samples");
  pass("amplifier gain");
  require(d->run_adding && d->set_run_adding_gain,"additive callbacks");
  gain=0;for(unsigned i=0;i<64;i++)output[i]=0.1f;
  d->set_run_adding_gain(state,0.5f);d->run_adding(state,64);
  for(unsigned i=0;i<64;i++)require(fabsf(output[i]-(0.1f+0.5f*input[i]))<1e-6f,"additive samples");
  pass("additive processing");d->cleanup(state);dlclose(amp);
  void *eq = load(argv[1], "mbeq_1197.so");
  d=((descriptor_fn)dlsym(eq,"ladspa_descriptor"))(0);
  require(d->UniqueID==1197 && d->PortCount==18,"equalizer ports");
  fprintf(stderr,"FFT_PHASE instantiate begin\n");fflush(stderr);
  alarm(30);
  state=d->instantiate(d,48000);require(state!=NULL,"FFT instance");
  fprintf(stderr,"FFT_PHASE instantiate complete\n");fflush(stderr);
  float controls[15]={0}, audio[4096], filtered[4096]={0}, latency=0;
  for(unsigned p=0;p<15;p++)d->connect_port(state,p,&controls[p]);
  for(unsigned i=0;i<4096;i++)audio[i]=0.1f*sinf(2.f*3.141592653589793f*440.f*i/48000.f);
  d->connect_port(state,15,audio);d->connect_port(state,16,filtered);d->connect_port(state,17,&latency);
  if(d->activate)d->activate(state);d->run(state,4096);
  double energy=0;for(unsigned i=0;i<4096;i++){require(isfinite(filtered[i]),"finite FFT output");energy+=filtered[i]*filtered[i];}
  require(energy>0.01 && latency>0,"real FFT audio response and latency");
  pass("FFT equalizer audio processing");d->cleanup(state);dlclose(eq);
  alarm(0);
  return 0;
}
