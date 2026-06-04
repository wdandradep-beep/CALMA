from flask import Flask
import sqlite3, os
from werkzeug.security import generate_password_hash

def create_app():
    app=Flask(__name__)
    app.secret_key="calma-secret"
    db=os.path.join(os.path.dirname(__file__),'calma.db')
    conn=sqlite3.connect(db)
    c=conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,email TEXT,password TEXT,role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS materias(id INTEGER PRIMARY KEY,nombre TEXT,descripcion TEXT,color TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS actividades(id INTEGER PRIMARY KEY,nombre TEXT,descripcion TEXT,materia_id INTEGER,user_id INTEGER,estado TEXT,prioridad TEXT,progreso INTEGER,fecha_inicio TEXT,fecha_entrega TEXT)")

    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.executemany(
    "INSERT INTO users(username,email,password,role) VALUES(?,?,?,?)",
    [
        ("admin","admin@calma.com",generate_password_hash("admin123"),"admin"),
        ("will","admin@calma.com",generate_password_hash("will123"),"admin")
    ]
)

    conn.commit()   
    conn.close()

    from .routes import main
    app.register_blueprint(main)
    return app
