
import pandas as pd
import os

# Ruta del archivo de entrada
archivo = "/Users/neto_shayo/Desktop/NETO/ICBF/EAS_correspondientes_correos.xlsx"


# Lista de entidades a filtrar
entidades_filtrar = [
   "ASOCIACION UNIDOS POR LA INFANCIA ASUINFANCIA",
   "CORPORACION IMAGINA TU MUNDO",
   "CORPORACIÓN COMUNIQUÉMONOS"
]

# Leer la primera hoja (EAS) para obtener los correos
df_eas = pd.read_excel(archivo, sheet_name=0, engine="openpyxl")
df_eas_filtrado = df_eas[df_eas["EAS"].isin(entidades_filtrar)]
correos_dict = dict(zip(df_eas_filtrado["EAS"], df_eas_filtrado["correo"]))

# Guardar los correos filtrados en un archivo txt, uno por línea
output_txt = f"{os.path.splitext(archivo)[0]}_correos.txt"
with open(output_txt, "w", encoding="utf-8") as f:
    for entidad in entidades_filtrar:
        correo = correos_dict.get(entidad, "no_email")
        f.write(str(correo).strip() + "\n")
print(f"Archivo generado: {output_txt}")
