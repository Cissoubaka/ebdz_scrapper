from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

# Créer les répertoires nécessaires
os.makedirs('./data/covers', exist_ok=True)
os.makedirs('./templates', exist_ok=True)
os.makedirs('./static/css', exist_ok=True)
os.makedirs('./static/js', exist_ok=True)

DB_FILE = "./data/edbz.db"
CONFIG_FILE = "./data/emule_config.json"
KEY_FILE = "./data/.emule_key"

# Configuration eMule/aMule - À PERSONNALISER
EMULE_CONFIG = {
    'enabled': False,  # Mettre True pour activer
    'type': 'amule',  # 'emule' ou 'amule'
    'host': '127.0.0.1',
    'port': 4711,  # Port interface web (non utilisé pour amule EC)
    'ec_port': 4712,  # Port External Connections pour aMule
    'password': ''  # Mot de passe admin / EC
}

def get_or_create_key():
    """Génère ou récupère la clé de chiffrement"""
    try:
        from cryptography.fernet import Fernet
        import os
        
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(KEY_FILE, 'wb') as f:
                f.write(key)
            print(f"✓ Clé de chiffrement générée dans {KEY_FILE}")
            return key
    except ImportError:
        print("⚠️ Module cryptography non installé. Mot de passe non chiffré.")
        return None

def encrypt_password(password):
    """Chiffre le mot de passe"""
    if not password:
        return ''
    try:
        from cryptography.fernet import Fernet
        key = get_or_create_key()
        if key:
            f = Fernet(key)
            return f.encrypt(password.encode()).decode()
        return password
    except:
        return password

def decrypt_password(encrypted_password):
    """Déchiffre le mot de passe"""
    if not encrypted_password:
        return ''
    try:
        from cryptography.fernet import Fernet
        key = get_or_create_key()
        if key:
            f = Fernet(key)
            return f.decrypt(encrypted_password.encode()).decode()
        return encrypted_password
    except:
        return encrypted_password

def load_emule_config():
    """Charge la configuration depuis le fichier JSON"""
    global EMULE_CONFIG
    try:
        import json
        import os
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                # Déchiffre le mot de passe
                if 'password' in saved_config:
                    saved_config['password'] = decrypt_password(saved_config['password'])
                EMULE_CONFIG.update(saved_config)
                print(f"✓ Configuration aMule chargée depuis {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️ Impossible de charger la config: {e}")

def save_emule_config():
    """Sauvegarde la configuration dans le fichier JSON"""
    try:
        import json
        # Copie de la config avec mot de passe chiffré
        config_to_save = EMULE_CONFIG.copy()
        config_to_save['password'] = encrypt_password(EMULE_CONFIG['password'])
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_to_save, f, indent=4)
        print(f"✓ Configuration aMule sauvegardée dans {CONFIG_FILE} (mot de passe chiffré)")
        return True
    except Exception as e:
        print(f"✗ Erreur lors de la sauvegarde: {e}")
        return False

# Charge la config au démarrage
load_emule_config()

@app.route('/')
def index():
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    
    # Compte total des liens
    cursor.execute("SELECT COUNT(*) FROM ed2k_links")
    total_links = cursor.fetchone()[0]
    
    # Compte total des threads uniques
    cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM ed2k_links")
    total_threads = cursor.fetchone()[0]
    
    # Récupère les catégories uniques
    cursor.execute("SELECT DISTINCT forum_category FROM ed2k_links WHERE forum_category IS NOT NULL")
    categories = [row[0] for row in cursor.fetchall()]
    
    connection.close()
    
    return render_template('index.html', 
                         total_links=total_links,
                         total_threads=total_threads,
                         categories=categories)

@app.route('/api/search')
def search():
    query = request.args.get('query', '')
    volume = request.args.get('volume', '')
    category = request.args.get('category', '')
    
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    sql = "SELECT * FROM ed2k_links WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (filename LIKE ? OR thread_title LIKE ?)"
        search_term = f"%{query}%"
        params.extend([search_term, search_term])
    
    if volume:
        sql += " AND volume = ?"
        params.append(int(volume))
    
    if category:
        sql += " AND forum_category = ?"
        params.append(category)
    
    sql += " ORDER BY thread_title, volume, filename"
    
    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    connection.close()
    
    return jsonify({'results': results})

@app.route('/covers/<path:filename>')
def serve_cover(filename):
    return send_from_directory('./data/covers', filename)

@app.route('/api/emule/add', methods=['POST'])
def emule_add():
    if not EMULE_CONFIG['enabled']:
        return jsonify({'success': False, 'error': 'aMule non activé'}), 400
    
    try:
        data = request.get_json()
        link = data.get('link')
        
        if not link:
            return jsonify({'success': False, 'error': 'Aucun lien fourni'}), 400
        
        if EMULE_CONFIG['type'] == 'amule':
            import subprocess
            
            try:
                # Essaie d'abord avec amulecmd
                cmd = [
                    'amulecmd',
                    '-h', EMULE_CONFIG['host'],
                    '-P', EMULE_CONFIG['password'],
                    '-p', str(EMULE_CONFIG['ec_port']),
                    '-c', f'add {link}'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    return jsonify({'success': True})
                else:
                    print(f"[ERROR] amulecmd failed: {result.stderr}")
                    raise Exception(result.stderr)
            except FileNotFoundError:
                print("[WARNING] amulecmd non trouvé, utilisation du protocole EC")
                # Fallback: utilise le protocole EC binaire simplifié
                return add_link_ec_protocol(link)
            except Exception as e:
                print(f"[ERROR] {str(e)}")
                return jsonify({'success': False, 'error': str(e)}), 500
        else:
            # eMule classique via interface web
            import requests
            from urllib.parse import quote
            
            encoded_link = quote(link, safe='')
            auth = None
            if EMULE_CONFIG['password']:
                auth = ('', EMULE_CONFIG['password'])
            
            emule_url = f"http://{EMULE_CONFIG['host']}:{EMULE_CONFIG['port']}/?"
            emule_url += f"ses=&w=&cat=0&c=ed2k&p={encoded_link}"
            
            response = requests.get(emule_url, auth=auth, timeout=10)
            
            if response.status_code == 200:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': f'HTTP {response.status_code}'}), 500
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def add_link_ec_protocol(link):
    """Ajoute un lien via le protocole EC binaire d'aMule"""
    import socket
    import struct
    import hashlib
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((EMULE_CONFIG['host'], EMULE_CONFIG['ec_port']))
        
        # Calcul du hash du mot de passe
        password_hash = hashlib.md5(EMULE_CONFIG['password'].encode()).hexdigest()
        
        # Construction du paquet EC2 pour ajouter un lien
        link_bytes = link.encode('utf-8')
        
        # Paquet simple: opcode + longueur + lien
        packet = struct.pack('!BB', 0x20, 0x15)  # FLAGS_ZLIB=0x20, EC_OP_ADD_LINK=0x15
        packet += struct.pack('!H', len(link_bytes))
        packet += link_bytes
        
        # Envoie le paquet
        sock.send(packet)
        
        # Attend la réponse
        response = sock.recv(1024)
        sock.close()
        
        print(f"[DEBUG] Réponse EC (hex): {response.hex()}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR] Protocole EC: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/emule/add-multiple', methods=['POST'])
def emule_add_multiple():
    if not EMULE_CONFIG['enabled']:
        return jsonify({'success': False, 'error': 'eMule/aMule non configuré'}), 400
    
    try:
        data = request.get_json()
        links = data.get('links', [])
        
        if not links:
            return jsonify({'success': False, 'error': 'Aucun lien fourni'}), 400
        
        sent = 0
        failed = 0
        
        if EMULE_CONFIG['type'] == 'amule':
            import subprocess
            
            print(f"[DEBUG] Envoi de {len(links)} liens via amulecmd...")
            
            for i, link in enumerate(links, 1):
                try:
                    cmd = [
                        'amulecmd',
                        '-h', EMULE_CONFIG['host'],
                        '-P', EMULE_CONFIG['password'],
                        '-p', str(EMULE_CONFIG['ec_port']),
                        '-c', f'add {link}'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        sent += 1
                        print(f"[DEBUG] [{i}/{len(links)}] ✓")
                    else:
                        failed += 1
                        print(f"[DEBUG] [{i}/{len(links)}] ✗ {result.stderr[:50]}")
                except Exception as e:
                    failed += 1
                    print(f"[DEBUG] [{i}/{len(links)}] ✗ Exception: {str(e)}")
        else:
            # eMule classique
            import requests
            from urllib.parse import quote
            
            auth = None
            if EMULE_CONFIG['password']:
                auth = ('', EMULE_CONFIG['password'])
            
            for link in links:
                try:
                    encoded_link = quote(link, safe='')
                    emule_url = f"http://{EMULE_CONFIG['host']}:{EMULE_CONFIG['port']}/?"
                    emule_url += f"ses=&w=&cat=0&c=ed2k&p={encoded_link}"
                    
                    response = requests.get(emule_url, auth=auth, timeout=10)
                    
                    if response.status_code == 200:
                        sent += 1
                    else:
                        failed += 1
                except:
                    failed += 1
        
        print(f"[DEBUG] Résultat final: {sent} envoyés, {failed} échecs")
        return jsonify({'success': True, 'sent': sent, 'failed': failed})
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/emule/config', methods=['GET', 'POST'])
def emule_config():
    global EMULE_CONFIG
    
    if request.method == 'GET':
        # Retourne la config actuelle (sans le mot de passe en clair)
        return jsonify({
            'enabled': EMULE_CONFIG['enabled'],
            'type': EMULE_CONFIG['type'],
            'host': EMULE_CONFIG['host'],
            'ec_port': EMULE_CONFIG['ec_port'],
            'password': '****' if EMULE_CONFIG['password'] else ''
        })
    else:
        # Sauvegarde la nouvelle config
        try:
            new_config = request.get_json()
            
            EMULE_CONFIG['enabled'] = new_config.get('enabled', False)
            EMULE_CONFIG['type'] = new_config.get('type', 'amule')
            EMULE_CONFIG['host'] = new_config.get('host', '127.0.0.1')
            EMULE_CONFIG['ec_port'] = new_config.get('ec_port', 4712)
            
            # Ne change le mot de passe que s'il n'est pas masqué
            new_password = new_config.get('password', '')
            if new_password and new_password != '****':
                EMULE_CONFIG['password'] = new_password
            
            # Sauvegarde dans le fichier
            if save_emule_config():
                return jsonify({'success': True, 'message': 'Configuration sauvegardée'})
            else:
                return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/emule/test', methods=['GET'])
def emule_test():
    if not EMULE_CONFIG['enabled']:
        return jsonify({'success': False, 'error': 'aMule non activé'}), 400
    
    try:
        import subprocess
        
        # Test avec amulecmd
        cmd = [
            'amulecmd',
            '-h', EMULE_CONFIG['host'],
            '-P', EMULE_CONFIG['password'],
            '-p', str(EMULE_CONFIG['ec_port']),
            '-c', 'status'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Connexion réussie'})
        else:
            return jsonify({'success': False, 'error': result.stderr}), 500
            
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'amulecmd introuvable. Installez amule-utils'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    import os
    
    if not os.path.exists(DB_FILE):
        print("=" * 60)
        print("❌ ERREUR : Le fichier edbz.db est introuvable !")
        print("=" * 60)
        print("\nAssure-toi que :")
        print("1. Le fichier edbz.db existe")
        print("2. Il est dans le même dossier que ce script")
        print("3. Le scraper a bien créé la base de données")
        print("=" * 60)
        input("\nAppuie sur Entrée pour quitter...")
        exit(1)
    
    print("=" * 60)
    print("🚀 Serveur de recherche ed2k démarré !")
    print("=" * 60)
    print("\n📍 Ouvre ton navigateur et va sur :")
    print("   http://localhost:8080")
    print("   ou http://127.0.0.1:8080")
    print("\n⏹️  Pour arrêter le serveur : Ctrl+C")
    print("=" * 60 + "\n")
    
    try:
        app.run(debug=False, host='127.0.0.1', port=8080, use_reloader=False)
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        input("\nAppuie sur Entrée pour quitter...")
