# NautaPy

__NautaPy__ Python API para el portal cautivo [Nauta](https://secure.etecsa.net:8443/) de Cuba + CLI.

![Screenshot](screenshots/console-screenshot.png?raw=true)

## Requisitos

1. Instale la última versión estable de [Python3](https://www.python.org/downloads/)

## Instalación

Instalación:

```bash
pip3 install --upgrade git+https://github.com/plinkr/nautapy.git
```
Alternativamente usando `python-pipx` (Recomendado):
```bash
pipx install git+https://github.com/plinkr/nautapy.git
```

## Modo de uso

#### Agrega un usuario

```bash
nauta users add periquito@nauta.com.cu
```

Introducir la contraseña cuando se pida. Cambie `periquito@nauta.com.cu` por 
su usuario Nauta.

#### Iniciar sesión:

__Especificando el usuario__

```bash
nauta up periquito
```

Se muestra el tiempo en el terminal, para cerrar la sesión se debe pulsar `Ctrl+C`.

* Opcionalmente puede especificar la duración máxima para la sesión, luego de la cual se desconecta automáticamente:
    
    El siguiente ejemplo mantiene abierta la sesión durante un minuto (la unidad de tiempo por defecto son segundos):
    ```bash
    nauta up --session-time 60 periquito
    ```
    
    También puede especificar el tiempo en horas (h) o minutos (m) para el tiempo de conexión:
    ```bash
    nauta up -t 1h
    ```
    
    Y en minutos:
    ```bash
    nauta up -t 30m
    ```

__Sin especificar el usuario__

```bash
nauta up
```
Se utiliza el usuario predeterminado o el primero que se encuentre en la base de datos.


#### Ejecutar un comando con conexión

```bash
run-connected <cmd>
```
Ejecuta la tarea especificada con conexión, la conexión se cierra al finalizar la tarea.


#### Consultar información del usuario

```bash
nauta info periquito
```

__Salida__:

```text
Usuario Nauta: periquito@nauta.com.cu
Tiempo restante: 02:14:24
Crédito: 1.12 CUC
```

#### Determinar si hay conexión a internet

```bash
nauta is-online
```

__Salida__:
```text
Online: No
```

#### Determinar si hay una sesión abierta

```bash
nauta is-logged-in
```

__Salida__:
```text
Sesión activa: No
```
    
## Opciones adicionales

### `--list-conn`, `-lc` 

Muestra una lista de las conexiones del mes actual de todos los usuarios almacenadas en la base de datos.

```bash
nauta --list-conn
```

**Opciones de filtrado:**

* **`--last-month`, `-lm`, :** Muestra solo las conexiones del mes anterior.
* **`--all-conn`, `-ac`:** Muestra todas las conexiones, sin importar el mes.

```bash
# Mostrar conexiones del mes anterior:
nauta --list-conn --last-month

# Mostrar todas las conexiones:
nauta --list-conn --all-conn
```

### `--resume-conn`, `-rc`

Genera un resumen mensual de todas las conexiones, agrupadas por usuario, mostrando la cantidad total de horas conectadas en cada mes.

```bash
nauta --resume-conn
```

### Combinando opciones

Puedes combinar las opciones para obtener resultados más específicos. Por ejemplo:

```bash
# Mostrar un resumen mensual y todas las conexiones
nauta -rc -lc -ac
```

```bash
# Mostrar las conexiones del mes pasado
nauta -lc -lm
```

**Nota:** Las opciones `--last-month` y `--all-conn` solo afectan al comando `--list-conn`.

**Explicación detallada:**

* **`--last-month`:** Esta opción permite filtrar las conexiones y mostrar solo aquellas que ocurrieron en el mes anterior.
* **`--all-conn`:** Con esta opción, se mostrarán todas las conexiones almacenadas en la base de datos, sin aplicar ningún filtro por fecha.

**Ejemplo de uso completo:**

```bash
nauta --list-conn --last-month --resume-conn
```

Este comando mostrará:

1. Una lista de todas las conexiones del mes anterior.
2. Un resumen mensual de todas las conexiones.

**Consideraciones adicionales:**

* **Orden de las opciones:** El orden de las opciones no suele importar.
* **Opciones mutuamente excluyentes:** En este caso, no hay opciones mutuamente excluyentes. Puedes combinarlas como quieras.

### `--no-log`, `-nl`

Evita que se registre la conexión actual en la base de datos:

```bash
nauta up -t 2h --no-log
```
de la misma manera usando opciones cortas:
```bash
nauta up -t 2h -nl
```

# Más Información

Lee la ayuda del módulo una vez instalado:

```bash
nauta --help
```

## Contribuir
__IMPORTANTE__: Notifícame por Twitter (enviar DM) sobre cualquier actividad en el proyecto (Issue o PR).

Todas las contribuciones son bienvenidas. Puedes ayudar trabajando en uno de los issues existentes. 
Clona el repo, crea una rama para el issue que estés trabajando y cuando estés listo crea un Pull Request.

También puedes contribuir difundiendo esta herramienta entre tus amigos y en tus redes. Mientras
más grande sea la comunidad más sólido será el proyecto. 

Si te gusta el proyecto dale una estrella para que otros lo encuentren más fácilmente.

### Contacto del autor 

- Twitter: [@atscub](https://twitter.com/atscub)


### Compartir
- [Twitter](https://twitter.com/intent/tweet?url=https%3A%2F%2Fgithub.com%2Fatscub%2Fnautapy%2F&text=Python%20API%20para%20el%20portal%20cautivo%20Nauta%20de%20Cuba%20%2B%20CLI)
