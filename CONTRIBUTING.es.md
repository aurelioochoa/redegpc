# Contribuir a redegpc

[English](CONTRIBUTING.md) · **Español**

`redegpc` es un port experimental de Resident Evil Degeneration para Linux, basado en touchHLE. Esta guía describe las contribuciones a este fork. Los informes y cambios se revisan en los [issues](https://github.com/aurelioochoa/redegpc/issues) y [pull requests](https://github.com/aurelioochoa/redegpc/pulls) de este repositorio.

## Alcance

El objetivo actual es **Linux x86_64** y la versión **inglesa de iPhone v1.03.00**, con identificador `jp.co.capcom.residentevil.en`. Son útiles las mejoras del host, importador, controles, lanzador, cargas, partidas, documentación y pruebas.

La compatibilidad con otras aplicaciones de iPhone queda fuera del alcance actual. Consulta el [README](README.es.md), la [guía del lanzador](launcher/README.md) y los [resultados y limitaciones observados](docs/qualification.md) antes de describir un problema. Las dos últimas referencias están en inglés.

## Informes y propuestas

Abre un [issue](https://github.com/aurelioochoa/redegpc/issues/new/choose) en inglés o español e incluye:

- La revisión de `redegpc` (`git rev-parse HEAD`), distribución Linux y arquitectura.
- GPU/controlador y sesión gráfica cuando el problema afecte al renderizado, ventana o entrada.
- Pasos para reproducirlo, resultado esperado y observado, y si funcionaba en una revisión anterior.
- Versión del juego, resultado de `make check-game` y registros pertinentes. No adjuntes el IPA ni archivos extraídos del juego; elimina datos privados de los registros.

Para propuestas amplias, explica el problema y el diseño previsto para facilitar la revisión. Distingue las pruebas de compilación o componentes de las observaciones reales del juego; llegar al menú no demuestra compatibilidad con toda la campaña.

## Preparar el entorno

Para enviar cambios, crea un fork en GitHub, clónalo y abre una rama a partir de `main`. Sigue los requisitos y la preparación del [README](README.es.md#requisitos), conservando `Cargo.lock` y los submódulos fijados.

```sh
git submodule update --init --recursive
make setup
make build
```

El lanzador requiere Python 3.10 o posterior, Tk y Pillow; FFmpeg reproduce la introducción original. No necesitas el juego para las comprobaciones sintéticas. Las pruebas reales requieren tu propio IPA compatible sin cifrar y un escritorio gráfico.

## Cambios y pruebas

Mantén cada pull request centrado en un problema y añade pruebas cuando permitan detectar una regresión significativa. Conserva los archivos originales importados y las partidas; usa datos sintéticos o instalaciones aisladas para las pruebas. Respeta el [estilo existente](dev-docs/code-style.md).

| Comando | Función |
| --- | --- |
| `make fmt-check` | Comprobar el formato de Rust |
| `make check` | Comprobar la biblioteca y binarios sin enlazar |
| `make test` | Ejecutar pruebas de biblioteca sin la cadena de herramientas iOS original |
| `make lint` | Ejecutar las comprobaciones específicas de Clippy |
| `make test-cli` | Comprobar CLI e importador con datos sintéticos |
| `make verify` | Comprobar, compilar y ejecutar formato, Clippy, pruebas de biblioteca y CLI sintética |
| `make test-launcher` | Probar el lanzador de forma aislada; requiere pantalla gráfica |
| `make check-game` | Verificar tu instalación importada |

Ejecuta `make verify` para cambios del runtime, importador o sistema de compilación. Añade `make test-launcher` para cambios en el lanzador. Para documentación, comprueba enlaces, ejemplos y formato; no hace falta recompilar el runtime. Indica qué comprobaste y cualquier comprobación que no pudiste ejecutar.

## Pull requests

Envía el pull request a **`aurelioochoa/redegpc:main`**. Describe el problema, el comportamiento resultante, las pruebas y cualquier límite o regresión pendiente. Incluye capturas si ayudan a revisar cambios visuales. El mantenedor revisa los cambios en GitHub; Gerrit y los identificadores de revisión de touchHLE no forman parte del proceso de este fork.

## Uso de IA

Este fork permite contribuciones asistidas por IA. Quien contribuye sigue siendo responsable de comprender y revisar el contenido, comprobar su funcionamiento y verificar su procedencia y compatibilidad de licencia. Describe en el pull request el uso sustancial de IA.

Esta política se aplica a `redegpc`. Si envías cambios al proyecto touchHLE original, debes seguir sus propias reglas de contribución.

## Procedencia y licencias

Aporta únicamente material que puedas compartir. Prioriza documentación pública, observaciones reproducibles y trabajo original; no incluyas código propietario copiado, material filtrado, IPA ni recursos extraídos del juego. Cumple la [política de piratería](CODE_OF_CONDUCT.es.md).

Conserva las cabeceras de licencia y derechos de autor, los avisos de dependencias y el historial de atribución. Los cambios en código cubierto por MPL continúan bajo sus términos. El código nuevo del host sigue actualmente MPL-2.0; los componentes conservan sus propias licencias y el binario combinado documentado es GPL-3.0-or-later. Consulta [LICENSE](LICENSE), los [avisos del proyecto](NOTICE.redegpc.md) y las [condiciones originales](README.touchHLE.md#license). Cambiar estas instrucciones no cambia las licencias del software.
