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

def get_auto_dirs():
    photos_dir  = os.path.expanduser(PHOTOSDIR)
    staging_dir = os.path.expanduser(STAGINGDIR)

    print
    print "searching for camera card"
    card_dir = None
    for d in os.listdir(MOUNTDIR):
        d1 = os.path.expanduser(os.path.join(MOUNTDIR, d, "DCIM"))
        if os.path.isdir(d1):
            card_dir = d1
        else:
            print "couldn't find card directory: " + d1

    fallback_dir = os.path.expanduser(FALLBACKDIR)
    if card_dir is None and os.path.exists(fallback_dir):
        card_dir = fallback_dir
        print "no card found, using fallback import location, " + fallback_dir

    if card_dir is None:
        print "no card found, aborting"
        sys.exit(-1)

    if not os.path.exists(staging_dir):
        print "creating staging directory: " + staging_dir
        os.mkdir(staging_dir)

    print
    print "using card directory: " + card_dir
    print "    photos directory: " + photos_dir
    print "   staging directory: " + staging_dir
    print
    return card_dir, photos_dir, staging_dir

def valid_extensions():
    extensions = []
    for ext in VALIDEXT:
        extensions.append(ext.lower())
        extensions.append(ext.upper())
    return extensions

def file_fingerprint(file_path):
    """Return a tuple that uniquely identifies a file"""
    # Note: This used to use an MD5 of the file, but it was way too slow. So
    #       instead it grabs some arbitrary data from the middle of the file.
    #       This isn't nearly as unique as a checksum, but with file name and
    #       size it is sufficient for our purposes.

    (root, file_name) = os.path.split(file_path)

    #filename (before extension or "-")
    name = file_name.split("-")[0].split(".")[0]

    #filesize
    fs = os.stat(file_path)
    size = fs.st_size

    #some arbitrary file data
    file_handle = open(file_path, "rb")
    file_handle.seek(-1024, 2) # seek from end of file
    data = file_handle.read(16)
    file_handle.close()

    return (name, size, data)

def file_set_from_dir(dir_path):
    """Return set of fingerprint/path tuples for all image files in dir_path"""
    # Structure of returned tuple: ((name, size, data), file_path)
    file_set = list()
    for root, dirs, files in os.walk(dir_path):
        skipdir = False
        for ex in EXCLUDE:
            if root.find(ex) != -1:
                skipdir = True
        if not skipdir:
            for f in files:
                if valid_extensions().count(os.path.splitext(f)[1]):
                    file_path = os.path.join(root, f)
                    file_set.append((file_fingerprint(file_path), file_path))
    return file_set

def compare_file_sets(card_set, photos_set):
    """Return set of fingerprint/path tuples for files that are in card_set but not in photos_set"""
    output_set = []
    for s in card_set:
        in_photos_set = False
        for d in photos_set:
            if s[0] == d[0]:
                in_photos_set = True
                break
        if not in_photos_set:
            output_set.append(s[1])
    return output_set

def progress_bar(width, progress, total):
    stars  = int(progress/float(total)*(width-2))
    spaces = int((total-progress)/float(total)*(width-2))
    percent = progress/float(total)*100
    bar = "[" + "="*stars + ">" + " "*spaces + "]"
    return bar, percent

def print_progress_bar(progress, total, filename):
    bar, percent = progress_bar(50, progress, total)
    sys.stdout.write(" "*80 + "\r")
    sys.stdout.write("%s %2.1f%% %s\r" % (bar, percent, filename))
    sys.stdout.flush()

def copy_file(source_file, dest, dupe=0):
    if dupe > 0:
        fl = os.path.splitext(os.path.split(source_file)[1])
        fname = fl[0] + "-" + str(dupe+1) + fl[1]
    else:
        fname = source_file

    if os.path.exists(os.path.join(dest, os.path.split(fname)[1])):
        existing_print = file_fingerprint(os.path.join(dest, os.path.split(fname)[1]))
        new_print      = file_fingerprint(source_file)
        if existing_print == new_print:
            print "duplicate file found in source - skipping"
        else:
            copy_file(source_file, dest, dupe+1)
    else:
        if dupe > 0:
            sys.stdout.write(" "*80 + "\r")
            print "duplicate file name found - renaming to " + fname
            shutil.copy(source_file, os.path.join(dest, fname))
        else:
            #print "copying " + fname
            shutil.copy(source_file, dest)

def copy_files(file_set, directory):
    i = 0
    total = len(file_set)
    for f in file_set:
        print_progress_bar(i, total, os.path.split(f)[1])
        copy_file( f, directory )
        i += 1
    print_progress_bar(i, total, os.path.split(f)[1])
    print


def parse_options():
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
    (options, arg, parser) = parse_options()

    # Get directories from commandline or automatically
    if len(arg) < 1 and options.automode:
        print "running in AUTOMATIC MODE"
        card_dir, photos_dir, staging_dir = get_auto_dirs()
    elif len(arg) == 3:
        card_dir    = arg[0]
        photos_dir  = arg[1]
        staging_dir = arg[2]
    else:
        parser.print_usage()
        sys.exit(-1)

    # Validate directories
    if not os.path.isdir(card_dir):
        print "Cannot find card directory: " + card_dir
        sys.exit(-1)
    if not os.path.isdir(photos_dir):
        print "Cannot find photos directory: " + photos_dir
        sys.exit(-1)
    if not os.path.isdir(staging_dir):
        print "Cannot find staging directory: " + staging_dir
        sys.exit(-1)

    # Perform scans
    print "scanning card"
    card_set = file_set_from_dir(card_dir)
    print len(card_set)

    print "scanning photos directory"
    photos_set = file_set_from_dir(photos_dir)
    print len(photos_set)

    print "scanning staging directory"
    staging_set = file_set_from_dir(staging_dir)
    print len(staging_set)
    photos_set.extend(staging_set)

    # Compute files to copy
    print "computing output files"
    staging_set = compare_file_sets(card_set, photos_set)
    print len(staging_set)

    # Do the copy if needed
    if len(staging_set) == 0:
        print "no files to copy"
    elif options.dryrun:
        print "not copying files, this is a dry run"
    else:
        print "copying files"
        copy_files(staging_set, staging_dir)
