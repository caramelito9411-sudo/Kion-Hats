from database import get_connection
try:
    conexion = get_connection()
    print("Conexión exitosa")
    conexion.close()
except Exception as e:
    print("Error:")
    print(e)