# rafreader
A decoder for the League of Legends RAF file format. Work was primarily based off of this wiki page
[http://leagueoflegends.wikia.com/wiki/RAF:_Riot_Archive_File]

Description
  
main
"contains some boilerplate code that I used for experimentation. My goal was to replace a mouse cursor file that was compressed in a .dat file. The steps to accomplish that are 1) read in the header and data file, 2) overwrite a section of the data file and update the header file accordingly, and 3) write both files back to disk. As of around August 2015, it seems like Riot has incorporated some type of checksum not part of the .raf and .dat files, and modifying any .raf or .dat files will cause the game to fail to load and trigger the game file repair wizard."

class RAFClass
"an in-memory representation of a pair of RAF header + data file"

  readHeaderFile
  "parses a .raf header file and loads its contents (header, file list, path list, path strings) into memory"

  readDataFile
  "reads a .dat data file, corresponding to the .raf header file, and loads its contents (concatenated binary file objects) into memory"

  printToTerminal
  "a debug function that prints header file info to the screen"

  dumpContents
  "separates and decompresses individual file objects that were inside the .dat file, and writes each one to disk"
  
  checkDataAlignent
  "checks that file offsets and file sizes are correct in the header file data"
  
  replaceContents
  "reads an individual file object from disk, compresses it, and overwrites a section of the .dat file corresponding to a target file name. Also modifies the target file size and file offsets accordingly in the header, in the case that the new file was of a different size"
  
  writeHeaderFile
  "writes a .raf header file back to disk"
  
  writeDataFile
  "writes a .dat data file back to disk"
