import pandas as pd

from analyzer import analyze_with_groq
from scraper import get_driver, scrap_facebook_data

# Configuración de guardado
SAVE_EVERY = 5  # Guardar cada 5 registros procesados
FILE_INPUT = "paginas.xlsx"
FILE_OUTPUT = "progreso.xlsx"


def main():
    # Cargar siempre desde el archivo de entrada completo
    df = pd.read_excel(FILE_INPUT)

    # Inicializar columnas si no existen
    for col in ["pais", "eliminar", "notas", "descripción"]:
        if col not in df.columns:
            df[col] = ""

    total_registros = len(df)
    processed_count = 0

    driver = get_driver()
    try:
        for i, row in df.iterrows():
            print(f"\n[Registro {i + 1}/{total_registros}] Analizando: {row.get('name', '')}")

            fb_url = row.get("url")
            if not isinstance(fb_url, str) or not fb_url.strip():
                df.at[i, "eliminar"] = "SI"
                df.at[i, "notas"] = "URL de Facebook vacía o inválida."
            else:
                fb_info = scrap_facebook_data(driver, fb_url)

                if not fb_info["exists"]:
                    df.at[i, "eliminar"] = "SI"
                    df.at[i, "notas"] = "Página no encontrada o caída."
                else:
                    analysis = analyze_with_groq(row.get("name", ""), fb_info)
                    if analysis:
                        df.at[i, "eliminar"] = analysis.get("eliminar")
                        if analysis.get("eliminar") == "NO":
                            df.at[i, "pais"] = analysis.get("pais")
                            df.at[i, "descripción"] = analysis.get("descripcion")
                        else:
                            df.at[i, "notas"] = f"Eliminado: {analysis.get('motivo')}"
                    else:
                        df.at[i, "notas"] = "Error en análisis de Gemini"

            processed_count += 1

            # GUARDADO CADA 'SAVE_EVERY' REGISTROS PROCESADOS
            if processed_count % SAVE_EVERY == 0:
                df.to_excel(FILE_OUTPUT, index=False)
                print(f"  [v] Progreso guardado en {FILE_OUTPUT} (Hasta registro procesado {processed_count})")

        # Guardado final
        df.to_excel(FILE_OUTPUT, index=False)
        print(f"\n--- PROCESO FINALIZADO --- Archivo final: {FILE_OUTPUT}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

