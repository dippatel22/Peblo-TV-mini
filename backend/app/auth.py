from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

security=HTTPBearer(auto_error=False)
DEMO_USERS={
 'admin': {'password':'admin123','role':'admin'},
 'editor': {'password':'editor123','role':'editor'},
}

def hash_password(p): return pbkdf2_hmac('sha256',p.encode(),b'peblo-demo',120_000).hex()

def create_token(username, role):
    return jwt.encode({'sub':username,'role':role,'exp':datetime.now(timezone.utc)+timedelta(hours=8)},settings.jwt_secret,algorithm='HS256')

def authenticate(username,password):
    u=DEMO_USERS.get(username)
    return u and u['password']==password and {'username':username,'role':u['role']}

def current_user(creds:HTTPAuthorizationCredentials=Depends(security)):
    if not creds: raise HTTPException(status_code=401,detail='Please sign in.')
    try: return jwt.decode(creds.credentials,settings.jwt_secret,algorithms=['HS256'])
    except JWTError: raise HTTPException(status_code=401,detail='Your session has expired. Please sign in again.')

def require_editor(user=Depends(current_user)): return user

def require_admin(user=Depends(current_user)):
    if user.get('role')!='admin': raise HTTPException(status_code=403,detail='Admin access is required for publishing.')
    return user
