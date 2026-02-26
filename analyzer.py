import json
import os
import re
import time
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq


# --- CONFIGURACIÓN GROQ ---
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def analyze_with_groq(excel_name, fb_data):
    hoy = datetime.now().strftime("%d de %B de %Y")

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

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.4,
            )

            # Pausa de seguridad tras cada llamada a la API
            time.sleep(2)

            res_text = response.choices[0].message.content or ""

            # Extraer el primer bloque JSON usando regex para evitar texto extra
            match = re.search(r"\{.*?\}", res_text, re.DOTALL)
            if not match:
                raise ValueError("No se encontró un bloque JSON en la respuesta del modelo.")

            json_text = match.group(0)
            json_text = json_text.replace("```json", "").replace("```", "").strip()

            return json.loads(json_text)
        except Exception as e:
            print(f"  [!] Error en análisis Groq (intento {attempt}/{max_attempts}): {e}")
            if attempt == max_attempts:
                return None

