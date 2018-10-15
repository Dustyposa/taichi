# This file generates a taichi header (analgamation)

import os
import sys
import re
import sys
import time

files_to_include = [
  'include/taichi/common/util.h',
  'src/system/timer.cpp',
  'src/core/core.cpp',
  'src/core/logging.cpp',
  'src/system/traceback.cpp',
  'src/gui/gui.cpp',
  'include/taichi/visual/gui.h',
  'include/taichi/visualization/image_buffer.cpp',
]

output_fn = 'build/taichi.h'

def expand_files(files):
  new_files = []
  for f in files:
    if f[-1] == '*':
      for header in os.listdir(f[:-1]):
        new_files.append(f[:-1] + header)
    else:
      assert f.endswith('.h') or f.endswith('.cpp') or f.endswith('.cc') or f.endswith('.c')
      new_files.append(f)
  new_files = map(os.path.realpath, new_files)
  return new_files
  
include_template = r'#\s?include.*([<"])(.*)[>"]'
search_directories = ['include', 'external/include']

class Amalgamator:
  def __init__(self):
    self.files = expand_files(files_to_include)
    self.included = set()

  def include(self, fn):
    if fn in self.included:
      print('  S - Skipping {}'.format(fn))
      return
    self.included.add(fn)
    print('  I - Including {}'.format(fn))
    with open(fn, 'r') as f:
      lines = f.readlines()
      protected = False
      for l in lines:
        l = l.rstrip()
        if l == '#pragma once':
          continue
        if protected:
          if l == '#endif':
            protected = False
          continue
        if l == '#if !defined(TC_AMALGAMATED)':
          protected = True
          continue
        match = re.search(include_template, l)
        need_expand = False
        if match:
          assert match.group(1) in ['\"', '<']
          local = (match.group(1) == '\"')
          includee = match.group(2)
          
          local_dir = os.path.dirname(fn)
          local_search_directories = search_directories
          if local:
            local_search_directories = [local_dir] + local_search_directories
          # Search for file
          found = False
          for d in local_search_directories:
            suspect_includee = os.path.join(d, includee)
            if os.path.exists(suspect_includee):
              found = True
              need_expand = True
              includee = suspect_includee
            else:
              pass # Should be system header
          if not found:
            print("  E - Classified as stdc++ header: {}".format(includee))
            #print("  ({})".format(l))
            need_expand = False
            
        if need_expand:
          includee = os.path.realpath(includee)
          self.include(includee)
        else:
          print(l, file=self.output_f)
  
  def run(self):
    self.output_f = open(output_fn, 'w')
    print("// This file is generated by the Taichi Amalgamator", file=self.output_f)
    print("// DO NOT EDIT BY HAND, unless you know that you are doing.", file=self.output_f)
    print("#define TC_INCLUDED", file=self.output_f)
    print("#define TC_AMALGAMATED", file=self.output_f)
    print("#define TC_ISE_NONE", file=self.output_f)
    for f in self.files:
      self.include(f)
    print("Included files:")
    for fn in sorted(list(self.included)):
      print("  {}".format(fn))
    self.output_f.close()
    self.output_f = None

  def test(self):
    with open('build/test_amal.cpp', 'w') as f:
      f.write('''\
#include "taichi.h"
using namespace taichi;

int main() {
  Vector4 v(21);
  auto x = v + v;
  fmt::print("{}\\n", x.x);
  TC_P(x);
}
''')
    t = time.time()
    if sys.platform.startswith('darwin'):
      os.system('g++ build/test_amal.cpp -o build/test_amal -std=c++14 -g -lpthread -I/opt/X11/include -L/opt/X11/lib -lX11  && ./build/test_amal')
    else:
      os.system('g++ build/test_amal.cpp -o build/test_amal -std=c++14 -g -lpthread -lX11 -O2  && ./build/test_amal')

    stat = os.stat('build/taichi.h')
    with open(output_fn) as f:
      print("taichi.h size: {} KB   LOC: {}".format(stat.st_size // 1024, len(list(f.readlines()))))
    print("Compilation time: {:.2f} seconds".format(time.time() - t))

if __name__ == '__main__':
  ama = Amalgamator()
  ama.run()
  ama.test()
