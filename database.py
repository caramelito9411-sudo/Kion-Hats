import os
import pymysql
from urllib.parse import urlparse
def get_connection():
    database_url = os.getenv("MYSQL_URL")
    if database_url:
        url = urlparse(database_url)
        return pymysql.connect(
            host=url.hostname,
            port=url.port,
            user=url.username,
            password=url.password,
            database=url.path.lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor
        )
    return pymysql.connect(
        host="localhost",
        user="root",
        password="8410",
        database="kion_hats",
        cursorclass=pymysql.cursors.DictCursor
    )