import requests
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

# Configuración
BASE_URL = "http://localhost:8000"
AUDIO_ZIP = "audios.zip"
QUERY_AUDIOS = ['query1.wav', 'query2.wav'] # Reemplaza con tus archivos de prueba

def check_files():
    if not os.path.exists(AUDIO_ZIP):
        print(f"❌ Error: No se encontró el archivo {AUDIO_ZIP}")
        print("Por favor crea un archivo ZIP con tus audios de prueba.")
        return False
    
    missing_queries = [f for f in QUERY_AUDIOS if not os.path.exists(f)]
    if missing_queries:
        print(f"⚠️ Advertencia: No se encontraron los siguientes archivos de query: {missing_queries}")
        print("Asegúrate de tener archivos de audio para probar la búsqueda.")
        # No retornamos False aquí para permitir intentar con los que existan o si el usuario edita el script
    return True

def build_index():
    print(f"\nConstruyendo índice de audio desde {AUDIO_ZIP}...")
    try:
        with open(AUDIO_ZIP, 'rb') as f:
            files = {'file': f}
            data = {'index_name': 'audio_test', 'k': 150}
            response = requests.post(f"{BASE_URL}/multimedia/build_index",
                                   files=files, data=data)
            if response.status_code == 200:
                print("✅ Índice construido exitosamente!")
                print(response.json())
                return True
            else:
                print(f"❌ Error al construir índice: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def search_audio(audio_path):
    if not os.path.exists(audio_path):
        return None
        
    print(f"\nBuscando similares a: {audio_path}")
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {'top_k': 5, 'index_name': 'audio_test'}
            
            # Comparar métodos
            response = requests.post(f"{BASE_URL}/multimedia/compare_methods",
                                    files=files, data=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error en búsqueda: {response.text}")
                return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    if not check_files():
        return

    if not build_index():
        return

    results = []
    valid_queries = [q for q in QUERY_AUDIOS if os.path.exists(q)]
    
    if not valid_queries:
        print("❌ No hay archivos de query válidos para probar.")
        return

    for audio_path in valid_queries:
        result = search_audio(audio_path)
        if result:
            results.append({
                'query': audio_path,
                'seq_time': result["sequential"]["time_seconds"],
                'idx_time': result["indexed"]["time_seconds"],
                'speedup': result["speedup"],
                'top_result_sim': result["indexed"]["results"][0]["similarity"] if result["indexed"]["results"] else 0
            })
            
            
    if results:
        # Visualizar resultados
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            queries = [r['query'] for r in results]
            seq_times = [r['seq_time'] for r in results]
            idx_times = [r['idx_time'] for r in results]
            
            x = np.arange(len(queries))
            width = 0.35
            
            ax1.bar(x - width/2, seq_times, width, label='Sequential', color='coral')
            ax1.bar(x + width/2, idx_times, width, label='Indexed', color='teal')
            ax1.set_xlabel('Query Audio')
            ax1.set_ylabel('Time (seconds)')
            ax1.set_title('Audio Search Performance')
            ax1.set_xticks(x)
            ax1.set_xticklabels(queries)
            ax1.legend()
            
            speedups = [r['speedup'] for r in results]
            ax2.bar(x, speedups, color='purple', alpha=0.7)
            ax2.set_xlabel('Query Audio')
            ax2.set_ylabel('Speedup (x times faster)')
            ax2.set_title('Indexing Speedup')
            ax2.set_xticks(x)
            ax2.set_xticklabels(queries)
            ax2.axhline(y=1, color='red', linestyle='--')
            
            plt.tight_layout()
            plt.savefig('audio_search_results.png')
            print("\n📊 Gráfico guardado como 'audio_search_results.png'")
        except Exception as e:
            print(f"\n⚠️ No se pudo generar el gráfico: {e}")

if __name__ == "__main__":
    main()
