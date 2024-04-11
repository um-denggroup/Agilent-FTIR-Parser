#!/usr/bin/env python3

import struct
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from datetime import datetime

    
@dataclass
class Data:
    step : float
    start : float
    size : int
    data : np.array
    
    @property
    def xvals(self):
        return np.arange(self.start,self.start+self.size)*self.step
    
    
@dataclass
class Parms:
    DisplayDirection : int
    PeakDirection : int
    XLabel : str
    YLabel : str
    Unknown : [int]
    
    
@dataclass
class Spectrum:
    Data: Data
    Parms: Parms
    Properties: dict

@dataclass
class ImageFile:
    bytes: bytes
        
        
class SpectrumParser:
    def __init__(self,data):
        self.ints = []
        self.parse(data)
        
        
    #############################
    # RAW VALUE READING
    #############################
        
    def parseString(self):
        l = self.parseInt()
        s = struct.unpack_from(f'{l}s',self.data,self.offset)[0].decode('ascii')
        self.offset += l
        return s
    def parseInt(self):
        i = struct.unpack_from('<i',self.data,self.offset)[0]
        self.offset += 4
        return i
    def parseInts(self,count,signed=True):
        i = struct.unpack_from(f'<{count}'+('i' if signed else 'I'),self.data,self.offset)
        self.offset += 4*count
        self.ints.append(i)
        return i
    def parseDouble(self):
        d = struct.unpack_from('<d',self.data,self.offset)[0]
        self.offset += 8
        return d
    def parseDoubleArray(self,size):
        arr = np.frombuffer(self.data,dtype=np.float64,count=size,offset=self.offset)
        self.offset += size*8
        return arr
    
    #############################
    # Compound Value Reading
    #############################
    
    def parseSizedInt(self):
        sz = self.parseInt()
        i = int.from_bytes(self.data[self.offset:self.offset+sz],'little')
        self.offset += sz
        return i
    
    def parseSizedIntString(self):
        sz = self.parseSizedInt()
        s = self.parseString()
        assert len(s) == sz, f'{sz} {len(s)}:"{s}"'
        return sz,s
        
    def parseBlock(self):
        
        # Block header? (Data)
        print('[',self.parseString())
        
        # Unknown? Version or datatype?
        print('   ',self.parseInts(2))
        
        # Version number?
        print('   ',self.parseString())
        
        # Unknown
        print('   ',self.parseInts(3))
        
    
    def parseLabeledString(self,expect=None):
        label = self.parseSizedIntString() # e.g. Time Stamp
        data = self.parseInts(8) # For some reason the length of the string is repeated a third time at the end of these
        value = self.parseSizedIntString() # e.g. <THE TIME>
        if expect is not None:
            assert label[1] == expect, f'{label}!={expect} ({data} {value})'
        assert data[-1] == len(value[1]), f'{label}!={expect} ({data} {value})'
        assert all(d == 4 for d in data[0::2]), f'{label}!={expect} ({data} {value})'
        self.ints[-1] = ['sz',data[1:-1:2]]
        return label[1],data[1:-1:2],value[1]
        
    def parseDataBlock(self):
        # Data block header
        self.parseBlock()
        
        # Some sort of double value
        print(self.parseDouble())
        
        # Maybe a float or an int with a 4byte size specified
        print(self.parseSizedInt())
        
        # The size of the array
        sz = self.parseSizedInt()
        
        #Unknown
        self.parseInt()
        
        # The actual data
        arr = self.parseDoubleArray(sz)
        
        print(f' -- Parsed {len(arr)} {arr.dtype}s')
        
        return arr
    
    def parseSizedValue(self,sz):
        if sz < 256 and all(d in b' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890().,:-\\%'  for d in self.data[self.offset:self.offset+sz]):
            out = self.data[self.offset:self.offset+sz]
            self.offset += sz
            return out.decode('ascii')
        if sz == 4:
            return self.parseInt()
        elif sz == 8:
            return self.parseDouble()
        elif sz > 100:
            self.offset += sz
            return f'<{sz}> bytes',self.offset-sz,self.offset#self.parseDoubleArray(sz//8);
        elif sz == 0:
            return None
        else:
            out = self.data[self.offset:self.offset+sz]
            self.offset += sz
            return out
        
    
    def parseValues(self,size,depth):
        return tuple(self.parseSizedValue(self.parseInt()) for i in range(size))
            
        
    
    def parseItem(self,activeDict,depth=0):
        s = self.parseString()
        isValue, size = self.parseInts(2)
        if not isValue:
            print('. '*depth + s + f': ({size})')
            activeDict[s] = {}
            for i in range(size):
                self.parseItem(activeDict[s],depth+1)
        else:
            print('. '*(depth) + '-' + s + f': [{size}]')
            items = self.parseValues(size,depth+1)
            print(*['. '*(depth+1)+str(v) for v in items],sep='\n')
            activeDict[s] = items
            
    ########################################################
    # Convert to classes and re-parse 1.00 and 2.00 entries
    
    
    def parseData(self,entry):
        assert len(entry) == 1 and list(entry.keys())[0] == '1.00', entry.keys()
        e = entry['1.00']
        
        b,end = e[3][1:]
        assert e[2] == (end-b)/8
        data = np.frombuffer(self.data,dtype=np.float64,count=e[2],offset=b)
        return Data(*e[:3],data)
    
    def parseParms(self,entry):
        assert len(entry) == 1 and list(entry.keys())[0] == '1.00', entry.keys()
        e = entry['1.00']
        assert e[2] == len(e[3])
        assert e[4] == len(e[5])
        return Parms(*e[:2],e[3],e[5],e[6:])
    
    def parseMethod(self,name,entry):
        assert len(entry) == 1 and '2.00' in entry, entry.keys()
        e = entry['2.00']
        #assert e[0] == 1 and e[1] == 0xffFFffFF,(name,e[:5])
        # Not sure what those are. Just return them as well?
        out = [e[0:2]]
        e = list(e[2:])
        
        def val(size):
            sizes = tuple(e[0:size*2:2])
            res = tuple(e[1:size*2:2])
            # TODO: Actually check the sizes?
            del e[:size*2]
            if len(res) == 2 and type(res[0]) == int and type(res[1]) == str:
                return res[1]
            return res
        
        def string():
            sz = e.pop(0)
            s = e.pop(0)
            assert len(s) == sz, f'Invalid String Length in {name} > {sz}:{s}'
            return s
        
        def item(activeDict,depth=0):
            s = string()
            isValue = e.pop(0)
            size = e.pop(0)
            if not isValue:
                print('. '*depth + s + f': ({size})')
                activeDict[s] = {}
                for i in range(size):
                    item(activeDict[s],depth+1)
            else:
                print('. '*(depth) + '-' + s + f': [{size}]')
                items = val(size)
                print(*['. '*(depth+1)+str(v) for v in items],sep='\n')
                activeDict[s] = items
        
        
        isValue = e.pop(0)
        size = e.pop(0)
        assert isValue == 0
        for i in range(size):
            out.append( {} )
            item(out[-1])
        
        assert len(e) == 0,e
        return out
    
    def deduceSpectrumFileName(self):
        id = self.parseProperty('ID',self.parsed['Properties']['ID'])
        name = self.parseProperty('SpectName',self.parsed['Properties']['SpectName'])
        return f'{id}_{name}'
        
    def parseProperty(self,name,entry):
        t = entry['PropType'][0]
        if t in {1 : 'str', 16 : 'id'}:
            assert len(entry) == 2
            e = entry['1.00']
            assert e[0] == len(e[1])
            return e[1]
        
        elif t == 2:
            # Unix timestamp
            assert len(entry) == 2
            e = entry['1.00']
            return datetime.fromtimestamp(e[0])
        
        
        elif t == 20:
            # (JPEG) File
            assert len(entry) == 2 and '1.00' in entry, entry.keys()
            e = entry['1.00']
            
            b,end = e[-1][1:]
            assert e[-2] == (end-b)
            
            return ImageFile(self.data[b:end])
        
        elif t == 7:
            # Interferogram
            assert len(entry) == 3
            d = self.parseData(entry['Data'])
            p = self.parseParms(entry['Parms'])
            return Spectrum(d,p,None)
        
        elif t in {11: 'Created',6: 'History'}:
            assert len(entry) == 2
            return { 'Method' : self.parseMethod(name,entry['Method']) }
        
        else:
            print(f'** Unknown PropType {t} in {name}')
            
            
    #11: 'Created:Method=2.00',
    #6: 'History:Method=2.00',
        
            
    def parseToClasses(self):
        spectrum = Spectrum(None,None,None)
        spectrum.Data = self.parseData(self.parsed['Data'])
        spectrum.Parms = self.parseParms(self.parsed['Parms'])
        spectrum.Properties = {k : self.parseProperty(k,v) for k,v in self.parsed['Properties'].items()}
        
        print(spectrum)
        return spectrum
        
    ######################################
    # Master parsing
        
    def parse(self,data):
        self.data = data
        self.offset = 0
        
        # Root level entries
        self.entries = self.parseInt()
        
        self.parsed = {}
        
        #while self.offset < len(self.data):
        for i in range(self.entries):
            self.parseItem(self.parsed)
            
        self.spectrum = self.parseToClasses()
        
        
if __name__ == '__main__':
    filename = 'Example-Spectrum.bin'
    with open(filename,'rb') as f:
        raw = f.read()
            
    print('#'*80)
    print('Parsing')
    print('#'*80)

    p = SpectrumParser(raw)

    #from pprint import pprint
    #pprint(p.parsed)

    import json
    with open(filename+'.json','w') as f:
        json.dump(p.parsed,f,indent=2)
        
    # https://stackoverflow.com/a/51286749
    import dataclasses
    class EnhancedJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o,ImageFile):
                    fn = f'{p.spectrum.deduceSpectrumFileName()}.{name}.jpg'
                    with open(fn,'wb') as f:
                        f.write(o.bytes)
                    return f'<@{fn}>'
                if dataclasses.is_dataclass(o):
                    return dataclasses.asdict(o)
                if isinstance(o,np.ndarray):
                    return '<Data Omitted to Reduce File Size>' # list(o)
                if isinstance(o,datetime):
                    return str(o)
                return super().default(o)
    with open(p.deduceSpectrumFileName()+'.json','w') as f:
        json.dump(p.spectrum,f,indent=2,cls=EnhancedJSONEncoder)
        
