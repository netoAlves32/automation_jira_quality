import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


# Parámetros
EAS = "RESGUARDO INDÍGENA SENÚ LOS ALMENDROS"
CZ = "CZ URABA"


# Cargar datos
df = pd.read_excel("/Users/neto_shayo/Desktop/NETO/ICBF/BASE CONCURRENCIAS SIMAT VS CUENTAME SIN MADRES GESTANTES.xlsx", sheet_name="BASE AGOSTO", engine="openpyxl")

# Filtrar por EAS y CZ
filtered_eas_cz = df[(df["EntidadContratista"] == EAS) & (df["CentroZonalUDS"] == CZ)]

# Obtener todas las UDS únicas para esa EAS y CZ
uds_unicas = filtered_eas_cz["UnidadServicio"].unique()

# Crear documento Word
doc = Document()


doc.add_paragraph("\nCordial saludo,\n")
doc.add_paragraph(
    f"Solicito de manera urgente el envío de una carta con LOGO incluido de la EAS correspondiente {EAS} "
    f"adscritas al Centro Zonal {CZ}, en la que se indique de manera clara su deseo de continuar con la atención por parte del ICBF "
    "firmada por parte de los acudientes de los siguientes beneficiario/a(s):\n"
)

# Columnas de la tabla
columns = [
    "PrimerNombreBeneficiario", "SegundoNombreBeneficiario",
    "PrimerApellidoBeneficiario", "SegundoApellidoBeneficiario", "FechaNacimientoBeneficiario",
    "EdadAños_FechaBackup", "BarrioBeneficiario", "OtroBarrioBeneficiario", "ZonaRestoBeneficiario",
    "OtraZonaRestoBeneficiario", "DireccionResidenciaBeneficiario", "Rancheria", "TelefonoResidenciaBeneficiario"
]


# Procesar cada UDS encontrada
for uds in uds_unicas:
    p_uds = doc.add_paragraph()
    run_uds = p_uds.add_run(f"\nUnidad de Servicio: {uds}")
    run_uds.bold = True
    filtered_df = filtered_eas_cz[filtered_eas_cz["UnidadServicio"] == uds]
    if filtered_df.empty:
        doc.add_paragraph("No hay beneficiarios para esta UDS.")
        continue
    table = doc.add_table(rows=1, cols=len(columns))
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(columns):
        hdr_cells[i].text = col
    for _, row in filtered_df.iterrows():
        row_cells = table.add_row().cells
        for i, col in enumerate(columns):
            value = row[col]
            row_cells[i].text = "" if pd.isna(value) else str(value)
    doc.add_paragraph("")

# Párrafo de cierre
doc.add_paragraph(
    "\nLa carta debe indicar:\n"
    "• Si el beneficiario continuará recibiendo atención por parte del ICBF, explicando causas.\n"
    "• Si el beneficiario no continuará, manifestando su decisión para proceder en la desvinculación.\n\n"

    "Con el fin de facilitar la comunicación con cada EA para atender una alerta generada en el sistema SIMAT (Sistema Integrado de Matrícula), herramienta del Ministerio de Educación Nacional. Esta carta tiene como objetivo identificar a los niños, niñas y adolescentes (NNA) que van a seguir suscritos al ICBF.\n\n"

    "Sin este documento, no será posible garantizar la permanencia del menor en el programa y, en cumplimiento de lo acordado con el Ministerio de Educación y demás entidades, "
    "se procederá a su desvinculación para evitar pagos duplicados. Agradecemos su pronta gestión para evitar contratiempos.\n\n"
    "Agradezco su colaboración y envío de la información solicitada con la mayor celeridad posible.\n"
    "Quedo atento a su pronta respuesta.\n\n"
    "Cordialmente,\n"
)

# Guardar documento
output_path = "Carta_Beneficiarios_Todas_UDS.docx"
doc.save(output_path)

print(f"Carta generada exitosamente: {output_path}")