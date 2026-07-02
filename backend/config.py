import pymysql

connection = pymysql.connect(
    host="localhost",
    user="root",
    password="MySQL@123123123",
    database="smart_quiz"
)

print("Database Connected Successfully ✅")