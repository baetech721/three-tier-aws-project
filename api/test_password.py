from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()
password = "myPassword123"
hashed = password_hash.hash(password)

print("Hash", hashed)
print("correct password:", password_hash.verify(password, hashed))
print("wrong password:", password_hash.verify("WrongPassword", hashed))
