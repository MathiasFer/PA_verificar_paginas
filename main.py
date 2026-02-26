import os
import time
import json
import pandas as pd
import google.generativeai as genai
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro") 

# Configuración de guardado
SAVE_EVERY = 5  # Guardar cada 5 registros
FILE_INPUT = "paginas.xlsx"
FILE_OUTPUT = "progreso_825_registros.xlsx"

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrap_facebook_data(fb_url):
    driver = get_driver()
    data = {"exists": False, "profile_name": None, "about_text": "", "recent_posts": []}
    
    try:
        driver.get(fb_url)
        time.sleep(5) 
        
        page_source = driver.page_source.lower()
        if "esta página no está disponible" in page_source or "this content isn't available" in page_source:
            return data 
        
        data["exists"] = True
        try:
            data["profile_name"] = driver.find_element(By.TAG_NAME, "h1").text
        except:
            data["profile_name"] = "No detectado"

        # Capturar posts para ver actividad reciente
        post_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
        for p in post_elements[:4]:
            data["recent_posts"].append(p.text.replace('\n', ' ')[:400])

        # Navegar a sección Información
        clean_url = driver.current_url.split('?')[0].rstrip('/')
        driver.get(f"{clean_url}/about")
        time.sleep(3)
        try:
            data["about_text"] = driver.find_element(By.XPATH, "//div[@role='main']").text
        except:
            data["about_text"] = "No disponible"

    except Exception as e:
        print(f"  [!] Error de red: {e}")
    finally:
        driver.quit()
    return data

def analyze_with_gemini(excel_name, fb_data):
    hoy = datetime.now().strftime('%d de %B de %Y')
    
    # Este prompt ahora obliga a la IA a redactar sobre la EMPRESA, no sobre el PERFIL
    prompt = f"""
    Hoy es {hoy}.
    Tu objetivo es redactar la identidad corporativa de la entidad: "{excel_name}" basándote en su información de Facebook.

    DATOS DE ORIGEN (Extraídos de Facebook):
    - Nombre del Perfil: {fb_data['profile_name']}
    - Sección Información: {fb_data['about_text']}
    - Publicaciones recientes: {fb_data['recent_posts']}

    REGLAS DE FILTRADO:
    1. ACTIVIDAD: Si no hay publicaciones en los últimos 30 días, responde eliminar: SI.
    2. IDENTIDAD: Si el perfil no pertenece a {excel_name} (o no hay relación clara), responde eliminar: SI.

    REGLAS DE REDACCIÓN (Si eliminar es NO):
    - NO menciones elementos de la página de Facebook (no hables de seguidores, fotos de perfil, reels, ni fechas de posts).
    - La descripción debe ser sobre la ORGANIZACIÓN o EMPRESA o persona de quien se habla en la cuenta.
    - Usa la técnica del "ADN": Describe qué hacen, qué los hace únicos, su alcance geográfico y su especialidad.
    - Debe ser TAN descriptiva que se identifique a la empresa de inmediato entre competidores similares.
    - Ejemplo de estilo aunque no necesariamente esto: "Plataforma líder en... se distingue por su ADN... es fácilmente identificable por... se caracteriza por su lema de..."
    - Extensión: Mínimo 80 palabras de contenido sustancial.

    RESPUESTA JSON:
    {{
      "eliminar": "SI/NO",
      "pais": "ISO-ALPHA-3",
      "descripcion": "AQUÍ LA DESCRIPCIÓN DETALLADA",
      "coincide": true/false,
      "motivo": "Breve explicación si marcas SI en eliminar"
    }}
    """
    try:
        # Usamos una temperatura ligeramente más alta (0.4) para que la redacción sea más fluida y menos robótica
        response = model.generate_content(prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(res_text)
    except Exception as e:
        print(f"  [!] Error en Gemini: {e}")
        return None

def main():
    # Cargar el archivo. Si ya existe un progreso previo, lo usamos para continuar.
    if os.path.exists(FILE_OUTPUT):
        df = pd.read_excel(FILE_OUTPUT)
        print(f"[*] Continuando desde el archivo de progreso existente: {FILE_OUTPUT}")
    else:
        df = pd.read_excel(FILE_INPUT)
        # Inicializar columnas si no existen
        for col in ['pais', 'eliminar', 'notas', 'descripción']:
            if col not in df.columns: df[col] = ""
        print("[*] Iniciando nuevo proceso.")

    # Definir rango: desde el registro 18 (índice 17) hasta el 825 (índice 824)
    start_idx = 17
    end_idx = 825

    for i in range(start_idx, end_idx):
        # Saltar si ya está procesado (por si el script se reinicia)
        if pd.notna(df.at[i, 'descripción']) and df.at[i, 'descripción'] != "" or df.at[i, 'eliminar'] == "SI":
            continue

        row = df.iloc[i]
        print(f"\n[Registro {i+1}/825] Analizando: {row['name']}")
        
        fb_info = scrap_facebook_data(row['url'])
        
        if not fb_info["exists"]:
            df.at[i, 'eliminar'] = "SI"
            df.at[i, 'notas'] = "Página no encontrada o caída."
        else:
            analysis = analyze_with_gemini(row['name'], fb_info)
            if analysis:
                df.at[i, 'eliminar'] = analysis.get('eliminar')
                if analysis.get('eliminar') == "NO":
                    df.at[i, 'pais'] = analysis.get('pais')
                    df.at[i, 'descripción'] = analysis.get('descripcion')
                else:
                    df.at[i, 'notas'] = f"Eliminado: {analysis.get('motivo')}"
            else:
                df.at[i, 'notas'] = "Error en análisis de Gemini."

        # GUARDADO CADA 'SAVE_EVERY' REGISTROS
        if (i + 1) % SAVE_EVERY == 0:
            df.to_excel(FILE_OUTPUT, index=False)
            print(f"  [v] Progreso guardado en {FILE_OUTPUT} (Hasta registro {i+1})")

    # Guardado final
    df.to_excel(FILE_OUTPUT, index=False)
    print(f"\n--- PROCESO FINALIZADO --- Archivo final: {FILE_OUTPUT}")

if __name__ == "__main__":
    main()