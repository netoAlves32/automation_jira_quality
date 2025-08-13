#!/usr/bin/env python3
# Script para mover todos los archivos PNG del Desktop a la carpeta screenshots

import os
import shutil
import glob

# Directorios
desktop_path = "/Users/neto_shayo/Desktop"
screenshots_path = "/Users/neto_shayo/Desktop/screenshots"

# Crear la carpeta screenshots si no existe
if not os.path.exists(screenshots_path):
    os.makedirs(screenshots_path)


# Buscar todos los archivos PNG en la raíz del Desktop (no en subdirectorios)
png_files = []
for file in os.listdir(desktop_path):
    if file.lower().endswith('.png') and os.path.isfile(os.path.join(desktop_path, file)):
        png_files.append(file)

print(f"Encontrados {len(png_files)} archivos PNG en el Desktop")

# Mover archivos
moved_count = 0
for png_file in png_files:
    source = os.path.join(desktop_path, png_file)
    destination = os.path.join(screenshots_path, png_file)
    
    try:
        shutil.move(source, destination)
        print(f"Movido: {png_file}")
        moved_count += 1
    except Exception as e:
        print(f"Error moviendo {png_file}: {e}")

print(f"\nProceso completado: {moved_count} archivos movidos a screenshots/")

# Ahora buscar y mover PNG files de TODAS las subcarpetas
def move_all_png_files(base_path, screenshots_path):
    all_png_files = []
    
    for root, dirs, files in os.walk(base_path):
        # Evitar procesar la carpeta screenshots para no crear bucles
        if 'screenshots' in dirs:
            dirs.remove('screenshots')
            
        for file in files:
            if file.lower().endswith('.png'):
                file_path = os.path.join(root, file)
                # Solo agregar si no está ya en screenshots
                if not file_path.startswith(screenshots_path):
                    all_png_files.append((file_path, file))
    
    return all_png_files

print("\nBuscando PNG en todas las subcarpetas...")
all_png_files = move_all_png_files(desktop_path, screenshots_path)
print(f"Encontrados {len(all_png_files)} archivos PNG adicionales en subcarpetas")

subdirs_moved = 0
for file_path, filename in all_png_files:
    # Crear un nombre único si ya existe
    destination = os.path.join(screenshots_path, filename)
    counter = 1
    original_destination = destination
    
    while os.path.exists(destination):
        name, ext = os.path.splitext(filename)
        destination = os.path.join(screenshots_path, f"{name}_{counter}{ext}")
        counter += 1
    
    try:
        shutil.move(file_path, destination)
        if destination != original_destination:
            print(f"Movido (renombrado): {filename} -> {os.path.basename(destination)}")
        else:
            print(f"Movido: {filename}")
        subdirs_moved += 1
    except Exception as e:
        print(f"Error moviendo {filename}: {e}")

print(f"\nProceso completado:")
print(f"- {moved_count} archivos movidos desde el Desktop raíz")
print(f"- {subdirs_moved} archivos movidos desde subcarpetas")
print(f"- Total: {moved_count + subdirs_moved} archivos PNG movidos a screenshots/")
