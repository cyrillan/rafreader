#!/usr/bin/env python

import os
import zlib

DEBUG=1
def dbg(s):
  if DEBUG:
    print s

def str2uint32(s):
  # string to little endian uint32
  return ord(s[0]) + ord(s[1])*256 + ord(s[2])*256*256 + ord(s[3])*256*256*256

def uint32tostr(u):
  # little endian uint32 to string
  return chr(u%256) + chr((u/256)%256) + chr((u/256/256)%256) + chr((u/256/256/256)%256)

class RAFClass:
  def readHeaderFile(self, headerfile):
    self.headerfile = headerfile
    
    f = open(headerfile, 'r')
    self.magicNumber = str2uint32(f.read(4))
    self.version = str2uint32(f.read(4))
    self.mgrIndex = str2uint32(f.read(4))
    self.fileListOffset = str2uint32(f.read(4))
    self.pathListOffset = str2uint32(f.read(4))
    
    # read File List
    self.fileListCount = str2uint32(f.read(4))
    self.fileList = []
    for i in range(self.fileListCount):
      hash = str2uint32(f.read(4))
      dataOffset = str2uint32(f.read(4))
      dataSize = str2uint32(f.read(4))
      pathlistIndex = str2uint32(f.read(4))
      fileListEntry = (hash, dataOffset, dataSize, pathlistIndex)
      self.fileList.append(fileListEntry)
    assert self.fileListCount == len(self.fileList)
 
    # read Path List
    self.pathListSize = str2uint32(f.read(4))
    self.pathListCount = str2uint32(f.read(4))
    self.pathList = []  
    for i in range(self.pathListCount):
      pathOffset = str2uint32(f.read(4))
      pathLength = str2uint32(f.read(4))
      pathListEntry = (pathOffset, pathLength)
      self.pathList.append(pathListEntry)
    assert self.pathListCount == len(self.pathList)

    # read Path Strings
    self.pathStrings = []
    for i in range(self.pathListCount):
      pathString = f.read(self.pathList[i][1]) # includes null terminator
      pathString = pathString[:-1] # remove null terminator
      self.pathStrings.append(pathString)
    assert self.pathListCount == len(self.pathStrings)
  
    # finished
    return
  
  def readDataFile(self, datafile):
    self.datafile = datafile
    f = open(datafile, 'r')
    
    self.contents = []
    for fileEntry in self.fileList:
      f.seek(fileEntry[1])
      content = f.read(fileEntry[2])
      self.contents.append(content)
    
    f.close()
    return
    
  def printToTerminal(self):
    dbg('Magic number = %08x' % self.magicNumber)
    dbg('Version = %i' % self.version)
    dbg('Manager index = %i' % self.mgrIndex)
    dbg('File list starts at byte %i' % self.fileListOffset)
    dbg('Path list starts at byte %i' % self.pathListOffset)
    
    # print File List
    dbg('File list contains %i entries' % self.fileListCount)
    for i in range(self.fileListCount):
      e = self.fileList[i]
      dbg('%i hash=%08x dataOffset=%i dataSize=%i pathListIndex=%i' % (i, e[0], e[1], e[2], e[3]))
    
    # print Path List and Path Strings
    dbg('Path list is %i bytes in size' % self.pathListSize)
    dbg('Path list contains %i entries' % self.pathListCount)
    for i in range(self.pathListCount):
      e = self.pathList[i]
      ee = self.pathStrings[i]
      dbg('%i pathOffset=%i pathLength=%i string=%s' % (i, e[0], e[1], ee))

    # print merged view (redundant data)
    dbg('MERGED VIEW')
    for i in range(self.fileListCount):
      e = self.fileList[i]
      ee = self.pathStrings[e[3]]
      dbg('%i dataOffset=%i dataSize=%i filePath=%s' % (i, e[1], e[2], ee))
    return
      
  def dumpContents(self, outputpath):
    for i in range(len(self.fileList)):
      fileEntry = self.fileList[i]
      fileName = self.pathStrings[fileEntry[3]].split('/')[-1]
      content = self.contents[i]
      decompressedContent = zlib.decompress(content)
      
      f = open(outputpath + fileName, 'w')
      f.write(decompressedContent)
      f.close()
    return
    
  def checkDataAlignment(self):
    offsets = [e[1] for e in self.fileList]
    sizes = [e[2] for e in self.fileList]
    l = sorted(zip(offsets, sizes), key=lambda x: x[0])
    for i in range(len(l)-1):
      assert l[i][0] + l[i][1] == l[i+1][0] 
    print 'Data alignment passed'
    return

  def replaceContents(self, fileOnDisk, targetFileName):
    dbg('Replacing old file %s with new file %s' % (targetFileName, fileOnDisk))
    
    fileNameOnDisk = fileOnDisk.split('/')[-1]
    targetCount = 0
    targetIndex = -1
    for i in range(len(self.fileList)):
      fileName = self.pathStrings[self.fileList[i][3]].split('/')[-1]
      if fileName == targetFileName:
        targetCount += 1
        targetIndex = i
    assert targetCount == 1
    
    dbg('Target index = %i' % targetIndex)
    dbg(str(self.fileList[targetIndex]))
    
    f = open(fileOnDisk, 'r')
    decompressedContent = f.read()
    content = zlib.compress(decompressedContent)
    f.close()
    
    # overwrite data
    self.contents[targetIndex] = content
    
    # overwrite data size
    e = self.fileList[targetIndex]
    newDataSize = len(content)
    oldDataSize = e[2]
    dataOffsetShift = newDataSize - oldDataSize
    dbg('Old data size = %i, new data size = %i' % (oldDataSize, newDataSize))
    targetDataOffset = e[1]
    dbg('Applying shift of %i to all data offsets after %i' % (dataOffsetShift, targetDataOffset))
    self.fileList[targetIndex] = (e[0], e[1], newDataSize, e[3])
    
    # overwrite data offsets for all file entries where data offset > offset of file being replaced
    for i in range(len(self.fileList)):
      if self.fileList[i][1] > targetDataOffset:
        dbg('Index %i in fileList is after replaced file' % i)
        e = self.fileList[i]
        dbg(str(e))
        self.fileList[i] = (e[0], e[1] + dataOffsetShift, e[2], e[3])
        dbg(str(self.fileList[i]))
    
    # finished
    return
    
  def writeHeaderFile(self, outfile):
    f = open(outfile, 'w')
    f.write(uint32tostr(self.magicNumber))
    f.write(uint32tostr(self.version))
    f.write(uint32tostr(self.mgrIndex))
    f.write(uint32tostr(self.fileListOffset))
    f.write(uint32tostr(self.pathListOffset))
    
    f.write(uint32tostr(self.fileListCount))
    for i in range(self.fileListCount):
      fileListEntry = self.fileList[i]
      f.write(uint32tostr(fileListEntry[0]))
      f.write(uint32tostr(fileListEntry[1]))
      f.write(uint32tostr(fileListEntry[2]))
      f.write(uint32tostr(fileListEntry[3]))
    
    f.write(uint32tostr(self.pathListSize))
    f.write(uint32tostr(self.pathListCount))
    for i in range(self.pathListCount):
      pathListEntry = self.pathList[i]
      f.write(uint32tostr(pathListEntry[0]))
      f.write(uint32tostr(pathListEntry[1]))
    
    for i in range(self.pathListCount):
      pathString = self.pathStrings[i] + chr(0) # put back null terminator since we took it off
      f.write(pathString)
      
    # finished
    f.close()
    return
  
  def writeDataFile(self, outfile):
    f = open(outfile, 'w')
    for i in range(len(self.fileList)):
      fileEntry = self.fileList[i]
      f.seek(fileEntry[1])
      f.write(self.contents[i])

    f.close()
    return

def main():
  basepath = '/cygdrive/c/Program Files/Riot Games/League of Legends/RADS/projects/lol_game_client/filearchives/'
  outputpath = '/cygdrive/c/Users/Cyril/Desktop/output/'
  
  # get list of subdirs
  subdirs = os.listdir(basepath)
  for subdir in sorted(subdirs, key=lambda x: int(x.split('.')[3]), reverse=True):
  
    # FOR TESTING
    if subdir != '0.0.0.150':
      continue
      
    path = basepath + subdir + '/'
    # read list of files in each dir
    headerfiles = [e for e in os.listdir(path) if e[-4:] == '.raf']
    for headerfile in headerfiles:
      print 'About to read %s' % (path + '/' + headerfile)
      myclass = RAFClass()
      myclass.readHeaderFile(path + headerfile)
      myclass.readDataFile(path + headerfile + '.dat')
      myclass.printToTerminal()
      myclass.dumpContents(outputpath)
      myclass.checkDataAlignment()
      
      '''
      (orig filename)   --> (replacement)
      Hand1.tga         --> SingleTarget_Colorblind.tga
      Hand2.tga         --> SingleTarget.tga
      HoverEnemy.tga    --> SingleTargetEnemy.tga
      HoverFriendly.tga --> SingleTargetAlly.tga
      '''

      myclass.replaceContents(outputpath + 'SingleTarget_Colorblind.tga', 'Hand1.tga')
      myclass.checkDataAlignment()
      #myclass.replaceContents(outputpath + 'SingleTarget.tga', 'Hand2.tga')
      #myclass.checkDataAlignment()
      #myclass.replaceContents(outputpath + 'SingleTargetEnemy.tga', 'HoverEnemy.tga')
      #myclass.checkDataAlignment()
      #myclass.replaceContents(outputpath + 'SingleTargetAlly.tga', 'HoverFriendly.tga')
      #myclass.checkDataAlignment()
      
      myclass.writeHeaderFile(path + headerfile + '.new')
      myclass.writeDataFile(path + headerfile + '.dat' + '.new')
  return

if __name__ == '__main__':
  main()

  
