from security import hash_password

password = "mypassword123"

print(password)
print(len(password))
print(type(password))
hashed = hash_password(password)
print(hashed)


