#!/usr/bin/env python3

import olefile
import sys
import dataclasses
import json
import pandas as pd

from parse_spectrum import *

if len(sys.argv) == 2:
    filename = sys.argv[1]
else:
    print('USAGE: {sys.argv[0]} <BSP-FILENAME>')
    exit(-1)



ole = olefile.OleFileIO(filename)
listdir = ole.listdir()
streams = []
for direntry in listdir:
    #print direntry
    streams.append('/'.join(direntry))
print(*streams,sep='\n')

spectra = {}
for s in streams:
    if s.startswith('Spectra/') and s != 'Spectra/IndexTable':
        data = ole.openstream(s).getvalue()
        try:
            p = SpectrumParser(data)
            spectra[p.deduceSpectrumFileName()] = p.spectrum
        except:
            print('Failed to parse stream',s)
            raise
        

class EnhancedJSONEncoder(json.JSONEncoder):    
    def default(self, o):
        if not hasattr(self,'images'):
            self.images = 0
            self.arrays = 0
        if isinstance(o,ImageFile):
            fn = f'out/{base}.{self.images}.jpg'
            self.images += 1
            with open(fn,'wb') as f:
                f.write(o.bytes)
            return f'<@{fn}>'
        if isinstance(o,Spectrum):
            self.arrays += 1
            fn = f'out/{base}.{self.arrays}.csv'
            xl,yl = o.Parms.XLabel, o.Parms.YLabel
            df = pd.DataFrame.from_dict({xl:o.Data.xvals, yl:o.Data.data})
            df.to_csv(fn,index=False)
            
            return {'Data':fn, 'Parms':o.Parms, 'Properties': o.Properties}            
            
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o,np.ndarray):
            return '<Data Omitted to Reduce File Size>'
        #if isinstance(o,np.ndarray):
            #fn = f'out/{s.deduceSpectrumFileName()}.npy'
            #np.save(fn,o)
            #return f'<@{fn}>'
        if isinstance(o,datetime):
            return str(o)
        return super().default(o)
for base,s in spectra.items():
    #fn = f'out/{base}.csv'
    #xl,yl = s.Parms.XLabel, s.Parms.YLabel
    #df = pd.DataFrame.from_dict({xl:s.Data.xvals, yl:s.Data.data})
    #df.to_csv(fn,index=False)
    with open(f'out/{base}.json','w') as f:
        json.dump(s,f,indent=2,cls=EnhancedJSONEncoder)
