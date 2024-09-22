import os
import sqlite3
from base64 import b85encode, b85decode
from datetime import datetime
from getpass import getpass

from nautapy import appdata_path

# Base de datos de los usuarios
USERS_DB = os.path.join(appdata_path, "users.db")
# Base de datos de las conexiones hechas por los usuarios
CONNECTIONS_DB = os.path.join(appdata_path, "connections.db")


def users_db_connect():
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user TEXT, password TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS default_user (user TEXT)")

    conn.commit()
    return cursor, conn


def _get_default_user():
    cursor, _ = users_db_connect()

    # Search for explicit default value
    cursor.execute("SELECT user FROM default_user LIMIT 1")
    rec = cursor.fetchone()
    if rec:
        return rec[0]

    # If no explicit value exists, find the first user
    cursor.execute("SELECT * FROM users LIMIT 1")

    rec = cursor.fetchone()
    if rec:
        return rec[0]


def _find_credentials(user, default_password=None):
    cursor, _ = users_db_connect()
    cursor.execute("SELECT * FROM users WHERE user LIKE ?", (user + "%",))

    rec = cursor.fetchone()
    if rec:
        return rec[0], b85decode(rec[1]).decode("utf-8")
    else:
        return user, default_password


def add_user(args):
    password = args.password or getpass("Contraseña para {}: ".format(args.user))

    cursor, connection = users_db_connect()
    cursor.execute(
        "INSERT INTO users VALUES (?, ?)",
        (args.user, b85encode(password.encode("utf-8"))),
    )
    connection.commit()

    print("Usuario guardado: {}".format(args.user))


def set_default_user(args):
    cursor, connection = users_db_connect()
    cursor.execute("SELECT count(user) FROM default_user")
    res = cursor.fetchone()

    if res[0]:
        cursor.execute("UPDATE default_user SET user=?", (args.user,))
    else:
        cursor.execute("INSERT INTO default_user VALUES (?)", (args.user,))

    connection.commit()

    print("Usuario predeterminado: {}".format(args.user))


def remove_user(args):
    cursor, connection = users_db_connect()
    cursor.execute("DELETE FROM users WHERE user=?", (args.user,))
    connection.commit()

    print("Usuario eliminado: {}".format(args.user))


def set_password(args):
    password = args.password or getpass("Contraseña para {}: ".format(args.user))

    cursor, connection = users_db_connect()
    cursor.execute(
        "UPDATE users SET password=? WHERE user=?",
        (b85encode(password.encode("utf-8")), args.user),
    )

    connection.commit()

    print("Contraseña actualizada: {}".format(args.user))


def list_users(args):
    cursor, _ = users_db_connect()

    for rec in cursor.execute("SELECT user FROM users"):
        print(rec[0])


def create_connections_db():
    conn = sqlite3.connect(CONNECTIONS_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS connections (
            user TEXT,
            fecha_inicio_sesion DATETIME,
            fecha_cierre_sesion DATETIME
        )
        """
    )
    conn.commit()
    conn.close()


def save_login(user):
    create_connections_db()
    conn = sqlite3.connect(CONNECTIONS_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO connections (user, fecha_inicio_sesion)
        VALUES (?, ?)
        """,
        (user, datetime.now()),
    )
    conn.commit()
    conn.close()


def save_logout(user):
    # create_connections_db()
    conn = sqlite3.connect(CONNECTIONS_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE connections
        SET fecha_cierre_sesion = ?
        WHERE user = ? AND fecha_cierre_sesion IS NULL
        AND fecha_inicio_sesion = (
            SELECT MAX(fecha_inicio_sesion)
            FROM connections
            WHERE user = ?
        )
        """,
        (datetime.now(), user, user)
    )
    conn.commit()
    conn.close()


def list_connections(args):
    # Asegurarse de que la base de datos de conexiones esté creada
    create_connections_db()

    # Conectarse a la base de datos
    conn = sqlite3.connect(CONNECTIONS_DB)
    cursor = conn.cursor()

    # Ejecutar la consulta para obtener los datos de las conexiones
    cursor.execute(
        """
        SELECT user, fecha_inicio_sesion, fecha_cierre_sesion
        FROM connections
        ORDER BY fecha_inicio_sesion
        """
    )

    # Obtener todos los registros y almacenarlos en una lista
    connections = cursor.fetchall()

    # Cerrar la conexión a la base de datos
    conn.close()

    # Devolver los registros obtenidos
    return connections
