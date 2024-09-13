import hashlib
from get_salt import get_salt

def hash_username(username):
    data_to_hash = get_salt() + username.encode('utf-8')
    hash_object = hashlib.sha256(data_to_hash)

    return hash_object.hexdigest()