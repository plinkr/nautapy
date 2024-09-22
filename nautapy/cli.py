import argparse
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime

from requests import RequestException

from nautapy import utils
from nautapy.__about__ import __cli__ as prog_name, __version__ as version
from nautapy.exceptions import NautaException
from nautapy.nauta_api import NautaClient, NautaProtocol
from nautapy.sqlite_utils import _get_default_user, save_login, save_logout, add_user, set_default_user, set_password, \
    remove_user, list_users, _find_credentials, list_connections


def _get_credentials(args):
    user = args.user or _get_default_user()
    password = args.password or None

    if not user:
        print(
            "No existe ningún usuario. Debe crear uno. "
            "Ejecute '{} --help' para más ayuda".format(prog_name),
            file=sys.stderr,
        )
        sys.exit(1)
    return _find_credentials(user=user, default_password=password)


def up(args):
    user, password = _get_credentials(args)
    client = NautaClient(user=user, password=password)

    print(
        "Conectando usuario: {}".format(
            client.user,
        )
    )

    if args.batch:
        client.login()
        print("[Sesión iniciada: {}]".format(datetime.now().strftime("%I:%M:%S %p")))
        print(
            "Tiempo restante: {}".format(
                utils.val_or_error(lambda: client.remaining_time)
            )
        )
    else:
        with client.login():
            login_time = int(time.time())
            if not args.no_log:
                save_login(client.user)
            print(
                "[Sesión iniciada: {}]".format(datetime.now().strftime("%I:%M:%S %p"))
            )
            print(
                "Tiempo restante: {}".format(
                    utils.val_or_error(lambda: client.remaining_time)
                )
            )
            print(
                "Presione Ctrl+C para desconectarse, o ejecute '{} down' desde otro terminal".format(
                    prog_name
                )
            )
            if args.session_time:
                if args.session_time.lower().endswith("h"):
                    args.session_time = int(args.session_time[:-1]) * 3600
                elif args.session_time.lower().endswith("m"):
                    args.session_time = int(args.session_time[:-1]) * 60
                else:
                    args.session_time = int(args.session_time)
            try:
                while True:
                    if not client.is_logged_in:
                        break

                    elapsed = int(time.time()) - login_time

                    print(
                        "\rTiempo de conexión: {}".format(
                            utils.seconds2strtime(elapsed)
                        ),
                        end="",
                    )

                    if args.session_time:
                        if args.session_time < elapsed:
                            break

                        print(
                            " La sesión se cerrará en {}".format(
                                utils.seconds2strtime(args.session_time - elapsed)
                            ),
                            end="",
                        )

                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                print("\n\nCerrando sesión ...")
                # Voy a chequear si tengo openvpn ejecutando antes del logout
                if NautaProtocol.check_if_process_running("openvpn"):
                    print("Está ejecutando openvpn, voy a cerrarlo")
                    subprocess.run(("sudo", "kill_openvpn.sh"))
                print(
                    "Tiempo restante: {}".format(
                        utils.val_or_error(lambda: client.remaining_time)
                    )
                )

        print(
            "Sesión cerrada con éxito: {}".format(
                datetime.now().strftime("%I:%M:%S %p")
            )
        )
        # print("Crédito: {}".format(
        #    utils.val_or_error(lambda: client.user_credit)
        # ))


def down(args):
    client = NautaClient(user=None, password=None)

    if client.is_logged_in:
        client.load_last_session()
        client.user = client.session.__dict__.get("username")
        client.logout()
        if not args.no_log:
            save_logout(client.user)
        print("Sesión cerrada con éxito")
    else:
        print("No hay ninguna sesión activa")


def is_logged_in(args):
    client = NautaClient(user=None, password=None)

    print("Sesión activa: {}".format("Sí" if client.is_logged_in else "No"))


def is_online(args):
    print("Online: {}".format("Sí" if NautaProtocol.is_connected() else "No"))


def info(args):
    user, password = _get_credentials(args)
    client = NautaClient(user, password)

    if client.is_logged_in:
        client.load_last_session()

    print("Usuario Nauta: {}".format(user))
    print(
        "Tiempo restante: {}".format(utils.val_or_error(lambda: client.remaining_time))
    )
    # print("Crédito: {}".format(
    #    utils.val_or_error(lambda: client.user_credit)
    # ))


def run_connected(args):
    user, password = _get_credentials(args)
    client = NautaClient(user, password)

    with client.login():
        os.system(" ".join(args.cmd))


def create_user_subparsers(subparsers):
    users_parser = subparsers.add_parser("users")
    user_subparsers = users_parser.add_subparsers()

    # Add user
    user_add_parser = user_subparsers.add_parser("add")
    user_add_parser.set_defaults(func=add_user)
    user_add_parser.add_argument("user", help="Usuario Nauta")
    user_add_parser.add_argument(
        "password", nargs="?", help="Password del usuario Nauta"
    )

    # Set default user
    user_set_default_parser = user_subparsers.add_parser("set-default")
    user_set_default_parser.set_defaults(func=set_default_user)
    user_set_default_parser.add_argument("user", help="Usuario Nauta")

    # Set user password
    user_set_password_parser = user_subparsers.add_parser("set-password")
    user_set_password_parser.set_defaults(func=set_password)
    user_set_password_parser.add_argument("user", help="Usuario Nauta")
    user_set_password_parser.add_argument(
        "password", nargs="?", help="Password del usuario Nauta"
    )

    # Remove user
    user_remove_parser = user_subparsers.add_parser("remove")
    user_remove_parser.set_defaults(func=remove_user)
    user_remove_parser.add_argument("user", help="Usuario Nauta")

    user_list_parser = user_subparsers.add_parser("list")
    user_list_parser.set_defaults(func=list_users)


def list_connections_cli(args):
    # Obtener las conexiones desde sqlite_utils
    connections = list_connections(args)

    # Asegurarse de que connections no sea None
    if connections is None or len(connections) == 0:
        print("No se encontraron conexiones.")
        return

    # Encabezados de la tabla
    headers = ["Usuario", "Fecha inicio sesión", "Fecha cierre sesión"]

    # Convertir las conexiones a listas para construir la tabla,
    # y eliminar los milisegundos de las fechas
    rows = [
        [
            connection[0],  # Usuario
            connection[1].split(".")[0] if connection[1] else "N/A",  # Fecha inicio sin milisegundos
            connection[2].split(".")[0] if connection[2] else "N/A"  # Fecha cierre sin milisegundos
        ]
        for connection in connections
    ]

    # Calcular los anchos de cada columna
    col_widths = [
        max(len(str(row[i])) for row in rows + [headers])  # ancho máximo de cada columna
        for i in range(len(headers))
    ]

    # Función para formatear una fila
    def format_row(row):
        return "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row))) + " |"

    # Separador
    separator = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
    # Crear la tabla
    table = [format_row(headers), separator]

    # Agregar las filas con los datos
    for row in rows:
        table.append(format_row(row))
        table.append(separator)

    # Mostrar la tabla
    print("\n".join(table))
    # Si se pide el resumen, se muestra al final de la tabla
    if args.resume_connections:
        resume_connections(args)


def resume_connections(args):
    # Obtener las conexiones desde sqlite_utils
    connections = list_connections(args)

    # Asegurarse de que connections no sea None
    if connections is None or len(connections) == 0:
        print("No se encontraron conexiones.")
        return

    # Diccionario para acumular las horas por usuario y mes
    user_hours_per_month = defaultdict(lambda: defaultdict(float))

    # Procesar cada conexión
    for connection in connections:
        user = connection[0]
        fecha_inicio = connection[1]
        fecha_cierre = connection[2]

        # Ignorar si no hay fecha de cierre o si está vacío
        if not fecha_cierre or fecha_cierre.strip() == '':
            continue

        try:
            # Convertir las fechas a objetos datetime
            inicio_dt = datetime.strptime(fecha_inicio.split(".")[0], "%Y-%m-%d %H:%M:%S")
            cierre_dt = datetime.strptime(fecha_cierre.split(".")[0], "%Y-%m-%d %H:%M:%S")

            # Calcular la duración de la conexión en horas
            duration = (cierre_dt - inicio_dt).total_seconds() / 3600.0

            # Obtener el nombre del mes y año de la fecha de inicio en español
            mes_anio = inicio_dt.strftime("%B %Y")

            # Acumular la duración en horas para el usuario y mes correspondiente
            user_hours_per_month[user][mes_anio] += duration

        except ValueError as e:
            print(f"Error al procesar las fechas para la conexión de {user}: {e}")
            continue

    # Mostrar el resumen de horas por usuario y mes
    if not user_hours_per_month:
        print("No se encontraron conexiones válidas.")
    else:
        # Cabecera de la tabla
        headers = ["Usuario", "Mes", "Cantidad de horas"]

        rows = []
        for user, hours_per_month in user_hours_per_month.items():
            for mes_anio, horas in sorted(hours_per_month.items()):
                horas_int = int(horas)
                minutos = int((horas - horas_int) * 60)
                if horas_int == 0:
                    horas_str = f"{minutos} minutos"
                elif minutos == 0:
                    horas_str = f"{horas_int} horas"
                else:
                    horas_str = f"{horas_int} hora{'s' if horas_int > 1 else ''} {minutos} minuto{'s' if minutos > 1 else ''}"
                rows.append([user, mes_anio.capitalize(), horas_str])

        col_widths = [
            max(len(str(row[i])) for row in rows + [headers])
            for i in range(len(headers))
        ]

        def format_row(row):
            return "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row))) + " |"

        table = [format_row(headers)]
        separator = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
        table.append(separator)

        for row in rows:
            table.append(format_row(row))
            table.append(separator)

        print("\n".join(table))


def main():
    parser = argparse.ArgumentParser(prog=prog_name)
    parser.add_argument(
        "--version", action="version", version="{} v{}".format(prog_name, version)
    )
    parser.add_argument("-d", "--debug", action="store_true", help="show debug info")
    # listar las conexiones de todos los usuarios
    parser.add_argument(
        "-lc",
        "--list-connections",
        action="store_true",
        default=False,
        help="Lista todas las conexiones de los usuarios")
    # Resumen mensual de las conexiones por usuario
    parser.add_argument(
        "-rc",
        "--resume-connections",
        action="store_true",
        default=False,
        help="Hace un resumen mensual de todas las conexiones, por usuario",
    )

    subparsers = parser.add_subparsers()

    # Create user subparsers in another function
    create_user_subparsers(subparsers)

    # loggin parser
    up_parser = subparsers.add_parser("up")
    up_parser.set_defaults(func=up)
    up_parser.add_argument(
        "-t",
        "--session-time",
        action="store",
        default=None,
        type=str,
        help="Tiempo de desconexión en segundos por defecto, se pueden usar modificadores 'h' y 'm' para horas y minutos, por ejemplo: '1h' o '10m'",
    )
    up_parser.add_argument(
        "-b",
        "--batch",
        action="store_true",
        default=False,
        help="Ejecutar en modo no interactivo",
    )
    up_parser.add_argument("user", nargs="?", help="Usuario Nauta")
    up_parser.add_argument("password", nargs="?", help="Password del usuario Nauta")
    up_parser.add_argument(
        "-nl",
        "--no-log",
        action="store_true",
        default=False,
        help="No salvar en la BD el log de esta conexión",
    )

    # Logout parser
    down_parser = subparsers.add_parser("down")
    down_parser.set_defaults(func=down)

    # Is logged in parser
    is_logged_in_parser = subparsers.add_parser("is-logged-in")
    is_logged_in_parser.set_defaults(func=is_logged_in)

    # Is online parser
    is_online_parser = subparsers.add_parser("is-online")
    is_online_parser.set_defaults(func=is_online)

    # User information parser
    info_parser = subparsers.add_parser("info")
    info_parser.set_defaults(func=info)
    info_parser.add_argument("user", nargs="?", help="Usuario Nauta")
    info_parser.add_argument("password", nargs="?", help="Password del usuario Nauta")

    # Run connected parser
    run_connected_parser = subparsers.add_parser("run-connected")
    run_connected_parser.set_defaults(func=run_connected)
    run_connected_parser.add_argument(
        "-u", "--user", required=False, help="Usuario Nauta"
    )
    run_connected_parser.add_argument(
        "-p", "--password", required=False, help="Password del usuario Nauta"
    )
    run_connected_parser.add_argument(
        "cmd", nargs=argparse.REMAINDER, help="The command line to run"
    )

    args = parser.parse_args()

    # Muestra las conexiones de los usuarios en la BD
    if args.list_connections:
        list_connections_cli(args)
        sys.exit(0)

    # Muestra un resumen mensual de las conexiones
    if args.resume_connections:
        resume_connections(args)
        sys.exit(0)

    if "func" not in args:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except NautaException as ex:
        print(ex.args[0], file=sys.stderr)
    except RequestException as ex:
        print("Hubo un problema en la red, por favor revise su conexión:", ex, file=sys.stderr)
