import sys
import pandas as pd


# Definir inputs aquí
archivo = "Beneficiarios-Activos-En-Cuentame-SIN-Prematricula-15-Septiembre-2025.xlsx"
centro_zonal = "CZ SUROESTE"  # Cambia por el nombre real

# Leer el archivo Excel
df = pd.read_excel(archivo, engine="openpyxl")
# Filtrar por el centro zonal
df_cz = df[df["CentroZonalUDS"] == centro_zonal]
# Contar registros por entidad
conteo = df_cz["EntidadContratista"].value_counts()


# Guardar resultado en un archivo Excel
import pandas as pd
df_result = pd.DataFrame(list(conteo.items()), columns=["Entidad", "Cantidad"])
df_result.to_excel("conteo_por_entidad_resultado.xlsx", index=False)
print("Archivo generado: conteo_por_entidad_resultado.xlsx")
