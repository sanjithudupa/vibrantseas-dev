import sys
import tarfile
import os

if len(sys.argv) != 3:
    print("Usage: python3 tar_extraction.py <tar_path> <dump_path>")
    sys.exit(1)

tar_path = sys.argv[1]
dump_path = sys.argv[2]

if not os.path.exists(tar_path):
    print(f"Error: {tar_path} does not exist")
    sys.exit(1)

if not os.path.exists(dump_path):
    os.makedirs(dump_path)
    
    
def convert_extensions_to_lowercase(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            base, ext = os.path.splitext(filename)
            if ext == '.tif':
                new_filename = base + ext.upper()
                new_file_path = os.path.join(directory, new_filename)
                os.rename(file_path, new_file_path)
with tarfile.open(tar_path, "r:gz") as tar:
    
    print(f"Extracting {tar_path} to {dump_path}")
    tar.extractall(path=dump_path)
    
    print("Done")
    
    print("Fixing file extension case")
    convert_extensions_to_lowercase(dump_path)
    
    print("Done")
