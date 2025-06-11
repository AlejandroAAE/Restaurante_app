from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler
import os
from db import *
from sqlalchemy.sql import text
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText





app = Flask(__name__, static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.jinja_env.globals.update(obtener_plato_por_id=obtener_plato_por_id)



# Configuración del logging
logging.basicConfig(level=logging.DEBUG)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)



logging.basicConfig(level=logging.DEBUG)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('File uploaded successfully', 'success')
        return redirect(url_for('home'))
    else:
        flash('File type not allowed', 'danger')
        return redirect(request.url)


# Inicializar la base de datos
create_database()


#Login:
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        usuario = obtener_usuario_por_nombre(username)
        print(f"Usuario obtenido: {usuario}")  # Para verificar que el usuario se está obteniendo correctamente
        if usuario:
            print(f"Contraseña ingresada: {password}")
            print(f"Contraseña almacenada (hash): {usuario['contraseña']}")
            if check_password_hash(usuario['contraseña'], password):
                session['username'] = username
                session['user_id'] = usuario['id']
                session['rango'] = usuario['rango']  # Guardar el rango en la sesión
                flash('¡Inicio de sesión exitoso!', 'success')

                if usuario['rango'] == 'jefe':
                    return redirect(url_for('admin_interface'))
                else:
                    return redirect(url_for('user_page', user_id=usuario['id']))
            else:
                print("Falló la verificación de la contraseña")
                flash('Usuario o contraseña incorrectos', 'danger')
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('rango', None)
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('home'))


# Configuración del correo electrónico, sustituir por un email original
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'Prueba@gmail.com'
EMAIL_PASSWORD = 'AAA2'

def enviar_correo(destinatario, asunto, mensaje):
    msg = MIMEText(mensaje)
    msg['Subject'] = asunto
    msg['From'] = EMAIL_USER
    msg['To'] = destinatario

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, [destinatario], msg.as_string())

@app.route('/admin_interface')
def admin_interface():
    if 'username' in session and session['rango'] == 'jefe':
        empleados = obtener_usuarios()
        ingredientes = obtener_ingredientes()
        ingredientes_bajos = obtener_ingredientes_bajos()

        # Obtener configuraciones desde la base de datos
        restaurant_name = obtener_nombre_restaurante()
        background_url = obtener_fondo_actual()
        welcome_message = obtener_mensaje_bienvenida()
        direccion = obtener_direccion()
        horario = obtener_horario()
        telefono = obtener_telefono()

        # Obtener la lista de páginas personalizadas
        with get_db() as db:
            paginas = db.execute(text('SELECT * FROM PaginasPersonalizadas')).fetchall()

        return render_template(
            'admin_interface.html',
            empleados=empleados,
            ingredientes=ingredientes,
            ingredientes_bajos=ingredientes_bajos,
            restaurant_name=restaurant_name,
            background_url=background_url,
            welcome_message=welcome_message,
            direccion=direccion,
            horario=horario,
            telefono=telefono,
            paginas=paginas  # Pasar la lista de páginas personalizadas
        )
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

@app.route('/')
def home():
    platos = obtener_platos()
    print(f"Archivos estáticos solicitados: {request.args}")  # Log para depuración

    # Obtener configuraciones desde la base de datos con valores por defecto
    restaurant_name = obtener_nombre_restaurante()
    background_url = obtener_fondo_actual()
    welcome_message = obtener_mensaje_bienvenida()
    direccion = obtener_direccion()
    horario = obtener_horario()
    telefono = obtener_telefono()
    logo_url = obtener_logo()
    imagenes_local = obtener_imagenes_local()

    with get_db() as db:
        # Obtener las páginas de menús creadas
        paginas = db.execute(text("SELECT id, titulo FROM PaginasPersonalizadas")).fetchall()

    return render_template(
        'home.html',
        platos=platos,
        restaurant_name=restaurant_name,
        background_url=background_url,
        welcome_message=welcome_message,
        direccion=direccion,
        horario=horario,
        telefono=telefono,
        logo_url=logo_url,
        imagenes_local=imagenes_local,
        paginas=paginas
    )


@app.route('/add_user', methods=['POST'])
def add_user():
    if 'username' in session and (session['username'] == 'admin' or session['rango'] == 'jefe'):
        nombre_usuario = request.form['nombre_usuario']
        contraseña = generate_password_hash(request.form['contraseña'])
        nombre = request.form['nombre']
        rango = request.form['rango']
        dias = {
            'lunes': bool(request.form.get('lunes')),
            'martes': bool(request.form.get('martes')),
            'miercoles': bool(request.form.get('miercoles')),
            'jueves': bool(request.form.get('jueves')),
            'viernes': bool(request.form.get('viernes')),
            'sabado': bool(request.form.get('sabado')),
            'domingo': bool(request.form.get('domingo'))
        }

        horas_inicio = {
            'lunes': request.form.get('hora_inicio_lunes', ''),
            'martes': request.form.get('hora_inicio_martes', ''),
            'miercoles': request.form.get('hora_inicio_miercoles', ''),
            'jueves': request.form.get('hora_inicio_jueves', ''),
            'viernes': request.form.get('hora_inicio_viernes', ''),
            'sabado': request.form.get('hora_inicio_sabado', ''),
            'domingo': request.form.get('hora_inicio_domingo', '')
        }
        horas_fin = {
            'lunes': request.form.get('hora_fin_lunes', ''),
            'martes': request.form.get('hora_fin_martes', ''),
            'miercoles': request.form.get('hora_fin_miercoles', ''),
            'jueves': request.form.get('hora_fin_jueves', ''),
            'viernes': request.form.get('hora_fin_viernes', ''),
            'sabado': request.form.get('hora_fin_sabado', ''),
            'domingo': request.form.get('hora_fin_domingo', '')
        }


        with get_db() as db:
            try:
                print({
                    'nombre_usuario': nombre_usuario,
                    'contraseña': contraseña,
                    'nombre': nombre,
                    'rango': rango,
                    'lunes': dias['lunes'],
                    'martes': dias['martes'],
                    'miercoles': dias['miercoles'],
                    'jueves': dias['jueves'],
                    'viernes': dias['viernes'],
                    'sabado': dias['sabado'],
                    'domingo': dias['domingo'],
                    'lunes_inicio': horas_inicio['lunes'],
                    'lunes_fin': horas_fin['lunes'],
                    'martes_inicio': horas_inicio['martes'],
                    'martes_fin': horas_fin['martes'],
                    'miercoles_inicio': horas_inicio['miercoles'],
                    'miercoles_fin': horas_fin['miercoles'],
                    'jueves_inicio': horas_inicio['jueves'],
                    'jueves_fin': horas_fin['jueves'],
                    'viernes_inicio': horas_inicio['viernes'],
                    'viernes_fin': horas_fin['viernes'],
                    'sabado_inicio': horas_inicio['sabado'],
                    'sabado_fin': horas_fin['sabado'],
                    'domingo_inicio': horas_inicio['domingo'],
                    'domingo_fin': horas_fin['domingo']
                })

                db.execute(text('''
                INSERT INTO Usuarios (nombre_usuario, contraseña, nombre, rango, lunes, martes, miercoles, jueves, viernes, sabado, domingo, lunes_inicio, lunes_fin, martes_inicio, martes_fin, miercoles_inicio, miercoles_fin, jueves_inicio, jueves_fin, viernes_inicio, viernes_fin, sabado_inicio, sabado_fin, domingo_inicio, domingo_fin)
                VALUES (:nombre_usuario, :contraseña, :nombre, :rango, :lunes, :martes, :miercoles, :jueves, :viernes, :sabado, :domingo, :lunes_inicio, :lunes_fin, :martes_inicio, :martes_fin, :miercoles_inicio, :miercoles_fin, :jueves_inicio, :jueves_fin, :viernes_inicio, :viernes_fin, :sabado_inicio, :sabado_fin, :domingo_inicio, :domingo_fin)
                '''), {
                    'nombre_usuario': nombre_usuario,
                    'contraseña': contraseña,
                    'nombre': nombre,
                    'rango': rango,
                    'lunes': dias['lunes'],
                    'martes': dias['martes'],
                    'miercoles': dias['miercoles'],
                    'jueves': dias['jueves'],
                    'viernes': dias['viernes'],
                    'sabado': dias['sabado'],
                    'domingo': dias['domingo'],
                    'lunes_inicio': horas_inicio['lunes'],
                    'lunes_fin': horas_fin['lunes'],
                    'martes_inicio': horas_inicio['martes'],
                    'martes_fin': horas_fin['martes'],
                    'miercoles_inicio': horas_inicio['miercoles'],
                    'miercoles_fin': horas_fin['miercoles'],
                    'jueves_inicio': horas_inicio['jueves'],
                    'jueves_fin': horas_fin['jueves'],
                    'viernes_inicio': horas_inicio['viernes'],
                    'viernes_fin': horas_fin['viernes'],
                    'sabado_inicio': horas_inicio['sabado'],
                    'sabado_fin': horas_fin['sabado'],
                    'domingo_inicio': horas_inicio['domingo'],
                    'domingo_fin': horas_fin['domingo']
                })
                db.commit()
                flash('Empleado añadido correctamente.', 'success')
            except Exception as e:
                db.rollback()  # Deshacer cambios en caso de error
                flash(f'Error al añadir empleado: {str(e)}', 'danger')
                print(f"Error al añadir usuario: {str(e)}")  # Para depuración

        return redirect(url_for('admin_empleados'))
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))



@app.route('/admin_interface/edit_user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if 'username' in session and (session['username'] == 'admin' or session['rango'] == 'jefe'):
        if request.method == 'POST':
            nombre_usuario = request.form['nombre_usuario']
            contraseña_nueva = request.form['contraseña']
            nombre = request.form['nombre']
            rango = request.form['rango']
            dias = {
                'lunes': bool(request.form.get('lunes')),
                'martes': bool(request.form.get('martes')),
                'miercoles': bool(request.form.get('miercoles')),
                'jueves': bool(request.form.get('jueves')),
                'viernes': bool(request.form.get('viernes')),
                'sabado': bool(request.form.get('sabado')),
                'domingo': bool(request.form.get('domingo'))
            }
            horas_inicio = {
                'lunes': request.form.get('hora_inicio_lunes', ''),
                'martes': request.form.get('hora_inicio_martes', ''),
                'miercoles': request.form.get('hora_inicio_miercoles', ''),
                'jueves': request.form.get('hora_inicio_jueves', ''),
                'viernes': request.form.get('hora_inicio_viernes', ''),
                'sabado': request.form.get('hora_inicio_sabado', ''),
                'domingo': request.form.get('hora_inicio_domingo', '')
            }
            horas_fin = {
                'lunes': request.form.get('hora_fin_lunes', ''),
                'martes': request.form.get('hora_fin_martes', ''),
                'miercoles': request.form.get('hora_fin_miercoles', ''),
                'jueves': request.form.get('hora_fin_jueves', ''),
                'viernes': request.form.get('hora_fin_viernes', ''),
                'sabado': request.form.get('hora_fin_sabado', ''),
                'domingo': request.form.get('hora_fin_domingo', '')
            }

            with get_db() as db:
                # Si la nueva contraseña está vacía, mantener la existente
                if contraseña_nueva:
                    contraseña = generate_password_hash(contraseña_nueva)
                else:
                    result = db.execute(text("SELECT contraseña FROM Usuarios WHERE id = :id"), {"id": id}).fetchone()
                    if result:
                        contraseña = result[0]
                    else:
                        raise ValueError("Usuario no encontrado")

                # Actualizar el usuario
                db.execute(text('''
                    UPDATE Usuarios 
                    SET nombre_usuario = :nombre_usuario, 
                        contraseña = :contraseña, 
                        nombre = :nombre, 
                        rango = :rango, 
                        lunes = :lunes, martes = :martes, miercoles = :miercoles, jueves = :jueves, 
                        viernes = :viernes, sabado = :sabado, domingo = :domingo, 
                        lunes_inicio = :lunes_inicio, lunes_fin = :lunes_fin, 
                        martes_inicio = :martes_inicio, martes_fin = :martes_fin, 
                        miercoles_inicio = :miercoles_inicio, miercoles_fin = :miercoles_fin, 
                        jueves_inicio = :jueves_inicio, jueves_fin = :jueves_fin, 
                        viernes_inicio = :viernes_inicio, viernes_fin = :viernes_fin, 
                        sabado_inicio = :sabado_inicio, sabado_fin = :sabado_fin, 
                        domingo_inicio = :domingo_inicio, domingo_fin = :domingo_fin
                    WHERE id = :id
                '''), {
                    "nombre_usuario": nombre_usuario,
                    "contraseña": contraseña,
                    "nombre": nombre,
                    "rango": rango,
                    "lunes": dias['lunes'], "martes": dias['martes'], "miercoles": dias['miercoles'],
                    "jueves": dias['jueves'], "viernes": dias['viernes'], "sabado": dias['sabado'],
                    "domingo": dias['domingo'],
                    "lunes_inicio": horas_inicio['lunes'], "lunes_fin": horas_fin['lunes'],
                    "martes_inicio": horas_inicio['martes'], "martes_fin": horas_fin['martes'],
                    "miercoles_inicio": horas_inicio['miercoles'], "miercoles_fin": horas_fin['miercoles'],
                    "jueves_inicio": horas_inicio['jueves'], "jueves_fin": horas_fin['jueves'],
                    "viernes_inicio": horas_inicio['viernes'], "viernes_fin": horas_fin['viernes'],
                    "sabado_inicio": horas_inicio['sabado'], "sabado_fin": horas_fin['sabado'],
                    "domingo_inicio": horas_inicio['domingo'], "domingo_fin": horas_fin['domingo'],
                    "id": id
                })
                db.commit()

                flash('Empleado actualizado correctamente.', 'success')
                return redirect(url_for('admin_empleados'))
        else:
            empleado = obtener_usuario_por_id(id)
            return render_template('edit_user.html', empleado=empleado)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))






@app.route('/admin_interface/delete_user/<int:id>', methods=['POST'])
def delete_user(id):
    if 'username' in session and session['rango'] == 'jefe':
        with get_db() as db:
            try:
                db.execute(text('DELETE FROM Usuarios WHERE id = :id'), {'id': id})
                db.commit()  # Confirmar cambios
                flash('Empleado eliminado correctamente.', 'success')
            except Exception as e:
                db.rollback()  # Deshacer cambios en caso de error
                flash(f'Error al eliminar empleado: {str(e)}', 'danger')

        return redirect(url_for('admin_empleados'))
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))



@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user_page(user_id):
    if 'username' not in session or session['user_id'] != user_id:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    usuario = obtener_usuario_por_id(user_id)  # Cambia a obtener_usuario_por_id para usar el ID.
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('login'))

    dias_trabajo = [
        {
            'dia': dia.capitalize(),
            'hora_inicio': usuario[f'{dia}_inicio'],
            'hora_fin': usuario[f'{dia}_fin']
        }
        for dia in ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        if usuario[dia]
    ]

    return render_template('user_page.html', usuario=usuario, dias_trabajo=dias_trabajo)



#Alimentos:

@app.route('/admin_interface/add_ingrediente', methods=['POST'])
def add_ingrediente():
    if 'username' not in session or (session['rango'] != 'jefe'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    try:
        nombre = request.form['nombre']
        cantidad = int(request.form['cantidad'])
        precio_unitario = float(request.form['precio_unitario'])
        valor_minimo = int(request.form['valor_minimo'])

        # Logs para depuración
        print(f"Datos recibidos: Nombre={nombre}, Cantidad={cantidad}, Precio Unitario={precio_unitario}, Valor Mínimo={valor_minimo}")

        # Intentar insertar el ingrediente
        if insertar_ingrediente(nombre, cantidad, precio_unitario, valor_minimo):
            flash(f"Ingrediente '{nombre}' añadido con éxito.", 'success')
        else:
            flash(f"El ingrediente '{nombre}' ya existe o ocurrió un error al añadirlo.", 'warning')

    except Exception as e:
        print(f"Error en la solicitud: {e}")
        flash(f"Error al añadir ingrediente: {e}", 'danger')

    return redirect(url_for('admin_ingredientes'))


@app.route('/admin_interface/edit_ingrediente/<int:id>', methods=['GET', 'POST'])
def edit_ingrediente(id):
    if 'username' in session and session['rango'] != 'jefe':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = int(request.form['cantidad'])
        precio_unitario = float(request.form['precio_unitario'])
        valor_minimo = int(request.form['valor_minimo'])

        actualizar_ingrediente(id, nombre, cantidad, precio_unitario, valor_minimo)

        flash(f"Ingrediente '{nombre}' actualizado con éxito.", 'success')
        return redirect(url_for('admin_ingredientes'))

    ingrediente = obtener_ingrediente_por_id(id)
    if not ingrediente:
        flash('Ingrediente no encontrado.', 'danger')
        return redirect(url_for('admin_ingredientes'))

    return render_template('edit_ingrediente.html', ingrediente=ingrediente)


@app.route('/admin_interface/delete_ingrediente/<int:id>', methods=['POST'])
def delete_ingrediente(id):
    if 'username' in session and session['rango'] != 'jefe':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    try:
        eliminar_ingrediente(id)
        flash(f"Ingrediente con ID {id} eliminado correctamente.", 'success')
    except Exception as e:
        flash(f"Error al eliminar ingrediente: {e}", 'danger')

    return redirect(url_for('admin_ingredientes'))



#Botones admin
@app.route('/admin_interface/platos')
def admin_platos():
    if 'username' in session and session['rango'] == 'jefe':
        platos = obtener_platos()
        return render_template('admin_platos.html', platos=platos)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

@app.route('/admin_empleados')
def admin_empleados():
    if 'username' in session and session['rango'] == 'jefe':
        empleados = obtener_usuarios()  # obtener_usuarios -> lista de empleados
        for empleado in empleados:
            print(empleado)  # Verificar q sea correcto
        return render_template('admin_empleados.html', empleados=empleados)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))




@app.route('/admin_ingredientes')
def admin_ingredientes():
    if 'username' in session and session['rango'] == 'jefe':
        ingredientes = obtener_ingredientes()
        return render_template('admin_ingredientes.html', ingredientes=ingredientes)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

@app.route('/admin_pagina_principal')
def admin_pagina_principal():
    if 'username' in session and session['rango'] == 'jefe':


        return render_template('admin_pagina_principal.html' )
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))


#Platos del Menu


@app.route('/add_plato', methods=['GET', 'POST'])
def add_plato():
    if request.method == 'POST':
        logging.debug("Datos del formulario recibidos: %s", request.form)
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        categoria = request.form['categoria']  # Obtener la categoría

        # Subir imagen
        imagen = request.files['imagen']
        image_url = None
        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/static/images/{filename}'

        try:
            with get_db() as db:
                # Insertar el plato con categoría
                db.execute(text(''' 
                    INSERT INTO Platos (nombre, descripcion, precio, image_url, categoria)
                    VALUES (:nombre, :descripcion, :precio, :image_url, :categoria)
                '''), {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'precio': precio,
                    'image_url': image_url,
                    'categoria': categoria  # Guardar la categoría
                })
                plato_id = db.execute(text('SELECT last_insert_rowid()')).fetchone()[0]

                # Procesar ingredientes existentes
                ingredientes_ids = request.form.getlist('ingrediente_id')
                cantidades = [int(request.form[f'cantidad_{ingrediente_id}']) for ingrediente_id in ingredientes_ids]
                for i, ingrediente_id in enumerate(ingredientes_ids):
                    cantidad = cantidades[i]
                    db.execute(text(''' 
                        INSERT INTO PlatosIngredientes (plato_id, ingrediente_id, cantidad_usada)
                        VALUES (:plato_id, :ingrediente_id, :cantidad_usada)
                    '''), {
                        'plato_id': plato_id,
                        'ingrediente_id': ingrediente_id,
                        'cantidad_usada': cantidad
                    })

                db.commit()
                flash(f"Plato '{nombre}' añadido con éxito.", 'success')

        except Exception as e:
            logging.error("Error al crear plato: %s", e)
            flash(f"Error al crear plato: {e}", 'danger')
            db.rollback()

        return redirect(url_for('admin_platos'))

    # Obtener lista de ingredientes disponibles
    ingredientes = obtener_ingredientes()
    return render_template('add_plato.html', ingredientes=ingredientes)




@app.route('/edit_plato/<int:id>', methods=['GET', 'POST'])
def edit_plato(id):
    plato = obtener_plato_por_id(id)
    ingredientes = obtener_ingredientes()  # Obtener todos los ingredientes disponibles
    ingredientes_actuales = obtener_ingredientes_por_plato(id)

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        categoria = request.form['categoria']

        # Manejar la imagen
        imagen = request.files['imagen']
        imagen_actual = request.form['imagen_actual']
        image_url = imagen_actual  # Por defecto, conservar la imagen actual

        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/static/images/{filename}'

        # Manejar los ingredientes
        ingredientes_ids = request.form.getlist('ingrediente_id')
        cantidades = []
        for ingrediente_id in ingredientes_ids:
            cantidad = request.form.get(f'cantidad_{ingrediente_id}')
            if cantidad:  # Si se proporciona una nueva cantidad
                cantidades.append(int(cantidad))
            else:  # Si no se proporciona una nueva cantidad, usar la cantidad previa
                cantidades.append(ingredientes_actuales.get(int(ingrediente_id), 1))  # Usar 1 como valor predeterminado si no hay cantidad previa

        try:
            with get_db() as db:

                db.execute(text('''
                    UPDATE Platos
                    SET nombre = :nombre, descripcion = :descripcion, precio = :precio, image_url = :image_url, categoria = :categoria
                    WHERE id = :id
                '''), {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'precio': precio,
                    'image_url': image_url,
                    'categoria': categoria,
                    'id': id
                })

                # Eliminar los ingredientes actuales del plato
                db.execute(text('DELETE FROM PlatosIngredientes WHERE plato_id = :plato_id'), {'plato_id': id})

                # Insertar los nuevos ingredientes
                for i, ingrediente_id in enumerate(ingredientes_ids):
                    cantidad = cantidades[i]
                    db.execute(text('''
                        INSERT INTO PlatosIngredientes (plato_id, ingrediente_id, cantidad_usada)
                        VALUES (:plato_id, :ingrediente_id, :cantidad_usada)
                    '''), {
                        'plato_id': id,
                        'ingrediente_id': ingrediente_id,
                        'cantidad_usada': cantidad
                    })

                db.commit()
                flash(f"Plato '{nombre}' actualizado con éxito.", 'success')

        except Exception as e:
            print(f"Error al actualizar plato: {e}")
            flash(f"Error al actualizar plato: {e}", 'danger')
            db.rollback()

        return redirect(url_for('admin_platos'))

    return render_template('edit_plato.html', plato=plato, ingredientes=ingredientes, ingredientes_actuales=ingredientes_actuales)




@app.route('/delete_plato/<int:id>', methods=['POST'])
def delete_plato(id):
    try:
        eliminar_plato(id)
        flash(f"Plato con ID {id} eliminado correctamente.", 'success')
    except Exception as e:
        flash(f"Error al eliminar plato: {e}", 'danger')

    return redirect(url_for('admin_platos'))



#botones empleado camarero
@app.route('/numero_mesa', methods=['GET', 'POST'])
def numero_mesa():
    if 'username' in session and session['rango'] in ['camarero', 'encargado']:
        return render_template('numero_mesa.html')
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))




@app.route('/seleccionar_mesa', methods=['POST'])
def seleccionar_mesa():
    if 'username' in session and session['rango'] in ['camarero', 'encargado']:
        mesa = request.form['mesa']
        return redirect(url_for('pedir_comida', mesa=mesa))
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))



#Pedidos
@app.route('/pedir_comida', methods=['GET'])
def pedir_comida():
    if 'username' in session and session['rango'] in ['camarero', 'encargado']:
        mesa = request.args.get('mesa')
        if mesa is None:
            flash('Número de mesa no proporcionado', 'danger')
            return redirect(url_for('user_page', user_id=session['user_id']))

        platos = obtener_platos()  # Asegúrate de que esta función esté definida y retorna la lista de platos
        pedidos_anteriores = obtener_pedidos_mesa(mesa)
        return render_template('pedir_comida.html', mesa=mesa, platos=platos, pedidos_anteriores=pedidos_anteriores)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

@app.route('/realizar_pedido', methods=['POST'])
def realizar_pedido():
    if 'username' in session and session['rango'] in ['camarero', 'encargado']:
        try:
            mesa = request.form['mesa']
            total = float(request.form['total'])
            pedidos = []

            # Procesar los platos seleccionados
            for key, value in request.form.items():
                if key.startswith('pedido_'):
                    # Extraer los datos del plato
                    pedido = value.split(',')
                    pedido_dict = {
                        'id': int(pedido[0]),
                        'nombre': pedido[1],
                        'precio': float(pedido[2]),
                        'cantidad': int(request.form[f'cantidad_{pedido[0]}'])
                    }
                    pedidos.append(pedido_dict)

            with get_db() as db:
                for pedido in pedidos:
                    db.execute(text('''
                        INSERT INTO Pedidos (usuario_id, plato_id, cantidad, estado, total, mesa)
                        VALUES (:usuario_id, :plato_id, :cantidad, :estado, :total, :mesa)
                    '''), {
                        'usuario_id': session['user_id'],
                        'plato_id': pedido['id'],
                        'cantidad': pedido['cantidad'],
                        'estado': 'Pendiente',
                        'total': pedido['precio'] * pedido['cantidad'],  # Total por plato
                        'mesa': mesa
                    })
                db.commit()

            flash(f"Pedido realizado para la mesa {mesa} con éxito. Total: €{total}", 'success')
        except Exception as e:
            flash(f"Error al realizar el pedido: {e}", 'danger')
    else:
        flash('Acceso no autorizado', 'danger')

    return redirect(url_for('user_page', user_id=session['user_id']))




@app.route('/recibir_pedidos', methods=['GET', 'POST'])
def recibir_pedidos():
    if 'username' in session and session['rango'] in ['cocina', 'encargado']:
        with get_db() as db:
            cursor = db.execute(text('''
                SELECT p.id, u.nombre_usuario, pl.nombre, p.cantidad, p.estado, p.mesa, p.timestamp, p.plato_id
                FROM Pedidos p
                JOIN Usuarios u ON p.usuario_id = u.id
                JOIN Platos pl ON p.plato_id = pl.id
                WHERE p.estado != 'Listo'
                ORDER BY p.timestamp ASC
            '''))
            pedidos = cursor.fetchall()

        mesas_pedidos = {}
        for pedido in pedidos:
            mesa = pedido[-3]  # El número de mesa es el penúltimo campo
            if mesa not in mesas_pedidos:
                mesas_pedidos[mesa] = []
            mesas_pedidos[mesa].append(pedido)

        if request.method == 'POST':
            try:
                if 'mesa_id' in request.form:
                    mesa_id = request.form['mesa_id']
                    nuevo_estado = request.form['nuevo_estado']

                    with get_db() as db:
                        db.execute(text('''
                            UPDATE Pedidos
                            SET estado = :nuevo_estado
                            WHERE mesa = :mesa_id
                        '''), {"nuevo_estado": nuevo_estado, "mesa_id": mesa_id})

                        if nuevo_estado == 'Listo':
                            pedidos_mesa = db.execute(text('''
                                SELECT plato_id, cantidad, mesa
                                FROM Pedidos
                                WHERE mesa = :mesa_id
                            '''), {"mesa_id": mesa_id}).fetchall()

                            for pedido in pedidos_mesa:
                                plato_id = pedido[0]
                                cantidad_pedido = pedido[1]
                                mesa = pedido[2]

                                # Obtener el nombre del plato
                                plato_nombre = db.execute(text('''
                                    SELECT nombre FROM Platos WHERE id = :plato_id
                                '''), {"plato_id": plato_id}).fetchone()[0]

                                # Insertar en la tabla Ticket
                                db.execute(text('''
                                    INSERT INTO Ticket (mesa, plato_id, plato_nombre, cantidad)
                                    VALUES (:mesa, :plato_id, :plato_nombre, :cantidad_pedido)
                                '''), {
                                    "mesa": mesa,
                                    "plato_id": plato_id,
                                    "plato_nombre": plato_nombre,
                                    "cantidad_pedido": cantidad_pedido
                                })

                                # Obtener los ingredientes del plato
                                ingredientes_plato = db.execute(text('''
                                    SELECT ingrediente_id, cantidad_usada
                                    FROM PlatosIngredientes
                                    WHERE plato_id = :plato_id
                                '''), {"plato_id": plato_id}).fetchall()

                                # Reducir el stock de cada ingrediente
                                for ingrediente in ingredientes_plato:
                                    ingrediente_id = ingrediente[0]
                                    cantidad_usada = ingrediente[1] * cantidad_pedido  # Cantidad total usada

                                    db.execute(text('''
                                        UPDATE Ingredientes
                                        SET cantidad = cantidad - :cantidad_usada
                                        WHERE id = :ingrediente_id
                                    '''), {
                                        "cantidad_usada": cantidad_usada,
                                        "ingrediente_id": ingrediente_id
                                    })

                        db.commit()

                    flash(f"Todos los pedidos de la mesa {mesa_id} se han actualizado a '{nuevo_estado}'.", 'success')

                else:
                    pedido_id = request.form['pedido_id']
                    nuevo_estado = request.form['nuevo_estado']

                    with get_db() as db:
                        db.execute(text('''
                            UPDATE Pedidos
                            SET estado = :nuevo_estado
                            WHERE id = :pedido_id
                        '''), {"nuevo_estado": nuevo_estado, "pedido_id": pedido_id})

                        if nuevo_estado == 'Listo':
                            pedido = db.execute(text('''
                                SELECT plato_id, cantidad, mesa
                                FROM Pedidos
                                WHERE id = :pedido_id
                            '''), {"pedido_id": pedido_id}).fetchone()

                            plato_id = pedido[0]
                            cantidad_pedido = pedido[1]
                            mesa = pedido[2]

                            plato_nombre = db.execute(text('''
                                SELECT nombre FROM Platos WHERE id = :plato_id
                            '''), {"plato_id": plato_id}).fetchone()[0]

                            db.execute(text('''
                                INSERT INTO Ticket (mesa, plato_id, plato_nombre, cantidad)
                                VALUES (:mesa, :plato_id, :plato_nombre, :cantidad_pedido)
                            '''), {
                                "mesa": mesa,
                                "plato_id": plato_id,
                                "plato_nombre": plato_nombre,
                                "cantidad_pedido": cantidad_pedido
                            })

                            ingredientes_plato = db.execute(text('''
                                SELECT ingrediente_id, cantidad_usada
                                FROM PlatosIngredientes
                                WHERE plato_id = :plato_id
                            '''), {"plato_id": plato_id}).fetchall()

                            for ingrediente in ingredientes_plato:
                                ingrediente_id = ingrediente[0]
                                cantidad_usada = ingrediente[1] * cantidad_pedido

                                db.execute(text('''
                                    UPDATE Ingredientes
                                    SET cantidad = cantidad - :cantidad_usada
                                    WHERE id = :ingrediente_id
                                '''), {
                                    "cantidad_usada": cantidad_usada,
                                    "ingrediente_id": ingrediente_id
                                })

                        db.commit()

                    flash(f"Estado del pedido {pedido_id} actualizado a '{nuevo_estado}'.", 'success')

            except Exception as e:
                flash(f"Error al actualizar el estado: {e}", 'danger')

            return redirect(url_for('recibir_pedidos'))

        return render_template('recibir_pedidos.html', mesas_pedidos=mesas_pedidos)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))


#quizas esto sobra?
@app.route('/ver_pedidos_mesa/<int:mesa>', methods=['GET', 'POST'])
def ver_pedidos_mesa(mesa):
    if 'username' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'cancelar_pedido' in request.form:
            pedido_id = request.form['cancelar_pedido']
            with get_db() as db:
                db.execute(text('DELETE FROM Pedidos WHERE id = :pedido_id'), {"pedido_id": pedido_id})
                db.commit()
            flash(f"Pedido {pedido_id} cancelado con éxito.", 'success')
        elif 'cancelar_todos' in request.form:
            with get_db() as db:
                db.execute(text('DELETE FROM Pedidos WHERE mesa = :mesa'), {"mesa": mesa})
                db.commit()
            flash(f"Todos los pedidos de la mesa {mesa} han sido cancelados.", 'success')

    # Obtener los pedidos de la mesa
    with get_db() as db:
        pedidos = db.execute(text('''
            SELECT p.id, u.nombre_usuario, pl.nombre, p.cantidad, p.estado, p.mesa, p.timestamp
            FROM Pedidos p
            JOIN Usuarios u ON p.usuario_id = u.id
            JOIN Platos pl ON p.plato_id = pl.id
            WHERE p.mesa = :mesa
            ORDER BY p.timestamp ASC
        '''), {"mesa": mesa}).fetchall()

    return render_template('ver_pedidos_mesa.html', mesa=mesa, pedidos=pedidos)


@app.route('/ver_tickets', methods=['GET'])
def ver_tickets():
    if 'username' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    with get_db() as db:
        # Obtener los tickets agrupados por mesa
        tickets = db.execute(text('''
            SELECT t.mesa, t.plato_nombre, t.cantidad, p.precio, t.timestamp, t.id
            FROM Ticket t
            JOIN Platos p ON t.plato_id = p.id
            ORDER BY t.mesa, t.timestamp DESC
        ''')).fetchall()

        # Agrupar los tickets por mesa
        mesas_tickets = {}
        for ticket in tickets:
            mesa = ticket[0]
            if mesa not in mesas_tickets:
                mesas_tickets[mesa] = []
            mesas_tickets[mesa].append(ticket)

        # Calcular el total por mesa
        totales_mesas = {}
        for mesa, platos in mesas_tickets.items():
            total = sum(plato[3] * plato[2] for plato in platos)  # precio por cantidad
            totales_mesas[mesa] = total

    return render_template('ver_tickets.html', mesas_tickets=mesas_tickets, totales_mesas=totales_mesas)


@app.route('/eliminar_plato_ticket', methods=['POST'])
def eliminar_plato_ticket():
    if 'username' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    ticket_id = request.form['ticket_id']
    with get_db() as db:
        db.execute(text('DELETE FROM Ticket WHERE id = :ticket_id'), {"ticket_id": ticket_id})
        db.commit()
    flash("Plato eliminado del ticket correctamente.", 'success')
    return redirect(url_for('ver_tickets'))


@app.route('/eliminar_todos_tickets_mesa', methods=['POST'])
def eliminar_todos_tickets_mesa():
    if 'username' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    mesa = request.form['mesa']
    with get_db() as db:
        db.execute(text('DELETE FROM Ticket WHERE mesa = :mesa'), {"mesa": mesa})
        db.commit()
    flash(f"Todos los platos de la mesa {mesa} han sido eliminados.", 'success')
    return redirect(url_for('ver_tickets'))

@app.route('/seleccionar_platos', methods=['POST'])
def seleccionar_platos():
    if 'username' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    try:
        mesa = request.form['mesa']
        platos = {int(k.split('[')[1].strip(']')): float(v) for k, v in request.form.items() if k.startswith('platos[') and v}

        for plato_id, cantidad in platos.items():
            plato = obtener_plato_por_id(plato_id)
            for ingrediente in plato['ingredientes']:
                actualizar_cantidad_ingrediente(ingrediente['id'], -ingrediente['cantidad'] * cantidad)

                if ingrediente['cantidad'] < ingrediente['valor_minimo']:
                    flash(f"El ingrediente '{ingrediente['nombre']}' está por debajo del valor mínimo.", 'warning')

        flash(f"Platos seleccionados para la mesa {mesa} con éxito.", 'success')
    except Exception as e:
        flash(f"Error al seleccionar platos: {e}", 'danger')

    return redirect(url_for('pedir_comida'))


#Fondo de pantalla de la web
@app.route('/set_background', methods=['POST'])
def set_background():
    if 'username' in session and session['rango'] == 'jefe':
        background = request.form.get('background')
        if background.startswith('http') or background.startswith('#'):
            actualizar_fondo(background)
            flash(f'Fondo actualizado correctamente.', 'success')
        else:
            flash('El fondo no es válido. Debe ser una URL o un color hexadecimal.', 'danger')
    else:
        flash('Acceso no autorizado.', 'danger')
    return redirect(url_for('admin_pagina_principal'))


@app.route('/upload_background', methods=['POST'])
def upload_background():
    if 'username' in session and session['rango'] == 'jefe':
        file = request.files.get('background_image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)  # Guardar la imagen en la carpeta de uploads
            background_url = f'/static/images/{filename}'
            print(f"URL del fondo: {background_url}")  # Log para depuración
            actualizar_fondo(background_url)  # Actualizar el fondo en la base de datos
            flash('Fondo actualizado correctamente.', 'success')
        else:
            flash('El archivo no es una imagen válida.', 'danger')
    else:
        flash('Acceso no autorizado.', 'danger')
    return redirect(url_for('admin_pagina_principal'))

@app.route('/static/css/dynamic_styles.css')
def dynamic_css():
    # Obtener valores dinámicos desde la base de datos con valores predeterminados
    configuracion = {
        'background_url': obtener_fondo_actual(),
        'typography': obtener_tipografia(),
        'color_bienvenida': obtener_color_bienvenida(),
        'color_direccion': obtener_color_direccion(),
        'color_horario': obtener_color_horario(),
        'color_telefono': obtener_color_telefono(),
        'color_boton': obtener_color_boton()
    }

    return render_template(
        'dynamic_styles.css',
        **configuracion
    ), 200, {'Content-Type': 'text/css'}




#Subir imagen Logo
@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if 'username' in session and session['rango'] == 'jefe':
        file = request.files.get('logo_image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)  # Guardar la imagen en la carpeta de uploads
            logo_url = f'/static/images/{filename}'
            actualizar_logo(logo_url)
            flash('Logo actualizado correctamente.', 'success')
        else:
            flash('El archivo no es una imagen válida.', 'danger')
    else:
        flash('Acceso no autorizado.', 'danger')
    return redirect(url_for('admin_pagina_principal'))


#Configuracion Pagina Principal
@app.route('/admin_interface/configuracion', methods=['GET', 'POST'])
def configuracion():
    if 'username' in session and session['rango'] == 'jefe':
        if request.method == 'POST':
            # Obtener datos del formulario
            usb_vendor_id = request.form.get('usb_vendor_id').strip()
            usb_product_id = request.form.get('usb_product_id').strip()
            restaurant_name = request.form.get('restaurant_name').strip() or "Restaurante"
            welcome_message = request.form.get('welcome_message').strip() or "Bienvenido a nuestro restaurante"
            direccion = request.form.get('direccion').strip() or "Dirección no disponible"
            horario = request.form.get('horario').strip() or "Horario no disponible"
            telefono = request.form.get('telefono').strip() or "Teléfono no disponible"
            typography = request.form.get('typography').strip() or "Arial"
            color_bienvenida = request.form.get('color_bienvenida').strip() or "#000000"
            color_direccion = request.form.get('color_direccion').strip() or "#FF5733"
            color_horario = request.form.get('color_horario').strip() or "#33FF57"
            color_telefono = request.form.get('color_telefono').strip() or "#3357FF"
            color_boton = request.form.get('color_boton').strip() or "#007bff"

            # Guardar en la base de datos
            actualizar_impresora('usb_vendor_id', usb_vendor_id)
            actualizar_impresora('usb_product_id', usb_product_id)

            flash('Configuración actualizada correctamente.', 'success')

            # Validar formato de colores (#RRGGBB)
            def is_valid_color(color):
                return color.startswith("#") and len(color) == 7

            if all([
                restaurant_name, welcome_message, direccion, horario, telefono, typography,
                is_valid_color(color_bienvenida),
                is_valid_color(color_direccion),
                is_valid_color(color_horario),
                is_valid_color(color_telefono),
                is_valid_color(color_boton)
            ]):
                # Actualizar valores en la base de datos
                actualizar_nombre_restaurante(restaurant_name)
                actualizar_mensaje_bienvenida(welcome_message)
                actualizar_direccion(direccion)
                actualizar_horario(horario)
                actualizar_telefono(telefono)
                actualizar_tipografia(typography)
                actualizar_color_bienvenida(color_bienvenida)
                actualizar_color_direccion(color_direccion)
                actualizar_color_horario(color_horario)
                actualizar_color_telefono(color_telefono)
                actualizar_color_boton(color_boton)

                # Subir fondo si se proporciona
                background_file = request.files.get('background_image')
                if background_file and allowed_file(background_file.filename):
                    filename = secure_filename(background_file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    background_file.save(filepath)
                    background_url = f'/static/images/{filename}'
                    actualizar_fondo(background_url)

                # Subir imagen del local si se proporciona
                local_image_file = request.files.get('local_image')
                if local_image_file and allowed_file(local_image_file.filename):
                    filename = secure_filename(local_image_file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    local_image_file.save(filepath)
                    image_url = f'/static/images/{filename}'
                    insertar_imagen_local(image_url)

                # Subir logo si se proporciona
                logo_file = request.files.get('logo_image')
                if logo_file and allowed_file(logo_file.filename):
                    filename = secure_filename(logo_file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logo_file.save(filepath)
                    logo_url = f'/static/images/{filename}'
                    actualizar_logo(logo_url)

                flash('Configuración actualizada correctamente.', 'success')
            else:
                flash('Todos los campos son obligatorios y los colores deben estar en formato hexadecimal (#RRGGBB).', 'danger')

        # Obtener valores actuales

        usb_vendor_id = obtener_impresora('usb_vendor_id') or "0x0000"
        usb_product_id = obtener_impresora('usb_product_id') or "0x0000"
        restaurant_name = obtener_nombre_restaurante()
        welcome_message = obtener_mensaje_bienvenida()
        direccion = obtener_direccion()
        horario = obtener_horario()
        telefono = obtener_telefono()
        typography = obtener_tipografia()
        color_bienvenida = obtener_color_bienvenida()
        color_direccion = obtener_color_direccion()
        color_horario = obtener_color_horario()
        color_telefono = obtener_color_telefono()
        color_boton = obtener_color_boton()
        background_url = obtener_fondo_actual()
        logo_url = obtener_logo()
        imagenes_local = obtener_imagenes_local()

        return render_template(
            'configuracion.html',
            restaurant_name=restaurant_name,
            welcome_message=welcome_message,
            direccion=direccion,
            horario=horario,
            telefono=telefono,
            typography=typography,
            color_bienvenida=color_bienvenida,
            color_direccion=color_direccion,
            color_horario=color_horario,
            color_telefono=color_telefono,
            color_boton=color_boton,
            background_url=background_url,
            logo_url=logo_url,
            imagenes_local=imagenes_local,
            usb_vendor_id=usb_vendor_id,
            usb_product_id=usb_product_id
        )
    else:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('login'))

#Imagenes
@app.route('/upload_local_image', methods=['POST'])
def upload_local_image():
    if 'username' in session and session['rango'] == 'jefe':
        file = request.files.get('local_image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = f'/static/images/{filename}'
            insertar_imagen_local(image_url)  # Guardar la URL en la base de datos
            flash('Imagen del local añadida correctamente.', 'success')
        else:
            flash('El archivo no es una imagen válida.', 'danger')
    else:
        flash('Acceso no autorizado.', 'danger')
    return redirect(url_for('admin_pagina_principal'))


@app.route('/eliminar_imagen_local/<int:id>', methods=['POST'])
def eliminar_imagen_local(id):
    print(f"ID recibido: {id}")  # Debug: Verificar el ID
    if 'username' in session and session['rango'] == 'jefe':
        try:
            eliminar_imagen_de_db(id)
            flash('Imagen eliminada correctamente.', 'success')
        except Exception as e:
            flash(f"Error al eliminar imagen: {e}", 'danger')
    else:
        flash('Acceso no autorizado.', 'danger')
    return redirect(url_for('configuracion'))


#Alerta de bajos niveles de ingredientes
def comprobar_ingredientes():
    ingredientes = obtener_ingredientes()
    ingredientes_a_reponer = []

    for ingrediente in ingredientes:
        if ingrediente['cantidad'] < ingrediente['valor_minimo']:
            ingredientes_a_reponer.append(ingrediente['nombre'])

    return ingredientes_a_reponer

#Crear Páginas de Menú
@app.route('/crear_pagina', methods=['GET', 'POST'])
def crear_pagina():
    if request.method == 'POST':
        # Obtener los datos del formulario
        tipo_menu = request.form['tipo_menu']
        precio = float(request.form['precio'])

        try:
            with get_db() as db:
                # Insertar la nueva página de menú en PaginasPersonalizadas
                db.execute(text('''
                    INSERT INTO PaginasPersonalizadas (titulo, precio)
                    VALUES (:titulo, :precio)
                '''), {
                    'titulo': tipo_menu,
                    'precio': precio
                })
                pagina_id = db.execute(text('SELECT last_insert_rowid()')).fetchone()[0]

                # Guardar los platos seleccionados en PlatosVisibilidad
                for categoria in ['entrante', 'principal', 'postre', 'bebida']:
                    platos_seleccionados = request.form.getlist(f'platos_{categoria}')

                    for plato_id in platos_seleccionados:
                        db.execute(text('''
                            INSERT INTO PlatosVisibilidad (pagina_id, plato_id, seccion, visible)
                            VALUES (:pagina_id, :plato_id, :seccion, 1)
                        '''), {
                            'pagina_id': pagina_id,
                            'plato_id': plato_id,
                            'seccion': categoria + 's'  # Pluralizar la categoría.
                        })

                db.commit()
                flash(f"Menú '{tipo_menu}' creado con éxito.", 'success')
                return redirect(url_for('admin_interface'))
        except Exception as e:
            print(f"Error al crear el menú: {e}")
            flash(f"Error al crear el menú: {e}", 'danger')
            db.rollback()

    # Obtener la lista de platos por categoría
    with get_db() as db:
        platos_entrantes = db.execute(
            text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'entrante'")).fetchall()
        platos_principales = db.execute(
            text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'principal'")).fetchall()
        platos_postres = db.execute(text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'postre'")).fetchall()
        platos_bebidas = db.execute(text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'bebida'")).fetchall()

    return render_template('crear_pagina.html',
                           platos_entrantes=platos_entrantes,
                           platos_principales=platos_principales,
                           platos_postres=platos_postres,
                           platos_bebidas=platos_bebidas)


@app.route('/pagina/<int:id>')
def ver_pagina(id):
    with get_db() as db:
        # Obtener la página por su ID
        pagina = db.execute(text('SELECT * FROM PaginasPersonalizadas WHERE id = :id'), {'id': id}).fetchone()


        # Obtener las páginas de menús creadas
        paginas = db.execute(text("SELECT id, titulo FROM PaginasPersonalizadas")).fetchall()

        logo_url = obtener_logo()

        if pagina:
            # Inicializar estructura para platos organizados por categoría
            platos_por_categoria = {
                'entrante': [],
                'principal': [],
                'postre': [],
                'bebida': []
            }

            # Obtener solo los platos visibles asociados a la página en PlatosVisibilidad
            platos = db.execute(text('''
                SELECT Platos.* FROM Platos
                JOIN PlatosVisibilidad ON Platos.id = PlatosVisibilidad.plato_id
                WHERE PlatosVisibilidad.pagina_id = :pagina_id 
                AND PlatosVisibilidad.visible = 1
            '''), {'pagina_id': id}).fetchall()

            # Organizar los platos por su categoría
            for plato in platos:
                categoria = plato.categoria
                if categoria in platos_por_categoria:
                    platos_por_categoria[categoria].append(plato)

            return render_template('ver_pagina.html', logo_url= logo_url, paginas=paginas, pagina={
                "id": pagina.id,
                "titulo": pagina.titulo,
                "platos_por_categoria": platos_por_categoria,
                "precio": pagina.precio
            })

        else:
            flash("Página no encontrada.", 'danger')
            return redirect(url_for('admin_interface'))


@app.route('/editar_pagina/<int:id>', methods=['GET', 'POST'])
def editar_pagina(id):
    with get_db() as db:
        # Obtener la página por su ID
        pagina = db.execute(text('SELECT * FROM PaginasPersonalizadas WHERE id = :id'), {'id': id}).fetchone()

        if not pagina:
            flash("Página no encontrada.", 'danger')
            return redirect(url_for('admin_interface'))

        if request.method == 'POST':
            # Obtener datos del formulario
            nuevo_titulo = request.form['tipo_menu']
            nuevo_precio = float(request.form['precio'])

            try:
                # Actualizar la información de la página
                db.execute(text('''
                    UPDATE PaginasPersonalizadas 
                    SET titulo = :titulo, precio = :precio
                    WHERE id = :id
                '''), {
                    'titulo': nuevo_titulo,
                    'precio': nuevo_precio,
                    'id': id
                })

                # Eliminar platos actuales de la página
                db.execute(text("DELETE FROM PlatosVisibilidad WHERE pagina_id = :id"), {'id': id})

                # Insertar los platos seleccionados nuevamente
                for categoria in ['entrante', 'principal', 'postre', 'bebida']:
                    platos_seleccionados = request.form.getlist(f'platos_{categoria}')

                    for plato_id in platos_seleccionados:
                        db.execute(text('''
                            INSERT INTO PlatosVisibilidad (pagina_id, plato_id, seccion, visible)
                            VALUES (:pagina_id, :plato_id, :seccion, 1)
                        '''), {
                            'pagina_id': id,
                            'plato_id': plato_id,
                            'seccion': categoria + 's'
                        })

                db.commit()
                flash("Página actualizada con éxito.", 'success')
                return redirect(url_for('admin_interface'))

            except Exception as e:
                print(f"Error al actualizar la página: {e}")
                flash(f"Error al actualizar la página: {e}", 'danger')
                db.rollback()

        # Obtener los platos disponibles por categoría
        platos_entrantes = db.execute(
            text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'entrante'")).fetchall()
        platos_principales = db.execute(
            text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'principal'")).fetchall()
        platos_postres = db.execute(text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'postre'")).fetchall()
        platos_bebidas = db.execute(text("SELECT id, nombre, precio FROM Platos WHERE categoria = 'bebida'")).fetchall()

        # Obtener los platos actualmente seleccionados para esta página
        platos_visibles = db.execute(text("""
            SELECT plato_id, seccion FROM PlatosVisibilidad 
            WHERE pagina_id = :pagina_id AND visible = 1
        """), {'pagina_id': id}).fetchall()

        # Organizar los platos visibles por categoría
        platos_seleccionados = {
            'entrante': set(),
            'principal': set(),
            'postre': set(),
            'bebida': set()
        }
        for p in platos_visibles:
            categoria = p.seccion.rstrip('s')  # Quitar la 's' del final (ejemplo: 'entrantes' → 'entrante')
            if categoria in platos_seleccionados:
                platos_seleccionados[categoria].add(p.plato_id)

    return render_template('editar_pagina.html',
                           pagina=pagina,
                           platos_entrantes=platos_entrantes,
                           platos_principales=platos_principales,
                           platos_postres=platos_postres,
                           platos_bebidas=platos_bebidas,
                           platos_seleccionados=platos_seleccionados)


@app.route('/eliminar_pagina/<int:id>', methods=['POST'])
def eliminar_pagina(id):
    if 'username' in session and session['rango'] == 'jefe':
        try:
            with get_db() as db:
                # Eliminar la página de la base de datos
                db.execute(text('DELETE FROM PaginasPersonalizadas WHERE id = :id'), {'id': id})
                db.commit()
                flash(f"Página eliminada con éxito.", 'success')
        except Exception as e:
            print(f"Error al eliminar la página: {e}")
            flash(f"Error al eliminar la página: {e}", 'danger')
            db.rollback()
        return redirect(url_for('admin_interface'))
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))



#reservas
@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre_cliente = request.form.get('nombre_cliente')
        email = request.form.get('email')
        numero_personas = request.form.get('numero_personas')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        zona = request.form.get('zona')

        # Validar datos
        if not all([nombre_cliente, email, numero_personas, fecha, hora, zona]):
            flash('Por favor, complete todos los campos.', 'danger')
            return redirect(url_for('reservar'))

        try:
            numero_personas = int(numero_personas)
            if numero_personas <= 0:
                flash('El número de personas debe ser mayor a 0.', 'danger')
                return redirect(url_for('reservar'))
        except ValueError:
            flash('Número de personas no válido.', 'danger')
            return redirect(url_for('reservar'))

        # Verificar disponibilidad de mesas
        mesas_disponibles = obtener_mesas_disponibles(zona, fecha, hora, numero_personas)
        if not mesas_disponibles:
            flash(f"No hay mesas disponibles para {numero_personas} comensales. "
                  "Lamentamos las molestias. Puede ponerse en contacto con nosotros a través del teléfono del restaurante.", "error")
            return redirect(url_for('reservar'))

        # Seleccionar la primera mesa disponible
        mesa_id = mesas_disponibles[0]['id']

        # Insertar la reserva en la base de datos
        try:
            insertar_reserva(nombre_cliente, email, numero_personas, fecha, hora, zona, mesa_id)
        except Exception as e:
            flash(f"Error al realizar la reserva: {e}", 'danger')
            return redirect(url_for('reservar'))

        # ✅ Mensaje de confirmación ANTES del envío del email
        flash("Su reserva ha sido confirmada con éxito. ¡Gracias por elegirnos!", "success")

        # Intentar enviar el correo de confirmación (si falla, la reserva sigue siendo válida)
        try:
            asunto = "Confirmación de Reserva"
            mensaje = f"""
            Hola {nombre_cliente},

            Gracias por reservar en nuestro restaurante. Aquí están los detalles de tu reserva:

            - Fecha: {fecha}
            - Hora: {hora}
            - Zona: {zona}
            - Número de personas: {numero_personas}

            ¡Esperamos verte pronto!

            Saludos,
            El equipo del restaurante
            """
            enviar_correo(email, asunto, mensaje)  # Enviar correo al cliente
        except Exception:
            flash("La reserva fue confirmada, pero hubo un error al enviar el correo de confirmación.", "warning")

        return redirect(url_for('home'))  # Redirigir al usuario a home después de reservar

    # Si es GET, verificar si la zona exterior está habilitada
    with get_db() as db:
        zona_exterior_habilitada = db.execute(text('''
            SELECT COUNT(*) FROM Mesas 
            WHERE zona = 'exterior' AND zona_habilitada = 1
        ''')).fetchone()[0] > 0

    return render_template('reservar.html', zona_exterior_habilitada=zona_exterior_habilitada)

@app.route('/admin/reservas/confirmar/<int:reserva_id>', methods=['POST'])
def confirmar_reserva(reserva_id):
    if 'username' in session and session['rango'] == 'jefe':
        try:
            with get_db() as db:
                # Confirmar la reserva
                db.execute(text('''
                    UPDATE Reservas 
                    SET confirmada = 1 
                    WHERE id = :reserva_id
                '''), {
                    "reserva_id": reserva_id
                })
                db.commit()
                flash('Reserva confirmada correctamente.', 'success')
        except Exception as e:
            flash(f'Error al confirmar la reserva: {e}', 'danger')
        return redirect(url_for('admin_reservas'))
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))


@app.route('/admin/reservas')
def admin_reservas():
    if 'username' in session and session['rango'] in ['jefe', 'encargado', 'camarero']:
        # Obtener todas las reservas
        with get_db() as db:
            reservas = db.execute(text('''
                SELECT Reservas.*, Mesas.zona 
                FROM Reservas 
                JOIN Mesas ON Reservas.mesa_id = Mesas.id
            ''')).fetchall()

        # Obtener el user_id del usuario actual
        user_id = session.get('user_id')

        return render_template('admin_reservas.html', reservas=reservas, user_id=user_id)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

@app.route('/admin/reservas/cancelar/<int:reserva_id>', methods=['POST'])
def cancelar_reserva(reserva_id):
    if 'username' in session and session['rango'] in ['jefe', 'encargado', 'camarero']:
        try:
            with get_db() as db:
                # Eliminar la reserva
                db.execute(text('DELETE FROM Reservas WHERE id = :reserva_id'), {
                    "reserva_id": reserva_id
                })
                db.commit()
                flash('Reserva cancelada correctamente.', 'success')
        except Exception as e:
            flash(f'Error al cancelar la reserva: {e}', 'danger')
        return redirect(url_for('admin_reservas'))
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

#Mesas reservas
@app.route('/admin/mesas', methods=['GET', 'POST'])
def admin_mesas():
    if 'username' in session and session['rango'] == 'jefe':
        if request.method == 'POST':
            try:
                with get_db() as db:
                    # Eliminar todas las mesas existentes
                    db.execute(text('DELETE FROM Mesas'))
                    db.commit()

                    # Insertar las nuevas mesas del interior
                    for i in range(6):  # 6 tipos de mesas (2, 4, 6, 8, 10, 12 personas)
                        num_mesas = int(request.form.get(f'mesa_interior_{i}'))
                        capacidad = (i + 1) * 2  # Capacidad de la mesa (2, 4, 6, 8, 10, 12 personas)
                        for _ in range(num_mesas):
                            db.execute(text('''
                                INSERT INTO Mesas (zona, capacidad, disponible, zona_habilitada)
                                VALUES (:zona, :capacidad, 1, 1)
                            '''), {
                                "zona": "interior",
                                "capacidad": capacidad
                            })

                    # Insertar las nuevas mesas del exterior
                    zona_exterior_habilitada = int(request.form.get('zona_exterior_habilitada'))
                    for i in range(6):  # 6 tipos de mesas = interior
                        num_mesas = int(request.form.get(f'mesa_exterior_{i}'))
                        capacidad = (i + 1) * 2  # Capacidad de la mesa =
                        for _ in range(num_mesas):
                            db.execute(text('''
                                INSERT INTO Mesas (zona, capacidad, disponible, zona_habilitada)
                                VALUES (:zona, :capacidad, 1, :zona_habilitada)
                            '''), {
                                "zona": "exterior",
                                "capacidad": capacidad,
                                "zona_habilitada": zona_exterior_habilitada
                            })

                    db.commit()
                    flash('Configuración de mesas guardada correctamente.', 'success')
            except Exception as e:
                flash(f'Error al guardar la configuración de mesas: {e}', 'danger')

        # Obtener todas las mesas para mostrar en la tabla
        mesas = obtener_mesas()

        # Calcular la cantidad de mesas de cada tipo
        mesas_interior = {2: 0, 4: 0, 6: 0, 8: 0, 10: 0, 12: 0}
        mesas_exterior = {2: 0, 4: 0, 6: 0, 8: 0, 10: 0, 12: 0}

        for mesa in mesas:
            if mesa['zona'] == 'interior':
                mesas_interior[mesa['capacidad']] += 1
            elif mesa['zona'] == 'exterior':
                mesas_exterior[mesa['capacidad']] += 1

        return render_template('admin_mesas.html', mesas=mesas, mesas_interior=mesas_interior, mesas_exterior=mesas_exterior)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))



#Impresora Térmica
@app.route('/imprimir_ticket_mesa/<int:mesa>', methods=['POST'])
def imprimir_ticket_mesa(mesa):
    if 'username' not in session:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))

    with get_db() as db:
        # Obtener los platos pedidos en la mesa
        platos = db.execute(text('''
            SELECT plato_nombre, cantidad, precio
            FROM Ticket
            JOIN Platos ON Ticket.plato_id = Platos.id
            WHERE mesa = :mesa
        '''), {"mesa": mesa}).fetchall()

        # Calcular el total
        total = sum(plato[2] * plato[1] for plato in platos)  # precio * cantidad

        # Llamar a la función de impresión
        imprimir_ticket(mesa, [{"nombre": plato[0], "precio": plato[2]} for plato in platos], total)

    flash(f"Ticket de la mesa {mesa} enviado a la impresora.", 'success')
    return redirect(url_for('ver_tickets'))


#Gráficos
@app.route('/graficos')
def graficos():
    if 'username' in session and session['rango'] == 'jefe':
        # Obtener la fecha actual
        ahora = datetime.now()

        # Definir los períodos de tiempo
        una_semana = ahora - timedelta(days=7)
        un_mes = ahora - timedelta(days=30)
        un_anyo = ahora - timedelta(days=365)

        # Obtener datos para los gráficos
        with get_db() as db:
            # Popularidad de los platos (veces pedidos)
            platos_popularidad = db.execute(text('''
                SELECT plato_nombre, SUM(cantidad) as total_pedidos
                FROM Ticket
                GROUP BY plato_nombre
                ORDER BY total_pedidos DESC
            ''')).fetchall()

            # Popularidad de los platos en los últimos 7 días
            platos_popularidad_semana = db.execute(text('''
                SELECT plato_nombre, SUM(cantidad) as total_pedidos
                FROM Ticket
                WHERE timestamp >= :fecha_inicio
                GROUP BY plato_nombre
                ORDER BY total_pedidos DESC
            '''), {"fecha_inicio": una_semana}).fetchall()

            # Popularidad de los platos en los últimos 30 días
            platos_popularidad_mes = db.execute(text('''
                SELECT plato_nombre, SUM(cantidad) as total_pedidos
                FROM Ticket
                WHERE timestamp >= :fecha_inicio
                GROUP BY plato_nombre
                ORDER BY total_pedidos DESC
            '''), {"fecha_inicio": un_mes}).fetchall()

            # Popularidad de los platos en los últimos 365 días
            platos_popularidad_anyo = db.execute(text('''
                      SELECT plato_nombre, SUM(cantidad) as total_pedidos
                      FROM Ticket
                      WHERE timestamp >= :fecha_inicio
                      GROUP BY plato_nombre
                      ORDER BY total_pedidos DESC
                  '''), {"fecha_inicio": un_anyo}).fetchall()

            # Ingredientes más gastados en los últimos 7 días
            ingredientes_gastados_semana = db.execute(text('''
                SELECT i.nombre, SUM(pi.cantidad_usada * t.cantidad) as total_gastado
                FROM PlatosIngredientes pi
                JOIN Ingredientes i ON pi.ingrediente_id = i.id
                JOIN Ticket t ON pi.plato_id = t.plato_id
                WHERE t.timestamp >= :fecha_inicio
                GROUP BY i.nombre
                ORDER BY total_gastado DESC
            '''), {"fecha_inicio": una_semana}).fetchall()

            # Ingredientes más gastados en los últimos 30 días
            ingredientes_gastados_mes = db.execute(text('''
                SELECT i.nombre, SUM(pi.cantidad_usada * t.cantidad) as total_gastado
                FROM PlatosIngredientes pi
                JOIN Ingredientes i ON pi.ingrediente_id = i.id
                JOIN Ticket t ON pi.plato_id = t.plato_id
                WHERE t.timestamp >= :fecha_inicio
                GROUP BY i.nombre
                ORDER BY total_gastado DESC
            '''), {"fecha_inicio": un_mes}).fetchall()

            # Rentabilidad de los platos (ingresos generados - costo ingredientes)
            platos_rentabilidad = db.execute(text('''
                SELECT p.nombre AS plato_nombre, 
                       p.precio AS precio_venta,
                       SUM(pi.cantidad_usada * i.precio_unitario) AS costo_ingredientes,
                       (p.precio - SUM(pi.cantidad_usada * i.precio_unitario)) AS rentabilidad
                FROM Platos p
                JOIN PlatosIngredientes pi ON p.id = pi.plato_id
                JOIN Ingredientes i ON pi.ingrediente_id = i.id
                GROUP BY p.id, p.nombre, p.precio
                ORDER BY rentabilidad DESC
            ''')).fetchall()

            # Días con mayor afluencia de público
            dias_afluencia = db.execute(text('''
                SELECT DATE(timestamp) as fecha, COUNT(*) as total_pedidos
                FROM Ticket
                GROUP BY fecha
                ORDER BY total_pedidos DESC
            ''')).fetchall()

        # Preparar datos para los gráficos
        popularidad_labels = [plato[0] for plato in platos_popularidad]
        popularidad_data = [plato[1] for plato in platos_popularidad]

        popularidad_semana_labels = [plato[0] for plato in platos_popularidad_semana]
        popularidad_semana_data = [plato[1] for plato in platos_popularidad_semana]

        popularidad_mes_labels = [plato[0] for plato in platos_popularidad_mes]
        popularidad_mes_data = [plato[1] for plato in platos_popularidad_mes]

        popularidad_anyo_labels = [plato[0] for plato in platos_popularidad_anyo]
        popularidad_anyo_data = [plato[1] for plato in platos_popularidad_anyo]

        ingredientes_semana_labels = [ingrediente[0] for ingrediente in ingredientes_gastados_semana]
        ingredientes_semana_data = [ingrediente[1] for ingrediente in ingredientes_gastados_semana]

        ingredientes_mes_labels = [ingrediente[0] for ingrediente in ingredientes_gastados_mes]
        ingredientes_mes_data = [ingrediente[1] for ingrediente in ingredientes_gastados_mes]

        rentabilidad_labels = [plato[0] for plato in platos_rentabilidad]
        rentabilidad_data = [plato[1] for plato in platos_rentabilidad]

        afluencia_labels = [dia[0] for dia in dias_afluencia]
        afluencia_data = [dia[1] for dia in dias_afluencia]

        return render_template('graficos.html',
                               popularidad_labels=popularidad_labels,
                               popularidad_data=popularidad_data,
                               popularidad_semana_labels=popularidad_semana_labels,
                               popularidad_semana_data=popularidad_semana_data,
                               popularidad_mes_labels=popularidad_mes_labels,
                               popularidad_mes_data=popularidad_mes_data,
                               popularidad_anyo_labels=popularidad_anyo_labels,
                               popularidad_anyo_data=popularidad_anyo_data,
                               ingredientes_semana_labels=ingredientes_semana_labels,
                               ingredientes_semana_data=ingredientes_semana_data,
                               ingredientes_mes_labels=ingredientes_mes_labels,
                               ingredientes_mes_data=ingredientes_mes_data,
                               rentabilidad_labels=[plato[0] for plato in platos_rentabilidad],  # Nombre del plato
                               rentabilidad_data = [plato[3] for plato in platos_rentabilidad],  # Rentabilidad total
                               afluencia_labels=afluencia_labels,
                               afluencia_data=afluencia_data)
    else:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))



if __name__ == '__main__':
    # Configurar el registro
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)


    insertar_usuario(
        nombre_usuario="admin",
        contraseña="123",  # Contraseña del administrador
        nombre="Administrador",
        rango="jefe",
        dias_trabajo=['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    )
    app.run(debug=True)
