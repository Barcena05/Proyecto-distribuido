import os
import hashlib

def calculate_hash(file_path):
    with open(file_path, "rb") as file:
        content = file.read()
        hash_object = hashlib.md5()
        hash_object.update(content)
        return hash_object.hexdigest()

def find_duplicate_files(folder_path):
    hashes: dict[str,list[str]] = {}
    file_names: list[str] = os.listdir(folder_path)
    for filename in file_names:
        file_format = filename.split('.')[-1] if len(filename.split('.'))>1 else None
        if file_format:            
            file_path = os.path.join(folder_path, filename)
            file_hash = calculate_hash(file_path)
            filename = filename[: -len(file_format)-1]
            if file_hash in hashes:
                hashes[file_hash].append((filename,file_format))
            else:
                hashes[file_hash] = [(filename,file_format)]
    return hashes