# Continuacion desde el piloto: analisis, figuras y GitHub

Los comandos se ejecutan en Bash dentro de DragonOS. El paquete se integra en la carpeta existente; no contiene ni reemplaza `data/raw/`.

## 1. Integrar el paquete

Descarga `falcon-project-kit.zip` desde el chat y transfierelo a la carpeta Descargas/Downloads de la VM. Si el navegador de Windows lo descarga, debes copiarlo a la VM mediante tu carpeta compartida o el mecanismo que ya utilizas.

```bash
cd ~/proyectos/lte-observatory-sdr-falcon
DOWNLOAD_DIR="$(xdg-user-dir DOWNLOAD)"
ls -lh "$DOWNLOAD_DIR/falcon-project-kit.zip"
unzip -n "$DOWNLOAD_DIR/falcon-project-kit.zip" -d .
```

`-n` conserva archivos existentes. Si el ZIP tiene otro nombre, usa el nombre que realmente muestre tu carpeta de descargas. Si no tienes unzip, instala `sudo apt install unzip`. El analizador solo necesita Python 3.10+.

## 2. Seleccionar el piloto sin depender de variables de otra terminal

```bash
PILOT_DIR="$PWD/data/raw/pilot_20261018_140240"
test -s "$PILOT_DIR/dci.tsv" && echo "Piloto localizado"
wc -l "$PILOT_DIR/dci.tsv"
awk 'NF && $0 !~ /^#/ {counts[NF]++} END {for (n in counts) print n, "campos:", counts[n], "filas"}' "$PILOT_DIR/dci.tsv"
```

Esperamos revisar el formato de 20 campos. Las filas con otro formato se contabilizan como invalidas; si ninguna es valida, el analizador termina con error. No publicamos conclusiones de ese archivo hasta resolverlo.

Captura sugerida: `08-pilot-format.png`, mostrando conteos, sin exponer filas con identificadores.

## 3. Registrar la correccion de frecuencia

La imagen del comando y el inicio de UHD muestran `1970e6` y `1.97e+09 Hz`. El metadata original decia 2120 MHz. Conserva ambos hechos para que el proceso sea auditable.

```bash
if [ ! -f "$PILOT_DIR/metadata.corrected.txt" ]; then
    sed 's/^frequency_hz=.*/frequency_hz=1970000000/' \
      "$PILOT_DIR/metadata.txt" > "$PILOT_DIR/metadata.corrected.txt"
    printf '\ncorrection_reason=frequency verified from command screenshot and UHD tuning log; original metadata preserved\n' \
      >> "$PILOT_DIR/metadata.corrected.txt"
fi
cat "$PILOT_DIR/metadata.corrected.txt"
grep -Ein 'Tunning|Tuning|1970|1\.97e' "$PILOT_DIR/console.log" | head -n 10
```

Captura: `09-frequency-correction.png`.

Texto de documentacion: "Se corrigio un error de transcripcion en la frecuencia de los metadatos, conservando el archivo original. La frecuencia utilizada fue 1970 MHz, corroborada por el comando y el registro del receptor."

## 4. Ejecutar las pruebas y el analisis

```bash
python3 --version
python3 -m unittest discover -s tests -v
python3 scripts/analyze.py \
  --input "$PILOT_DIR/dci.tsv" \
  --console "$PILOT_DIR/console.log" \
  --session-label pilot_1970 \
  --frequency-mhz 1970 \
  --window 1
```

Capturas: `10-tests.png` y `11-analysis-summary.png`.

El resumen calcula el lapso entre marcas de tiempo. No supone que `-n 120000` haya producido dos minutos de recepcion continua. `stats.txt` vacio se documenta: la consola puede contener el resumen de la corrida. Tampoco se asigna al piloto el 14.4547% visto en otra captura de GUI.

Si el analizador devuelve error, conserva el mensaje y resuelvelo antes de continuar. No sustituyas el piloto con datos de prueba.

## 5. Abrir las figuras y el informe

```bash
xdg-open figures/pilot_1970/activity.svg
xdg-open figures/pilot_1970/mcs.svg
xdg-open figures/pilot_1970/synthetic_record_removal.svg
cat docs/results/pilot_1970.md
```

Capturas nuevas:

| Nombre | Contenido | Explicacion |
|---|---|---|
| `12-activity.png` | Tres paneles temporales | Actividad observada en los mensajes decodificados; las ventanas sin registros son desconocidas |
| `13-mcs.png` | Distribucion UL/DL | Frecuencia de indices MCS observados; no mide por si sola calidad de canal |
| `14-record-removal.png` | Experimento sintetico | Cambio de indicadores al eliminar registros DCI con semilla fija |
| `15-results.png` | Informe generado | Resultados reales, conteos invalidos y limitaciones |

El SVG original es el artefacto principal para GitHub: conserva nitidez. Las capturas muestran como se ejecuto y reviso el proyecto.

Texto para el experimento: "Se evaluo la sensibilidad de los indicadores ante la eliminacion sintetica de registros DCI. La semilla fija permite reproducir la realizacion. El experimento no representa una calibracion de errores RF ni de perdidas de subtramas y no constituye validacion de un detector de anomalias."

## 6. Obtener otra sesion (recomendado para comparar)

Primero cierra FalconGUI. Mantiene antena, punto y frecuencia. El script usa un limite externo de tiempo para que el resultado no dependa de interpretar `-n` como duracion de recepcion sincronizada.

```bash
bash scripts/capture.sh 1970 120 P01
```

Al terminar, copia y ejecuta el comando de analisis que imprime. Completa el `notes.md` de esa sesion. No hace falta otra captura para ejecutar el analisis del piloto existente. Una comparacion diaria requiere varias sesiones y repeticiones, y queda como ampliacion si aun no las tienes.

## 7. Incorporar las fotos y resultados al README

El paquete ya contiene siete de las imagenes enviadas al chat: carpeta, estructura, gitignore, entorno, USB, ayuda e inicio de captura a 1970 MHz. Las tablas que exponen identificadores individuales y las filas DCI originales no se incluyeron en esta galeria.

Copia tus nuevas capturas `08` a `15` a `docs/images/` si deseas incluirlas. El README usa las graficas SVG directamente.

Tras generar el piloto, anade una sola vez:

```bash
if ! grep -q '^## Resultados del piloto procesado' README.md; then
cat >> README.md <<'EOF'

## Resultados del piloto procesado

[Informe de resultados](docs/results/pilot_1970.md) · [Resumen JSON](data/processed/pilot_1970/summary.json) · [Serie agregada](data/processed/pilot_1970/activity.csv)

### Distribucion MCS

![Distribucion de indices MCS observados](figures/pilot_1970/mcs.svg)

### Sensibilidad a registros faltantes

![Eliminacion sintetica de registros DCI](figures/pilot_1970/synthetic_record_removal.svg)

Las tasas indicadas corresponden a un experimento sintetico sobre registros ya decodificados. No son tasas de error medidas en el enlace de radio.
EOF
fi
```

Lee el informe antes de escribir conclusiones. Puedes publicar una primera version completa como **estudio piloto y herramienta reproducible**, dejando claro que la campana multihorario y un detector validado de anomalias son trabajo futuro.

## 8. Crear el repositorio en GitHub

En GitHub, crea un repositorio vacio llamado `lte-observatory-sdr-falcon`, de visibilidad publica si esa es tu eleccion de portafolio. No marques "Add README", licencia ni gitignore porque ya tienes archivos locales.

Descripcion sugerida:

> Experimental LTE monitoring at 1970 MHz using SDR and FALCON, with reproducible DCI analysis and missing-record sensitivity experiments.

En la terminal:

```bash
git init -b main
git status --short
git check-ignore data/raw/pilot_20261018_140240/dci.tsv
python3 -m unittest discover -s tests -v
git add README.md .gitignore scripts tests docs figures data/processed
git diff --cached --stat
git diff --cached --name-only
```

Comprueba que lo preparado incluya tu informe y figuras, y excluya `data/raw/`, `console.log` y grabaciones IQ. Revisa tambien las fotos que agregaste.

```bash
git diff --cached --check
git commit -m "Add LTE pilot analysis and record-loss sensitivity experiment"
git remote add origin https://github.com/Josueeeoo-0/lte-observatory-sdr-falcon.git
git push -u origin main
```

Si Git pide nombre/correo, configura los tuyos en este repositorio con `git config user.name` y `git config user.email`; usa tu correo de commits o el noreply exacto de Settings > Emails en GitHub. Si pide autenticacion, usa el gestor de credenciales de tu entorno o `gh auth login` si ya tienes GitHub CLI. No pegues tokens en capturas, archivos ni URLs de comandos.

Si `origin` ya existe, consulta `git remote -v`; no repitas `remote add` ni sobrescribas otra configuracion sin revisarla. Si el repositorio remoto ya tiene commits, no uses force push: revisa esa situacion antes de continuar.

## 9. Revision visual final

Abre la pagina del repositorio. Comprueba que el informe y las tres figuras se visualicen y que las conclusiones correspondan al reporte generado. Guarda `16-github-project.png` mostrando la portada y una figura. Anade temas como `sdr`, `lte`, `falcon`, `signal-processing`, `python` y `experimental-research`.

El autor debe poder explicar: diferencia entre RNTI y persona; canal de control y trafico de usuario; fila DCI y subtrama; intervalo sin registros y actividad cero; perdidas sinteticas y errores de adquisicion reales.
