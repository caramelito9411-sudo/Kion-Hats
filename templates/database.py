import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="8410",      
        database="kion_hats",
        cursorclass=pymysql.cursors.DictCursor
    )