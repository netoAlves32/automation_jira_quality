#!/bin/bash

echo "=== ORGANIZADOR DE SCREENSHOTS ==="
echo "Moviendo todas las imágenes PNG a la carpeta screenshots..."
echo ""

# Navegar al Desktop
cd "/Users/neto_shayo/Desktop"

# Crear carpeta screenshots si no existe
mkdir -p screenshots

# Contador de archivos movidos
count=0

# Función para mover archivo con manejo de duplicados
move_file() {
    local source="$1"
    local filename=$(basename "$source")
    local destination="screenshots/$filename"
    
    # Si ya existe, agregar número
    local counter=1
    while [ -f "$destination" ]; do
        local base="${filename%.*}"
        local ext="${filename##*.}"
        destination="screenshots/${base}_${counter}.${ext}"
        counter=$((counter + 1))
    done
    
    mv "$source" "$destination"
    echo "✓ Movido: $(basename "$source")"
    count=$((count + 1))
}

# Mover PNG files del Desktop raíz (excluyendo carpetas)
echo "1. Moviendo PNG del Desktop principal..."
find . -maxdepth 1 -name "*.png" -type f | while read -r file; do
    move_file "$file"
done

# Mover PNG files de todas las subcarpetas
echo ""
echo "2. Moviendo PNG de subcarpetas..."
find . -mindepth 2 -name "*.png" -type f | while read -r file; do
    move_file "$file"
done

echo ""
echo "=== PROCESO COMPLETADO ==="
echo "Todos los archivos PNG han sido organizados en la carpeta 'screenshots'"
echo ""

# Mostrar contenido de la carpeta screenshots
echo "Archivos en screenshots/:"
ls -la screenshots/ | grep "\.png$" | wc -l | xargs echo "Total de PNG movidos:"
