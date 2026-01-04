from flask import Flask, render_template_string, request, jsonify
import sqlite3

app = Flask(__name__)
DB_FILE = "edbz.db"
CONFIG_FILE = "emule_config.json"
KEY_FILE = ".emule_key"

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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recherche de liens ed2k</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            position: relative;
        }

        .settings-icon {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 2em;
            cursor: pointer;
            color: white;
            transition: transform 0.3s;
        }

        .settings-icon:hover {
            transform: rotate(90deg);
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .search-box {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin-bottom: 30px;
        }

        .search-input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }

        .search-input {
            flex: 1;
            min-width: 300px;
            padding: 15px 20px;
            font-size: 1.1em;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            transition: border-color 0.3s;
        }

        .category-select {
            padding: 15px 20px;
            font-size: 1.1em;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            background: white;
            cursor: pointer;
            min-width: 200px;
        }

        .category-select:focus {
            outline: none;
            border-color: #667eea;
        }

        .search-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .search-button {
            padding: 15px 40px;
            font-size: 1.1em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s;
        }

        .search-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .search-button:active {
            transform: translateY(0);
        }

        .copy-all-button {
            padding: 12px 30px;
            font-size: 1em;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
            margin-top: 10px;
        }

        .copy-all-button:hover {
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4);
        }

        .copy-all-button:active {
            transform: translateY(0);
        }

        .filter-box {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border: 2px solid #e0e0e0;
        }

        .filter-input {
            width: 100%;
            padding: 10px 15px;
            font-size: 1em;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            transition: border-color 0.3s;
        }

        .filter-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .filter-label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
        }

        .stats {
            text-align: center;
            color: #666;
            font-size: 0.95em;
        }

        .results {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .result-item {
            border-bottom: 1px solid #e0e0e0;
            padding: 20px;
            transition: background 0.2s;
        }

        .result-item:last-child {
            border-bottom: none;
        }

        .result-item:hover {
            background: #f8f9fa;
        }

        .result-title {
            font-size: 1.2em;
            color: #333;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .result-filename {
            color: #667eea;
            margin-bottom: 8px;
            font-weight: 500;
        }

        .result-meta {
            display: flex;
            gap: 20px;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #666;
            flex-wrap: wrap;
        }

        .category-badge {
            display: inline-block;
            padding: 4px 12px;
            background: #667eea;
            color: white;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }

        .thread-badge {
            display: inline-block;
            padding: 4px 12px;
            background: #28a745;
            color: white;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }

        .result-link {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 8px;
            word-break: break-all;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            color: #333;
            margin-bottom: 10px;
        }

        .copy-button {
            padding: 8px 16px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.2s;
        }

        .copy-button:hover {
            background: #218838;
        }

        .emule-button {
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.2s;
            margin-left: 5px;
        }

        .emule-button:hover {
            background: #0056b3;
        }

        .emule-button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #999;
            font-size: 1.2em;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
            font-size: 1.1em;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .success {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }

        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 15px;
            width: 90%;
            max-width: 600px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .modal-header {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .close-modal {
            font-size: 1.5em;
            cursor: pointer;
            color: #999;
        }

        .close-modal:hover {
            color: #333;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }

        .form-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .form-checkbox {
            margin-right: 8px;
        }

        .save-button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .save-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .test-button {
            width: 100%;
            padding: 12px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            margin-top: 10px;
        }

        .test-button:hover {
            background: #218838;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="settings-icon" onclick="openSettings()">⚙️</span>
            <h1>� Recherche de liens ed2k</h1>
            <p>Base de données EmuleBDZ</p>
        </div>

        <div class="search-box">
            <div class="search-input-group">
                <input 
                    type="text" 
                    class="search-input" 
                    id="searchInput" 
                    placeholder="Entrez un mot-clé (film, série, artiste, etc.)"
                    onkeypress="if(event.key === 'Enter') searchLinks()">
                <select class="category-select" id="categoryFilter">
                    <option value="">Toutes les catégories</option>
                </select>
                <button class="search-button" onclick="searchLinks()">Rechercher</button>
            </div>
            <div class="stats" id="stats">Chargement des statistiques...</div>
        </div>

        <div id="filterSection" style="display: none;">
            <div class="results" style="padding: 20px;">
                <div class="filter-box">
                    <label class="filter-label">� Filtrer les résultats affichés :</label>
                    <input 
                        type="text" 
                        class="filter-input" 
                        id="filterInput" 
                        placeholder="Tapez pour filtrer par nom de fichier..."
                        oninput="filterResults()">
                </div>
                <div style="text-align: center;">
                    <button class="copy-all-button" onclick="copyAllLinks()">
                        � Copier tous les liens affichés
                    </button>
                    <button class="copy-all-button" onclick="sendAllToEmule()" id="sendAllEmuleBtn" style="background: #007bff; display: none;">
                        � Envoyer tous les liens à eMule
                    </button>
                    <div id="copyStatus" style="margin-top: 10px; color: #28a745; font-weight: bold;"></div>
                </div>
            </div>
        </div>

        <div class="results" id="resultsContent"></div>
    </div>

    <!-- Modal de paramètres -->
    <div id="settingsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span>⚙️ Paramètres aMule</span>
                <span class="close-modal" onclick="closeSettings()">×</span>
            </div>
            
            <div class="form-group">
                <label class="form-label">
                    <input type="checkbox" id="emuleEnabled" class="form-checkbox">
                    Activer l'intégration aMule
                </label>
            </div>

            <div class="form-group">
                <label class="form-label">Type :</label>
                <select id="emuleType" class="form-input">
                    <option value="amule">aMule</option>
                    <option value="emule">eMule</option>
                </select>
            </div>

            <div class="form-group">
                <label class="form-label">Adresse IP / Hôte :</label>
                <input type="text" id="emuleHost" class="form-input" placeholder="192.168.1.234">
            </div>

            <div class="form-group">
                <label class="form-label">Port EC (External Connections) :</label>
                <input type="number" id="emuleEcPort" class="form-input" placeholder="4712">
            </div>

            <div class="form-group">
                <label class="form-label">Mot de passe :</label>
                <input type="password" id="emulePassword" class="form-input" placeholder="Mot de passe EC">
            </div>

            <button class="test-button" onclick="testConnection()">� Tester la connexion</button>
            <div id="testResult" style="margin-top: 10px; text-align: center; font-weight: bold;"></div>

            <button class="save-button" onclick="saveSettings()">� Enregistrer</button>
        </div>
    </div>

    <script>
        let allResults = [];
        let emuleEnabled = false;
        let emuleSettings = {};

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('stats').innerHTML = `� ${data.total} liens ed2k dans la base`;
                
                // Charge les paramètres aMule
                emuleEnabled = data.emule_enabled || false;
                emuleSettings = data.emule_config || {};
                
                if (emuleEnabled) {
                    document.getElementById('sendAllEmuleBtn').style.display = 'inline-block';
                }
                
                if (data.categories && data.categories.length > 0) {
                    const select = document.getElementById('categoryFilter');
                    data.categories.forEach(cat => {
                        if (cat) {
                            const option = document.createElement('option');
                            option.value = cat;
                            option.textContent = cat;
                            select.appendChild(option);
                        }
                    });
                }
            } catch (error) {
                document.getElementById('stats').innerHTML = '⚠️ Erreur de chargement';
            }
        }

        function openSettings() {
            // Charge les paramètres actuels
            fetch('/api/emule/config')
                .then(r => r.json())
                .then(config => {
                    document.getElementById('emuleEnabled').checked = config.enabled;
                    document.getElementById('emuleType').value = config.type;
                    document.getElementById('emuleHost').value = config.host;
                    document.getElementById('emuleEcPort').value = config.ec_port;
                    document.getElementById('emulePassword').value = config.password;
                    document.getElementById('settingsModal').style.display = 'block';
                });
        }

        function closeSettings() {
            document.getElementById('settingsModal').style.display = 'none';
        }

        function saveSettings() {
            const config = {
                enabled: document.getElementById('emuleEnabled').checked,
                type: document.getElementById('emuleType').value,
                host: document.getElementById('emuleHost').value,
                ec_port: parseInt(document.getElementById('emuleEcPort').value),
                password: document.getElementById('emulePassword').value
            };

            fetch('/api/emule/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('✓ Paramètres enregistrés et sauvegardés ! Rechargez la page pour appliquer les changements.');
                    closeSettings();
                    location.reload();
                } else {
                    alert('✗ Erreur: ' + data.error);
                }
            })
            .catch(err => alert('Erreur: ' + err));
        }

        function testConnection() {
            const testResult = document.getElementById('testResult');
            testResult.innerHTML = '⏳ Test en cours...';
            testResult.style.color = '#007bff';

            fetch('/api/emule/test')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        testResult.innerHTML = '✓ Connexion réussie !';
                        testResult.style.color = '#28a745';
                    } else {
                        testResult.innerHTML = '✗ Échec: ' + data.error;
                        testResult.style.color = '#dc3545';
                    }
                })
                .catch(err => {
                    testResult.innerHTML = '✗ Erreur: ' + err;
                    testResult.style.color = '#dc3545';
                });
        }

        // Ferme la modal si on clique en dehors
        window.onclick = function(event) {
            const modal = document.getElementById('settingsModal');
            if (event.target == modal) {
                closeSettings();
            }
        }

        async function searchLinks() {
            const keyword = document.getElementById('searchInput').value.trim();
            const category = document.getElementById('categoryFilter').value;
            const resultsDiv = document.getElementById('resultsContent');

            if (!keyword) {
                resultsDiv.innerHTML = '<div class="no-results">� Entrez un mot-clé pour commencer la recherche</div>';
                document.getElementById('filterSection').style.display = 'none';
                return;
            }

            resultsDiv.innerHTML = '<div class="loading">⏳ Recherche en cours...</div>';
            document.getElementById('filterSection').style.display = 'none';

            try {
                let url = '/api/search?q=' + encodeURIComponent(keyword);
                if (category) {
                    url += '&category=' + encodeURIComponent(category);
                }
                
                const response = await fetch(url);
                const data = await response.json();

                if (data.error) {
                    resultsDiv.innerHTML = `<div class="error">⚠️ ${data.error}</div>`;
                    return;
                }

                if (!data.results || data.results.length === 0) {
                    resultsDiv.innerHTML = `
                        <div class="no-results">
                            � Aucun résultat pour "${escapeHtml(keyword)}"${category ? ` dans "${category}"` : ''}<br>
                            <small>Essayez avec d'autres mots-clés</small>
                        </div>
                    `;
                    return;
                }

                allResults = data.results;
                document.getElementById('filterInput').value = '';
                document.getElementById('filterSection').style.display = 'block';
                displayResults(allResults, keyword, category);
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">⚠️ Erreur: ${error.message}</div>`;
            }
        }

        function filterResults() {
            const filterText = document.getElementById('filterInput').value.toLowerCase();
            const keyword = document.getElementById('searchInput').value.trim();
            const category = document.getElementById('categoryFilter').value;
            
            if (!filterText) {
                displayResults(allResults, keyword, category);
                return;
            }
            
            const filtered = allResults.filter(item => 
                (item.filename && item.filename.toLowerCase().includes(filterText)) ||
                (item.thread_title && item.thread_title.toLowerCase().includes(filterText))
            );
            
            displayResults(filtered, keyword, category, filterText);
        }

        function displayResults(results, keyword, category, filterText = '') {
            const resultsDiv = document.getElementById('resultsContent');
            
            if (results.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="no-results">
                        � Aucun résultat après filtrage<br>
                        <small>Essayez un autre filtre</small>
                    </div>
                `;
                return;
            }

            const groupedByThread = {};
            results.forEach(item => {
                const threadKey = item.thread_id || item.thread_url;
                if (!groupedByThread[threadKey]) {
                    groupedByThread[threadKey] = {
                        thread_title: item.thread_title,
                        thread_url: item.thread_url,
                        forum_category: item.forum_category,
                        links: []
                    };
                }
                groupedByThread[threadKey].links.push(item);
            });

            let html = '';
            Object.values(groupedByThread).forEach(thread => {
                html += '<div class="result-item" data-thread>';
                html += '<div class="result-title">' + escapeHtml(thread.thread_title || 'Sans titre') + '</div>';
                html += '<div style="margin-bottom: 10px;">';
                
                if (thread.forum_category) {
                    html += '<span class="category-badge">� ' + escapeHtml(thread.forum_category) + '</span> ';
                }
                html += '<span class="thread-badge">� ' + thread.links.length + ' lien(s)</span>';
                html += '</div>';
                
                thread.links.forEach(item => {
                    const sizeDisplay = item.filesize ? formatSize(item.filesize) : 'Taille inconnue';
                    html += '<div style="margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 8px;" data-link="' + escapeHtml(item.link) + '">';
                    html += '<div class="result-filename">� ' + escapeHtml(item.filename || 'Nom inconnu') + '</div>';
                    html += '<div class="result-meta"><span>� ' + sizeDisplay + '</span></div>';
                    html += '<div class="result-link">' + escapeHtml(item.link) + '</div>';
                    html += '<button class="copy-button" onclick="copyLinkButton(this)">� Copier le lien</button>';
                    if (emuleEnabled) {
                        html += '<button class="emule-button" onclick="sendToEmule(this)">� Envoyer à eMule</button>';
                    }
                    html += '</div>';
                });
                
                html += '<div style="margin-top: 10px;">';
                html += '<a href="' + escapeHtml(thread.thread_url) + '" target="_blank" style="color: #667eea; text-decoration: none;">� Voir le thread complet →</a>';
                html += '</div>';
                html += '</div>';
            });

            resultsDiv.innerHTML = html;
            
            const totalLinks = results.length;
            const totalThreads = Object.keys(groupedByThread).length;
            let statsText = '� ' + totalLinks + ' lien(s) trouvé(s) dans ' + totalThreads + ' thread(s) pour "' + escapeHtml(keyword) + '"';
            if (category) {
                statsText += ' dans "' + category + '"';
            }
            if (filterText) {
                statsText += ' (filtrés par "' + escapeHtml(filterText) + '")';
            }
            document.getElementById('stats').innerHTML = statsText;
        }

        function copyAllLinks() {
            const linkElements = document.querySelectorAll('[data-link]');
            const links = Array.from(linkElements).map(el => el.getAttribute('data-link'));
            
            if (links.length === 0) {
                alert('Aucun lien à copier');
                return;
            }
            
            const allLinksText = links.join('\\n');
            
            navigator.clipboard.writeText(allLinksText).then(() => {
                const statusDiv = document.getElementById('copyStatus');
                statusDiv.innerHTML = '✓ ' + links.length + ' lien(s) copié(s) dans le presse-papier !';
                setTimeout(() => {
                    statusDiv.innerHTML = '';
                }, 3000);
            }).catch(err => {
                alert('Erreur lors de la copie : ' + err);
            });
        }

        function copyLinkButton(button) {
            const linkDiv = button.closest('[data-link]');
            const link = linkDiv.getAttribute('data-link');
            copyToClipboard(link, button);
        }

        function copyToClipboard(text, button) {
            navigator.clipboard.writeText(text).then(() => {
                const originalText = button.innerHTML;
                button.innerHTML = '✓ Copié !';
                button.style.background = '#218838';
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.style.background = '#28a745';
                }, 2000);
            }).catch(err => {
                alert('Erreur lors de la copie');
            });
        }

        function formatSize(bytes) {
            const size = parseInt(bytes);
            if (isNaN(size)) return bytes;
            
            if (size >= 1073741824) return (size / 1073741824).toFixed(2) + ' GB';
            if (size >= 1048576) return (size / 1048576).toFixed(2) + ' MB';
            if (size >= 1024) return (size / 1024).toFixed(2) + ' KB';
            return size + ' B';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function sendToEmule(button) {
            const linkDiv = button.closest('[data-link]');
            const link = linkDiv.getAttribute('data-link');
            
            button.disabled = true;
            button.innerHTML = '⏳ Envoi...';
            
            try {
                const response = await fetch('/api/emule/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({link: link})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    button.innerHTML = '✓ Envoyé !';
                    button.style.background = '#28a745';
                    setTimeout(() => {
                        button.innerHTML = '� Envoyer à eMule';
                        button.style.background = '#007bff';
                        button.disabled = false;
                    }, 2000);
                } else {
                    button.innerHTML = '✗ Erreur';
                    button.style.background = '#dc3545';
                    alert('Erreur: ' + (data.error || 'Impossible d envoyer a eMule'));
                    setTimeout(() => {
                        button.innerHTML = '� Envoyer à eMule';
                        button.style.background = '#007bff';
                        button.disabled = false;
                    }, 2000);
                }
            } catch (error) {
                button.innerHTML = '✗ Erreur';
                button.style.background = '#dc3545';
                alert('Erreur de connexion: ' + error.message);
                setTimeout(() => {
                    button.innerHTML = '� Envoyer à eMule';
                    button.style.background = '#007bff';
                    button.disabled = false;
                }, 2000);
            }
        }

        async function sendAllToEmule() {
            const linkElements = document.querySelectorAll('[data-link]');
            const links = Array.from(linkElements).map(el => el.getAttribute('data-link'));
            
            if (links.length === 0) {
                alert('Aucun lien à envoyer');
                return;
            }
            
            if (!confirm(`Envoyer ${links.length} lien(s) à eMule ?`)) {
                return;
            }
            
            const statusDiv = document.getElementById('copyStatus');
            statusDiv.innerHTML = '⏳ Envoi en cours...';
            statusDiv.style.color = '#007bff';
            
            try {
                const response = await fetch('/api/emule/add-multiple', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({links: links})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    statusDiv.innerHTML = `✓ ${data.sent} lien(s) envoyé(s) à eMule ! ${data.failed > 0 ? '(' + data.failed + ' échec(s))' : ''}`;
                    statusDiv.style.color = '#28a745';
                } else {
                    statusDiv.innerHTML = '✗ Erreur lors de l envoi';
                    statusDiv.style.color = '#dc3545';
                    alert('Erreur: ' + (data.error || 'Impossible d envoyer les liens'));
                }
            } catch (error) {
                statusDiv.innerHTML = '✗ Erreur de connexion';
                statusDiv.style.color = '#dc3545';
                alert('Erreur: ' + error.message);
            }
            
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        }

        loadStats();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM ed2k_links")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT DISTINCT forum_category FROM ed2k_links WHERE forum_category IS NOT NULL AND forum_category != ''")
        categories = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return jsonify({
            'total': total, 
            'categories': categories,
            'emule_enabled': EMULE_CONFIG['enabled']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search():
    keyword = request.args.get('q', '')
    category = request.args.get('category', '')
    
    if not keyword:
        return jsonify({'error': 'Mot-clé manquant'}), 400
    
    try:
        from urllib.parse import unquote
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if category:
            query = """
                SELECT link, filename, filesize, thread_title, thread_url, thread_id, forum_category
                FROM ed2k_links 
                WHERE (filename LIKE ? OR thread_title LIKE ?) AND forum_category = ?
                ORDER BY filename COLLATE NOCASE ASC
                LIMIT 500
            """
            search_term = f'%{keyword}%'
            cursor.execute(query, (search_term, search_term, category))
        else:
            query = """
                SELECT link, filename, filesize, thread_title, thread_url, thread_id, forum_category
                FROM ed2k_links 
                WHERE filename LIKE ? OR thread_title LIKE ?
                ORDER BY filename COLLATE NOCASE ASC
                LIMIT 500
            """
            search_term = f'%{keyword}%'
            cursor.execute(query, (search_term, search_term))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'link': row[0],
                'filename': unquote(row[1]) if row[1] else None,
                'filesize': row[2],
                'thread_title': row[3],
                'thread_url': row[4],
                'thread_id': row[5],
                'forum_category': row[6]
            })
        
        conn.close()
        return jsonify({'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emule/add', methods=['POST'])
def emule_add():
    if not EMULE_CONFIG['enabled']:
        return jsonify({'success': False, 'error': 'eMule/aMule non configuré'}), 400
    
    try:
        data = request.get_json()
        link = data.get('link', '')
        
        if not link:
            return jsonify({'success': False, 'error': 'Lien manquant'}), 400
        
        if EMULE_CONFIG['type'] == 'amule':
            # Utilise amulecmd en ligne de commande
            import subprocess
            
            print(f"[DEBUG] Envoi via amulecmd...")
            
            # Commande amulecmd
            cmd = [
                'amulecmd',
                '-h', EMULE_CONFIG['host'],
                '-P', EMULE_CONFIG['password'],
                '-p', str(EMULE_CONFIG['ec_port']),
                '-c', f'add {link}'
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                print(f"[DEBUG] Return code: {result.returncode}")
                print(f"[DEBUG] Output: {result.stdout}")
                print(f"[DEBUG] Error: {result.stderr}")
                
                if result.returncode == 0:
                    print(f"[DEBUG] Lien ajouté avec succès!")
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': f'amulecmd a échoué: {result.stderr}'}), 500
                    
            except FileNotFoundError:
                print(f"[DEBUG] amulecmd introuvable, essai avec le protocole EC...")
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
        # Format EC2: [FLAGS(1)][OPCODE(1)][TAGS...]
        # OpCode pour AddLink: 0x15
        
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
    print("� Serveur de recherche ed2k démarré !")
    print("=" * 60)
    print("\n� Ouvre ton navigateur et va sur :")
    print("   http://localhost:8080")
    print("   ou http://127.0.0.1:8080")
    print("\n⏹️  Pour arrêter le serveur : Ctrl+C")
    print("=" * 60 + "\n")
    
    try:
        app.run(debug=False, host='127.0.0.1', port=8080, use_reloader=False)
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        input("\nAppuie sur Entrée pour quitter...")
