#!/usr/bin/env python

import os, sys, optparse, commands, shutil

######### Extensions and exclusions configuration here #########

VALIDEXT = [".jpg", ".jpeg", ".cr2", ".mov", ".mpg", ".mpeg", ".avi", ".mp4"]
EXCLUDE  = ["aplibrary"]

############# AUTOMATIC MODE CONFIGURATION HERE!!!! ############

# Path where camera cards are mounted. Will search each subfolder looking
# for one that contains a DCIM folder, which will be used as the card_dir.
MOUNTDIR = "/Volumes"

# Folder where your photos are stored. Photos will NOT be copied here.
# The script only scans this folder to see which photos you already have.
PHOTOSDIR = "~/Pictures/Photo Library"

# Folder to copy your photos to
STAGINGDIR = "~/Desktop/Photo Staging"

# Fallback directory to copy from if no card is found
# (useful if you've manually copied photos off the card)
FALLBACKDIR = "~/Desktop/Photo Import"

################################################################

def getAutoDirs():
    photosDir  = os.path.expanduser(PHOTOSDIR)
    stagingDir = os.path.expanduser(STAGINGDIR)

    print
    print "searching for camera card"
    cardDir = None
    for d in os.listdir(MOUNTDIR):
        d1 = os.path.expanduser(os.path.join(MOUNTDIR, d, "DCIM"))
        if os.path.isdir(d1):
            cardDir = d1
        else:
            print "couldn't find card directory: " + d1

    fallbackDir = os.path.expanduser(FALLBACKDIR)
    if cardDir is None and os.path.exists(fallbackDir):
        cardDir = fallbackDir
        print "no card found, using fallback import location, " + fallbackDir

    if cardDir is None:
        print "no card found, aborting"
        sys.exit(-1)

    if not os.path.exists(stagingDir):
        print "creating staging directory: " + stagingDir
        os.mkdir(stagingDir)

    print
    print "using card directory: " + cardDir
    print "    photos directory: " + photosDir
    print "   staging directory: " + stagingDir
    print
    return cardDir, photosDir, stagingDir

def validExtensions():
    extensions = []
    for ext in VALIDEXT:
        extensions.append(ext.lower())
        extensions.append(ext.upper())
    return extensions

def fileFingerprint(filePath):
    """Return a tuple that uniquely identifies a file"""
    # Note: This used to use an MD5 of the file, but it was way too slow. So
    #       instead it grabs some arbitrary data from the middle of the file.
    #       This isn't nearly as unique as a checksum, but with file name and
    #       size it is sufficient for our purposes.

    (root, fileName) = os.path.split(filePath)

    #filename (before extension or "-")
    name = fileName.split("-")[0].split(".")[0]

    #filesize
    fs = os.stat(filePath)
    size = fs.st_size

    #some arbitrary file data
    fileHandle = open(filePath, "rb")
    fileHandle.seek(-1024, 2) # seek from end of file
    data = fileHandle.read(16)
    fileHandle.close()

    return (name, size, data)

def fileSetFromDir(dirPath):
    """Return set of fingerprint/path tuples for all image files in dirPath"""
    # Structure of returned tuple: ((name, size, data), filePath)
    fileSet = list()
    for root, dirs, files in os.walk(dirPath):
        skipdir = False
        for ex in EXCLUDE:
            if root.find(ex) != -1:
                skipdir = True
        if not skipdir:
            for f in files:
                if validExtensions().count(os.path.splitext(f)[1]):
                    filePath = os.path.join(root, f)
                    fileSet.append((fileFingerprint(filePath), filePath))
    return fileSet

def compareFileSets(cardSet, photosSet):
    """Return set of fingerprint/path tuples for files that are in cardSet but not in photosSet"""
    outputSet = []
    for s in cardSet:
        inPhotosSet = False
        for d in photosSet:
            if s[0] == d[0]:
                inPhotosSet = True
                break
        if not inPhotosSet:
            outputSet.append(s[1])
    return outputSet

def progressBar(width, progress, total):
    stars  = int(progress/float(total)*(width-2))
    spaces = int((total-progress)/float(total)*(width-2))
    percent = progress/float(total)*100
    bar = "[" + "="*stars + ">" + " "*spaces + "]"
    return bar, percent

def printProgressBar(progress, total, filename):
    bar, percent = progressBar(50, progress, total)
    sys.stdout.write(" "*80 + "\r")
    sys.stdout.write("%s %2.1f%% %s\r" % (bar, percent, filename))
    sys.stdout.flush()

def copyFile(sourceFile, dest, dupe=0):
    if dupe > 0:
        fl = os.path.splitext(os.path.split(sourceFile)[1])
        fname = fl[0] + "-" + str(dupe+1) + fl[1]
    else:
        fname = sourceFile

    if os.path.exists(os.path.join(dest, os.path.split(fname)[1])):
        existingPrint = fileFingerprint(os.path.join(dest, os.path.split(fname)[1]))
        newPrint      = fileFingerprint(sourceFile)
        if existingPrint == newPrint:
            print "duplicate file found in source - skipping"
        else:
            copyFile(sourceFile, dest, dupe+1)
    else:
        if dupe > 0:
            sys.stdout.write(" "*80 + "\r")
            print "duplicate file name found - renaming to " + fname
            shutil.copy(sourceFile, os.path.join(dest, fname))
        else:
            #print "copying " + fname
            shutil.copy(sourceFile, dest)

def copyFiles(fileSet, directory):
    i = 0
    total = len(fileSet)
    for f in fileSet:
        printProgressBar(i, total, os.path.split(f)[1])
        copyFile( f, directory )
        i += 1
    printProgressBar(i, total, os.path.split(f)[1])
    print


def parseOptions():
    parser = optparse.OptionParser()

    parser.usage = "%prog [options] card_dir photos_dir staging_dir"
    parser.usage += "\n  card_dir:    directory to copy photos from (usually an SD card)"
    parser.usage += "\n  photos_dir:  directory containing your photo library"
    parser.usage += "\n  staging_dir: directory to copy photos to"

    parser.add_option("-d", "--dry-run", dest="dryrun", action="store_true",
        help = "dry run (don't perform any copy)")

    parser.add_option("-a", "--automode", dest="automode", action="store_true",
        help = "automatic mode (use defaults defined at top of script)")

    options, arguments = parser.parse_args()

    return (options, arguments, parser)


if __name__ == "__main__":
    (options, arg, parser) = parseOptions()

    # Get directories from commandline or automatically
    if len(arg) < 1 and options.automode:
        print "running in AUTOMATIC MODE"
        cardDir, photosDir, stagingDir = getAutoDirs()
    elif len(arg) == 3:
        cardDir    = arg[0]
        photosDir  = arg[1]
        stagingDir = arg[2]
    else:
        parser.print_usage()
        sys.exit(-1)

    # Validate directories
    if not os.path.isdir(cardDir):
        print "Cannot find card directory: " + cardDir
        sys.exit(-1)
    if not os.path.isdir(photosDir):
        print "Cannot find photos directory: " + photosDir
        sys.exit(-1)
    if not os.path.isdir(stagingDir):
        print "Cannot find staging directory: " + stagingDir
        sys.exit(-1)

    # Perform scans
    print "scanning card"
    cardSet = fileSetFromDir(cardDir)
    print len(cardSet)

    print "scanning photos directory"
    photosSet = fileSetFromDir(photosDir)
    print len(photosSet)

    print "scanning staging directory"
    stagingSet = fileSetFromDir(stagingDir)
    print len(stagingSet)
    photosSet.extend(stagingSet)

    # Compute files to copy
    print "computing output files"
    stagingSet = compareFileSets(cardSet, photosSet)
    print len(stagingSet)

    # Do the copy if needed
    if len(stagingSet) == 0:
        print "no files to copy"
    elif options.dryrun:
        print "not copying files, this is a dry run"
    else:
        print "copying files"
        copyFiles(stagingSet, stagingDir)
