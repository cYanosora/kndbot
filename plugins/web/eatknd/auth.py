from typing import Dict, Any
try:
    from jose import jwt
except:
    import jwt

SECRET_KEY = "here are your key~"
algorithm = "here are your algorithm~"

def encrypt(data: Dict[Any, Any]):

    return jwt.encode(data, SECRET_KEY, algorithm=algorithm)


def decrypt(text: str):

    return jwt.decode(text, SECRET_KEY, algorithms=[algorithm])

