**Gestor Avanzado de Punteros - Advanced Pointer Manager**

Herramienta en *Python con interfaz GUI*, ideal para *mods, traducciones y edición de binarios*. Permite gestionar punteros (intercambiar) y editar strings de forma visual y segura.

Este es un proyecto *Open Source* desarrollado con asistencia de IA *(Gemini de Google)*.

✨ Características Principales

- *Interfaz agradable e intuitiva:* Diseñada para ser fácil de usar, incluso en proyectos grandes.
- *Filtros de búsqueda avanzados:* Encuentra strings y punteros rápidamente.
- *Botones de navegación:* Flujo de trabajo ágil y sin complicaciones.
- *Flujo de trabajo completo:* Cambia, intercambia punteros y edita strings directamente desde la GUI.
- *Sistema de restauración seguro:* Capacidad de restaurar strings y punteros originales. Todos los cambios se guardan en un archivo `JSON` para tener un respaldo total.
- *Tabla de remapeo de caracteres:* Soporte para abrir una tabla `.txt` para el remapeo de caracteres especiales (ideal para traducciones).

⚠️ Limitaciones

> *IMPORTANTE:* Esta herramienta *NO recalcula ni crea punteros nuevos*. Solo trabaja con los punteros ya existentes dentro del Binario. Es una herramienta de reasignación, no de inyección.
> No funciona con strings con codificación UTF-16

🚀 Cómo Usar

1. Preparar el archivo TXT descriptor

Necesitas un archivo `.txt` con el *mismo nombre que el binario* (ej: si tu binario es `game.exe`, el txt debe ser `game.txt`).

Cada línea debe contener estos datos y estar separada por una *tabulación (sangría)*:


`offset_del_string` | `longitud_en_decimal` | `puntero(s)_hex_LE_o_BE` | `string`

Los endianes de los punteros es según como los tenga el binario.
Puedes obtener esta información usando programas como *IDA Pro o Ghidra*.

*Ejemplo de 2 líneas:*
```
0001A4B0	8	00FF1234	String_1
0001A4D0	8	00FF1280	String_2
```

2. Preparar la tabla de caracteres (Opcional-Requiere editar la fuente por aparte)

Crea un archivo `.txt` para el remapeo. 

*Ejemplo:*
```

á=#
é=+
í="
ó=*
ú=/

```
3. Flujo de trabajo en el programa

-  Abre el Binario con el botón *"Abrir archivo"*. El programa cargará automáticamente el `.txt` si está en la misma carpeta.
-  El programa se compone de *dos secciones*:
    - *Sección 1:* Punteros de ORIGEN
    - *Sección 2:* Punteros de DESTINO
-  Para cambiar un puntero, selecciona una línea diferente en cada sección y usa el botón *"Aplicar cambios"* para cambiar el puntero de la sección 1 por el de la sección 2.
-  Para *editar un string*, configura la misma línea en ambas secciones y edita el texto.
-  Usa los botones *"REVERTIR PTR"* y *"REVERTIR STRING"* para restaurar los valores originales.
-  Cuando se cambia un puntero, la información original se mostrará en el label *"Información de offsets de punteros"* (esquina inferior izquierda).
-  Usa la casilla *"manual"* en el label "flujo automático de punteros" para especificar un puntero manualmente.
-  Usa el botón *"INVERTIR PTR"* para intercambiar los punteros de dos líneas de strings.
-  Usa el botón *"Abrir Tabla"* para cargar tu archivo de remapeo de caracteres.

🐛 Bugs Conocidos

Al cambiar más de dos punteros hacia un mismo string y tratar de restaurar, el programa se confunde y la información se pierde en el JSON, provocando que no se puedan restaurar todos los punteros correctamente.



## Cambios de la versión 4.4

Mejoras enfocadas en el flujo de trabajo para que editar punteros y strings sea más rápido, más claro y con menos pasos.

### ✏️ Edición de punteros y strings separada

- 🔘 El botón **APLICAR CAMBIOS** se cambió por **CAMBIAR PTR**. Esto separa por completo la edición de punteros de la edición de strings, para que no se confundan las dos acciones.

### 📝 Edición de strings más simple

- ✅ Ya **no es necesario sincronizar la misma línea en ambas secciones** para editar un string. Ahora solo seleccionas la línea en la **Sección 2** y lo editas con el botón **EDITAR STRING**.
- ✅ Ahora tiene soporte para caracteres Latinos.
- 🔁 Si editas un string, **ya no es necesario revertir el string original** para volver a editarlo. Puedes editarlo de nuevo directamente.
- 👉 Se implementó el botón **Expandir** para editar los strings en un cuadro de texto mas grande con soporte para saltos de línea.
- 🧩 Se implementó la **escritura sobre padding**, que permite aprovechar los bytes de relleno al final de un string y así sumar longitud. ⚠️ **Úsalo con cuidado:** esta opción puede generar conflictos en algunos binarios.

### 📂 Cerrar archivos abiertos

- ❌ Ahora se permite **cerrar un binario o una tabla abierta** sin tener que cerrar el programa.

### 🛠️ Nuevo botón HERRAMIENTAS

Se implementó el botón **HERRAMIENTAS**, que permite ejecutar:

#### 1. Programa para crear / editar tablas

- 🔤 Sirve para crear tablas o editar tablas para **remapeo de caracteres**.
- ⌨️ Forma de uso: pon los pares de caracteres en la barra de **"Ingrese caracteres seguidos"** y automáticamente se organiza la información.

#### 2. Programa para generar el txt descriptor

- 📄 Sirve para generar el **txt descriptor**.

**Modo IDA:**
- ☑️ Selecciona el checkbox **IDA** para cargar un txt con la información de strings del desensamblador **IDA**, usando el botón **Seleccionar**.
- 📐 Especifica el valor para el **offset relativo**. 💡 *Truco para obtener ese valor: resta un puntero con un offset.*

**Modo Manual:**
- ☑️ Selecciona el checkbox **Manual**.
- 📐 Usando un **offset de inicio** y un **offset final**, más un valor para calcular los punteros, puedes extraer bloques de cadenas de cualquier **Binario**, que también se selecciona con el botón **Seleccionar** (sólo funciona con strings en utf-8).



🙏 Créditos y Agradecimientos

- *Diseño y Desarrollo:* ZARF
- *Programación:* Gemini AI (Google)
- *Agradecimiento especial:* A **Sora Leon** por la idea de la tabla de remapeo de caracteres.
