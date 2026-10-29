# Releases y reintento de publish

Las releases salen del workflow `release.yml` al fusionar `dev` en `main`
(o con `./release.sh` desde `main`). El workflow tiene estos jobs:

| Job | Qué hace |
|---|---|
| `bump` | Calcula la versión con git-cliff, actualiza `CHANGELOG.md`, crea el tag y lo empuja |
| `release` | Crea el GitHub Release a partir del tag |
| `publish` | Construye sdist y wheel y los sube a PyPI (Trusted Publishing, entorno `pypi`) |
| `sync-dev` | Avanza `dev` hasta `main` con `git merge --ff-only` |

## Reintentar un publish fallido

Antes de reintentar, revisa en qué punto falló:

- **Falló `publish` pero el tag ya existe.** Abre la ejecución en la pestaña
  Actions y usa "Re-run failed jobs". Solo se repite `publish`, que hace
  checkout del tag y reconstruye el mismo código. No hay que tocar el tag ni
  crear otra versión.
- **El tag existe y el re-run no es posible** (por ejemplo la ejecución es
  muy vieja). Lanza `workflow_dispatch` sobre `main` desde Actions. Como
  `bump` ve que la versión calculada ya coincide con el último tag,
  responde `released=false` y los demás jobs se saltan: este camino no
  republica. En ese caso empuja un commit nuevo de tipo `fix:` a `main` para
  obtener una versión patch nueva, o sube a mano el build del tag (ver abajo).
- **PyPI ya tiene los archivos de esa versión.** PyPI no permite resubir el
  mismo nombre de archivo. Confirma en pypi.org/project/hueman qué archivos
  existen; si ya están todos, no hay nada que reintentar. Si falta alguno,
  la action usa `skip-existing` solo si se configura; por defecto fallará, y
  la salida limpia es publicar una versión patch nueva.
- **Falló `bump` antes de empujar el tag.** No hay nada publicado: relanza
  el workflow completo con "Re-run all jobs".

Subida manual desde el tag, solo como último recurso:

```bash
git checkout vX.Y.Z
python -m pip install build twine
python -m build
twine upload dist/*
```

`sync-dev` falla a propósito si `dev` avanzó con commits que `main` no
tiene (por ejemplo del bot del changelog). Resuélvelo a mano fusionando
`main` en `dev` y no fuerces el push.

`release.sh` no cambia: sigue calculando la versión, generando el changelog
y creando el tag localmente, con `--push` opcional.
