# Me-Paga para Android

Version movil nativa construida con Flet (Python sobre Flutter). Los datos viven
en el almacenamiento privado de la app, no se envian a ningun servidor.

## Diferencias con la version de escritorio

- Interfaz tactil con rueda de fecha estilo iOS (`CupertinoDatePicker`).
- Base SQLite en el almacenamiento interno de la app (`FLET_APP_STORAGE_DATA`).
- Exportacion a Excel con formulas vivas y a CSV, igual que en escritorio.
- Sin permiso de INTERNET: la app no sale a la red.

## Probar en tu PC antes de compilar

```
cd movil
pip install -r requirements.txt
flet run main.py
```

## Compilar con Android Studio instalado

Flet necesita Flutter ademas del SDK de Android que ya tienes.

```
sudo snap install flutter --classic
flutter doctor --android-licenses
cd movil
flet build aab
```

El bundle queda en `movil/build/aab/`. Para probar en tu telefono por USB usa
`flet build apk` e instala el `.apk` de `movil/build/apk/`.

## Compilar sin usar tu equipo

El workflow `.github/workflows/android.yml` compila en GitHub Actions. Entra en
la pestana Actions del repositorio, elige "Android", pulsa "Run workflow" y
selecciona `aab` o `apk`. El archivo queda como artefacto descargable. Tambien
se dispara solo al publicar una etiqueta `v*`.

## Publicar en Google Play

1. Crea la cuenta de desarrollador en Play Console. Tiene un pago unico.
2. Verifica identidad. Para cuentas personales Google pide un periodo de pruebas
   cerradas con un minimo de testers antes de pasar a produccion; confirma el
   numero y los dias vigentes en Play Console porque esa politica cambia.
3. Crea la aplicacion con el identificador `com.bitcoinalexis.mepaga`. Ese valor
   esta en `movil/pyproject.toml` y no se puede cambiar despues de publicar.
4. Sube el `.aab`. Activa Play App Signing: subes con tu clave de carga y Google
   firma la version final.
5. Revisa que el `targetSdk` cumpla el minimo que exige Play ese ano. Si lo
   rechaza, actualiza Flutter y vuelve a compilar.
6. Rellena el formulario de Seguridad de los datos. Esta app no recopila ni
   comparte nada: todo queda en el dispositivo.
7. Publica una politica de privacidad accesible por URL. Puedes alojarla en
   GitHub Pages de este mismo repositorio.
8. Prepara la ficha: icono 512x512, grafico 1024x500, capturas de pantalla,
   descripcion corta y larga, y categoria.

## Generar la clave de carga

```
keytool -genkey -v -keystore me-paga-upload.jks -keyalg RSA -keysize 2048 \
  -validity 10000 -alias me-paga
```

Guarda el `.jks` y su contrasena fuera del repositorio. Si los pierdes no podras
publicar actualizaciones con esa clave de carga.

## Subir version nueva

Incrementa `version` en `movil/pyproject.toml` antes de cada entrega. Play
rechaza dos subidas con el mismo numero de version.
