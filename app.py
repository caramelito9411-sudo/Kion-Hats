from flask import Flask, render_template, session, redirect, url_for, request
from database import get_connection
from collections import Counter
from pymysql.err import IntegrityError
app = Flask(__name__)
app.secret_key = "kion_hats_2026"
@app.route("/")
def inicio():
    return render_template("index.html")
@app.route("/catalogo")
def catalogo():
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT
            id_producto,
            modelo,
            precio,
            imagen,
            stock
        FROM productos
        WHERE activo = 1
        ORDER BY id_producto DESC
    """)
    productos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("catalogo.html", productos=productos)
@app.route("/producto/<int:id_producto>")
def producto(id_producto):
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT
            p.*,
            m.nombre AS marca
        FROM productos p
        INNER JOIN marcas m
            ON p.id_marca = m.id_marca
        WHERE p.id_producto = %s
    """, (id_producto,))
    producto = cursor.fetchone()
    cursor.close()
    conexion.close()
    if producto is None:
        return "Producto no encontrado", 404
    return render_template("producto.html", producto=producto)
@app.route("/agregar_carrito/<int:id_producto>")
def agregar_carrito(id_producto):
    if "carrito" not in session or not isinstance(session["carrito"], list):
        session["carrito"] = []
    carrito = session["carrito"]
    carrito.append(id_producto)
    session["carrito"] = carrito
    return redirect(url_for("carrito"))
@app.route("/carrito")
def carrito():
    if "carrito" not in session:
        session["carrito"] = []
    ids = session["carrito"]
    productos = []
    total = 0
    if ids:
        cantidades = Counter(ids)
        conexion = get_connection()
        cursor = conexion.cursor()
        placeholders = ",".join(["%s"] * len(cantidades))
        consulta = f"""
            SELECT
                p.*,
                m.nombre AS marca
            FROM productos p
            INNER JOIN marcas m
                ON p.id_marca = m.id_marca
            WHERE p.id_producto IN ({placeholders})
        """
        cursor.execute(consulta, list(cantidades.keys()))
        resultados = cursor.fetchall()
        cursor.close()
        conexion.close()
        for producto in resultados:
            cantidad = cantidades[producto["id_producto"]]
            producto["cantidad"] = cantidad
            producto["subtotal"] = float(producto["precio"]) * cantidad
            total += producto["subtotal"]
            productos.append(producto)
    return render_template(
        "carrito.html",
        productos=productos,
        total=total
    )
@app.route("/eliminar_carrito/<int:id_producto>")
def eliminar_carrito(id_producto):
    if "carrito" in session:
        carrito = session["carrito"]
        if id_producto in carrito:
            carrito.remove(id_producto)
        session["carrito"] = carrito
    return redirect(url_for("carrito"))
@app.route("/aumentar_cantidad/<int:id_producto>")
def aumentar_cantidad(id_producto):
    if "carrito" in session:
        carrito = session["carrito"]
        carrito.append(id_producto)
        session["carrito"] = carrito
    return redirect(url_for("carrito"))
@app.route("/disminuir_cantidad/<int:id_producto>")
def disminuir_cantidad(id_producto):
    if "carrito" in session:
        carrito = session["carrito"]
        if id_producto in carrito:
            carrito.remove(id_producto)
        session["carrito"] = carrito
    return redirect(url_for("carrito"))
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["password"]
        conexion = get_connection()
        cursor = conexion.cursor()
        sql = """
        SELECT * FROM usuarios
        WHERE correo = %s AND password = %s
        """
        cursor.execute(sql, (correo, password))
        usuario = cursor.fetchone()
        cursor.close()
        conexion.close()
        if usuario:
            session["id_usuario"] = usuario["id_usuario"]
            session["nombre_usuario"] = usuario["nombre"]
            session["rol"] = usuario["rol"]
            return redirect(url_for("inicio"))
        return render_template(
            "login.html",
            error="Correo o contraseña incorrectos."
        )
    return render_template("login.html")
    return render_template("login.html")
from pymysql.err import IntegrityError
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        conexion = get_connection()
        cursor = conexion.cursor()
        try:
            nombre = request.form["nombre"]
            apellido = request.form["apellido"]
            correo = request.form["correo"]
            password = request.form["password"]
            telefono = request.form["telefono"]
            direccion = request.form["direccion"]
            sql = """
            INSERT INTO usuarios
            (nombre, apellido, correo, password, telefono, direccion)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                nombre,
                apellido,
                correo,
                password,
                telefono,
                direccion
            ))
            conexion.commit()
            return redirect(url_for("login"))
        except IntegrityError:
            conexion.rollback()
            return render_template(
                "registro.html",
                error="Ese correo ya está registrado."
            )
        except Exception as e:
            conexion.rollback()
            return f"Error: {e}"
        finally:
            cursor.close()
            conexion.close()
    return render_template("registro.html")
@app.route("/finalizar_compra")
def finalizar_compra():
    if "id_usuario" not in session:
        return redirect(url_for("login"))
    if "carrito" not in session or len(session["carrito"]) == 0:
        return redirect(url_for("carrito"))
    ids = session["carrito"]
    cantidades = Counter(ids)
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        placeholders = ",".join(["%s"] * len(cantidades))
        consulta = f"""
        SELECT id_producto, precio
        FROM productos
        WHERE id_producto IN ({placeholders})
        """
        cursor.execute(consulta, list(cantidades.keys()))
        productos = cursor.fetchall()
        total = 0
        for producto in productos:
            total += float(producto["precio"]) * cantidades[producto["id_producto"]]
        sql = """
        INSERT INTO pedidos
        (id_usuario, fecha, total, estado)
        VALUES (%s, NOW(), %s, %s)
        """
        cursor.execute(sql, (
            session["id_usuario"],
            total,
            "Pendiente"
        ))
        id_pedido = cursor.lastrowid
        for producto in productos:
            cantidad = cantidades[producto["id_producto"]]
            precio = float(producto["precio"])
            subtotal = precio * cantidad
            sql = """
            INSERT INTO detalle_pedido
            (id_pedido, id_producto, cantidad, precio, subtotal)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                id_pedido,
                producto["id_producto"],
                cantidad,
                precio,
                subtotal
            ))
        conexion.commit()
        return redirect(url_for("mis_pedidos"))
    except Exception as e:
        conexion.rollback()
        return f"Error: {e}"
    finally:
        cursor.close()
        conexion.close()
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("inicio"))
@app.route("/mis_pedidos")
def mis_pedidos():
    if "id_usuario" not in session:
        return redirect(url_for("login"))
    conexion = get_connection()
    cursor = conexion.cursor()
    sql = """
    SELECT *
    FROM pedidos
    WHERE id_usuario = %s
    ORDER BY fecha DESC
    """
    cursor.execute(sql, (session["id_usuario"],))
    pedidos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("mis_pedidos.html", pedidos=pedidos)
@app.route("/admin")
def admin():
    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))
    conexion = get_connection()
    cursor = conexion.cursor()
    sql = """
    SELECT
        p.id_producto,
        p.modelo,
        p.descripcion,
        p.precio,
        p.stock,
        p.imagen,
        m.nombre AS marca
    FROM productos p
    INNER JOIN marcas m
        ON p.id_marca = m.id_marca
    ORDER BY p.id_producto
    """
    cursor.execute(sql)
    productos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("admin/admin.html", productos=productos)
@app.route("/agregar_producto", methods=["GET", "POST"])
def agregar_producto():
    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))
    conexion = get_connection()
    cursor = conexion.cursor()
    if request.method == "POST":
        modelo = request.form["modelo"]
        descripcion = request.form["descripcion"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        imagen = request.form["imagen"]
        id_marca = request.form["id_marca"]
        sql = """
        INSERT INTO productos
        (id_marca, modelo, descripcion, precio, stock, imagen, disponible, fecha_registro, activo)
        VALUES
        (%s,%s,%s,%s,%s,%s,1,NOW(),1)
        """
        cursor.execute(sql, (
            id_marca,
            modelo,
            descripcion,
            precio,
            stock,
            imagen
        ))
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("admin"))
    cursor.execute("SELECT * FROM marcas")
    marcas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("admin/agregar_producto.html", marcas=marcas)
@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
def editar_producto(id):
    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))
    conexion = get_connection()
    cursor = conexion.cursor()
    if request.method == "POST":
        modelo = request.form["modelo"]
        descripcion = request.form["descripcion"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        imagen = request.form["imagen"]
        id_marca = request.form["id_marca"]
        sql = """
        UPDATE productos
        SET
            id_marca=%s,
            modelo=%s,
            descripcion=%s,
            precio=%s,
            stock=%s,
            imagen=%s
        WHERE id_producto=%s
        """
        cursor.execute(sql, (
            id_marca,
            modelo,
            descripcion,
            precio,
            stock,
            imagen,
            id
        ))
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("admin"))
    cursor.execute("SELECT * FROM productos WHERE id_producto=%s", (id,))
    producto = cursor.fetchone()
    cursor.execute("SELECT * FROM marcas")
    marcas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template(
        "admin/editar_producto.html",
        producto=producto,
        marcas=marcas
    )
@app.route("/eliminar_producto/<int:id>")
def eliminar_producto(id):
    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute(
        "DELETE FROM productos WHERE id_producto=%s",
        (id,)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for("admin"))
if __name__ == "__main__":
    app.run(debug=True)