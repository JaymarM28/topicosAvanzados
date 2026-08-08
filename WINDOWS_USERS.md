# Guía de Configuración: Entorno de Trabajo para Usuarios Windows

¡Bienvenidos al módulo de Tendencias Emergentes en Desarrollo de Software! 

Para garantizar que todos los comandos, scripts y herramientas de DataOps funcionen perfectamente y sin errores durante nuestras sesiones prácticas, estandarizaremos nuestra terminal de comandos. Si utilizas Windows, **es un requisito obligatorio utilizar Git Bash** como tu terminal por defecto dentro de Visual Studio Code.

Sigue estos sencillos pasos antes de nuestra primera clase para dejar tu entorno listo.

### Paso 1: Instalar Git (y Git Bash)
Si no tienes Git instalado en tu computador, este paquete instalará tanto el control de versiones como la terminal que necesitamos.

1. Ve a la página oficial de descargas de Git para Windows: [gitforwindows.org](https://gitforwindows.org/)
2. Haz clic en el botón **Download**.
3. Ejecuta el instalador que acabas de descargar. 
4. Puedes hacer clic en **Next** (Siguiente) en todas las pantallas dejando las opciones que vienen marcadas por defecto. La instalación estándar es perfecta para nuestro curso.

### Paso 2: Instalar Visual Studio Code (VS Code)
Si aún no tienes VS Code, instálalo, ya que será nuestro editor de código principal.

1. Ve a [code.visualstudio.com](https://code.visualstudio.com/) y descarga la versión para Windows.
2. Ejecuta el instalador y sigue los pasos con las opciones por defecto.

### Paso 3: Configurar Git Bash como Terminal por Defecto en VS Code
Ahora le diremos a VS Code que deje de usar PowerShell o CMD y utilice Git Bash cada vez que abramos una terminal.

1. Abre **Visual Studio Code**.
2. Presiona la combinación de teclas: `Ctrl` + `Shift` + `P` (Esto abrirá la paleta de comandos en la parte superior central de la pantalla).
3. Escribe la palabra **Terminal** y busca en la lista la opción que dice: **Terminal: Select Default Profile** (Terminal: Seleccionar perfil predeterminado) y haz clic en ella.
4. Aparecerá una lista con los perfiles disponibles (PowerShell, Command Prompt, etc.). Haz clic en **Git Bash**.

### Paso 4: Validar la Configuración
Asegurémonos de que todo quedó funcionando correctamente.

1. En VS Code, abre una nueva terminal presionando `Ctrl` + `ñ` (o yendo al menú superior: *Terminal* -> *New Terminal*).
2. Observa la ventana de la terminal que se abre en la parte inferior. Deberías ver las letras de colores y, lo más importante, el símbolo de dólar (`$`) al final de la línea donde escribes. 
3. Escribe el siguiente comando y presiona Enter:
   `git --version`
4. Si la terminal te responde con la versión de Git (por ejemplo, `git version 2.41.0.windows.1`), ¡felicidades! Tu entorno está listo.

**Nota importante:** Durante todo el curso, cuando en las presentaciones y guías veamos un comando que empieza con `$`, significa que debes escribirlo en esta terminal Git Bash. Nunca copies el símbolo `$`, solo el texto que va después.