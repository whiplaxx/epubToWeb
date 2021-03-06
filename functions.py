#!/bin/env python3

from os import path, mkdir, scandir, listdir, getcwd
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from shutil import copy, rmtree

__location__ = path.realpath( path.join( getcwd(), path.dirname(__file__) ) )

def getSpineFromOpf( opfAbsPath ):

    with open( opfAbsPath, 'r' ) as contentOpfFile:
        root = ET.fromstring( contentOpfFile.read() )

    # Getting and setting the namespace
    ns = { 'ns': root.tag[1: root.tag.find('}')] }
    
    # Getting the manifest items
    # manifest is the list of all the items (html, images, etc) in the epub
    manifestObj = root.find('ns:manifest', ns)
    manifestItems = { item.attrib['id']: item.attrib['href']  for item in manifestObj.findall('ns:item', ns) }

    # Getting spine items refs
    # spine is the ordered list of ids of the items that compose the book index
    spineObj = root.find('ns:spine', ns)
    spineIds = [ item.attrib['idref'] for item in spineObj.findall('ns:itemref', ns) ]

    spine = []
    for itemId in spineIds:
        itemPath = manifestItems[ itemId ]
        spine.append( [itemPath, itemPath] )
    
    return spine

def getAllItemsFromNcx( root ):
    
    ns = {'ns': root.tag[1:root.tag.find('}')]}

    navMap = root.find('ns:navMap', ns)
    labels = navMap.findall('.//ns:navLabel', ns)
    contents = navMap.findall('.//ns:content', ns)
    
    if( len(labels) != len(contents )):
        raise
    
    items = []
    for index in range( len(labels) ):
        try:
            path = contents[ index ].attrib['src']
            title = labels[ index ].find('ns:text', ns).text
            if( title == None ):
                title = path
            items.append( [title, path] )
        except:
            print( "An exception ocurred and some content could be lost in the book index." )
            print("Aborting the execution.")

    return items

def getSpineFromNcx( ncxContent, ncxAbsPath ):
    # spine is the files and their order that will appear in the book index
    
    root = ET.fromstring( ncxContent )
    ns = {'ns': root.tag[ 1: root.tag.find('}') ] }

    # trying to load book's infos
    infos = {'title':'', 'author':''}
    try:
        title = root.find('ns:docTitle', ns).find('ns:text', ns).text
        infos['title'] = title
        try:
            author = root.find('ns:docAuthor', ns).find('ns:text', ns).text
            infos['author'] = author
        except:
            print("Book's author could not be loaded.")
    except:
        print("Book's title could not be loaded.")
    
    try:
        unverifiedSpine = getAllItemsFromNcx( root )
    except:
        print('An error ocurred while reading the .ncx file.')
        raise
    
    # iterating over each item in the spine to verify the path
    # in some epub there can be extra stuffs at the end and this is removing them
    spine = []
    for item in unverifiedSpine:
        # removing char by char at the end until the path exists or the item path is empty
        itemPath = item[1]
        for index in range( len(itemPath) ):
            if( path.exists( path.join(ncxAbsPath, itemPath) ) ):
                break
            itemPath = itemPath[0:-1]
        
        if( len(itemPath) > 0 ):
            item[1] = itemPath
            spine.append( item )
        else:
            print("Errors ocurred with {} file and will not be in the spine.".format(content.attrib['src']))
    
    return spine, infos

# if str1 ends with str2, return str1 cutting str2
def endsWith( str1, str2 ):
    len1 = len(str1)
    len2 = len(str2)

    if( str1[ len1-len2: len1 ] == str2 ):
        return str1[0:len1-len2]
    return str1

# Get the relative path for the first path link the second one
def getRelativePath( firstPath, secondPath ):
    
    splittedFirstPath = firstPath.split('/')
    splittedSecondPath = secondPath.split('/')

    while( len(splittedFirstPath) > 1 ):
        if splittedFirstPath[0] == splittedSecondPath[0]:
            del splittedFirstPath[0]
            del splittedSecondPath[0]
        else:
            break
    relativePath = ''

    # Second path is above
    if len(splittedFirstPath) > 1:
        for index in range( len(splittedFirstPath) - 1): relativePath += '../'
        for folder in splittedSecondPath: relativePath = path.join(relativePath, folder)
    # Second path is a neighbour or is under the first
    else:
        for folder in splittedSecondPath: relativePath = path.join(relativePath, folder)
    
    return relativePath

# Returns the path of the first file found with the extensions passed
def findFileByExtension( filesPathList, extension ):
    if( extension[0] != '.'):
        extension = '.' + extension.lower()

    for filePath in filesPathList:
        fileExtension = path.splitext( filePath )[1].lower()
        if( fileExtension == extension ):
            return filePath
    return ''

# Copy a folder and every content in it to the destiny folder
def copyFolderRecursively( originFolderPath, destinyFolderPath ):
    
    try:
        listdir( destinyFolderPath )
    except FileNotFoundError:
        try:
            createFolder( destinyFolderPath )
        except:
            raise

    scanFiles = scandir( originFolderPath )
    paths = [ destinyFolderPath ]
    for scanFile in scanFiles:
        if( scanFile.is_file() ):
            originFilePath = path.join( originFolderPath, scanFile.name )
            destinyFilePath = path.join( destinyFolderPath, scanFile.name )
            copy( originFilePath, destinyFilePath )

            paths.append( destinyFilePath )
        elif( scanFile.is_dir() ):
            temp_originFolderPath = path.join( originFolderPath, scanFile.name )
            temp_destinyFolderPath = path.join( destinyFolderPath, scanFile.name )
            temp_paths = copyFolderRecursively( temp_originFolderPath, temp_destinyFolderPath )
            paths.extend( temp_paths )
    
    return paths

"""
# Creating a dict that represents the tree of content for the extracted epub
def getTreeOfContent(self, absPath):
    tree = {'/':{}}
    scanDir = scandir(absPath)
    for scanFile in scanDir:
        if( scanFile.is_file() ):
            tree['/'][scanFile.name] = scanFile

            # Verifying if it's the [toc].ncx file
            if( (path.splitext(scanFile.name)[1]).lower() == '.ncx' ):
                self.tocInfos = (absPath, scanFile.name)
            # Verifying if it's the [content].opf file
            elif( (path.splitext(scanFile.name)[1]).lower() == '.opf' ):
                self.contentOpfInfos = (absPath, scanFile.name)
        else:
            scanFileAbsPath = path.join( absPath, scanFile.name )
            tree[scanFile.name] = getTreeOfContent( scanFileAbsPath )
    return tree
"""

def strStartsWith( str1, str2 ):
    
    for charIndex in range( len(str2) ):
        if( str1[charIndex] != str2[charIndex] ):
            return False
    return True

def extractEpub( epub, extractedEpubAbsPath ):
    try:
        epub.extractall( extractedEpubAbsPath )
    except:
        print("Couldn't extract the epub.")
        print("Aborting the execution.")
        raise

def loadEpub( epubAbsPath ):
    try:
        epub = ZipFile( epubAbsPath )
        return epub
    except:
        print("Couldn't load the epub file {}.".format(epubAbsPath))
        print("Aborting the execution.")
        raise

def createFolder( path ):
    try:
        mkdir( path )
    except:
        print("Couldn't create {} folder.".format(path))
        print("Aborting the execution.")
        raise

def deleteFolder( path ):
    rmtree( path )

### nao lembro oque e isso
def formatData(t,s):
    if not isinstance(t,dict) and not isinstance(t,list):
        print("\t"*s+str(t))
    else:
        for key in t:
            print("\t"*s+str(key))
            if not isinstance(t,list):
                self.formatData(t[key],s+1)

if __name__ == '__main__':
    # print( getSpineFromOpf( '/home/alex/Documents/epubToWeb/content.opf' ) )
    print( getRelativePath( '/dir1/dir2/file1.html', '/') )
