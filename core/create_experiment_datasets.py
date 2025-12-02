import os
import zipfile
from tqdm import tqdm

# --- CONFIGURACIÓN ---
# Ruta donde están tus imágenes descomprimidas (detectada automáticamente)
SOURCE_DIR = os.path.join("data", "mm_index_img", "media", "images")

# Dónde quieres guardar los nuevos zips
OUTPUT_DIR = "datasets_para_experimentos"

# Los tamaños que quieres probar
SIZES = [1000, 2000, 4000, 8000, 16000, 32000]

def create_experimental_zips():
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: No encuentro la carpeta {SOURCE_DIR}")
        # Try absolute path fallback if running from core root
        abs_source = os.path.abspath(SOURCE_DIR)
        print(f"Buscando en: {abs_source}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Leyendo y ordenando archivos...")
    # 1. Obtenemos todas las imágenes y las ORDENAMOS para garantizar consistencia
    all_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    all_files.sort() 
    
    total_found = len(all_files)
    print(f"Encontradas {total_found} imágenes en total.")

    # 2. Creamos un ZIP para cada tamaño N
    for n in SIZES:
        if n > total_found:
            print(f"Saltando N={n} (solo tienes {total_found} imágenes).")
            continue

        zip_name = os.path.join(OUTPUT_DIR, f"imagenes_{n}.zip")
        print(f"Generando {zip_name}...")

        # Tomamos las primeras N imágenes (Slicing)
        subset = all_files[:n]

        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Usamos tqdm para mostrar progreso
            for file in tqdm(subset, desc=f"Zippeando {n}", unit="img"):
                file_path = os.path.join(SOURCE_DIR, file)
                # arcname es el nombre que tendrá el archivo DENTRO del zip
                zipf.write(file_path, arcname=file)
        
        print(f"✅ Creado: {zip_name}")

if __name__ == "__main__":
    create_experimental_zips()
