# Ejemplos para Windows

Scripts de PowerShell de ejemplo para usar hueman desde WSL con Windows. Son
puntos de partida para adaptar, no parte del producto. La guía completa está en
`website/content/latest/guides/windows.md` ("Windows y WSL").

| Archivo | Para qué |
|---------|----------|
| `install-windhawk-taskbar-task.ps1` | Instalación única (PowerShell como Administrador): copia el script de aplicar a `$env:ProgramData\DotfilesTheme` y registra la tarea programada elevada `DotfilesThemeWindhawk`. `-Uninstall` la elimina. |
| `windhawk-taskbar-apply.ps1` | Lo ejecuta la tarea: lee `taskbar-colors.json` (`fill`, `text`) y actualiza los colores del mod `windows-11-taskbar-styler` de Windhawk. Solo recarga el mod si algo cambió. |

## Uso

Desde un PowerShell elevado, en la carpeta con ambos archivos:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windhawk-taskbar-task.ps1
```

Opciones: `-TaskName <NombreTarea>` y `-DataFile <RUTA>`. Por defecto el JSON
es `$env:LOCALAPPDATA\DotfilesTheme\taskbar-colors.json`; el target de hueman
debe escribir ahí (`/mnt/c/Users/<usuario>/AppData/Local/DotfilesTheme/...`).

## Seguridad

- El script de aplicar vive en una carpeta de `ProgramData` con permisos solo
  para SYSTEM y Administradores (los usuarios, lectura y ejecución).
- El JSON, escribible por el usuario, se trata solo como dato: cada valor debe
  cumplir `^#[0-9A-Fa-f]{6}$` o el script aborta sin cambios.
- Solo toca valores de la clave de ajustes del mod y su bandera `Disabled`.

## Aviso

Estos scripts no se probaron en este repositorio (no hay PowerShell ni Windows
en el entorno de desarrollo). Léelos y pruébalos con cuidado antes de usarlos.
