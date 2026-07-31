import pymysql
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="8410",      # Si tienes contraseña, escríbela aquí
        database="kion_hats",
        cursorclass=pymysql.cursors.DictCursor
    )