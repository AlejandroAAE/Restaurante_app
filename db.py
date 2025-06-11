from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import contextmanager
import logging
from escpos.printer import Usb


# Configuración del logging para db.py
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Crear un manejador de archivo para guardar los logs
handler = logging.FileHandler('db.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configuración del pool de conexiones
DATABASE_URL = 'sqlite:///restaurante.db'  # Cambia esto según tu configuración
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Establece en True para ver las consultas SQL en la consola
    pool_size=20,  # Número máximo de conexiones en el pool
    max_overflow=10,  # Número máximo de conexiones adicionales permitidas
    pool_timeout=30,  # Tiempo de espera antes de abandonar la conexión
    pool_recycle=1800  # Reciclar conexiones después de 30 minutos (1800 segundos)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Context manager para manejar sesiones
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Función para inicializar la base de datos
def create_database():
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_usuario TEXT NOT NULL UNIQUE,
                contraseña TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rango TEXT NOT NULL,
                lunes INTEGER DEFAULT 0,
                martes INTEGER DEFAULT 0,
                miercoles INTEGER DEFAULT 0,
                jueves INTEGER DEFAULT 0,
                viernes INTEGER DEFAULT 0,
                sabado INTEGER DEFAULT 0,
                domingo INTEGER DEFAULT 0,
                lunes_inicio TEXT,
                lunes_fin TEXT,
                martes_inicio TEXT,
                martes_fin TEXT,
                miercoles_inicio TEXT,
                miercoles_fin TEXT,
                jueves_inicio TEXT,
                jueves_fin TEXT,
                viernes_inicio TEXT,
                viernes_fin TEXT,
                sabado_inicio TEXT,
                sabado_fin TEXT,
                domingo_inicio TEXT,
                domingo_fin TEXT
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Ingredientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 0,
                precio_unitario REAL NOT NULL,
                valor_minimo INTEGER NOT NULL DEFAULT 0
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Platos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL,
                ingredientes TEXT,
                image_url TEXT,
                categoria TEXT,
                veces_pedido INTEGER
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS PlatosIngredientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plato_id INTEGER NOT NULL,
            ingrediente_id INTEGER NOT NULL,
            cantidad_usada INTEGER NOT NULL,
            FOREIGN KEY (plato_id) REFERENCES Platos (id),
            FOREIGN KEY (ingrediente_id) REFERENCES Ingredientes (id)
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                plato_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                estado TEXT NOT NULL,
                total REAL NOT NULL,
                mesa INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES Usuarios(id),
                FOREIGN KEY (plato_id) REFERENCES Platos(id)
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Configuracion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave TEXT UNIQUE NOT NULL,
                valor TEXT NOT NULL
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS ImagenesLocal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_imagen TEXT NOT NULL
            )
        '''))
        conn.execute(text('''
            INSERT OR IGNORE INTO Configuracion (clave, valor)
            VALUES 
                ('nombre_restaurante', 'Restaurante'),
                ('fondo', '/static/images/default_background.jpg'),
                ('mensaje_bienvenida', 'Bienvenido a Restaurante'),
                ('direccion', 'Calle Ficticia 123'),  
                ('horario', 'Lunes a Domingo: 10:00 - 22:00'), 
                ('telefono', '+34 123 456 789'),
                ('tipografia', 'Arial'),
                ('color_bienvenida', '#000000'),  
                ('color_direccion', '#FF5733'),  
                ('color_horario', '#33FF57'),  
                ('color_telefono', '#3357FF'),
                ('color_boton', '#007bff'), 
                ('logo','/static/images/default_logo.png')    
        '''))

        conn.execute(text('''
         CREATE TABLE IF NOT EXISTS PaginasPersonalizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            precio REAL
            )
        '''))

        conn.execute(text('''
        CREATE TABLE IF NOT EXISTS PlatosVisibilidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pagina_id INTEGER NOT NULL,
            plato_id INTEGER NOT NULL,
            seccion TEXT NOT NULL,  -- Puede ser 'entrantes', 'principales', 'postres', 'bebidas'
            visible INTEGER DEFAULT 1,  -- 1 para visible, 0 para oculto
            FOREIGN KEY (pagina_id) REFERENCES PaginasPersonalizadas(id),
            FOREIGN KEY (plato_id) REFERENCES Platos(id)
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_cliente TEXT NOT NULL,
                email TEXT NOT NULL,
                numero_personas INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                zona TEXT NOT NULL,  -- 'interior' o 'exterior'
                mesa_id INTEGER,
                confirmada INTEGER DEFAULT 0  -- 0: no confirmada, 1: confirmada
            )
        '''))

        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS Mesas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zona TEXT NOT NULL,  -- 'interior' o 'exterior'
                capacidad INTEGER NOT NULL,  -- Número de personas que caben en la mesa
                mesa_id INTEGER,
                disponible INTEGER DEFAULT 1,  -- 1: disponible, 0: no disponible
                zona_habilitada  INTEGER NOT NULL DEFAULT 1  -- 1: Habilitada, 0: cerrada
                
            )
        '''))
        conn.execute(text('''
                  CREATE TABLE IF NOT EXISTS Ticket (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      mesa INTEGER NOT NULL,
                      plato_id INTEGER NOT NULL,
                      plato_nombre TEXT NOT NULL,
                      cantidad INTEGER NOT NULL,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                      FOREIGN KEY (plato_id) REFERENCES Platos(id)
                  )
              '''))

        conn.execute(text('''
                CREATE TABLE IF NOT EXISTS Impresora (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clave TEXT UNIQUE,
                    valor TEXT
                );

        
            '''))

        conn.commit()




# Función para insertar un usuario
def insertar_usuario(nombre_usuario, contraseña, nombre, rango, dias_trabajo):
    hashed_password = generate_password_hash(contraseña)
    dias = {dia: 1 if dia in dias_trabajo else 0 for dia in [
        'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']}

    with get_db() as db:
        # Verificar si el usuario ya existe
        usuario_existente = db.execute(text("""
            SELECT 1 FROM Usuarios WHERE nombre_usuario = :nombre_usuario
        """), {"nombre_usuario": nombre_usuario}).fetchone()

        if usuario_existente:
            print(f"El usuario '{nombre_usuario}' ya existe.")
            return

        # Insertar usuario si no existe
        db.execute(text("""
            INSERT INTO Usuarios (nombre_usuario, contraseña, nombre, rango, lunes, martes, miercoles, jueves, viernes, sabado, domingo)
            VALUES (:nombre_usuario, :contraseña, :nombre, :rango, :lunes, :martes, :miercoles, :jueves, :viernes, :sabado, :domingo)
        """), {
            "nombre_usuario": nombre_usuario,
            "contraseña": hashed_password,
            "nombre": nombre,
            "rango": rango,
            "lunes": dias['lunes'],
            "martes": dias['martes'],
            "miercoles": dias['miercoles'],
            "jueves": dias['jueves'],
            "viernes": dias['viernes'],
            "sabado": dias['sabado'],
            "domingo": dias['domingo']
        })
        db.commit()
        print(f"Usuario '{nombre_usuario}' insertado correctamente.")


# Función para actualizar un usuario
def actualizar_usuario(id, nombre_usuario, contraseña, nombre, rango, dias_trabajo):
    hashed_password = generate_password_hash(contraseña) if contraseña else None
    dias = {dia: 1 if dia in dias_trabajo else 0 for dia in [
        'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']}
    with get_db() as db:
        if hashed_password:
            db.execute(text("""
                UPDATE Usuarios
                SET nombre_usuario = :nombre_usuario, contraseña = :contraseña, nombre = :nombre, rango = :rango,
                    lunes = :lunes, martes = :martes, miercoles = :miercoles, jueves = :jueves, viernes = :viernes, sabado = :sabado, domingo = :domingo
                WHERE id = :id
            """), {
                "id": id,
                "nombre_usuario": nombre_usuario,
                "contraseña": hashed_password,
                "nombre": nombre,
                "rango": rango,
                "lunes": dias['lunes'],
                "martes": dias['martes'],
                "miercoles": dias['miercoles'],
                "jueves": dias['jueves'],
                "viernes": dias['viernes'],
                "sabado": dias['sabado'],
                "domingo": dias['domingo']
            })
        else:
            db.execute(text("""
                UPDATE Usuarios
                SET nombre_usuario = :nombre_usuario, nombre = :nombre, rango = :rango,
                    lunes = :lunes, martes = :martes, miercoles = :miercoles, jueves = :jueves, viernes = :viernes, sabado = :sabado, domingo = :domingo
                WHERE id = :id
            """), {
                "id": id,
                "nombre_usuario": nombre_usuario,
                "nombre": nombre,
                "rango": rango,
                "lunes": dias['lunes'],
                "martes": dias['martes'],
                "miercoles": dias['miercoles'],
                "jueves": dias['jueves'],
                "viernes": dias['viernes'],
                "sabado": dias['sabado'],
                "domingo": dias['domingo']
            })
        db.commit()


# Función para obtener un usuario por nombre
def obtener_usuario_por_nombre(username):
    with get_db() as db:
        result = db.execute(text("SELECT * FROM Usuarios WHERE nombre_usuario = :username"), {"username": username}).fetchone()
        if result:
            return {
                "id": result.id,
                "nombre_usuario": result.nombre_usuario,
                "contraseña": result.contraseña,
                "nombre": result.nombre,
                "rango": result.rango
            }
        return None





def obtener_usuarios():
    with get_db() as db:
        usuarios = db.execute(text("""
            SELECT id, nombre_usuario, contraseña, nombre, rango,
                   lunes, martes, miercoles, jueves, viernes, sabado, domingo,
                   lunes_inicio, lunes_fin, martes_inicio, martes_fin, 
                   miercoles_inicio, miercoles_fin, jueves_inicio, jueves_fin, 
                   viernes_inicio, viernes_fin, sabado_inicio, sabado_fin, 
                   domingo_inicio, domingo_fin
            FROM Usuarios
        """)).fetchall()
        empleados = []
        for usuario in usuarios:
            empleado = {
                'id': usuario[0],
                'nombre_usuario': usuario[1],
                'contraseña': usuario[2],
                'nombre': usuario[3],
                'rango': usuario[4],
                'dias': {
                    'lunes': usuario[5],
                    'martes': usuario[6],
                    'miercoles': usuario[7],
                    'jueves': usuario[8],
                    'viernes': usuario[9],
                    'sabado': usuario[10],
                    'domingo': usuario[11]
                },
                'horas_inicio': {
                    'lunes': usuario[12] or '',
                    'martes': usuario[14] or '',
                    'miercoles': usuario[16] or '',
                    'jueves': usuario[18] or '',
                    'viernes': usuario[20] or '',
                    'sabado': usuario[22] or '',
                    'domingo': usuario[24] or ''
                },
                'horas_fin': {
                    'lunes': usuario[13] or '',
                    'martes': usuario[15] or '',
                    'miercoles': usuario[17] or '',
                    'jueves': usuario[19] or '',
                    'viernes': usuario[21] or '',
                    'sabado': usuario[23] or '',
                    'domingo': usuario[25] or ''
                }
            }
            empleados.append(empleado)
    return empleados





def obtener_usuario_por_id(id):
    with get_db() as db:
        empleado = db.execute(text("SELECT * FROM Usuarios WHERE id = :id"), {"id": id}).fetchone()
        if empleado:
            # Convertir el resultado a un diccionario
            empleado_dict = {
                'id': empleado.id,
                'nombre_usuario': empleado.nombre_usuario,
                'nombre': empleado.nombre,
                'rango': empleado.rango,
                'lunes': empleado.lunes,
                'martes': empleado.martes,
                'miercoles': empleado.miercoles,
                'jueves': empleado.jueves,
                'viernes': empleado.viernes,
                'sabado': empleado.sabado,
                'domingo': empleado.domingo,
                'lunes_inicio': empleado.lunes_inicio,
                'lunes_fin': empleado.lunes_fin,
                'martes_inicio': empleado.martes_inicio,
                'martes_fin': empleado.martes_fin,
                'miercoles_inicio': empleado.miercoles_inicio,
                'miercoles_fin': empleado.miercoles_fin,
                'jueves_inicio': empleado.jueves_inicio,
                'jueves_fin': empleado.jueves_fin,
                'viernes_inicio': empleado.viernes_inicio,
                'viernes_fin': empleado.viernes_fin,
                'sabado_inicio': empleado.sabado_inicio,
                'sabado_fin': empleado.sabado_fin,
                'domingo_inicio': empleado.domingo_inicio,
                'domingo_fin': empleado.domingo_fin
            }

            empleado_dict['dias'] = {
                'lunes': empleado_dict.get('lunes', False),
                'martes': empleado_dict.get('martes', False),
                'miercoles': empleado_dict.get('miercoles', False),
                'jueves': empleado_dict.get('jueves', False),
                'viernes': empleado_dict.get('viernes', False),
                'sabado': empleado_dict.get('sabado', False),
                'domingo': empleado_dict.get('domingo', False)
            }
            empleado_dict['horas_inicio'] = {
                'lunes': empleado_dict.get('lunes_inicio', ''),
                'martes': empleado_dict.get('martes_inicio', ''),
                'miercoles': empleado_dict.get('miercoles_inicio', ''),
                'jueves': empleado_dict.get('jueves_inicio', ''),
                'viernes': empleado_dict.get('viernes_inicio', ''),
                'sabado': empleado_dict.get('sabado_inicio', ''),
                'domingo': empleado_dict.get('domingo_inicio', '')
            }
            empleado_dict['horas_fin'] = {
                'lunes': empleado_dict.get('lunes_fin', ''),
                'martes': empleado_dict.get('martes_fin', ''),
                'miercoles': empleado_dict.get('miercoles_fin', ''),
                'jueves': empleado_dict.get('jueves_fin', ''),
                'viernes': empleado_dict.get('viernes_fin', ''),
                'sabado': empleado_dict.get('sabado_fin', ''),
                'domingo': empleado_dict.get('domingo_fin', '')
            }
            return empleado_dict
        else:
            return None

#Alimentacion:
def insertar_ingrediente(nombre, cantidad=0, precio_unitario=0, valor_minimo=0):
    with get_db() as db:
        try:
            resultado = db.execute(text("SELECT id FROM Ingredientes WHERE nombre = :nombre"), {"nombre": nombre}).fetchone()
            if resultado:
                print(f"El ingrediente '{nombre}' ya existe en la base de datos.")
                return False
            db.execute(text("""
                INSERT INTO Ingredientes (nombre, cantidad, precio_unitario, valor_minimo)
                VALUES (:nombre, :cantidad, :precio_unitario, :valor_minimo)
            """), {
                "nombre": nombre,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "valor_minimo": valor_minimo
            })
            db.commit()
            print(f"Ingrediente '{nombre}' insertado con éxito.")
            return True
        except Exception as e:
            print(f"Error al insertar ingrediente: {e}")
            db.rollback()
            return False

def obtener_ingredientes():
    with get_db() as db:
        result = db.execute(text("SELECT * FROM Ingredientes"))
        ingredientes = []
        for ingrediente in result.fetchall():
            ingrediente_dict = {
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "cantidad": ingrediente.cantidad,
                "precio_unitario": ingrediente.precio_unitario,
                "valor_minimo": ingrediente.valor_minimo
            }
            ingredientes.append(ingrediente_dict)
        return ingredientes


def obtener_ingrediente_por_id(id):
    with get_db() as db:
        ingrediente = db.execute(text("SELECT * FROM Ingredientes WHERE id = :id"), {"id": id}).fetchone()
        if ingrediente:
            return {
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "cantidad": ingrediente.cantidad,
                "precio_unitario": ingrediente.precio_unitario,
                "valor_minimo": ingrediente.valor_minimo
            }
        return None



def actualizar_ingrediente(id, nombre, cantidad, precio_unitario, valor_minimo):
    with get_db() as db:
        db.execute(text("""
            UPDATE Ingredientes
            SET nombre = :nombre, cantidad = :cantidad, 
                precio_unitario = :precio_unitario, valor_minimo = :valor_minimo
            WHERE id = :id
        """), {
            "nombre": nombre,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "valor_minimo": valor_minimo,
            "id": id
        })
        db.commit()



def actualizar_cantidad_ingrediente(id, cantidad):
    with get_db() as db:
        try:
            db.execute(text("""
                UPDATE Ingredientes 
                SET cantidad = cantidad + :cantidad 
                WHERE id = :id
            """), {"cantidad": cantidad, "id": id})
            db.commit()
            print(f"Ingrediente con ID {id} actualizado correctamente.")
        except Exception as e:
            print(f"Error al actualizar cantidad del ingrediente: {e}")


def eliminar_ingrediente(id):
    with get_db() as db:
        try:
            db.execute(text("DELETE FROM Ingredientes WHERE id = :id"), {"id": id})
            db.commit()
            print(f"Ingrediente con ID {id} eliminado correctamente.")
        except Exception as e:
            print(f"Error al eliminar ingrediente: {e}")
#Platos del Menu
def insertar_plato(nombre, descripcion, precio, ingredientes, image_url):
    with get_db() as db:
        # Insertar el plato en la tabla Platos
        db.execute(text('''
            INSERT INTO Platos (nombre, descripcion, precio, image_url)
            VALUES (:nombre, :descripcion, :precio, :image_url)
        '''), {
            "nombre": nombre,
            "descripcion": descripcion,
            "precio": precio,
            "image_url": image_url
        })

        # Obtener el id del plato recién insertado
        plato_id = db.execute(text("SELECT last_insert_rowid()")).fetchone()[0]

        # Insertar los ingredientes en la tabla Platos_Ingredientes
        for ingrediente_id, cantidad in ingredientes.items():
            db.execute(text('''
                INSERT INTO Platos_Ingredientes (plato_id, ingrediente_id, cantidad)
                VALUES (:plato_id, :ingrediente_id, :cantidad)
            '''), {
                "plato_id": plato_id,
                "ingrediente_id": ingrediente_id,
                "cantidad": cantidad
            })

        db.commit()

def obtener_menus():
    with get_db() as db:
        # Obtener todos los menús
        menus = db.execute(text('''
            SELECT id, titulo, precio
            FROM PaginasPersonalizadas
        ''')).mappings().fetchall()  # Usar .mappings() para obtener diccionarios

        # Para cada menú, obtener sus componentes
        menus_completos = []
        for menu in menus:
            entrantes = db.execute(text('''
                SELECT p.id, p.nombre
                FROM PlatosVisibilidad pv
                JOIN Platos p ON pv.plato_id = p.id
                WHERE pv.pagina_id = :pagina_id AND pv.seccion = 'entrantes'
            '''), {'pagina_id': menu['id']}).mappings().fetchall()
            print(f"SQL Entrantes: {entrantes}")

            principales = db.execute(text('''
                SELECT p.id, p.nombre
                FROM PlatosVisibilidad pv
                JOIN Platos p ON pv.plato_id = p.id
                WHERE pv.pagina_id = :pagina_id AND pv.seccion = 'principales'
            '''), {'pagina_id': menu['id']}).mappings().fetchall()
            print(f"SQL Principales: {principales}")

            postres = db.execute(text('''
                SELECT p.id, p.nombre
                FROM PlatosVisibilidad pv
                JOIN Platos p ON pv.plato_id = p.id
                WHERE pv.pagina_id = :pagina_id AND pv.seccion = 'postres'
            '''), {'pagina_id': menu['id']}).mappings().fetchall()
            print(f"SQL Postres: {postres}")

            bebidas = db.execute(text('''
                SELECT p.id, p.nombre
                FROM PlatosVisibilidad pv
                JOIN Platos p ON pv.plato_id = p.id
                WHERE pv.pagina_id = :pagina_id AND pv.seccion = 'bebidas'
            '''), {'pagina_id': menu['id']}).mappings().fetchall()
            print(f"SQL Bebidas: {bebidas}")

            menus_completos.append({
                'id': menu['id'],
                'titulo': menu['titulo'],
                'precio': menu['precio'],
                'entrantes': entrantes,
                'principales': principales,
                'postres': postres,
                'bebidas': bebidas
            })
        print(f"SQL Principales: {principales}, Menú ID: {menu['id']}")

        return menus_completos


def obtener_platos():
    with get_db() as db:
        query = text('''
            SELECT Platos.id, Platos.nombre, Platos.descripcion, Platos.precio, Platos.categoria, 
                   Platos.image_url,  -- Agregamos la columna de la imagen
                   GROUP_CONCAT(Ingredientes.nombre, ', ') AS ingredientes
            FROM Platos
            LEFT JOIN PlatosIngredientes ON Platos.id = PlatosIngredientes.plato_id
            LEFT JOIN Ingredientes ON PlatosIngredientes.ingrediente_id = Ingredientes.id
            GROUP BY Platos.id
        ''')
        platos = db.execute(query).fetchall()
        return platos


def actualizar_plato(id, nombre, descripcion, precio, categoria, ingredientes, image_url):
    with get_db() as db:

        db.execute(text('''
            UPDATE Platos 
            SET nombre = :nombre, descripcion = :descripcion, precio = :precio, categoria = :categoria, image_url = :image_url 
            WHERE id = :id
        '''), {
            "nombre": nombre,
            "descripcion": descripcion,
            "precio": precio,
            "categoria": categoria,
            "image_url": image_url,
            "id": id
        })

        # Eliminar ingredientes antiguos
        db.execute(text("DELETE FROM PlatosIngredientes WHERE plato_id = :id"), {"id": id})

        # Insertar nuevos ingredientes
        for ingrediente_id, cantidad in ingredientes.items():
            db.execute(text('''
                INSERT INTO PlatosIngredientes (plato_id, ingrediente_id, cantidad_usada)
                VALUES (:plato_id, :ingrediente_id, :cantidad)
            '''), {
                "plato_id": id,
                "ingrediente_id": ingrediente_id,
                "cantidad": cantidad
            })

        db.commit()




def eliminar_plato(id):
    with get_db() as db:
        db.execute(text("DELETE FROM Platos WHERE id = :id"), {"id": id})
        db.commit()

def obtener_plato_por_id(plato_id):
    with get_db() as db:
        plato = db.execute(text('''
            SELECT id, nombre, descripcion, precio, categoria, image_url
            FROM Platos
            WHERE id = :plato_id
        '''), {'plato_id': plato_id}).fetchone()
        if plato:
            return {
                "id": plato.id,
                "nombre": plato.nombre,
                "descripcion": plato.descripcion,
                "precio": plato.precio,
                "categoria": plato.categoria,
                "image_url": plato.image_url
            }
        return None

def obtener_nombre_plato(plato_id):
    with get_db() as db:
        plato = db.execute(text('SELECT nombre FROM Platos WHERE id = :id'), {'id': plato_id}).fetchone()
        return plato[0] if plato else "Plato no encontrado"

def obtener_precio_plato(plato_id):
    with get_db() as db:
        plato = db.execute(text('SELECT precio FROM Platos WHERE id = :id'), {'id': plato_id}).fetchone()
        return plato[0] if plato else 0.0

def obtener_ingredientes_por_plato(plato_id):
    with get_db() as db:
        # Obtener los ingredientes asociados al plato
        ingredientes = db.execute(text('''
            SELECT ingrediente_id, cantidad_usada
            FROM PlatosIngredientes
            WHERE plato_id = :plato_id
        '''), {'plato_id': plato_id}).fetchall()

        # Convertir la lista de tuplas en un diccionario
        ingredientes_actuales = {ingrediente_id: cantidad for ingrediente_id, cantidad in ingredientes}
        return ingredientes_actuales

def obtener_platos_por_categoria(categoria):
    with get_db() as db:
        platos = db.execute(text('''
            SELECT id, nombre, descripcion, precio, image_url
            FROM Platos
            WHERE categoria = :categoria
        '''), {'categoria': categoria}).fetchall()
        return platos

#Pedidos
def actualizar_estado_pedido(id, nuevo_estado):
    with get_db() as db:
        db.execute(text('''
            UPDATE Pedidos SET estado = :nuevo_estado WHERE id = :id
        '''), {"nuevo_estado": nuevo_estado, "id": id})
        db.commit()

def obtener_pedidos_mesa(mesa):
    with get_db() as db:
        cursor = db.execute(text('''
            SELECT p.id, u.nombre_usuario, pl.nombre, p.cantidad, p.estado, p.mesa, p.timestamp
            FROM Pedidos p
            JOIN Usuarios u ON p.usuario_id = u.id
            JOIN Platos pl ON p.plato_id = pl.id
            WHERE p.mesa = :mesa
            ORDER BY p.timestamp ASC
        '''), {"mesa": mesa})
        pedidos = cursor.fetchall()
    return pedidos


#Fondo
def obtener_fondo_actual():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'fondo'")).fetchone()
        return resultado[0] if resultado else '/static/images/default_background.jpg'

def actualizar_fondo(nuevo_fondo):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'fondo'"), {"valor": nuevo_fondo})
        db.commit()

# Imágenes
def insertar_imagen_local(url_imagen):
    with get_db() as db:
        db.execute(text("INSERT INTO ImagenesLocal (url_imagen) VALUES (:url_imagen)"), {"url_imagen": url_imagen})
        db.commit()

def obtener_imagenes_local():
    with get_db() as db:
        imagenes = db.execute(text("SELECT id, url_imagen FROM ImagenesLocal ORDER BY id ASC")).fetchall()
        return [{'id': imagen[0], 'url_imagen': imagen[1]} for imagen in imagenes]

def eliminar_imagen_de_db(id):
    with get_db() as db:
        try:
            # Verificar si la imagen existe
            resultado = db.execute(text("SELECT * FROM ImagenesLocal WHERE id = :id"), {"id": id}).fetchone()
            if resultado:
                db.execute(text("DELETE FROM ImagenesLocal WHERE id = :id"), {"id": id})
                db.commit()
                print(f"Imagen con ID {id} eliminada correctamente.")
            else:
                print(f"Imagen con ID {id} no encontrada en la base de datos.")
        except Exception as e:
            print(f"Error al eliminar imagen: {e}")

#nombre restaurante
def obtener_nombre_restaurante():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'nombre_restaurante'")).fetchone()
        return resultado[0] if resultado else "Restaurante"

def actualizar_nombre_restaurante(nuevo_nombre):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'nombre_restaurante'"), {"valor": nuevo_nombre})
        db.commit()

#mensaje de Bienvenida
def obtener_mensaje_bienvenida():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'mensaje_bienvenida'")).fetchone()
        return resultado[0] if resultado else "Bienvenido a Restaurante"

def actualizar_mensaje_bienvenida(nuevo_mensaje):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'mensaje_bienvenida'"), {"valor": nuevo_mensaje})
        db.commit()


#Configuración
def obtener_direccion():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'direccion'")).fetchone()
        return resultado[0] if resultado else "Dirección no disponible"

def obtener_horario():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'horario'")).fetchone()
        return resultado[0] if resultado else "Horario no disponible"

def obtener_telefono():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'telefono'")).fetchone()
        return resultado[0] if resultado else "Teléfono no disponible"

def actualizar_direccion(nueva_direccion):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'direccion'"), {"valor": nueva_direccion})
        db.commit()

def actualizar_horario(nuevo_horario):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'horario'"), {"valor": nuevo_horario})
        db.commit()

def actualizar_telefono(nuevo_telefono):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'telefono'"), {"valor": nuevo_telefono})
        db.commit()


#Tipografía
def obtener_tipografia():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'tipografia'")).fetchone()
        return resultado[0] if resultado else "Arial"

def actualizar_tipografia(nueva_tipografia):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'tipografia'"), {"valor": nueva_tipografia})
        db.commit()


#Colores
def obtener_color_bienvenida():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'color_bienvenida'")).fetchone()
        return resultado[0] if resultado else "#000000"  # Negro por defecto

def obtener_color_direccion():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'color_direccion'")).fetchone()
        return resultado[0] if resultado else "#FF5733"  # Rojo claro por defecto

def obtener_color_horario():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'color_horario'")).fetchone()
        return resultado[0] if resultado else "#33FF57"  # Verde claro por defecto

def obtener_color_telefono():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'color_telefono'")).fetchone()
        return resultado[0] if resultado else "#3357FF"  # Azul claro por defecto

def actualizar_color_bienvenida(nuevo_color):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'color_bienvenida'"), {"valor": nuevo_color})
        db.commit()

def actualizar_color_direccion(nuevo_color):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'color_direccion'"), {"valor": nuevo_color})
        db.commit()

def actualizar_color_horario(nuevo_color):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'color_horario'"), {"valor": nuevo_color})
        db.commit()

def actualizar_color_telefono(nuevo_color):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'color_telefono'"), {"valor": nuevo_color})
        db.commit()


#Color boton
def obtener_color_boton():
    with get_db() as db:
        resultado = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'color_boton'")).fetchone()
        return resultado[0] if resultado else "#007bff"  # Azul Bootstrap por defecto

def actualizar_color_boton(nuevo_color):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :valor WHERE clave = 'color_boton'"), {"valor": nuevo_color})
        db.commit()
#Logo

def obtener_logo():
    with get_db() as db:
        result = db.execute(text("SELECT valor FROM Configuracion WHERE clave = 'logo'")).fetchone()
        if result:
            return result[0]
    return None


def actualizar_logo(nueva_logo):
    with get_db() as db:
        db.execute(text("UPDATE Configuracion SET valor = :nueva_logo WHERE clave = 'logo'"), {"nueva_logo": nueva_logo})
        db.commit()



#Alerta de bajos ingredientes
def obtener_ingredientes_bajos():
    with get_db() as db:
        return db.execute(text("SELECT nombre, cantidad, valor_minimo FROM Ingredientes WHERE cantidad < valor_minimo"))

#Reservas
def insertar_reserva(nombre_cliente, email, numero_personas, fecha, hora, zona, mesa_id):
    try:
        with get_db() as db:
            logger.debug(f"Intentando insertar reserva: {nombre_cliente}, {email}, {numero_personas}, {fecha}, {hora}, {zona}, {mesa_id}")
            db.execute(text('''
                INSERT INTO Reservas (nombre_cliente, email, numero_personas, fecha, hora, zona, mesa_id)
                VALUES (:nombre_cliente, :email, :numero_personas, :fecha, :hora, :zona, :mesa_id)
            '''), {
                "nombre_cliente": nombre_cliente,
                "email": email,
                "numero_personas": numero_personas,
                "fecha": fecha,
                "hora": hora,
                "zona": zona,
                "mesa_id": mesa_id
            })
            db.commit()
            logger.info("Reserva insertada correctamente.")
    except Exception as e:
        logger.error(f"Error al insertar reserva: {e}")
        raise

def obtener_reservas():
    with get_db() as db:
        reservas = db.execute(text("SELECT * FROM Reservas")).fetchall()
        return [dict(reserva) for reserva in reservas]

def confirmar_reserva_db(reserva_id):
    try:
        with get_db() as db:
            db.execute(text('''
                UPDATE Reservas 
                SET confirmada = 1 
                WHERE id = :reserva_id
            '''), {"reserva_id": reserva_id})
            db.commit()
            print(f"Reserva {reserva_id} confirmada correctamente")  # Log para depuración
    except Exception as e:
        print(f"Error al confirmar la reserva {reserva_id}: {e}")  # Log para depuración
        raise

def insertar_mesa(zona, capacidad):
    with get_db() as db:
        db.execute(text('''
            INSERT INTO Mesas (zona, capacidad, disponible, zona_habilitada)
            VALUES (:zona, :capacidad, 1, 1)
        '''), {
            "zona": zona,
            "capacidad": capacidad
        })
        db.commit()


def obtener_mesas_disponibles(zona, fecha, hora, numero_personas):
    try:
        with get_db() as db:
            mesas = db.execute(text('''
                SELECT * FROM Mesas 
                WHERE zona = :zona 
                AND disponible = 1 
                AND zona_habilitada = 1
                AND capacidad >= :numero_personas
                AND id NOT IN (
                    SELECT mesa_id FROM Reservas 
                    WHERE fecha = :fecha AND hora = :hora
                )
            '''), {
                "zona": zona,
                "fecha": fecha,
                "hora": hora,
                "numero_personas": numero_personas
            }).fetchall()

            # Convertir cada fila a un diccionario
            return [dict(mesa._asdict()) for mesa in mesas]
    except Exception as e:
        logger.error(f"Error al obtener mesas disponibles: {e}")
        raise

def actualizar_disponibilidad_mesa(mesa_id, disponible):
    with get_db() as db:
        db.execute(text("UPDATE Mesas SET disponible = :disponible WHERE id = :id"), {
            "disponible": disponible,
            "id": mesa_id
        })
        db.commit()

#Mesas REservas
def obtener_mesas():
    with get_db() as db:
        mesas = db.execute(text('SELECT * FROM Mesas')).fetchall()
        # Convertir cada fila a un diccionario
        return [dict(mesa._asdict()) for mesa in mesas]

#Impresora Térmica
def actualizar_impresora(clave: str, valor: str):
    #Actualiza o inserta el valor de la impresora en la base de datos.
    with get_db() as db:
        db.execute(text('''
        INSERT INTO impresora (clave, valor) 
        VALUES (:clave, :valor) 
        ON CONFLICT(clave) DO UPDATE SET valor = :valor
        '''), {"clave": clave, "valor": valor})
    db.commit()

def obtener_impresora( clave: str):
    #Obtiene el valor de una configuración de la impresora.
    with get_db() as db:
        result = db.execute(text('SELECT valor FROM impresora WHERE clave = :clave'), {"clave": clave}).fetchone()
        return result[0] if result else None



def obtener_valores_impresora():
    vendor_id = int(obtener_impresora('usb_vendor_id') or "0x0000", 16)
    product_id = int(obtener_impresora('usb_product_id') or "0x0000", 16)
    return vendor_id, product_id

class ImpresoraSimulada:
    def __init__(self):
        pass

    def text(self, texto):
        print(f"[Impresora Simulada] Texto: {texto}")

    def cut(self):
        print("[Impresora Simulada] Papel cortado.")

    def close(self):
        print("[Impresora Simulada] Impresora cerrada.")

def imprimir_ticket(mesa, pedidos, total):
    try:
        vendor_id, product_id = obtener_valores_impresora()
        print(f"Vendor ID: {vendor_id}, Product ID: {product_id}")  # Debug

        # Intentar usar la impresora real
        try:
            p = Usb(vendor_id, product_id)  # Usa los valores configurados
        except ImportError:
            print("Advertencia: No se encontró el módulo 'escpos'. Usando impresora simulada.")
            p = ImpresoraSimulada()
        except Exception as e:
            print(f"Advertencia: No se pudo conectar a la impresora. Usando impresora simulada. Error: {e}")
            p = ImpresoraSimulada()

        p.text(f"Ticket de la Mesa {mesa}\n")
        p.text("-----------------------------\n")
        for pedido in pedidos:
            p.text(f"{pedido['nombre']}  -  €{pedido['precio']:.2f}\n")
        p.text("-----------------------------\n")
        p.text(f"Total: €{total:.2f}\n")
        p.cut()  # Corta el papel
    except Exception as e:
        print(f"Error al imprimir el ticket: {e}")
        print("Error al imprimir el ticket. Verifica la conexión de la impresora.", 'danger')


if __name__ == "__main__":
    create_database()
    insertar_usuario(
        nombre_usuario="admin",
        contraseña="123",  # Contraseña del administrador
        nombre="Administrador",
        rango="jefe",
        dias_trabajo=['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    )

