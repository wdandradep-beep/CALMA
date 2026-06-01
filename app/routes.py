from flask import Blueprint,render_template,request,redirect,session
import sqlite3,os,datetime
from werkzeug.security import check_password_hash,generate_password_hash
from werkzeug.utils import secure_filename
import os 
# TIPOS PERMITIDOS
ALLOWED_EXTENSIONS = {'pdf','png','jpg','jpeg'}

# TAMAÑO MAXIMO 40MB
MAX_SIZE = 40 * 1024 * 1024
def allowed_file(filename):

    return '.' in filename and \
    filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

main=Blueprint('main',__name__)

def db():
    return sqlite3.connect(os.path.join(os.path.dirname(__file__),'calma.db'))

@main.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        conn=db()
        c=conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?",(request.form['username'],))
        user=c.fetchone()
        conn.close()
        if user and check_password_hash(user[3],request.form['password']):
            session['user']=user[1]
            session['role']=user[4]
            session['id']=user[0]
            return redirect('/')
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@main.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        conn=db()
        c=conn.cursor()
        c.execute("INSERT INTO users(username,email,password,role) VALUES(?,?,?,?)",
        (request.form['username'],request.form['email'],generate_password_hash(request.form['password']),'user'))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@main.route('/')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    conn = db()
    c = conn.cursor()

    # Total actividades
    c.execute("""
    SELECT COUNT(*) FROM actividades 
    WHERE user_id=?
    """,(session['id'],))
    total = c.fetchone()[0]

    # Completadas
    c.execute("""
    SELECT COUNT(*) FROM actividades 
    WHERE user_id=? AND estado='Completado'
    """,(session['id'],))
    completadas = c.fetchone()[0]

    # Pendientes
    c.execute("""
    SELECT COUNT(*) FROM actividades 
    WHERE user_id=? AND estado='Pendiente'
    """,(session['id'],))
    pendientes = c.fetchone()[0]

    # Vencidas
    c.execute("""
    SELECT COUNT(*) FROM actividades 
    WHERE user_id=? AND estado='Plazo vencido'
    """,(session['id'],))
    vencidas = c.fetchone()[0]

    # GANTT PRO (CORREGIDO)
    c.execute("""
    SELECT nombre, fecha_inicio, fecha_entrega
    FROM actividades
    WHERE user_id=? AND estado!='Completado'
    """,(session['id'],))

    rows = c.fetchall()

    hoy = datetime.date.today()

    gantt = []

    for r in rows:

        nombre = r[0]

        try:
            inicio = datetime.datetime.strptime(r[1], "%Y-%m-%d").date()
            entrega = datetime.datetime.strptime(r[2], "%Y-%m-%d").date()

            offset = (inicio - hoy).days
            duracion = (entrega - inicio).days

            offset = max(offset, 0)
            duracion = max(duracion, 1)

        except:
            offset = 0
            duracion = 1

        gantt.append({
            "nombre": nombre,
            "offset": offset,
            "duracion": duracion
        })

    conn.close()

    return render_template(
        'dashboard.html',
        total=total,
        completadas=completadas,
        pendientes=pendientes,
        vencidas=vencidas,
        gantt=gantt
    )
@main.route('/materias',methods=['GET','POST'])
def materias():
    if 'user' not in session:
        return redirect('/login')
    conn=db()
    c=conn.cursor()
    if request.method=='POST' and session['role']=='admin':
        c.execute("INSERT INTO materias(nombre,descripcion,color) VALUES(?,?,?)",
        (request.form['nombre'],request.form['descripcion'],request.form['color']))
        conn.commit()
    c.execute("SELECT * FROM materias")
    data=c.fetchall()
    conn.close()
    return render_template('materias.html',materias=data)

@main.route('/actividades',methods=['GET','POST'])
def actividades():
    if 'user' not in session:
        return redirect('/login')

    conn=db()
    c=conn.cursor()

    if request.method=='POST':
        estado=request.form['estado']
        fecha=request.form['fecha_entrega']
        if fecha < str(datetime.date.today()) and estado!='Completado':
            estado='Plazo vencido'

        c.execute("INSERT INTO actividades(nombre,descripcion,materia_id,user_id,estado,prioridad,progreso,fecha_inicio,fecha_entrega) VALUES(?,?,?,?,?,?,?,?,?)",
        (request.form['nombre'],request.form['descripcion'],request.form['materia'],session['id'],estado,request.form['prioridad'],request.form['progreso'],request.form['fecha_inicio'],fecha))
        conn.commit()

    c.execute("""
SELECT 
a.id,
a.nombre,
a.descripcion,
m.nombre,
a.estado,
a.prioridad,
a.progreso,
a.fecha_inicio,
a.fecha_entrega
FROM actividades a
LEFT JOIN materias m 
ON m.id=a.materia_id
WHERE a.user_id=?
""",
(session['id'],))
    acts=c.fetchall()

    c.execute("SELECT * FROM materias")
    mats=c.fetchall()

    conn.close()
    return render_template('actividades.html',actividades=acts,materias=mats)

@main.route('/users')
def users():
    if session.get('role')!='admin':
        return redirect('/')
    conn=db()
    c=conn.cursor()
    c.execute("SELECT id,username,email,role FROM users")
    data=c.fetchall()
    conn.close()
    return render_template('users.html',users=data)

@main.route('/delete_activity/<id>')
def delete_activity(id):

    if 'user' not in session:
        return redirect('/login')

    conn=db()
    c=conn.cursor()

    c.execute("DELETE FROM actividades WHERE id=? AND user_id=?",
              (id,session['id']))

    conn.commit()
    conn.close()

    return redirect('/actividades')

@main.route('/edit_activity/<id>', methods=['GET','POST'])
def edit_activity(id):

    if 'user' not in session:
        return redirect('/login')

    conn=db()
    c=conn.cursor()

    # Si envían el formulario (POST)
    if request.method=='POST':

        c.execute("""
        UPDATE actividades
        SET nombre=?,
            descripcion=?,
            estado=?,
            prioridad=?,
            progreso=?,
            fecha_inicio=?,
            fecha_entrega=?
        WHERE id=? AND user_id=?
        """,

        (
            request.form['nombre'],
            request.form['descripcion'],
            request.form['estado'],
            request.form['prioridad'],
            request.form['progreso'],
            request.form['fecha_inicio'],
            request.form['fecha_entrega'],
            id,
            session['id']
        ))

        conn.commit()
        conn.close()

        return redirect('/actividades')

    # Si solo quieren ver el formulario (GET)
    c.execute("""
    SELECT * FROM actividades
    WHERE id=? AND user_id=?
    """,(id,session['id']))

    actividad=c.fetchone()

    conn.close()

    return render_template(
        'edit_activity.html',
        actividad=actividad
    )

@main.route('/delete_materia/<id>')
def delete_materia(id):

    if session.get('role')!='admin':
        return redirect('/')

    conn=db()
    c=conn.cursor()

    c.execute("DELETE FROM materias WHERE id=?",(id,))

    conn.commit()
    conn.close()

    return redirect('/materias')

@main.route('/edit_materia/<id>', methods=['GET','POST'])
def edit_materia(id):

    if session.get('role')!='admin':
        return redirect('/')

    conn=db()
    c=conn.cursor()

    if request.method=='POST':

        c.execute("""
        UPDATE materias
        SET nombre=?,
            descripcion=?,
            color=?
        WHERE id=?
        """,

        (
            request.form['nombre'],
            request.form['descripcion'],
            request.form['color'],
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/materias')

    c.execute("SELECT * FROM materias WHERE id=?",(id,))

    materia=c.fetchone()

    conn.close()

    return render_template(
        'edit_materia.html',
        materia=materia
    )

@main.route('/delete_user/<id>')
def delete_user(id):

    if session.get('role')!='admin':
        return redirect('/')

    # PROTECCIÓN ADMIN
    if id == str(session['id']):
        return redirect('/users')

    conn=db()

    c=conn.cursor()

    c.execute("DELETE FROM users WHERE id=?",(id,))

    conn.commit()

    conn.close()

    return redirect('/users')

@main.route('/edit_user/<id>', methods=['GET','POST'])
def edit_user(id):

    if session.get('role')!='admin':
        return redirect('/')

    conn=db()

    c=conn.cursor()

    if request.method=='POST':

        c.execute(
        "UPDATE users SET role=? WHERE id=?",
        (request.form['role'],id)
        )

        conn.commit()

        conn.close()

        return redirect('/users')

    c.execute(
    "SELECT * FROM users WHERE id=?",
    (id,)
    )

    user=c.fetchone()

    conn.close()

    return render_template(
        'edit_user.html',
        user=user
    )

@main.route('/actividad/<id>')
def actividad_detalle(id):

    if 'user' not in session:
        return redirect('/login')

    conn=db()
    c=conn.cursor()

    c.execute("""

    SELECT 
    a.id,
    a.nombre,
    a.descripcion,
    m.nombre,
    a.estado,
    a.prioridad,
    a.progreso,
    a.fecha_inicio,
    a.fecha_entrega

    FROM actividades a

    LEFT JOIN materias m 
    ON m.id=a.materia_id

    WHERE a.id=? AND a.user_id=?

    """,(id,session['id']))

    actividad=c.fetchone()

    # buscar archivos de la actividad

    c.execute("""

    SELECT * FROM activity_files

    WHERE activity_id=?

    """,(id,))

    # guardar archivos encontrados

    files=c.fetchall()

    # cerrar base de datos

    conn.close()

    # enviar todo al HTML

    return render_template(

        'actividad_detalle.html',

        actividad=actividad,

        files=files

    )

@main.route('/upload/<id>',methods=['POST'])
def upload_file(id):

    if 'user' not in session:
        return redirect('/login')

    file=request.files['file']

    # validar archivo

    if not file or file.filename == '':
        return redirect('/actividad/'+id)

    # validar tipo

    if not allowed_file(file.filename):
        return redirect('/actividad/'+id)

    # validar tamaño

    file.seek(0,os.SEEK_END)

    size=file.tell()

    file.seek(0)

    if size > MAX_SIZE:
        return redirect('/actividad/'+id)

    # nombre único

    import time

    filename=str(int(time.time()))+"_"+secure_filename(file.filename)

    path=os.path.join(

    os.path.dirname(__file__),

    'static/uploads',

    filename

    )

    file.save(path)

    conn=db()

    c=conn.cursor()

    c.execute("""

    INSERT INTO activity_files(

    activity_id,

    filename,

    filepath

    )

    VALUES(?,?,?)

    """,(id,filename,filename))

    conn.commit()

    conn.close()

    return redirect('/actividad/'+id)

@main.route('/delete_file/<file_id>/<activity_id>')
def delete_file(file_id,activity_id):

    if 'user' not in session:
        return redirect('/login')

    conn=db()
    c=conn.cursor()

    c.execute("SELECT filepath FROM activity_files WHERE id=?",(file_id,))

    file=c.fetchone()

    if file:

        path=os.path.join(
        os.path.dirname(__file__),
        'static/uploads',
        file[0]
        )

        if os.path.exists(path):

            os.remove(path)

    c.execute("DELETE FROM activity_files WHERE id=?",(file_id,))

    conn.commit()
    conn.close()

    return redirect('/actividad/'+activity_id)