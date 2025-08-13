import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

# Load the Excel file and filter for CDI CURRULAO and Alcaldía de Turbo
df = pd.read_excel("BASE CONCURRENCIAS SIMAT VS CUENTAME SIN MADRES GESTANTES.xlsx", sheet_name="BASE AGOSTO", engine="openpyxl")
filtered_df = df[(df["UnidadServicio"] == "CDI CURRULAO") & (df["EntidadContratista"] == "ALCALDIA DE TURBO")]

# Create a Word document
doc = Document()

# Add header
header = doc.add_paragraph()
header.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
run = header.add_run("ALCALDÍA DE TURBO\nUnidad de Servicio: CDI CURRULAO")
run.bold = True
run.font.size = Pt(14)

doc.add_paragraph("\nCordial saludo,\n")
doc.add_paragraph(
    "Solicito de manera urgente el envío de una carta con LOGO incluido de la EAS correspondiente ALCALDÍA DE TURBO "
    "adscritas al Centro Zonal CZ URABA, en la que se indique de manera clara su deseo de continuar con la atención por parte del ICBF "
    "firmada por parte de los acudientes de los siguientes beneficiario/a(s):"
)

# Add table of beneficiaries
columns = [
    "NumeroDocumentoBeneficiario", "PrimerNombreBeneficiario", "SegundoNombreBeneficiario",
    "PrimerApellidoBeneficiario", "SegundoApellidoBeneficiario", "FechaNacimientoBeneficiario",
    "EdadAños_FechaBackup", "BarrioBeneficiario", "OtroBarrioBeneficiario", "ZonaRestoBeneficiario",
    "OtraZonaRestoBeneficiario", "DireccionResidenciaBeneficiario", "Rancheria", "TelefonoResidenciaBeneficiario"
]

table = doc.add_table(rows=1, cols=len(columns))
hdr_cells = table.rows[0].cells
for i, col in enumerate(columns):
    hdr_cells[i].text = col

for _, row in filtered_df.iterrows():
    row_cells = table.add_row().cells
    for i, col in enumerate(columns):
        value = row[col]
        row_cells[i].text = "" if pd.isna(value) else str(value)

# Add closing paragraph
doc.add_paragraph(
    "\nLa carta debe indicar:\n"
    "• Si el beneficiario continuará recibiendo atención por parte del ICBF, explicando causas.\n"
    "• Si el beneficiario no continuará, manifestando su decisión para proceder en la desvinculación.\n\n"
    "Sin este documento, no será posible garantizar la permanencia del menor en el programa y, en cumplimiento de lo acordado con el Ministerio de Educación y demás entidades, "
    "se procederá a su desvinculación para evitar pagos duplicados. Agradecemos su pronta gestión para evitar contratiempos.\n\n"
    "Agradezco su colaboración y envío de la información solicitada con la mayor celeridad posible.\n"
    "Quedo atento a su pronta respuesta.\n\n"
    "Cordialmente,\n"
    "Harvin Moreno Palacios\n"
    "Contratista\n"
    "Grupo Atención en Ciclos de Vida y nutrición\n"
    "Regional Antioquia\n"
    "Calle 45 #79-141 Barrio la América, Medellín\n"
    "Teléfono: 604 4093440 Ext. 400205\n"
    "www.icbf.gov.co\n"
    "Clasificación de la información: CLASIFICADA"
)

# Save the document
output_path = "Carta_Beneficiarios_CDI_CURRULAO.docx"
doc.save(output_path)

print(f"Carta generada exitosamente: {output_path}")