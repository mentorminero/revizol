import fitz  # PyMuPDF

def extraer_texto_pdf(archivo_bytes):
    """
    Extrae el texto de un PDF en formato bytes y lo organiza por páginas.
    """
    doc = fitz.open(stream=archivo_bytes, filetype="pdf")
    paginas = []
    
    for num in range(len(doc)):
        texto = doc[num].get_text()
        if texto.strip():
            paginas.append({
                "pagina": num + 1,
                "contenido": texto
            })
            
    return paginas