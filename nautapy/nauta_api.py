"""
API for interacting with Nauta Captive Portal

Example:
    nauta_client = NautaClient("pepe@nauta.com.cu", "pepepass")
    try:
        with nauta_client.login():
            # We are connected

        # We are disconnected now
    except NautaLoginException as ex:
        # Handle exception here
        # Clean session (logout)
    except NautaLogoutException as ex:
        # Handle exception here
        # Clean session (logout)
    except NautaException as ex:
        # Handle exception here
        # Clean session (logout)

"""

import http.cookiejar as cookielib
import json
import os
import re
import subprocess
import time

import bs4
import psutil
import requests
from requests import RequestException

from nautapy import appdata_path
from nautapy.__about__ import __name__ as prog_name
from nautapy.exceptions import (
    NautaLoginException,
    NautaLogoutException,
    NautaException,
    NautaPreLoginException,
)
from nautapy.sqlite_utils import save_logout

MAX_DISCONNECT_ATTEMPTS = 10

CHECK_PAGE = "http://www.cubadebate.cu/"

LOGIN_DOMAIN = b"secure.etecsa.net"
# _re_login_fail_reason = re.compile("alert\(\"(?P<reason>[^\"]*?)\"\)")

NAUTA_SESSION_FILE = os.path.join(appdata_path, "nauta-session")


class SessionObject(object):
    def __init__(
            self, login_action=None, csrfhw=None, wlanuserip=None, attribute_uuid=None
    ):
        self.requests_session = self.__class__._create_requests_session()

        self.login_action = login_action
        self.csrfhw = csrfhw
        self.wlanuserip = wlanuserip
        self.attribute_uuid = attribute_uuid

    @classmethod
    def _create_requests_session(cls):
        requests_session = requests.Session()
        requests_session.cookies = cookielib.MozillaCookieJar(NAUTA_SESSION_FILE)
        return requests_session

    def save(self, username=None):
        self.requests_session.cookies.save()

        data = {**self.__dict__}
        data.pop("requests_session")
        data["username"] = username

        with open(NAUTA_SESSION_FILE, "w") as fp:
            json.dump(data, fp)

    @classmethod
    def load(cls):
        inst = object.__new__(cls)
        inst.requests_session = cls._create_requests_session()

        with open(NAUTA_SESSION_FILE, "r") as fp:
            inst.__dict__.update(json.load(fp))

        return inst

    def dispose(self):
        self.requests_session.cookies.clear()
        self.requests_session.cookies.save()
        try:
            os.remove(NAUTA_SESSION_FILE)
        except:
            pass

    @classmethod
    def is_logged_in(cls):
        return os.path.exists(NAUTA_SESSION_FILE)


class NautaProtocol(object):
    """Protocol Layer (Interface)

    Abstracts the details of dealing with nauta server
    This is the lower layer of the application. API client must
    use this instead of directly talk with nauta server

    """

    @classmethod
    def _get_inputs(cls, form_soup):
        return {
            _["name"]: _.get("value", default=None)
            for _ in form_soup.select("input[name]")
        }

    @classmethod
    def is_connected(cls):
        try:
            r = requests.get(CHECK_PAGE, timeout=3)
            return LOGIN_DOMAIN not in r.content
        except (requests.ConnectionError, requests.Timeout) as exception:
            return False
        # return LOGIN_DOMAIN not in r.content

    @classmethod
    def create_session(cls):
        if cls.is_connected():
            if SessionObject.is_logged_in():
                raise NautaPreLoginException("Hay una sessión abierta")
            else:
                raise NautaPreLoginException("Hay una conexión activa")

        session = SessionObject()
        # resp = session.requests_session.get(CHECK_PAGE, allow_redirects=True)
        resp = session.requests_session.get("https://secure.etecsa.net:8443")
        if not resp.ok:
            raise NautaPreLoginException("Failed to create session")

        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        # action = soup.form["action"]
        action = "https://secure.etecsa.net:8443"
        data = cls._get_inputs(soup)

        # Now go to the login page
        resp = session.requests_session.post(action, data)
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        form_soup = soup.find("form", id="formulario")

        session.login_action = form_soup["action"]
        data = cls._get_inputs(form_soup)

        session.csrfhw = data["CSRFHW"]
        session.wlanuserip = data["wlanuserip"]

        return session

    @classmethod
    def login(cls, session, username, password):
        r = session.requests_session.post(
            session.login_action,
            {
                "CSRFHW": session.csrfhw,
                "wlanuserip": session.wlanuserip,
                "username": username,
                "password": password,
            },
        )

        if not r.ok:
            raise NautaLoginException(
                "Falló el inicio de sesión: {} - {}".format(r.status_code, r.reason)
            )

        if not "online.do" in r.url:
            soup = bs4.BeautifulSoup(r.text, "html.parser")
            script_text = soup.find_all("script")[-1].get_text()
            # match = _re_login_fail_reason.match(script_text)
            match = re.search(r"alert\(\"(?P<reason>[^\"]*?)\"\)", script_text)
            raise NautaLoginException(
                "Falló el inicio de sesión: {}".format(
                    match and match.groupdict().get("reason")
                )
            )

        m = re.search(r"ATTRIBUTE_UUID=(\w+)&CSRFHW=", r.text)

        return m.group(1) if m else None

    @classmethod
    def logout(cls, session, username):
        logout_url = (
                "https://secure.etecsa.net:8443/LogoutServlet?"
                + "CSRFHW={}&"
                + "username={}&"
                + "ATTRIBUTE_UUID={}&"
                + "wlanuserip={}"
        ).format(session.csrfhw, username, session.attribute_uuid, session.wlanuserip)
        response = session.requests_session.post(logout_url)
        cls._handle_logout_errors(response, username)

    @staticmethod
    def _handle_logout_errors(response, username):
        """
        Si hay errores en el logout, los trato aquí

        Args:
            response (requests.Response): La respuesta de la petición de cierre de sesión.
            username: El usuario al que se está cerrando sesión.
        """
        error_message = None

        try:
            if not response.ok:
                error_message = "Fallo al cerrar la sesión: {} - {}".format(
                    response.status_code, response.reason
                )

            if "SUCCESS" not in response.text.upper():
                error_message = "Fallo al cerrar la sesión: {}".format(response.text[:100])

            if error_message:
                raise NautaLogoutException(error_message)

        finally:
            # Guardo en la BD el usuario y la hora de cierre de sesión
            # Cierra la entrada en la BD aunque hayan errores
            save_logout(username)

    @classmethod
    def get_user_time(cls, session, username):

        r = session.requests_session.post(
            "https://secure.etecsa.net:8443/EtecsaQueryServlet",
            {
                "op": "getLeftTime",
                "ATTRIBUTE_UUID": session.attribute_uuid,
                "CSRFHW": session.csrfhw,
                "wlanuserip": session.wlanuserip,
                "username": username,
            },
        )

        return r.text

    @classmethod
    def get_user_credit(cls, session, username, password):

        r = session.requests_session.post(
            "https://secure.etecsa.net:8443/EtecsaQueryServlet",
            {
                "CSRFHW": session.csrfhw,
                "wlanuserip": session.wlanuserip,
                "username": username,
                "password": password,
            },
        )

        if not r.ok:
            raise NautaException(
                "Fallo al obtener la información del usuario: {} - {}".format(
                    r.status_code, r.reason
                )
            )

        if "secure.etecsa.net" not in r.url:
            raise NautaException(
                "No se puede obtener el crédito del usuario mientras está online"
            )

        soup = bs4.BeautifulSoup(r.text, "html.parser")
        credit_tag = soup.select_one(
            "#sessioninfo > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(2)"
        )

        if not credit_tag:
            raise NautaException(
                "Fallo al obtener el crédito del usuario: no se encontró la información"
            )

        return credit_tag.get_text().strip()

    @classmethod
    def check_if_process_running(cls, process_name):
        """
        Chequea si existe algun proceso con el nombre processName.
        """
        # Iterar la lista de todos los procesos
        for proc in psutil.process_iter():
            try:
                # Chequea si el nombre del proceso contiene la cadena a buscar
                if process_name.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False


class NautaClient(object):
    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.session = None

    def init_session(self):
        self.session = NautaProtocol.create_session()
        self.session.save()

    @property
    def is_logged_in(self):
        return SessionObject.is_logged_in()

    def login(self):
        if not self.session:
            self.init_session()

        self.session.attribute_uuid = NautaProtocol.login(
            self.session, self.user, self.password
        )

        self.session.save(self.user)

        return self

    @property
    def user_credit(self):
        dispose_session = False
        try:
            if not self.session:
                dispose_session = True
                self.init_session()

            return NautaProtocol.get_user_credit(
                session=self.session, username=self.user, password=self.password
            )
        finally:
            if self.session and dispose_session:
                self.session.dispose()
                self.session = None

    @property
    def remaining_time(self):
        dispose_session = False
        try:
            if not self.session:
                dispose_session = True
                self.session = SessionObject()

            return NautaProtocol.get_user_time(
                session=self.session,
                username=self.user,
            )
        finally:
            if self.session and dispose_session:
                self.session.dispose()
                self.session = None

    def logout(self):
        try:
            for _ in range(0, MAX_DISCONNECT_ATTEMPTS):
                try:
                    # Voy a chequear si tengo openvpn ejecutando antes del logout
                    if NautaProtocol.check_if_process_running("openvpn"):
                        print("Está ejecutando openvpn, voy a cerrarlo")
                        subprocess.run(("sudo", "kill_openvpn.sh"))

                    NautaProtocol.logout(
                        session=self.session,
                        username=self.user
                    )
                    self.session.dispose()
                    self.session = None

                    return  # Si el logout es exitoso, se sale del método
                except RequestException as e:
                    print("Error al intentar cerrar la sesión:", e)
                    print("Esperando 10 segundos antes de volver a intentar...")
                    time.sleep(10)
            else:
                raise NautaLogoutException(
                    "Hay problemas en la red y no se puede cerrar la sesión.\n"
                    "Es posible que ya esté desconectado. Intente con '{} down' "
                    "dentro de unos minutos".format(prog_name)
                )
        finally:
            # Guardo en la BD el usuario y la hora de cierre de sesión
            # Cierra la entrada en la BD sin importar si hubo excepciones o no
            save_logout(self.user)

    def load_last_session(self):
        self.session = SessionObject.load()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if SessionObject.is_logged_in():
            self.logout()
