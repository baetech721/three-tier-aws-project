from fastapi import FastAPI
from pydantic import BaseModel
from database import get_connection
from prometheus_fastapi_instrumentator import Instrumentator
app = FastAPI()
Instrumentator().instrument(app).expose(app)
@app.get("/")
def home():
	return {"message": "backend api is running"}
@app.get("/users")
def get_users():
	conn = get_connection()
	cursor = conn.cursor()

	cursor.execute("select id, username FROM users;")
	users = cursor.fetchall()

	cursor.close()
	conn.close()

	return users
class User(BaseModel):
	username: str
	password: str
@app.post("/register")
def register(user: User):
	conn = get_connection()
	cursor = conn.cursor()
	password_hash = hash_password(user.password)

	cursor.execute(
		"INSERT INTO users (username, password_hash) VALUES (%s, %s)",
		(user.username, password_hash)
	)
	conn.commit()

	cursor.close()
	conn.close()

	return {"message": "User registered successfully"}

from fastapi import Form, HTTPException
from database import get_user_by_username
from security import verify_password, hash_password

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
	user = get_user_by_username(username)
	if not user:
		raise HTTPException(status_code=401, detail="Invalid login")

	if not verify_password(password, user[1]):
		raise HTTPException(status_code=401, detail="invalid login")

	return {"message": "login successful"}
