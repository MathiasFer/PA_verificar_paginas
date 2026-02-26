import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def scrap_facebook_data(driver, fb_url):
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
        except Exception:
            data["profile_name"] = "No detectado"

        # Capturar posts para ver actividad reciente
        post_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
        for p in post_elements[:4]:
            data["recent_posts"].append(p.text.replace("\n", " ")[:400])

        # Navegar a sección Información
        clean_url = driver.current_url.split("?")[0].rstrip("/")
        driver.get(f"{clean_url}/about")
        time.sleep(3)
        try:
            data["about_text"] = driver.find_element(By.XPATH, "//div[@role='main']").text
        except Exception:
            data["about_text"] = "No disponible"

    except Exception as e:
        print(f"  [!] Error de red: {e}")

    return data

