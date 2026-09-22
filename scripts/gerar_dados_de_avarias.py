import requests
import time
import psycopg2
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ====================== CONFIGURAÇÃO ======================
OPENCAGE_API_KEY = "4c484585c6da4e0a8d1ca940b1bd96d9"   # ← substitui pela tua chave
# ==========================================================

# Sessão com retries
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
session.mount("https://", HTTPAdapter(max_retries=retries))


def geocode(endereco: str):
    """Geocodifica um endereço usando OpenCage"""
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": f"{endereco}, Luanda, Angola",
        "key": OPENCAGE_API_KEY,
        "countrycode": "ao",
        "limit": 1,
        "language": "pt",
        "no_annotations": 1,
        "abbrv": 1
    }

    try:
        response = session.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        if data.get("results"):
            geometry = data["results"][0]["geometry"]
            return geometry["lat"], geometry["lng"]
        
        return None, None

    except Exception as e:
        print(f"   Erro: {e}")
        return None, None


enderecos = [
    # Avenidas Principais
    "Avenida 4 de Fevereiro, Ingombota",
    "Avenida Comandante Valódia, Maianga",
    "Avenida Lenine, Ingombota",
    "Avenida Deolinda Rodrigues, Kilamba Kiaxi",
    "Avenida Ho Chi Minh, Rangel",
    "Avenida Revolução de Outubro, Maianga",
    "Avenida Pedro de Castro Van-Dúnem Loy, Talatona",
    "Avenida 21 de Janeiro, Samba",
    "Avenida Murtala Mohamed, Ilha de Luanda",
    "Avenida Dr. António Agostinho Neto, Ingombota",
    # Ruas na Ingombota e Baixa de Luanda
    "Rua da Missão, Ingombota",
    "Rua dos Coqueiros, Ingombota",
    "Rua da Alfândega, Ingombota",
    "Rua dos Mercadores, Ingombota",
    "Rua Dr. Alvares Maciel, Ingombota",
    "Rua Direita da Ingombota, Ingombota",
    "Rua da Muxima, Ingombota",
    "Rua do Carmo, Ingombota",
    "Rua Rainha Ginga, Ingombota",
    "Rua Major Kanhangulo, Ingombota",
    "Rua da Olivença, Ingombota",
    "Rua Amílcar Cabral, Ingombota",
    "Rua Engrácia Fragoso, Ingombota",
    "Rua da Boavista, Ingombota",
    "Rua dos Pescadores, Ingombota",
    # Ruas em Maculusso, Maianga e Alvalade
    "Rua Alda Lara, Maculusso",
    "Rua Alameda Manuel Van-Dunen, Maculusso",
    "Rua Amílcar Cabral, Maculusso",
    "Rua Fernando Pessoa, Maculusso",
    "Rua Conego Manuel das Neves, Maianga",
    "Rua do N'Gola, Maianga",
    "Rua da Samba, Samba",
    "Rua Gago Coutinho, Alvalade",
    "Rua Comandante Gika, Alvalade",
    "Rua do Seminário, Maianga",
    "Rua Santa Cruz, Prenda",
    "Rua do Kwanza, Maculusso",
    "Rua da Liberdade, Rangel",
    "Rua Hoji-Ya-Henda, Rangel",
    "Rua Direita do Kilamba, Kilamba Kiaxi",
    # Talatona e Sul de Luanda
    "Rua do Talatona, Talatona",
    "Rua S10, Talatona",
    "Rua A1, Talatona",
    "Via Expressa Cacuaco-Viana-Talatona, Talatona",
    "Condomínio Rosas de Talatona, Talatona",
    "Condomínio Palm Beach, Ilha de Luanda",
    "Largo do Patriota, Lar do Patriota",
    "Estrada do Lar do Patriota, Patriota",
    "Zona C, Talatona",
    "Centralidade do Kilamba, Kilamba",
    # Viana e Outras Zonas Periféricas
    "Rua Direita de Viana, Viana",
    "Zona Industrial de Viana, Viana",
    "Estrada de Catete, Viana",
    "Bairro Zango 0, Zango",
    "Bairro Zango 3, Zango",
    "Bairro Zango 8, Zango",
    "Kikuxi, Viana",
    "Vila Flor, Viana",
    "Gamek a Sassa, Kilamba Kiaxi",
    "Terra Vermelha, Cacuaco",
]


# Conexão à base de dados
conn = psycopg2.connect("dbname=gis_test user=postgres password=pass host=localhost")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id SERIAL PRIMARY KEY,
        endereco TEXT,
        descricao TEXT,
        geom GEOGRAPHY(Point, 4326)
    );
""")
print("A começar a geocodificação com OpenCage...\n")

sucesso = 0
falhas = 0
ja_existiam = 0

for i, endereco in enumerate(enderecos, 1):
    print(f"[{i:02d}/{len(enderecos)}] {endereco}")
    
    # Verifica se o endereço já existe
    cur.execute("SELECT 1 FROM tickets WHERE endereco = %s", (endereco,))
    if cur.fetchone():
        print("   → Já existe (ignorado)")
        ja_existiam += 1
        continue
    
    lat, lon = geocode(endereco)
    
    if lat and lon:
        cur.execute(
            "INSERT INTO tickets (endereco, descricao, geom) VALUES (%s, %s, ST_MakePoint(%s, %s)::geography)",
            (endereco, "Avaria reportada", lon, lat)
        )
        print(f"   → OK  ({lat:.5f}, {lon:.5f})")
        sucesso += 1
    else:
        print(f"   → Não geocodificado")
        falhas += 1
    
    time.sleep(1.05)

conn.commit()
cur.close()
conn.close()

print("\n" + "="*50)
print(f"Concluído!")
print(f"Novos inseridos : {sucesso}")
print(f"Já existiam     : {ja_existiam}")
print(f"Falhas          : {falhas}")
print("="*50)