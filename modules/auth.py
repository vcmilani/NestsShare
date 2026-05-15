"""NestShare — PAM authentication"""
import pam as _pam

def authenticate(username: str, password: str) -> bool:
    return _pam.pam().authenticate(username, password, service="login")
