from security import hash_password, verify_password

password = "mypassword123"

hashed = hash_password(password)

print("Hash:", hashed)
print("correct password:", verify_password(password, hashed))
print("Wrong password:", verify_password("wrongpassword", hashed))
