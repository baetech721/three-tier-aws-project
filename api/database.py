import os
import psycopg
from dotenv import load_dotenv
load_dotenv()

def get_connection():
    return psycopg.connect(
	host=os.getenv("db_host"),
	port=int(os.getenv("db_port")),
	dbname=os.getenv("db_name"),
	user=os.getenv("db_user"),
	password=os.getenv("db_password")
    )

def get_user_by_username(username):
    conn = get_connection()  # use your existing connection function
    cur = conn.cursor()

    cur.execute(
	"SELECT username, password_hash  FROM users WHERE username = %s",
	(username,)
    )
    user = cur.fetchone()

    cur.close()
    conn.close()

    return user
