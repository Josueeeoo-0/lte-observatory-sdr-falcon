# Validación del programa

Las pruebas comprueban el formato de entrada, el descarte de filas inválidas, la agregación de ambos sentidos, los intervalos sin registros, el filtro de identificadores y la repetición del experimento con semilla fija. También verifican los índices MCS, los límites del procesamiento y los textos en español.

```bash
python3 -m unittest discover -s tests -v
```

Los datos de prueba son sintéticos y se crean en carpetas temporales. No sustituyen los registros del receptor ni validan la exactitud de FALCON.

Esta actualización conserva los valores numéricos publicados y cambia la presentación al español. Las figuras se regeneran a partir de las tablas agregadas existentes. Para repetir el procesamiento completo de la sesión se necesita el archivo DCI original, que permanece fuera del repositorio.
