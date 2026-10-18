# Guía de uso y publicación

El tutorial de adquisición y análisis está en el [README](../README.md). Los comandos se ejecutan en Bash dentro de DragonOS.

## Fotografía del montaje

La única fotografía del tutorial es `foto1.png`, situada después del diagrama inicial. Para copiarla desde Descargas:

```bash
cd ~/proyectos/lte-observatory-sdr-falcon
DOWNLOAD_DIR="$(xdg-user-dir DOWNLOAD)"
mkdir -p docs/images
cp "$DOWNLOAD_DIR/foto1.png" docs/images/foto1.png
```

Las tres gráficas de resultados son archivos SVG generados por el analizador y se conservan. Los comandos aparecen como texto copiable, sin capturas de pantalla.

## Conservar los registros originales

Los archivos de adquisición se guardan en `data/raw/`, excluido de Git. Si los metadatos contienen un error, conservar el original y documentar la corrección por separado.

En el piloto, el comando y la sintonización muestran 1970 MHz; los metadatos iniciales indicaban 2120 MHz. La corrección se puede registrar así:

```bash
PILOT_DIR="$PWD/data/raw/pilot_20261018_140240"
sed 's/^frequency_hz=.*/frequency_hz=1970000000/' \
    "$PILOT_DIR/metadata.txt" > "$PILOT_DIR/metadata.corrected.txt"
printf '\nmotivo_correccion=Frecuencia corroborada en el comando y la sintonizacion; original conservado\n' \
    >> "$PILOT_DIR/metadata.corrected.txt"
```

## Publicar una actualización

```bash
python3 -m unittest discover -s tests -v
git diff --check
git status --short

git add README.md docs figures scripts tests data/processed
git diff --cached --stat
git diff --cached --check

git commit -m "Actualizar documentación y resultados"
git push
```

Revisar que el cambio contenga resultados agregados y no incluya registros originales ni grabaciones IQ. Finalmente, abrir el repositorio y comprobar la fotografía, las tres gráficas y los enlaces al informe.
