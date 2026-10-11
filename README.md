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

🚀 Cómo Usar

1. Preparar el archivo TXT descriptor

Necesitas un archivo `.txt` con el *mismo nombre que el binario* (ej: si tu binario es `game.exe`, el txt debe ser `game.txt`).

Cada línea debe contener, separada por una *tabulación (sangría)*:
`offset_del_string` | `longitud_en_decimal` | `puntero(s)_hex_LE_o_BE` | `string`

Los endianes de los punteros es según como los tenga el binario.
Puedes obtener esta información usando programas como *IDA Pro o Ghidra*.

*Ejemplo de 2 líneas:*
0001A4B0	22	00FF1234	String_1
0001A4D0	18	00FF1280	String_2

2. Preparar la tabla de caracteres (Opcional)

Crea un archivo `.txt` para el remapeo. 

*Ejemplo:*

á=#
é=+
í="
ó=*
ú=/

3. Flujo de trabajo en el programa

1.  Abre el Binario con el botón *"Abrir archivo"*. El programa cargará automáticamente el `.txt` si está en la misma carpeta.
2.  El programa se compone de *dos secciones*:
    - *Sección 1:* Punteros de ORIGEN
    - *Sección 2:* Punteros de DESTINO
3.  Para cambiar un puntero, selecciona una línea diferente en cada sección y usa el botón *"Aplicar cambios"* para cambiar el puntero de la sección 1 por el de la sección 2.
4.  Para *editar un string*, configura la misma línea en ambas secciones y edita el texto.
5.  Usa los botones *"REVERTIR PTR"* y *"REVERTIR STRING"* para restaurar los valores originales.
6.  Cuando se cambia un puntero, la información original se mostrará en el label *"Información de offsets de punteros"* (esquina inferior izquierda).
7.  Usa la casilla *"manual"* en el label "flujo automático de punteros" para especificar un puntero manualmente.
8.  Usa el botón *"INVERTIR PTR"* para intercambiar los punteros de dos líneas de strings.
9.  Usa el botón *"Abrir Tabla"* para cargar tu archivo de remapeo de caracteres.

🐛 Bugs Conocidos

Al cambiar más de dos punteros hacia un mismo string y tratar de restaurar, el programa se confunde y la información se pierde en el JSON, provocando que no se puedan restaurar todos los punteros correctamente.

🙏 Créditos y Agradecimientos

- *Diseño y Desarrollo:* ZARF
- *Programación:* Gemini AI (Google)
- *Agradecimiento especial:* A **Sora Leon** por la idea de la tabla de remapeo de caracteres.
