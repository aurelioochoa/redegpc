# Resident Evil Degeneration PC Port

[English](#english) · [Español](#español)

## English

![Resident Evil Degeneration — Leon and Claire at the airport](docs/media/banner.png)

Play the English iPhone release of **Resident Evil Degeneration** on Linux with keyboard and mouse controls, a native desktop launcher, and local saves. `redegpc` is a Rust compatibility host based on touchHLE revision `ca1de89c578e79746f33c1332e28efd106c334ba`.

**Bring your own game:** the supported release is the unencrypted **English iPhone v1.03.00 IPA**. The project does not include game files. This is an experimental preservation project; full playable compatibility has not been established.

[Gameplay](#gameplay) · [Quick start](#quick-start) · [Game files](#game-files) · [Controls](#controls) · [Development](#development)

### Gameplay

Actual Linux gameplay captured at the original **480×320** resolution.

| Airport exploration | Aiming and firing |
| --- | --- |
| ![Leon exploring the airport](docs/media/gameplay-exploration.gif) | ![Leon aiming and firing](docs/media/gameplay-aiming.gif) |
| ![Airport scene](docs/media/screenshot-airport.png) | ![Over-the-shoulder aiming](docs/media/screenshot-aiming.png) |

The banner is illustrated fan artwork; screenshots and GIFs show the running project. See [media provenance](docs/media/README.md).

### Requirements

- **Linux x86_64** with a graphical desktop.
- Rust, C/C++ compilers, CMake, Boost headers, `pkg-config`, liblzma development headers (XZ), and native SDL/OpenAL development dependencies.
- **Python 3.10+, Tk and Pillow** for the launcher.
- **FFmpeg** on `PATH` for the original intro's video and audio.

Keep `Cargo.lock` and the pinned submodules. See the [build documentation](dev-docs/building.md) and [launcher dependency guide](launcher/README.md#install-and-open-the-launcher) for platform packages and Python setup.

### Quick start

Install the system prerequisites above, then:

```sh
git clone https://github.com/aurelioochoa/redegpc.git
cd redegpc
git submodule update --init --recursive
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r launcher/requirements.txt
make launcher
```

`make launcher` builds the optimized host and opens the incident dossier launcher. In **Installation**, choose your supported IPA and wait for **Ready to play**, then use **Overview → Play**. The first launch prepares a local asset cache and takes longer.

For direct command-line play:

```sh
CARGO_BUILD_JOBS=4 cargo build --locked --release --bin redegpc
./target/release/redegpc import "/path/to/Resident Evil Degeneration - v1.03.00.ipa"
./target/release/redegpc check
./target/release/redegpc run
```

### Game files

Only bundle **`jp.co.capcom.residentevil.en`**, version **`1.03.00`**, with an **unencrypted ARM Mach-O** is supported. Select the intact `.ipa`; do not extract it first. Other versions, languages and encrypted executables are rejected.

Import validates the app, copies it to local storage, records SHA-256 hashes and switches installations only after success. Rejected imports preserve existing installations and saves. After import, the source IPA and external drive are no longer needed. `check` verifies the installed originals; the decoded cache is separate and can be regenerated.

See [import and recovery details](launcher/README.md#import-your-game) and the [detailed usage guide](docs/advanced-usage.md#build-and-play).

### Launcher

![Native incident dossier launcher](docs/launcher/overview-1000x620.png)

- **Installation:** import and verify the game.
- **Overview:** play after verification succeeds.
- **Settings & controls:** save display, input and volume preferences for the next launch; choose a desktop icon.
- **Achievements:** browse 23 proposed goals and category filters. Gameplay achievement tracking is not implemented.
- **View logs:** inspect import, verification and runtime output.

F11 toggles launcher fullscreen independently of the game's display preference. Tab and Shift-Tab move between controls; Enter or Space activates them.

Run `make desktop` to install the applications-menu entry, desktop shortcut and `~/.local/bin/redegpc`. With an active virtual environment, use `make desktop PYTHON=.venv/bin/python`. The installed command opens the launcher without arguments; `redegpc run` starts the game directly. Keep this checkout in place. `make uninstall-desktop` removes the integration while preserving game files and saves. See the [full launcher guide](launcher/README.md).

### Controls

| Input | Action |
| --- | --- |
| W / A / S / D or arrows | Move |
| Hold right mouse and move mouse | Aim |
| Left mouse while aiming | Fire |
| R | Reload |
| Hold Space | Shake off a grab |
| E | Contextual action |
| Tab | Open inventory |
| Escape | Pause / back |
| F11 | Toggle game fullscreen |

Menus retain normal pointer navigation. Desktop mode hides the original movement, aim/fire, knife and walk graphics while keeping contextual actions, health, ammo and the phone shortcut visible. E follows the current contextual icon; without a nearby interaction it can enter the game's native aim mode. Losing focus releases held inputs.

Use `./target/release/redegpc run --touch` for original touch controls. Other options include `--fullscreen`, `--windowed`, `--volume=0..100` and `--fps`; display, input and volume settings persist. Escape, Enter, Space or a click skips the movie. See [detailed runtime behavior](docs/advanced-usage.md#build-and-play).

### Saves and settings

| Content | Default location |
| --- | --- |
| Imported installations, manifest and cache | `~/.local/share/redegpc` |
| Saves | `~/.local/share/redegpc/touchHLE_sandbox` |
| Settings and upstream options | `~/.config/redegpc` |
| Runtime log | `~/.local/state/redegpc/logs/redegpc.log` |

`XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_STATE_HOME` override the corresponding base directories. Clearing the asset cache is recoverable; deleting the data directory also deletes saves. Previous installations are retained, and an OS lease prevents overlapping runtimes from using the same saves.

### Status and limitations

The project is under local qualification. A successful build or a gameplay capture does not establish full campaign compatibility. Read the [observed results and remaining defects](docs/qualification.md) and [acceptance gates](GATES.md) before assessing support.

The runtime preserves the game's original resolution and timing. Cached asset decoding improves later loads while keeping imported originals intact. The launcher can browse proposed achievements but does not award them. Current platform support targets Linux x86_64.

### Development

| Command | Purpose |
| --- | --- |
| `make help` | Show available targets |
| `make setup` | Initialize submodules, fetch locked dependencies and check launcher prerequisites |
| `make build` | Build the release host |
| `make dev` / `make launcher` | Build and open the native launcher |
| `make run ARGS="--windowed --fps"` | Run with extra options |
| `make check-game` | Verify imported game files (`check-install` is an alias) |
| `make check` | Check Rust without linking |
| `make verify` | Build and run formatting, focused Clippy, library and synthetic CLI checks |
| `make test-launcher` | Run isolated launcher checks on a graphical display |
| `make clean` / `make distclean` | Remove Python caches / also clean Cargo artifacts |

Builds default to four Cargo jobs; override with `CARGO_BUILD_JOBS=8 make build`. Cleaning preserves game files and saves. The inherited runtime remains available with `cargo run --locked --release --bin touchHLE -- ...`.

See [detailed usage, architecture and qualification tools](docs/advanced-usage.md), [loading measurements](docs/qualification.md#loading-optimization-2026-10-16), and the [upstream README](README.touchHLE.md).

Contributions use this repository's GitHub issues and pull requests. Read the bilingual [contribution guide](CONTRIBUTING.md#english) and [piracy policy](CODE_OF_CONDUCT.md#english).

### License and credits

Based on **touchHLE**, retaining its history and notices. New host and compatibility code follows **MPL-2.0** source notices; the documented combined binary is **GPL-3.0-or-later**. Individual components retain their licenses. See [LICENSE](LICENSE), [upstream terms](README.touchHLE.md) and [redegpc notices](NOTICE.redegpc.md).

Resident Evil Degeneration and its game assets belong to their respective owners. The game is not distributed here; runtime resources and dependencies retain their required notices.

## Español

![Resident Evil Degeneration: Leon y Claire en el aeropuerto](docs/media/banner.png)

Juega la versión inglesa de **Resident Evil Degeneration para iPhone** en Linux con teclado y ratón, un lanzador de escritorio y partidas locales. `redegpc` es un host de compatibilidad escrito en Rust y basado en la revisión `ca1de89c578e79746f33c1332e28efd106c334ba` de touchHLE.

**Debes aportar tu propio juego:** solo se admite el **IPA de iPhone en inglés v1.03.00 sin cifrar**. El proyecto no incluye archivos del juego. Es un proyecto experimental de preservación; la compatibilidad completa durante el juego aún no está establecida.

[Jugabilidad](#jugabilidad) · [Inicio rápido](#inicio-rápido) · [Archivos del juego](#archivos-del-juego) · [Controles](#controles) · [Desarrollo](#desarrollo)

### Jugabilidad

Capturas reales del juego en Linux, a su resolución original de **480×320**.

| Exploración del aeropuerto | Apuntar y disparar |
| --- | --- |
| ![Leon explorando el aeropuerto](docs/media/gameplay-exploration.gif) | ![Leon apuntando y disparando](docs/media/gameplay-aiming.gif) |
| ![Escena del aeropuerto](docs/media/screenshot-airport.png) | ![Vista de apuntado sobre el hombro](docs/media/screenshot-aiming.png) |

El banner es una ilustración de aficionados; las capturas y los GIF muestran el proyecto en ejecución. Consulta la [procedencia del material visual](docs/media/README.md) (en inglés).

### Requisitos

- **Linux x86_64** con escritorio gráfico.
- Rust, compiladores de C/C++, CMake, cabeceras de Boost, `pkg-config`, cabeceras de desarrollo de liblzma (XZ) y dependencias de desarrollo de SDL/OpenAL.
- **Python 3.10 o posterior, Tk y Pillow** para el lanzador.
- **FFmpeg** en `PATH` para el vídeo y audio de la introducción original.

Conserva `Cargo.lock` y las revisiones fijadas de los submódulos. La [documentación de compilación](dev-docs/building.md) y la [guía de dependencias del lanzador](launcher/README.md#install-and-open-the-launcher) detallan los paquetes y la preparación de Python (en inglés).

### Inicio rápido

Instala los requisitos del sistema y ejecuta:

```sh
git clone https://github.com/aurelioochoa/redegpc.git
cd redegpc
git submodule update --init --recursive
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r launcher/requirements.txt
make launcher
```

`make launcher` compila el host optimizado y abre el lanzador con aspecto de expediente. En **Installation**, selecciona el IPA compatible y espera a **Ready to play**; después, usa **Overview → Play**. El primer inicio prepara una caché local de recursos y tarda más.

Para importar y jugar desde la terminal:

```sh
CARGO_BUILD_JOBS=4 cargo build --locked --release --bin redegpc
./target/release/redegpc import "/ruta/a/Resident Evil Degeneration - v1.03.00.ipa"
./target/release/redegpc check
./target/release/redegpc run
```

### Archivos del juego

Solo se admite el paquete **`jp.co.capcom.residentevil.en`**, versión **`1.03.00`**, con un **ejecutable ARM Mach-O sin cifrar**. Selecciona el `.ipa` intacto; no lo extraigas antes. Se rechazan otras versiones, idiomas y ejecutables cifrados.

La importación valida la aplicación, la copia al almacenamiento local, registra sus hashes SHA-256 y cambia de instalación solo al terminar correctamente. Una importación rechazada conserva las instalaciones y partidas existentes. Después de importar, ya no necesitas el IPA de origen ni la unidad externa. `check` verifica los originales instalados; la caché decodificada se guarda aparte y puede regenerarse.

Consulta los [detalles de importación y recuperación](launcher/README.md#import-your-game) y la [guía detallada de uso](docs/advanced-usage.md#build-and-play) (en inglés).

### Lanzador

![Lanzador de escritorio con aspecto de expediente](docs/launcher/overview-1000x620.png)

- **Installation:** importa y verifica el juego.
- **Overview:** inicia el juego tras verificarlo.
- **Settings & controls:** guarda las preferencias de pantalla, entrada y volumen para el próximo inicio; permite elegir el icono de escritorio.
- **Achievements:** muestra 23 objetivos propuestos y filtros por categoría. El seguimiento de logros durante el juego no está implementado.
- **View logs:** muestra los registros de importación, verificación y ejecución.

F11 alterna la pantalla completa del lanzador independientemente de la preferencia del juego. Tab y Shift-Tab recorren los controles; Enter o Espacio los activan.

Ejecuta `make desktop` para instalar la entrada del menú, el acceso directo de escritorio y `~/.local/bin/redegpc`. Con un entorno virtual activo, usa `make desktop PYTHON=.venv/bin/python`. El comando instalado abre el lanzador sin argumentos; `redegpc run` inicia directamente el juego. Conserva este repositorio en su ubicación. `make uninstall-desktop` elimina los accesos y conserva el juego y las partidas. Consulta la [guía completa del lanzador](launcher/README.md) (en inglés).

### Controles

| Entrada | Acción |
| --- | --- |
| W / A / S / D o flechas | Moverse |
| Mantener botón derecho y mover el ratón | Apuntar |
| Botón izquierdo mientras apuntas | Disparar |
| R | Recargar |
| Mantener Espacio | Librarse de un agarre |
| E | Acción contextual |
| Tab | Abrir el inventario |
| Escape | Pausa / volver |
| F11 | Alternar la pantalla completa del juego |

Los menús mantienen la navegación con el puntero. El modo de escritorio oculta los gráficos táctiles de movimiento, apuntado/disparo, cuchillo y caminar; conserva las acciones contextuales, salud, munición y acceso al teléfono. E sigue el icono contextual actual; sin una interacción cercana puede activar el apuntado nativo. Al perder el foco se liberan las entradas mantenidas.

Usa `./target/release/redegpc run --touch` para los controles táctiles originales. También existen `--fullscreen`, `--windowed`, `--volume=0..100` y `--fps`; las preferencias de pantalla, entrada y volumen se guardan. Escape, Enter, Espacio o un clic omiten el vídeo. Consulta el [comportamiento detallado del runtime](docs/advanced-usage.md#build-and-play) (en inglés).

### Partidas y ajustes

| Contenido | Ubicación predeterminada |
| --- | --- |
| Instalaciones importadas, manifiesto y caché | `~/.local/share/redegpc` |
| Partidas | `~/.local/share/redegpc/touchHLE_sandbox` |
| Ajustes y opciones de touchHLE | `~/.config/redegpc` |
| Registro de ejecución | `~/.local/state/redegpc/logs/redegpc.log` |

`XDG_DATA_HOME`, `XDG_CONFIG_HOME` y `XDG_STATE_HOME` sustituyen los directorios base correspondientes. La caché de recursos se puede regenerar; eliminar el directorio de datos también elimina las partidas. Se conservan las instalaciones anteriores y un bloqueo del sistema impide ejecutar varias instancias sobre las mismas partidas.

### Estado y limitaciones

El proyecto sigue en validación local. Una compilación correcta o una captura del juego no demuestran compatibilidad con toda la campaña. Consulta los [resultados observados y defectos pendientes](docs/qualification.md) y los [criterios de aceptación](GATES.md) (en inglés).

El runtime conserva la resolución y el ritmo originales. La caché decodificada mejora las cargas posteriores sin alterar los originales importados. El lanzador permite consultar objetivos propuestos, pero no otorga logros. La plataforma objetivo actual es Linux x86_64.

### Desarrollo

| Comando | Función |
| --- | --- |
| `make help` | Mostrar los objetivos disponibles |
| `make setup` | Inicializar submódulos, descargar dependencias fijadas y comprobar requisitos del lanzador |
| `make build` | Compilar el host optimizado |
| `make dev` / `make launcher` | Compilar y abrir el lanzador |
| `make run ARGS="--windowed --fps"` | Ejecutar con opciones adicionales |
| `make check-game` | Verificar el juego importado (`check-install` es un alias) |
| `make check` | Comprobar Rust sin enlazar |
| `make verify` | Compilar y ejecutar formato, Clippy específico, pruebas de biblioteca y CLI sintética |
| `make test-launcher` | Ejecutar pruebas aisladas del lanzador con pantalla gráfica |
| `make clean` / `make distclean` | Eliminar cachés de Python / limpiar también los artefactos de Cargo |

La compilación usa cuatro tareas de Cargo por defecto; cambia el valor con `CARGO_BUILD_JOBS=8 make build`. La limpieza conserva el juego y las partidas. El runtime heredado sigue disponible con `cargo run --locked --release --bin touchHLE -- ...`.

Consulta la [guía detallada de uso, arquitectura y herramientas de validación](docs/advanced-usage.md), las [mediciones de carga](docs/qualification.md#loading-optimization-2026-10-16) y el [README de touchHLE](README.touchHLE.md) (en inglés).

Las contribuciones se revisan en los issues y pull requests de este repositorio. Lee la [guía de contribución](CONTRIBUTING.md#español) y la [política de piratería](CODE_OF_CONDUCT.md#español); cada documento contiene inglés y español.

### Licencia y créditos

Basado en **touchHLE**, conservando su historial y avisos. El nuevo código del host y de compatibilidad sigue los avisos **MPL-2.0**; el binario combinado documentado es **GPL-3.0-or-later**. Cada componente conserva su licencia. Consulta [LICENSE](LICENSE), las [condiciones originales](README.touchHLE.md) y los [avisos de redegpc](NOTICE.redegpc.md).

Resident Evil Degeneration y sus recursos pertenecen a sus respectivos propietarios. El juego no se distribuye aquí; los recursos del runtime y las dependencias conservan sus avisos obligatorios.
